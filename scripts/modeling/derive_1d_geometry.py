#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]

PROCESSED = ROOT / "data/processed/aramburu_2024"
AORTA_GEOMETRY = PROCESSED / "model_inputs/aorta_geometry.csv"
FONTAN_GEOMETRY = PROCESSED / "model_inputs/fontan_cross_geometry.csv"
CONFIG_DIR = ROOT / "models/coupled_0d_1d/configs"
GEOMETRY_OUT = ROOT / "models/coupled_0d_1d/calibration/one_d_openloop_geometry.json"

DENSITY_KG_M3 = 1060.0
DYNAMIC_VISCOSITY_PA_S = 0.0035
AORTIC_WAVE_SPEED_M_S = 5.35
FONTAN_WAVE_SPEED_M_S = 2.81
PROTOTYPE_CELLS_PER_SEGMENT = 3


@dataclass(frozen=True)
class SourceSegment:
    segment_name: str
    domain_id: str
    node_1: str
    node_2: str
    length_m: float
    radius_in_m: float
    radius_out_m: float


@dataclass(frozen=True)
class DomainRef:
    case_name: str
    domain_no: int
    output_file: str
    distances_m: tuple[float, ...]
    fs_hz: float

    @property
    def path(self) -> Path:
        return PROCESSED / "nektar_1d" / self.case_name / self.output_file


AORTA_NODE_NAMES = {
    "1": "aao_inlet",
    "2": "arch_junction",
    "3": "dao_outlet",
    "4": "bca_outlet",
    "5": "left_carotid_outlet",
}

TCPC_NODE_NAMES = {
    "1": "ivc_inlet",
    "2": "tcpc_junction",
    "3": "lpa_junction",
    "4": "svc_inlet",
    "5": "rpa_outlet",
    "6": "lpa_outlet",
}


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT))


def clean_key(value: str) -> str:
    return (
        value.lower()
        .replace("/", "_")
        .replace("-", "_")
        .replace(" ", "_")
        .replace("__", "_")
    )


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def read_geometry(path: Path) -> list[SourceSegment]:
    segments: list[SourceSegment] = []
    for row in read_rows(path):
        if not row.get("segment_name") or row["segment_name"] == "-":
            continue
        segments.append(
            SourceSegment(
                segment_name=row["segment_name"],
                domain_id=row["domain_id"],
                node_1=str(row["node_1"]).rstrip(".0"),
                node_2=str(row["node_2"]).rstrip(".0"),
                length_m=float(row["length_m"]),
                radius_in_m=float(row["radius_in_m"]),
                radius_out_m=float(row["radius_out_m"]),
            )
        )
    return segments


def parse_distances(text: str) -> tuple[float, ...]:
    values = json.loads(text)
    return tuple(float(value) for value in values)


def read_domain_manifest(case_name: str) -> dict[int, DomainRef]:
    manifest = PROCESSED / "nektar_1d" / case_name / "domain_manifest.csv"
    refs: dict[int, DomainRef] = {}
    for row in read_rows(manifest):
        domain_no = int(row["domain_no"])
        refs[domain_no] = DomainRef(
            case_name=case_name,
            domain_no=domain_no,
            output_file=row["output_file"],
            distances_m=parse_distances(row["distances_m"]),
            fs_hz=float(row["fs_hz"]),
        )
    return refs


def area_from_radius(radius_m: float) -> float:
    return math.pi * radius_m * radius_m


def average_area(radius_in_m: float, radius_out_m: float) -> float:
    return 0.5 * (area_from_radius(radius_in_m) + area_from_radius(radius_out_m))


def poiseuille_resistance(
    length_m: float,
    radius_in_m: float,
    radius_out_m: float,
) -> float:
    if math.isclose(radius_in_m, radius_out_m, rel_tol=1e-12, abs_tol=1e-15):
        radius_integral = length_m / radius_in_m**4
    else:
        radius_integral = (
            length_m
            / (3.0 * (radius_out_m - radius_in_m))
            * (1.0 / radius_in_m**3 - 1.0 / radius_out_m**3)
        )
    return 8.0 * DYNAMIC_VISCOSITY_PA_S * radius_integral / math.pi


def inertance(length_m: float, area_m2: float) -> float:
    return DENSITY_KG_M3 * length_m / area_m2


def compliance(length_m: float, area_m2: float, wave_speed_m_s: float) -> float:
    return area_m2 * length_m / (DENSITY_KG_M3 * wave_speed_m_s * wave_speed_m_s)


def wall_stiffness_from_wave_speed(area_m2: float, wave_speed_m_s: float) -> float:
    return 2.0 * DENSITY_KG_M3 * wave_speed_m_s * wave_speed_m_s / math.sqrt(area_m2)


def segment_domain_id(
    source: SourceSegment,
    case: str,
    combined_domain_offset: int = 0,
) -> int:
    pieces = [int(float(piece)) for piece in source.domain_id.split("-")]
    if case == "combined" and len(pieces) > 1:
        return pieces[1]
    return pieces[0] + combined_domain_offset


def cell_specs(source: SourceSegment, wave_speed_m_s: float) -> list[dict[str, Any]]:
    cells: list[dict[str, Any]] = []
    for index in range(PROTOTYPE_CELLS_PER_SEGMENT):
        x0 = index / PROTOTYPE_CELLS_PER_SEGMENT
        x1 = (index + 1) / PROTOTYPE_CELLS_PER_SEGMENT
        radius_in = source.radius_in_m + (source.radius_out_m - source.radius_in_m) * x0
        radius_out = source.radius_in_m + (source.radius_out_m - source.radius_in_m) * x1
        reference_area = average_area(radius_in, radius_out)
        length = source.length_m / PROTOTYPE_CELLS_PER_SEGMENT
        cells.append(
            {
                "cell_index": index + 1,
                "length_m": length,
                "radius_in_m": radius_in,
                "radius_out_m": radius_out,
                "reference_area_m2": reference_area,
                "wall_stiffness_pa_m-1": wall_stiffness_from_wave_speed(
                    reference_area,
                    wave_speed_m_s,
                ),
                "inertance_pa_s2_m-3": inertance(length, reference_area),
                "capacitance_m3_pa-1": compliance(
                    length,
                    reference_area,
                    wave_speed_m_s,
                ),
                "poiseuille_resistance_pa_s_m-3": poiseuille_resistance(
                    length,
                    radius_in,
                    radius_out,
                ),
            }
        )
    return cells


def build_segment(
    source: SourceSegment,
    domain: DomainRef,
    node_names: dict[str, str],
    prefix: str,
    wave_speed_m_s: float,
) -> dict[str, Any]:
    reference_area = average_area(source.radius_in_m, source.radius_out_m)
    return {
        "segment_id": f"{prefix}_{domain.domain_no:02d}_{clean_key(source.segment_name)}",
        "source_segment": source.segment_name,
        "domain_no": domain.domain_no,
        "nektar_domain_file": rel(domain.path),
        "nektar_distance_m": list(domain.distances_m),
        "node_1": node_names[source.node_1],
        "node_2": node_names[source.node_2],
        "length_m": source.length_m,
        "radius_in_m": source.radius_in_m,
        "radius_out_m": source.radius_out_m,
        "reference_area_m2": reference_area,
        "wave_speed_m_s": wave_speed_m_s,
        "wall_stiffness_pa_m-1": wall_stiffness_from_wave_speed(
            reference_area,
            wave_speed_m_s,
        ),
        "density_kg_m-3": DENSITY_KG_M3,
        "dynamic_viscosity_pa_s": DYNAMIC_VISCOSITY_PA_S,
        "poiseuille_resistance_pa_s_m-3": poiseuille_resistance(
            source.length_m,
            source.radius_in_m,
            source.radius_out_m,
        ),
        "inertance_pa_s2_m-3": inertance(source.length_m, reference_area),
        "capacitance_m3_pa-1": compliance(
            source.length_m,
            reference_area,
            wave_speed_m_s,
        ),
        "prototype_block": {
            "model_type": "fixed_3cell_1d_vessel_block",
            "cell_count": PROTOTYPE_CELLS_PER_SEGMENT,
            "state": ["area_01", "area_02", "area_03", "flow_00", "flow_01", "flow_02", "flow_03"],
        },
        "cells": cell_specs(source, wave_speed_m_s),
    }


def validation_signals(kind: str) -> list[dict[str, Any]]:
    if kind == "aorta":
        return [
            signal("ascending_aorta_pressure", "pressure", "mmHg", "paao_mmhg", "ascending_aorta_pressure_mmHg", 3.0, 6.0),
            signal("aortic_arch_pressure", "pressure", "mmHg", "parch_mmhg", "aortic_arch_pressure_mmHg", 3.0, 6.0),
            signal("descending_aorta_pressure", "pressure", "mmHg", "pdao_mmhg", "descending_aorta_pressure_mmHg", 3.0, 6.0),
            signal("descending_aorta_flow", "flow", "ml/s", "qdao_ml_per_s", "descending_aorta_flow_ml_s", 4.0, 15.0),
        ]
    if kind == "tcpc":
        return [
            signal("ivc_pressure", "pressure", "mmHg", "pivc_mmhg", "ivc_pressure_mmHg", 1.5, 3.0),
            signal("svc_pressure", "pressure", "mmHg", "psvc_mmhg", "svc_pressure_mmHg", 1.5, 3.0),
            signal("rpa_pressure", "pressure", "mmHg", "prpa_mmhg", "rpa_pressure_mmHg", 1.5, 3.0),
            signal("rpa_flow", "flow", "ml/s", "qrpa_ml_per_s", "rpa_flow_ml_s", 4.0, 8.0),
            signal("lpa_pressure", "pressure", "mmHg", "plpa_mmhg", "lpa_pressure_mmHg", 1.5, 3.0),
            signal("lpa_flow", "flow", "ml/s", "qlpa_ml_per_s", "lpa_flow_ml_s", 4.0, 8.0),
        ]
    if kind == "combined":
        return [
            signal("ascending_aorta_pressure", "pressure", "mmHg", "ascending_aorta_pressure_mmHg", "ascending_aorta_pressure_mmHg", 3.0, 6.0),
            signal("aortic_arch_pressure", "pressure", "mmHg", "aortic_arch_pressure_mmHg", "aortic_arch_pressure_mmHg", 3.0, 6.0),
            signal("descending_aorta_pressure", "pressure", "mmHg", "descending_aorta_pressure_mmHg", "descending_aorta_pressure_mmHg", 3.0, 6.0),
            signal("descending_aorta_flow", "flow", "ml/s", "descending_aorta_flow_ml_s", "descending_aorta_flow_ml_s", 4.0, 15.0),
            signal("ivc_pressure", "pressure", "mmHg", "ivc_pressure_mmHg", "ivc_pressure_mmHg", 1.5, 3.0),
            signal("ivc_flow", "flow", "ml/s", "ivc_flow_ml_s", "ivc_flow_ml_s", 4.0, 8.0),
            signal("svc_pressure", "pressure", "mmHg", "svc_pressure_mmHg", "svc_pressure_mmHg", 1.5, 3.0),
            signal("svc_flow", "flow", "ml/s", "svc_flow_ml_s", "svc_flow_ml_s", 4.0, 8.0),
            signal("rpa_pressure", "pressure", "mmHg", "rpa_pressure_mmHg", "rpa_pressure_mmHg", 1.5, 3.0),
            signal("rpa_flow", "flow", "ml/s", "rpa_flow_ml_s", "rpa_flow_ml_s", 4.0, 8.0),
            signal("lpa_pressure", "pressure", "mmHg", "lpa_pressure_mmHg", "lpa_pressure_mmHg", 1.5, 3.0),
            signal("lpa_flow", "flow", "ml/s", "lpa_flow_ml_s", "lpa_flow_ml_s", 4.0, 8.0),
        ]
    raise ValueError(f"Unknown validation kind {kind}")


def signal(
    name: str,
    quantity: str,
    unit: str,
    reference_column: str,
    clinical_column: str,
    mean_tolerance: float,
    rmse_tolerance: float,
) -> dict[str, Any]:
    return {
        "name": name,
        "quantity": quantity,
        "unit": unit,
        "reference_column": reference_column,
        "clinical_column": clinical_column,
        "mean_abs_tolerance": mean_tolerance,
        "rmse_tolerance": rmse_tolerance,
    }


def config_payload(
    *,
    submodel_id: str,
    title: str,
    kind: str,
    segments: list[dict[str, Any]],
    nodes: list[str],
    inputs: list[dict[str, Any]],
    reference_table: Path,
    clinical_table: Path,
    notes: list[str],
) -> dict[str, Any]:
    return {
        "type": "open_loop_1d_submodel",
        "model_family": "coupled_0d_1d",
        "status": "reference_validation_spec",
        "submodel_id": submodel_id,
        "title": title,
        "generated_by": "scripts/modeling/derive_1d_geometry.py",
        "run_with": "python3 scripts/calibration/validate_1d_submodels.py",
        "constants": {
            "density_kg_m-3": DENSITY_KG_M3,
            "dynamic_viscosity_pa_s": DYNAMIC_VISCOSITY_PA_S,
            "aortic_wave_speed_m_s": AORTIC_WAVE_SPEED_M_S,
            "fontan_wave_speed_m_s": FONTAN_WAVE_SPEED_M_S,
            "prototype_cells_per_segment": PROTOTYPE_CELLS_PER_SEGMENT,
        },
        "topology": {
            "nodes": nodes,
            "segments": segments,
        },
        "inputs": inputs,
        "validation": {
            "kind": kind,
            "reference_table": rel(reference_table),
            "clinical_table": rel(clinical_table),
            "signals": validation_signals(kind),
        },
        "notes": notes,
    }


def build_payloads() -> dict[str, dict[str, Any]]:
    aorta_sources = read_geometry(AORTA_GEOMETRY)
    tcpc_sources = read_geometry(FONTAN_GEOMETRY)
    aorta_domains = read_domain_manifest("01_aorta")
    tcpc_domains = read_domain_manifest("02_tcpc")
    combined_domains = read_domain_manifest("03_aorta_tcpc")

    aorta_segments = [
        build_segment(
            source,
            aorta_domains[segment_domain_id(source, "aorta")],
            AORTA_NODE_NAMES,
            "aorta",
            AORTIC_WAVE_SPEED_M_S,
        )
        for source in aorta_sources
    ]
    tcpc_segments = [
        build_segment(
            source,
            tcpc_domains[segment_domain_id(source, "tcpc")],
            TCPC_NODE_NAMES,
            "tcpc",
            FONTAN_WAVE_SPEED_M_S,
        )
        for source in tcpc_sources
    ]
    combined_segments = [
        build_segment(
            source,
            combined_domains[segment_domain_id(source, "combined")],
            AORTA_NODE_NAMES,
            "combined_aorta",
            AORTIC_WAVE_SPEED_M_S,
        )
        for source in aorta_sources
    ] + [
        build_segment(
            source,
            combined_domains[segment_domain_id(source, "combined")],
            TCPC_NODE_NAMES,
            "combined_tcpc",
            FONTAN_WAVE_SPEED_M_S,
        )
        for source in tcpc_sources
    ]

    clinical = PROCESSED / "measurements_clinical.csv"
    payloads = {
        "submodel_aorta_1d_openloop": config_payload(
            submodel_id="submodel_aorta_1d_openloop",
            title="Aorta 1-D open-loop reference submodel",
            kind="aorta",
            segments=aorta_segments,
            nodes=sorted({node for segment in aorta_segments for node in [segment["node_1"], segment["node_2"]]}),
            inputs=[
                {
                    "name": "ascending_aorta_inflow",
                    "path": rel(PROCESSED / "model_inputs/aorta_waves_clinical.csv"),
                    "time_column": "time_s",
                    "flow_column": "ascending_aorta_flow_ml_s",
                    "pressure_column": "ascending_aorta_pressure_mmHg",
                    "role": "measured inlet waveform",
                }
            ],
            reference_table=PROCESSED / "paper_results/submodel2.csv",
            clinical_table=clinical,
            notes=[
                "Uses the tracked patient-specific aorta geometry from data.xlsx.",
                "Includes BCA and left carotid branches present in the source geometry.",
                "Does not add a normal LSA branch that is absent from the source table.",
                "DAo flow is screened with a broad waveform RMSE tolerance because the accepted signal policy treats downstream DAo/bed-entry flow as sensitive to terminal-load dynamics.",
            ],
        ),
        "submodel_tcpc_1d_openloop": config_payload(
            submodel_id="submodel_tcpc_1d_openloop",
            title="TCPC 1-D open-loop reference submodel",
            kind="tcpc",
            segments=tcpc_segments,
            nodes=sorted({node for segment in tcpc_segments for node in [segment["node_1"], segment["node_2"]]}),
            inputs=[
                {
                    "name": "ivc_svc_inflows",
                    "path": rel(PROCESSED / "model_inputs/fontan_cross_inflows_clinical.csv"),
                    "time_column": "time_s",
                    "flow_columns": ["ivc_flow_ml_s", "svc_flow_ml_s"],
                    "role": "measured inlet waveforms",
                }
            ],
            reference_table=PROCESSED / "paper_results/submodel3.csv",
            clinical_table=clinical,
            notes=[
                "Uses the tracked Fontan cross geometry from data.xlsx.",
                "SVC and IVC flows are prescribed inputs; RPA/LPA pressure and flow are validation outputs.",
            ],
        ),
        "submodel_aorta_tcpc_1d_openloop": config_payload(
            submodel_id="submodel_aorta_tcpc_1d_openloop",
            title="Combined aorta-TCPC 1-D open-loop reference submodel",
            kind="combined",
            segments=combined_segments,
            nodes=sorted({node for segment in combined_segments for node in [segment["node_1"], segment["node_2"]]}),
            inputs=[
                {
                    "name": "ascending_aorta_inflow",
                    "path": rel(PROCESSED / "model_inputs/aorta_waves_clinical.csv"),
                    "time_column": "time_s",
                    "flow_column": "ascending_aorta_flow_ml_s",
                    "pressure_column": "ascending_aorta_pressure_mmHg",
                    "role": "measured aortic inlet waveform",
                },
                {
                    "name": "ivc_svc_inflows",
                    "path": rel(PROCESSED / "model_inputs/fontan_cross_inflows_clinical.csv"),
                    "time_column": "time_s",
                    "flow_columns": ["ivc_flow_ml_s", "svc_flow_ml_s"],
                    "role": "measured TCPC inlet waveforms",
                },
                {
                    "name": "dao_ivc_coupling",
                    "parameter_path": rel(PROCESSED / "model_inputs/coupling_dao_ivc_parameters.csv"),
                    "waveform_path": rel(PROCESSED / "model_inputs/coupling_dao_ivc_waveforms.csv"),
                    "role": "reference coupling-bed behavior",
                },
                {
                    "name": "supao_svc_coupling",
                    "parameter_path": rel(PROCESSED / "model_inputs/coupling_supao_svc_parameters.csv"),
                    "waveform_path": rel(PROCESSED / "model_inputs/coupling_supao_svc_waveforms.csv"),
                    "role": "reference coupling-bed behavior",
                },
            ],
            reference_table=PROCESSED / "comparison/03_aorta_tcpc_1d_last_cycle_clinical.csv",
            clinical_table=clinical,
            notes=[
                "Uses combined Nektar domains 1-4 for aorta and 5-9 for TCPC.",
                "This remains open-loop validation; no closed-loop heart or beds are inserted.",
                "No normal LSA branch is added to the patient-specific aorta.",
                "DAo flow is screened with a broad waveform RMSE tolerance because the accepted signal policy treats downstream DAo/bed-entry flow as sensitive to terminal-load dynamics.",
            ],
        ),
    }
    return payloads


def geometry_summary(payloads: dict[str, dict[str, Any]]) -> dict[str, Any]:
    return {
        "generated_by": "scripts/modeling/derive_1d_geometry.py",
        "inputs": {
            "aorta_geometry": rel(AORTA_GEOMETRY),
            "fontan_cross_geometry": rel(FONTAN_GEOMETRY),
        },
        "constants": {
            "density_kg_m-3": DENSITY_KG_M3,
            "dynamic_viscosity_pa_s": DYNAMIC_VISCOSITY_PA_S,
            "aortic_wave_speed_m_s": AORTIC_WAVE_SPEED_M_S,
            "fontan_wave_speed_m_s": FONTAN_WAVE_SPEED_M_S,
        },
        "submodels": {
            key: {
                "config": rel(CONFIG_DIR / f"{key}.jsonc"),
                "segment_count": len(payload["topology"]["segments"]),
                "segments": [
                    {
                        "segment_id": segment["segment_id"],
                        "source_segment": segment["source_segment"],
                        "length_m": segment["length_m"],
                        "radius_in_m": segment["radius_in_m"],
                        "radius_out_m": segment["radius_out_m"],
                        "wave_speed_m_s": segment["wave_speed_m_s"],
                        "wall_stiffness_pa_m-1": segment["wall_stiffness_pa_m-1"],
                    }
                    for segment in payload["topology"]["segments"]
                ],
            }
            for key, payload in payloads.items()
        },
    }


def write_json(path: Path, payload: dict[str, Any], *, check: bool) -> bool:
    text = json.dumps(payload, indent=2, sort_keys=False) + "\n"
    if check:
        return path.exists() and path.read_text(encoding="utf-8") == text
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return True


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Derive coupled-model open-loop 1-D geometry/config specs."
    )
    parser.add_argument("--check", action="store_true", help="verify generated files are current")
    args = parser.parse_args()

    payloads = build_payloads()
    paths = [
        CONFIG_DIR / f"{key}.jsonc"
        for key in payloads
    ]
    ok = True
    for path, (key, payload) in zip(paths, payloads.items()):
        ok = write_json(path, payload, check=args.check) and ok
    ok = write_json(GEOMETRY_OUT, geometry_summary(payloads), check=args.check) and ok

    if args.check and not ok:
        raise SystemExit("generated 1-D open-loop configs are stale")

    print(
        json.dumps(
            {
                "configs": [rel(path) for path in paths],
                "geometry": rel(GEOMETRY_OUT),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
