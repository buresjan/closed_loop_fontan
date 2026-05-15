#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.calibration.objective import load_json

RHO_KG_M3 = 1060.0
MU_PA_S = 0.0035
AORTIC_WAVE_SPEED_M_S = 5.35
FONTAN_WAVE_SPEED_M_S = 2.81

AORTA_GEOMETRY = ROOT / "data/processed/aramburu_2024/model_inputs/aorta_geometry.csv"
FONTAN_GEOMETRY = ROOT / "data/processed/aramburu_2024/model_inputs/fontan_cross_geometry.csv"
TARGET_POLICY = ROOT / "data/processed/aramburu_2024/targets/target_policy.csv"
FULL_0D_BASELINE = ROOT / "models/full_0d/configs/fontan_0d_baseline.jsonc"
PRIORS_OUT = ROOT / "models/quasi_0d_1d/calibration/parameter_priors.yaml"
FRAGMENT_OUT = ROOT / "models/quasi_0d_1d/config_fragments/quasi_vessel_chains.json"

UNITS = {
    "length_m": "m",
    "radius_m": "m",
    "area_m2": "m^2",
    "resistance_pa_s_m3": "Pa*s/m^3",
    "inertance_pa_s2_m3": "Pa*s^2/m^3",
    "capacitance_m3_pa": "m^3/Pa",
    "wave_speed_m_s": "m/s",
    "density_kg_m3": "kg/m^3",
    "dynamic_viscosity_pa_s": "Pa*s",
}


@dataclass(frozen=True)
class ChainSpec:
    key: str
    label: str
    geometry_source: str
    source_segments: tuple[str, ...]
    inlet_node: str
    outlet_node: str
    segment_count: int
    wave_speed_m_s: float
    selected_resistance_source: str


CHAIN_SPECS = [
    ChainSpec(
        "aao_arch",
        "AAo/arch quasi chain",
        "aorta_geometry.csv",
        ("Ascending aorta",),
        "aao",
        "aortic_arch",
        4,
        AORTIC_WAVE_SPEED_M_S,
        "geometry_poiseuille",
    ),
    ChainSpec(
        "dao",
        "DAo quasi chain",
        "aorta_geometry.csv",
        ("Thoracic aorta",),
        "aortic_arch",
        "dao",
        6,
        AORTIC_WAVE_SPEED_M_S,
        "geometry_poiseuille",
    ),
    ChainSpec(
        "svc",
        "SVC quasi chain",
        "fontan_cross_geometry.csv",
        ("SVC",),
        "svc",
        "tcpc",
        3,
        FONTAN_WAVE_SPEED_M_S,
        "calibrated_full_0d_pathway",
    ),
    ChainSpec(
        "ivc",
        "IVC quasi chain",
        "fontan_cross_geometry.csv",
        ("IVC",),
        "ivc",
        "tcpc",
        5,
        FONTAN_WAVE_SPEED_M_S,
        "calibrated_full_0d_pathway",
    ),
    ChainSpec(
        "rpa",
        "RPA quasi chain",
        "fontan_cross_geometry.csv",
        ("RPA",),
        "tcpc",
        "rpa",
        3,
        FONTAN_WAVE_SPEED_M_S,
        "calibrated_full_0d_pathway",
    ),
    ChainSpec(
        "lpa",
        "LPA quasi chain",
        "fontan_cross_geometry.csv",
        ("LPA I", "LPA II"),
        "tcpc",
        "lpa",
        4,
        FONTAN_WAVE_SPEED_M_S,
        "calibrated_full_0d_pathway",
    ),
]


def read_geometry(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df = df[df["segment_name"].notna()]
    df = df[df["segment_name"] != "-"]
    for column in ["length_m", "radius_in_m", "radius_out_m"]:
        df[column] = pd.to_numeric(df[column], errors="coerce")
    return df[df["length_m"].notna()].copy()


def area(radius_m: float) -> float:
    return math.pi * radius_m**2


def average_area(radius_in_m: float, radius_out_m: float) -> float:
    return 0.5 * (area(radius_in_m) + area(radius_out_m))


def poiseuille_resistance_tapered(
    length_m: float,
    radius_in_m: float,
    radius_out_m: float,
    dynamic_viscosity_pa_s: float = MU_PA_S,
) -> float:
    if math.isclose(radius_in_m, radius_out_m, rel_tol=1e-12, abs_tol=1e-15):
        integral = length_m / radius_in_m**4
    else:
        integral = (
            length_m
            / (3.0 * (radius_out_m - radius_in_m))
            * (1.0 / radius_in_m**3 - 1.0 / radius_out_m**3)
        )
    return 8.0 * dynamic_viscosity_pa_s * integral / math.pi


def inertance(length_m: float, area_bar_m2: float, density_kg_m3: float = RHO_KG_M3) -> float:
    return density_kg_m3 * length_m / area_bar_m2


def compliance(
    length_m: float,
    area_bar_m2: float,
    wave_speed_m_s: float,
    density_kg_m3: float = RHO_KG_M3,
) -> float:
    return area_bar_m2 * length_m / (density_kg_m3 * wave_speed_m_s**2)


def allocate_counts(lengths: list[float], total_count: int) -> list[int]:
    if total_count < len(lengths):
        raise ValueError("total_count must be at least the number of source segments")
    total_length = sum(lengths)
    raw = [total_count * length / total_length for length in lengths]
    counts = [max(1, math.floor(value)) for value in raw]
    while sum(counts) < total_count:
        remainders = [value - math.floor(value) for value in raw]
        idx = max(range(len(counts)), key=lambda i: (remainders[i], lengths[i]))
        counts[idx] += 1
        raw[idx] = math.floor(raw[idx])
    while sum(counts) > total_count:
        idx = max(
            (i for i, count in enumerate(counts) if count > 1),
            key=lambda i: (counts[i], -lengths[i]),
        )
        counts[idx] -= 1
    return counts


def full_0d_pathway_resistance(params: dict[str, Any], key: str) -> float | None:
    if key in {"svc", "ivc"}:
        return (
            1.0 / float(params[f"{key}_conduit_rl.conductance"])
            + float(params[f"{key}_conduit_junction.resistance"])
        )
    if key in {"rpa", "lpa"}:
        return (
            1.0 / float(params[f"{key}_conduit_rl.conductance"])
            + float(params[f"{key}_conduit_out.resistance"])
        )
    if key == "aao_arch":
        return float(params["aao_arch.resistance"])
    if key == "dao":
        return float(params["arch_dao.resistance"])
    return None


def full_0d_compliance_prior(params: dict[str, Any], key: str) -> float | None:
    compliance_names = {
        "aao_arch": ["aao_compliance.capacitance", "aortic_arch_compliance.capacitance"],
        "dao": ["dao_compliance.capacitance"],
        "svc": ["svc_compliance.capacitance", "svc_conduit_compliance.capacitance"],
        "ivc": ["ivc_compliance.capacitance", "ivc_conduit_compliance.capacitance"],
        "rpa": ["rpa_compliance.capacitance", "rpa_conduit_compliance.capacitance"],
        "lpa": ["lpa_compliance.capacitance", "lpa_conduit_compliance.capacitance"],
    }
    names = compliance_names.get(key)
    if names is None:
        return None
    return sum(float(params[name]) for name in names)


def full_0d_inertance_prior(params: dict[str, Any], key: str) -> float | None:
    name = f"{key}_conduit_rl.inductance"
    if name in params:
        return float(params[name])
    return None


def source_rows_for_spec(spec: ChainSpec, aorta: pd.DataFrame, fontan: pd.DataFrame) -> pd.DataFrame:
    df = aorta if spec.geometry_source == "aorta_geometry.csv" else fontan
    rows = df[df["segment_name"].isin(spec.source_segments)].copy()
    if set(rows["segment_name"]) != set(spec.source_segments):
        missing = set(spec.source_segments) - set(rows["segment_name"])
        raise ValueError(f"{spec.key} missing geometry rows: {sorted(missing)}")
    order = {name: i for i, name in enumerate(spec.source_segments)}
    rows["order"] = rows["segment_name"].map(order)
    return rows.sort_values("order")


def cell_geometry(rows: pd.DataFrame, total_count: int) -> list[dict[str, Any]]:
    counts = allocate_counts([float(row.length_m) for row in rows.itertuples()], total_count)
    cells: list[dict[str, Any]] = []
    for row, count in zip(rows.itertuples(index=False), counts):
        length = float(row.length_m)
        radius_in = float(row.radius_in_m)
        radius_out = float(row.radius_out_m)
        for local_idx in range(count):
            x0 = local_idx / count
            x1 = (local_idx + 1) / count
            rin = radius_in + (radius_out - radius_in) * x0
            rout = radius_in + (radius_out - radius_in) * x1
            cells.append(
                {
                    "source_segment": str(row.segment_name),
                    "length_m": length / count,
                    "radius_in_m": rin,
                    "radius_out_m": rout,
                    "area_bar_m2": average_area(rin, rout),
                    "geometry_resistance_pa_s_m3": poiseuille_resistance_tapered(
                        length / count,
                        rin,
                        rout,
                    ),
                }
            )
    return cells


def distribute_selected_resistance(
    cells: list[dict[str, Any]],
    selected_total: float,
) -> list[float]:
    geometry_total = sum(float(cell["geometry_resistance_pa_s_m3"]) for cell in cells)
    return [
        selected_total * float(cell["geometry_resistance_pa_s_m3"]) / geometry_total
        for cell in cells
    ]


def chain_nodes(spec: ChainSpec) -> list[str]:
    internal = [
        f"quasi_{spec.key}_p_{i:02d}" for i in range(1, spec.segment_count)
    ]
    return [spec.inlet_node, *internal, spec.outlet_node]


def block_fragment_for_chain(
    spec: ChainSpec,
    cells: list[dict[str, Any]],
) -> dict[str, Any]:
    nodes = chain_nodes(spec)
    blocks: dict[str, Any] = {}
    parameters: dict[str, float] = {}
    variables_initialization: dict[str, float] = {}
    variables_magnitudes: dict[str, float] = {}
    for i, cell in enumerate(cells, start=1):
        rl_name = f"quasi_{spec.key}_rl_{i:02d}"
        c_name = f"quasi_{spec.key}_c_{i:02d}"
        upstream = nodes[i - 1]
        downstream = nodes[i]
        blocks[rl_name] = {
            "type": "block_description",
            "model_type": "hydraulic_rl_block",
            "time": "time",
            "flux_type": "blood_flow",
            "resistance": f"{rl_name}.resistance",
            "inductance": f"{rl_name}.inductance",
            "nodes": {"1": upstream, "2": downstream},
        }
        blocks[c_name] = {
            "type": "block_description",
            "model_type": "c_block",
            "time": "time",
            "flux_type": "blood_flow",
            "nodes": {"1": downstream},
        }
        parameters[f"{rl_name}.resistance"] = float(cell["resistance_pa_s_m3"])
        parameters[f"{rl_name}.inductance"] = float(cell["inertance_pa_s2_m3"])
        parameters[f"{c_name}.capacitance"] = float(cell["capacitance_m3_pa"])
        variables_initialization[f"{rl_name}.flux"] = 0.0
        variables_magnitudes[f"{rl_name}.flux"] = 0.001
    return {
        "nodes": nodes,
        "blocks": blocks,
        "parameters": parameters,
        "variables_initialization": variables_initialization,
        "variables_magnitudes": variables_magnitudes,
    }


def derive_chain(
    spec: ChainSpec,
    aorta: pd.DataFrame,
    fontan: pd.DataFrame,
    full_0d_params: dict[str, Any],
) -> dict[str, Any]:
    rows = source_rows_for_spec(spec, aorta, fontan)
    cells = cell_geometry(rows, spec.segment_count)
    for cell in cells:
        cell["inertance_pa_s2_m3"] = inertance(
            float(cell["length_m"]),
            float(cell["area_bar_m2"]),
        )
        cell["capacitance_m3_pa"] = compliance(
            float(cell["length_m"]),
            float(cell["area_bar_m2"]),
            spec.wave_speed_m_s,
        )

    geometry_resistance = sum(float(cell["geometry_resistance_pa_s_m3"]) for cell in cells)
    full_resistance = full_0d_pathway_resistance(full_0d_params, spec.key)
    if spec.selected_resistance_source == "geometry_poiseuille":
        selected_resistance = geometry_resistance
    elif spec.selected_resistance_source == "calibrated_full_0d_pathway":
        if full_resistance is None:
            raise ValueError(f"{spec.key} has no full 0-D resistance prior")
        selected_resistance = full_resistance
    else:
        raise ValueError(f"Unsupported resistance source {spec.selected_resistance_source}")

    selected_cell_resistances = distribute_selected_resistance(cells, selected_resistance)
    for index, (cell, selected_r) in enumerate(zip(cells, selected_cell_resistances), start=1):
        cell["index"] = index
        cell["resistance_pa_s_m3"] = selected_r
        cell["parameter_names"] = {
            "resistance": f"quasi_{spec.key}_rl_{index:02d}.resistance",
            "inertance": f"quasi_{spec.key}_rl_{index:02d}.inductance",
            "capacitance": f"quasi_{spec.key}_c_{index:02d}.capacitance",
        }

    total_length = sum(float(cell["length_m"]) for cell in cells)
    totals = {
        "length_m": total_length,
        "area_bar_m2": sum(
            float(cell["area_bar_m2"]) * float(cell["length_m"]) for cell in cells
        )
        / total_length,
        "geometry_resistance_pa_s_m3": geometry_resistance,
        "selected_resistance_pa_s_m3": selected_resistance,
        "selected_resistance_source": spec.selected_resistance_source,
        "inertance_pa_s2_m3": sum(float(cell["inertance_pa_s2_m3"]) for cell in cells),
        "capacitance_m3_pa": sum(float(cell["capacitance_m3_pa"]) for cell in cells),
        "full_0d_resistance_prior_pa_s_m3": full_resistance,
        "full_0d_compliance_prior_m3_pa": full_0d_compliance_prior(full_0d_params, spec.key),
        "full_0d_inertance_prior_pa_s2_m3": full_0d_inertance_prior(full_0d_params, spec.key),
    }
    return {
        "label": spec.label,
        "geometry_source": spec.geometry_source,
        "source_segments": list(spec.source_segments),
        "inlet_node": spec.inlet_node,
        "outlet_node": spec.outlet_node,
        "segment_count": spec.segment_count,
        "wave_speed_m_s": spec.wave_speed_m_s,
        "totals": totals,
        "cells": cells,
    }


def lpa_narrowing_metadata(fontan: pd.DataFrame) -> dict[str, Any]:
    lpa = fontan[fontan["segment_name"].isin(["LPA I", "LPA II"])]
    min_radius = float(lpa[["radius_in_m", "radius_out_m"]].min().min())
    return {
        "parameter_name": "quasi_lpa.narrowing_radius_m",
        "radius_m": min_radius,
        "area_m2": area(min_radius),
        "source_segments": ["LPA I", "LPA II"],
        "location": "shared LPA I outlet / LPA II inlet",
        "default_resistance_scale_parameter": "quasi_lpa.narrowing_resistance_scale",
        "default_resistance_scale": 1.0,
        "notes": (
            "Explicit baseline narrowing prior for later LPA-obstruction and "
            "quasi-chain calibration work."
        ),
    }


def build_priors_payload(
    aorta_geometry: Path = AORTA_GEOMETRY,
    fontan_geometry: Path = FONTAN_GEOMETRY,
    target_policy: Path = TARGET_POLICY,
    full_0d_baseline: Path = FULL_0D_BASELINE,
) -> dict[str, Any]:
    aorta = read_geometry(aorta_geometry)
    fontan = read_geometry(fontan_geometry)
    policy_rows = pd.read_csv(target_policy).to_dict(orient="records")
    full_0d_params = load_json(full_0d_baseline)["parameters"]
    chains = {
        spec.key: derive_chain(spec, aorta, fontan, full_0d_params)
        for spec in CHAIN_SPECS
    }
    return {
        "model_family": "quasi_0d_1d",
        "status": "first_pass_parameter_priors",
        "generated_by": "scripts/modeling/derive_quasi_vessel_parameters.py",
        "inputs": {
            "aorta_geometry": str(aorta_geometry.relative_to(ROOT)),
            "fontan_cross_geometry": str(fontan_geometry.relative_to(ROOT)),
            "target_policy": str(target_policy.relative_to(ROOT)),
            "full_0d_baseline": str(full_0d_baseline.relative_to(ROOT)),
        },
        "constants": {
            "density_kg_m3": RHO_KG_M3,
            "dynamic_viscosity_pa_s": MU_PA_S,
            "aortic_wave_speed_m_s": AORTIC_WAVE_SPEED_M_S,
            "fontan_wave_speed_m_s": FONTAN_WAVE_SPEED_M_S,
        },
        "units": UNITS,
        "target_policy_summary": {
            "direct_dao_pressure": "diagnostic/low-weight",
            "ivc_flow": "soft; compare raw direct and mass-closure implied values",
            "aortic_profile": "use paper/Nektar profile as quasi/1-D guide",
            "full_0d_parameters": "priors, not immutable constraints",
        },
        "target_policy_rows": policy_rows,
        "chains": chains,
        "metadata": {
            "lpa_narrowing": lpa_narrowing_metadata(fontan),
            "excluded_geometry_segments": {
                "aorta": ["Brachiocephalic", "Carotic left"],
                "reason": (
                    "Task 005 derives first-pass main aortic and Fontan chains. "
                    "Upper arch branch chains remain out of scope for the first quasi release."
                ),
            },
        },
    }


def build_config_fragment(priors: dict[str, Any]) -> dict[str, Any]:
    fragments: dict[str, Any] = {
        "model_family": "quasi_0d_1d",
        "generated_by": priors["generated_by"],
        "block_library_requirements": ["hydraulic_rl_block", "c_block"],
        "chains": {},
        "metadata": {
            "lpa_narrowing": priors["metadata"]["lpa_narrowing"],
        },
    }
    for key, chain in priors["chains"].items():
        spec = next(spec for spec in CHAIN_SPECS if spec.key == key)
        fragments["chains"][key] = block_fragment_for_chain(spec, chain["cells"])
    fragments["parameters"] = {
        "quasi_lpa.narrowing_radius_m": priors["metadata"]["lpa_narrowing"]["radius_m"],
        "quasi_lpa.narrowing_resistance_scale": 1.0,
    }
    return fragments


def write_yaml(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Derive first-pass quasi 0-D/1-D vessel R-L-C priors."
    )
    parser.add_argument("--aorta-geometry", type=Path, default=AORTA_GEOMETRY)
    parser.add_argument("--fontan-geometry", type=Path, default=FONTAN_GEOMETRY)
    parser.add_argument("--target-policy", type=Path, default=TARGET_POLICY)
    parser.add_argument("--full-0d-baseline", type=Path, default=FULL_0D_BASELINE)
    parser.add_argument("--priors-out", type=Path, default=PRIORS_OUT)
    parser.add_argument("--fragment-out", type=Path, default=FRAGMENT_OUT)
    args = parser.parse_args()

    priors = build_priors_payload(
        args.aorta_geometry,
        args.fontan_geometry,
        args.target_policy,
        args.full_0d_baseline,
    )
    fragment = build_config_fragment(priors)
    write_yaml(args.priors_out, priors)
    write_json(args.fragment_out, fragment)
    print(
        json.dumps(
            {
                "priors": str(args.priors_out),
                "fragment": str(args.fragment_out),
                "chains": sorted(priors["chains"]),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
