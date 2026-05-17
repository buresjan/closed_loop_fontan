#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
from copy import deepcopy
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
FULL_CONFIG_DIR = ROOT / "models/full_0d/configs"
COUPLED_DIR = ROOT / "models/coupled_0d_1d"
COUPLED_CONFIG_DIR = COUPLED_DIR / "configs"
AORTA_SPEC = COUPLED_CONFIG_DIR / "submodel_aorta_1d_openloop.jsonc"
TCPC_SPEC = COUPLED_CONFIG_DIR / "submodel_tcpc_1d_openloop.jsonc"

SCENARIOS = {
    "smoke": (
        FULL_CONFIG_DIR / "fontan_0d_smoke.jsonc",
        COUPLED_CONFIG_DIR / "fontan_coupled_0d_1d_smoke.jsonc",
    ),
    "baseline": (
        FULL_CONFIG_DIR / "fontan_0d_baseline.jsonc",
        COUPLED_CONFIG_DIR / "fontan_coupled_0d_1d_baseline.jsonc",
    ),
    "vasodilation": (
        FULL_CONFIG_DIR / "fontan_0d_vasodilation.jsonc",
        COUPLED_CONFIG_DIR / "fontan_coupled_0d_1d_vasodilation.jsonc",
    ),
    "fenestration": (
        FULL_CONFIG_DIR / "fontan_0d_fenestration.jsonc",
        COUPLED_CONFIG_DIR / "fontan_coupled_0d_1d_fenestration.jsonc",
    ),
    "lpa_obstruction": (
        FULL_CONFIG_DIR / "fontan_0d_lpa_obstruction.jsonc",
        COUPLED_CONFIG_DIR / "fontan_coupled_0d_1d_lpa_obstruction.jsonc",
    ),
}

REMOVED_BLOCKS = {
    "aao_arch",
    "aortic_arch_compliance",
    "arch_dao",
    "arch_bca",
    "arch_lcca",
    "svc_conduit_compliance",
    "ivc_conduit_compliance",
    "rpa_conduit_compliance",
    "lpa_conduit_compliance",
    "svc_conduit_rl",
    "ivc_conduit_rl",
    "rpa_conduit_rl",
    "lpa_conduit_rl",
    "svc_conduit_junction",
    "ivc_conduit_junction",
    "rpa_conduit_out",
    "lpa_conduit_out",
    "tcpc_compliance",
}

REMOVED_NODES = {
    "aortic_arch",
    "svc_conduit",
    "ivc_conduit",
    "rpa_conduit",
    "lpa_conduit",
    "tcpc",
}

REMOVED_PARAMETER_PREFIXES = tuple(f"{name}." for name in REMOVED_BLOCKS)
REMOVED_STATE_PREFIXES = tuple(f"{name}." for name in REMOVED_BLOCKS) + tuple(
    f"{name}." for name in REMOVED_NODES
)

AORTA_NODE_MAP = {
    "Ascending aorta": ("aao", "coupled_aao_arch"),
    "Thoracic aorta": ("coupled_dao_arch", "coupled_dao_out"),
    "Brachiocephalic": ("coupled_bca_arch", "coupled_bca_out"),
    "Carotic left": ("coupled_lcca_arch", "coupled_lcca_out"),
}

TCPC_NODE_MAP = {
    "IVC": ("ivc", "coupled_ivc_tcpc"),
    "SVC": ("svc", "coupled_svc_tcpc"),
    "RPA": ("coupled_rpa_tcpc", "rpa"),
}

SEGMENT_NAME_MAP = {
    "Ascending aorta": "coupled_aao",
    "Thoracic aorta": "coupled_dao",
    "Brachiocephalic": "coupled_bca",
    "Carotic left": "coupled_lcca",
    "IVC": "coupled_ivc",
    "SVC": "coupled_svc",
    "RPA": "coupled_rpa",
}

TCPC_BRANCH_DEFINITIONS = {
    "svc": {
        "node": "coupled_svc_tcpc",
        "flow_initial": "coupled_svc",
        "segments": ("SVC",),
    },
    "ivc": {
        "node": "coupled_ivc_tcpc",
        "flow_initial": "coupled_ivc",
        "segments": ("IVC",),
    },
    "rpa": {
        "node": "coupled_rpa_tcpc",
        "flow_initial": "coupled_rpa",
        "segments": ("RPA",),
    },
    "lpa": {
        "node": "coupled_lpa_tcpc",
        "flow_initial": "coupled_lpa",
        "segments": ("LPA I", "LPA II"),
    },
}

AORTA_TERMINAL_LOSS_DEFINITIONS = {
    "coupled_dao_loss": {
        "upstream": "coupled_dao_out",
        "downstream": "dao",
        "resistance": "arch_dao.resistance",
        "segments": ("Thoracic aorta",),
    },
    "coupled_bca_loss": {
        "upstream": "coupled_bca_out",
        "downstream": "bca",
        "resistance": "arch_bca.resistance",
        "segments": ("Brachiocephalic",),
    },
    "coupled_lcca_loss": {
        "upstream": "coupled_lcca_out",
        "downstream": "lcca",
        "resistance": "arch_lcca.resistance",
        "segments": ("Carotic left",),
    },
}

AREA_IDS = ("area_01", "area_02", "area_03")
LOG_AREA_IDS = ("log_area_01", "log_area_02", "log_area_03")
FLOW_IDS = ("flow_00", "flow_01", "flow_02", "flow_03")
COUPLED_1D_MODEL_TYPE = "fixed_3cell_1d_log_area_vessel_block"
COUPLED_LPA_MODEL_TYPE = "fixed_6cell_tapered_1d_log_area_vessel_block"
AORTIC_JUNCTION_MODEL_TYPE = "aortic_arch_total_pressure_junction_block"
TCPC_JUNCTION_MODEL_TYPE = "tcpc_characteristic_total_pressure_junction_block"
FLOW_MAGNITUDE_FACTORS = (1.0, 0.97, 1.03, 0.99)
LPA_FLOW_MAGNITUDE_FACTORS = (1.0, 0.98, 1.02, 0.99, 1.01, 0.97, 1.03)
TCPC_BRANCH_FLOW_MAGNITUDE_FACTORS = {
    "svc": 1.01,
    "ivc": 1.01,
    "rpa": 0.97,
    "lpa": 0.97,
}
FLOW_MAGNITUDES = {
    "coupled_aao": 4.2e-5,
    "coupled_dao": 2.2e-5,
    "coupled_bca": 1.0e-5,
    "coupled_lcca": 5.1e-6,
    "coupled_ivc": 2.2e-5,
    "coupled_svc": 2.0e-5,
    "coupled_rpa": 2.5e-5,
    "coupled_lpa": 1.72e-5,
}
FLOW_INITIALS = {
    "coupled_aao": 4.2e-5,
    "coupled_dao": 2.17e-5,
    "coupled_bca": 1.0e-5,
    "coupled_lcca": 5.1e-6,
    "coupled_ivc": 2.16e-5,
    "coupled_svc": 2.02e-5,
    "coupled_rpa": 2.47e-5,
    "coupled_lpa": 1.71e-5,
}
AORTA_LSA_FLOW_INITIAL = (
    FLOW_INITIALS["coupled_aao"]
    - FLOW_INITIALS["coupled_dao"]
    - FLOW_INITIALS["coupled_bca"]
    - FLOW_INITIALS["coupled_lcca"]
)
AORTA_LSA_FLOW_MAGNITUDE = abs(AORTA_LSA_FLOW_INITIAL)
WALL_STIFFNESS_SCALES = {
    "coupled_ivc": 16.0,
    "coupled_svc": 16.0,
    "coupled_rpa": 16.0,
    "coupled_lpa": 16.0,
}


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any], *, check: bool) -> bool:
    text = json.dumps(payload, indent=2) + "\n"
    if check:
        return path.exists() and path.read_text(encoding="utf-8") == text
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return True


def remove_existing_lumped_paths(cfg: dict[str, Any]) -> None:
    blocks = cfg["net"]["blocks"]
    for name in REMOVED_BLOCKS:
        blocks.pop(name, None)

    cfg["net"]["nodes"] = [
        node for node in cfg["net"]["nodes"] if node not in REMOVED_NODES
    ]
    for mapping_name in [
        "parameters",
        "variables_initialization",
        "variables_magnitudes",
    ]:
        mapping = cfg[mapping_name]
        for key in list(mapping):
            if key.startswith(REMOVED_PARAMETER_PREFIXES if mapping_name == "parameters" else REMOVED_STATE_PREFIXES):
                mapping.pop(key)


def add_node(cfg: dict[str, Any], node: str, pressure: float, magnitude: float) -> None:
    if node not in cfg["net"]["nodes"]:
        cfg["net"]["nodes"].append(node)
    cfg["variables_initialization"][f"{node}.blood_pressure"] = pressure
    cfg["variables_magnitudes"][f"{node}.blood_pressure"] = magnitude


def node_pressure(cfg: dict[str, Any], node: str) -> float:
    return float(cfg["variables_initialization"].get(f"{node}.blood_pressure", 0.0))


def node_pressure_magnitude(cfg: dict[str, Any], node: str) -> float:
    return float(cfg["variables_magnitudes"].get(f"{node}.blood_pressure", 2000.0))


def add_intermediate_node(cfg: dict[str, Any], node: str, node_1: str, node_2: str) -> None:
    pressure = 0.5 * (node_pressure(cfg, node_1) + node_pressure(cfg, node_2))
    magnitude = max(node_pressure_magnitude(cfg, node_1), node_pressure_magnitude(cfg, node_2))
    add_node(cfg, node, pressure, magnitude)


def friction_coefficient(segment: dict[str, Any]) -> float:
    resistance = float(segment["poiseuille_resistance_pa_s_m-3"])
    area = float(segment["reference_area_m2"])
    density = float(segment["density_kg_m-3"])
    length = float(segment["length_m"])
    return resistance * area * area / (density * length)


def initial_area_from_pressure(
    segment: dict[str, Any],
    pressure: float,
    external_pressure: float,
    wall_stiffness: float,
) -> float:
    reference_area = float(segment["reference_area_m2"])
    radius_like = math.sqrt(reference_area) + (pressure - external_pressure) / wall_stiffness
    if radius_like <= 0.0:
        raise ValueError("initial pressure implies non-positive 1-D vessel area")
    return radius_like * radius_like


def add_vessel_block(
    cfg: dict[str, Any],
    *,
    name: str,
    segment: dict[str, Any],
    node_1: str,
    node_2: str,
    flow_initial: float | None = None,
) -> None:
    cfg["net"]["blocks"][name] = {
        "type": "block_description",
        "model_type": COUPLED_1D_MODEL_TYPE,
        "time": "time",
        "flux_type": "blood_flow",
        "length": f"{name}.length",
        "reference_area": f"{name}.reference_area",
        "wall_stiffness": f"{name}.wall_stiffness",
        "external_pressure": f"{name}.external_pressure",
        "density": f"{name}.density",
        "friction_coefficient": f"{name}.friction_coefficient",
        "momentum_correction": f"{name}.momentum_correction",
        "nodes": {"1": node_1, "2": node_2},
    }

    reference_area = float(segment["reference_area_m2"])
    pressure_mid = 0.5 * (node_pressure(cfg, node_1) + node_pressure(cfg, node_2))
    external_pressure = float(cfg["parameters"].get("pleural.pressure", 0.0))
    wall_stiffness = (
        float(segment["wall_stiffness_pa_m-1"])
        * WALL_STIFFNESS_SCALES.get(name, 1.0)
    )
    initial_area = initial_area_from_pressure(
        segment,
        pressure_mid,
        external_pressure,
        wall_stiffness,
    )
    cfg["parameters"].update(
        {
            f"{name}.length": float(segment["length_m"]),
            f"{name}.reference_area": reference_area,
            f"{name}.wall_stiffness": wall_stiffness,
            f"{name}.external_pressure": external_pressure,
            f"{name}.density": float(segment["density_kg_m-3"]),
            f"{name}.friction_coefficient": friction_coefficient(segment),
            f"{name}.momentum_correction": 1.1,
        }
    )
    for area_id in AREA_IDS:
        cfg["variables_initialization"].pop(f"{name}.{area_id}", None)
        cfg["variables_magnitudes"].pop(f"{name}.{area_id}", None)
    log_initial_area = math.log(initial_area)
    for log_area_id in LOG_AREA_IDS:
        cfg["variables_initialization"][f"{name}.{log_area_id}"] = log_initial_area
        cfg["variables_magnitudes"][f"{name}.{log_area_id}"] = max(
            abs(log_initial_area),
            1.0,
        )
    initial_flow = FLOW_INITIALS[name] if flow_initial is None else flow_initial
    flow_magnitude = FLOW_MAGNITUDES[name]
    for flow_id, factor in zip(FLOW_IDS, FLOW_MAGNITUDE_FACTORS, strict=True):
        cfg["variables_initialization"][f"{name}.{flow_id}"] = initial_flow
        cfg["variables_magnitudes"][f"{name}.{flow_id}"] = flow_magnitude * factor


def segment_cell_radii(segment: dict[str, Any], cells: int = 3) -> list[float]:
    radius_in = float(segment["radius_in_m"])
    radius_out = float(segment["radius_out_m"])
    return [
        radius_in + (radius_out - radius_in) * ((idx + 0.5) / cells)
        for idx in range(cells)
    ]


def segment_cell_payload(segment: dict[str, Any], wall_scale: float) -> dict[str, list[float]]:
    cells = 3
    length = float(segment["length_m"])
    density = float(segment["density_kg_m-3"])
    segment_area = float(segment["reference_area_m2"])
    segment_beta = float(segment["wall_stiffness_pa_m-1"]) * wall_scale
    wave_speed_squared = segment_beta * math.sqrt(segment_area) / (2.0 * density)

    radii = segment_cell_radii(segment, cells)
    cell_lengths = [length / cells] * cells
    areas = [math.pi * radius * radius for radius in radii]
    wall_stiffnesses = [
        2.0 * density * wave_speed_squared / math.sqrt(area)
        for area in areas
    ]

    resistance = float(segment["poiseuille_resistance_pa_s_m-3"])
    resistance_weights = [
        cell_length / (radius**4)
        for cell_length, radius in zip(cell_lengths, radii, strict=True)
    ]
    total_weight = sum(resistance_weights)
    cell_resistances = [
        resistance * weight / total_weight
        for weight in resistance_weights
    ]
    friction_coefficients = [
        cell_resistance * area * area / (density * cell_length)
        for cell_resistance, area, cell_length in zip(
            cell_resistances,
            areas,
            cell_lengths,
            strict=True,
        )
    ]
    return {
        "cell_lengths": cell_lengths,
        "reference_areas": areas,
        "wall_stiffnesses": wall_stiffnesses,
        "friction_coefficients": friction_coefficients,
    }


def initial_areas_from_pressure_profile(
    *,
    reference_areas: list[float],
    wall_stiffnesses: list[float],
    cell_lengths: list[float],
    inlet_pressure: float,
    outlet_pressure: float,
    external_pressure: float,
) -> list[float]:
    total_length = sum(cell_lengths)
    center = 0.0
    areas: list[float] = []
    for area, stiffness, length in zip(
        reference_areas,
        wall_stiffnesses,
        cell_lengths,
        strict=True,
    ):
        center += 0.5 * length
        pressure = inlet_pressure + (outlet_pressure - inlet_pressure) * (
            center / total_length
        )
        radius_like = math.sqrt(area) + (pressure - external_pressure) / stiffness
        if radius_like <= 0.0:
            raise ValueError("initial pressure implies non-positive LPA area")
        areas.append(radius_like * radius_like)
        center += 0.5 * length
    return areas


def add_lpa_composite_block(
    cfg: dict[str, Any],
    *,
    segments_by_source: dict[str, dict[str, Any]],
) -> None:
    name = "coupled_lpa"
    lpa_i = segment_cell_payload(
        segments_by_source["LPA I"],
        WALL_STIFFNESS_SCALES[name],
    )
    lpa_ii = segment_cell_payload(
        segments_by_source["LPA II"],
        WALL_STIFFNESS_SCALES[name],
    )
    cell_lengths = lpa_i["cell_lengths"] + lpa_ii["cell_lengths"]
    reference_areas = lpa_i["reference_areas"] + lpa_ii["reference_areas"]
    wall_stiffnesses = lpa_i["wall_stiffnesses"] + lpa_ii["wall_stiffnesses"]
    friction_coefficients = (
        lpa_i["friction_coefficients"] + lpa_ii["friction_coefficients"]
    )
    density = float(segments_by_source["LPA I"]["density_kg_m-3"])
    external_pressure = float(cfg["parameters"].get("pleural.pressure", 0.0))

    cfg["net"]["blocks"][name] = {
        "type": "block_description",
        "model_type": COUPLED_LPA_MODEL_TYPE,
        "time": "time",
        "flux_type": "blood_flow",
        "external_pressure": f"{name}.external_pressure",
        "density": f"{name}.density",
        "momentum_correction": f"{name}.momentum_correction",
        "nodes": {"1": "coupled_lpa_tcpc", "2": "lpa"},
    }
    for idx in range(1, 7):
        cfg["net"]["blocks"][name][f"cell_length_{idx:02d}"] = (
            f"{name}.cell_length_{idx:02d}"
        )
        cfg["net"]["blocks"][name][f"reference_area_{idx:02d}"] = (
            f"{name}.reference_area_{idx:02d}"
        )
        cfg["net"]["blocks"][name][f"wall_stiffness_{idx:02d}"] = (
            f"{name}.wall_stiffness_{idx:02d}"
        )
        cfg["net"]["blocks"][name][f"friction_coefficient_{idx:02d}"] = (
            f"{name}.friction_coefficient_{idx:02d}"
        )

    cfg["parameters"][f"{name}.length"] = sum(cell_lengths)
    cfg["parameters"][f"{name}.reference_area"] = sum(
        area * length
        for area, length in zip(reference_areas, cell_lengths, strict=True)
    ) / sum(cell_lengths)
    cfg["parameters"][f"{name}.external_pressure"] = external_pressure
    cfg["parameters"][f"{name}.density"] = density
    cfg["parameters"][f"{name}.momentum_correction"] = 1.1
    for idx, value in enumerate(cell_lengths, start=1):
        cfg["parameters"][f"{name}.cell_length_{idx:02d}"] = value
    for idx, value in enumerate(reference_areas, start=1):
        cfg["parameters"][f"{name}.reference_area_{idx:02d}"] = value
    for idx, value in enumerate(wall_stiffnesses, start=1):
        cfg["parameters"][f"{name}.wall_stiffness_{idx:02d}"] = value
    for idx, value in enumerate(friction_coefficients, start=1):
        cfg["parameters"][f"{name}.friction_coefficient_{idx:02d}"] = value

    initial_areas = initial_areas_from_pressure_profile(
        reference_areas=reference_areas,
        wall_stiffnesses=wall_stiffnesses,
        cell_lengths=cell_lengths,
        inlet_pressure=node_pressure(cfg, "coupled_lpa_tcpc"),
        outlet_pressure=node_pressure(cfg, "lpa"),
        external_pressure=external_pressure,
    )
    for idx, area in enumerate(initial_areas, start=1):
        cfg["variables_initialization"][f"{name}.log_area_{idx:02d}"] = math.log(area)
        cfg["variables_magnitudes"][f"{name}.log_area_{idx:02d}"] = max(
            abs(math.log(area)),
            1.0,
        )

    initial_flow = FLOW_INITIALS[name]
    flow_magnitude = FLOW_MAGNITUDES[name]
    for idx, factor in enumerate(LPA_FLOW_MAGNITUDE_FACTORS):
        cfg["variables_initialization"][f"{name}.flow_{idx:02d}"] = initial_flow
        cfg["variables_magnitudes"][f"{name}.flow_{idx:02d}"] = (
            flow_magnitude * factor
        )


def add_resistance_loss_block(
    cfg: dict[str, Any],
    *,
    name: str,
    upstream: str,
    downstream: str,
    resistance: float,
) -> None:
    cfg["net"]["blocks"][name] = {
        "type": "block_description",
        "model_type": "rc_block",
        "time": "time",
        "flux_type": "blood_flow",
        "capacitance": "zero_capacitance",
        "nodes": {"1": downstream, "2": upstream},
    }
    cfg["parameters"][f"{name}.resistance"] = resistance


def add_aortic_junction_block(
    cfg: dict[str, Any],
    *,
    aorta_spec: dict[str, Any],
) -> None:
    name = "coupled_aortic_arch_junction"
    cfg["net"]["blocks"][name] = {
        "type": "block_description",
        "model_type": AORTIC_JUNCTION_MODEL_TYPE,
        "flux_type": "blood_flow",
        "aao_flow": f"{name}.aao_flow",
        "dao_flow": f"{name}.dao_flow",
        "bca_flow": f"{name}.bca_flow",
        "lcca_flow": f"{name}.lcca_flow",
        "lsa_flow": f"{name}.lsa_flow",
        "log_area_aao": "coupled_aao.log_area_03",
        "log_area_dao": "coupled_dao.log_area_01",
        "log_area_bca": "coupled_bca.log_area_01",
        "log_area_lcca": "coupled_lcca.log_area_01",
        "density": f"{name}.density",
        "nodes": {
            "1": "coupled_aao_arch",
            "2": "coupled_dao_arch",
            "3": "coupled_bca_arch",
            "4": "coupled_lcca_arch",
            "5": "coupled_lsa_arch",
        },
    }
    cfg["parameters"][f"{name}.density"] = float(
        aorta_spec["topology"]["segments"][0]["density_kg_m-3"]
    )
    for branch, (flow_key, magnitude_factor) in {
        "aao": ("coupled_aao", 1.01),
        "dao": ("coupled_dao", 0.97),
        "bca": ("coupled_bca", 1.03),
        "lcca": ("coupled_lcca", 0.99),
    }.items():
        cfg["variables_initialization"][f"{name}.{branch}_flow"] = FLOW_INITIALS[
            flow_key
        ]
        cfg["variables_magnitudes"][f"{name}.{branch}_flow"] = FLOW_MAGNITUDES[
            flow_key
        ] * magnitude_factor
    cfg["variables_initialization"][f"{name}.lsa_flow"] = AORTA_LSA_FLOW_INITIAL
    cfg["variables_magnitudes"][f"{name}.lsa_flow"] = (
        AORTA_LSA_FLOW_MAGNITUDE * 0.98
    )


def rewire_lsa_terminal_branch(cfg: dict[str, Any]) -> None:
    cfg["net"]["blocks"]["arch_lsa"]["nodes"] = {
        "1": "lsa",
        "2": "coupled_lsa_arch",
    }


def add_tcpc_junction_block(
    cfg: dict[str, Any],
    *,
    tcpc_spec: dict[str, Any],
) -> None:
    name = "coupled_tcpc_junction"
    cfg["net"]["blocks"][name] = {
        "type": "block_description",
        "model_type": TCPC_JUNCTION_MODEL_TYPE,
        "flux_type": "blood_flow",
        "svc_flow": f"{name}.svc_flow",
        "ivc_flow": f"{name}.ivc_flow",
        "rpa_flow": f"{name}.rpa_flow",
        "lpa_flow": f"{name}.lpa_flow",
        "log_area_svc": "coupled_svc.log_area_03",
        "log_area_ivc": "coupled_ivc.log_area_03",
        "log_area_rpa": "coupled_rpa.log_area_01",
        "log_area_lpa": "coupled_lpa.log_area_01",
        "reference_area_svc": "coupled_svc.reference_area",
        "reference_area_ivc": "coupled_ivc.reference_area",
        "reference_area_rpa": "coupled_rpa.reference_area",
        "reference_area_lpa": "coupled_lpa.reference_area_01",
        "wall_stiffness_svc": "coupled_svc.wall_stiffness",
        "wall_stiffness_ivc": "coupled_ivc.wall_stiffness",
        "wall_stiffness_rpa": "coupled_rpa.wall_stiffness",
        "wall_stiffness_lpa": "coupled_lpa.wall_stiffness_01",
        "external_pressure_svc": "coupled_svc.external_pressure",
        "external_pressure_ivc": "coupled_ivc.external_pressure",
        "external_pressure_rpa": "coupled_rpa.external_pressure",
        "external_pressure_lpa": "coupled_lpa.external_pressure",
        "density": f"{name}.density",
        "wall_pressure_weight": f"{name}.wall_pressure_weight",
        "characteristic_scale": f"{name}.characteristic_scale",
        "loss_coefficient": f"{name}.loss_coefficient",
        "nodes": {
            "1": "coupled_svc_tcpc",
            "2": "coupled_ivc_tcpc",
            "3": "coupled_rpa_tcpc",
            "4": "coupled_lpa_tcpc",
        },
    }
    cfg["parameters"][f"{name}.density"] = float(
        tcpc_spec["topology"]["segments"][0]["density_kg_m-3"]
    )
    cfg["parameters"][f"{name}.wall_pressure_weight"] = 0.75
    cfg["parameters"][f"{name}.characteristic_scale"] = 0.0
    cfg["parameters"][f"{name}.loss_coefficient"] = 2.0
    for branch, definition in TCPC_BRANCH_DEFINITIONS.items():
        flow_key = definition["flow_initial"]
        cfg["variables_initialization"][f"{name}.{branch}_flow"] = FLOW_INITIALS[
            flow_key
        ]
        cfg["variables_magnitudes"][f"{name}.{branch}_flow"] = FLOW_MAGNITUDES[
            flow_key
        ] * TCPC_BRANCH_FLOW_MAGNITUDE_FACTORS[branch]


def aorta_loss_resistances(
    source_cfg: dict[str, Any],
    aorta_spec: dict[str, Any],
) -> dict[str, float]:
    segments_by_source = {
        segment["source_segment"]: segment
        for segment in aorta_spec["topology"]["segments"]
    }
    losses: dict[str, float] = {}
    for name, definition in AORTA_TERMINAL_LOSS_DEFINITIONS.items():
        target_resistance = float(source_cfg["parameters"][definition["resistance"]])
        one_d_resistance = sum(
            float(segments_by_source[source]["poiseuille_resistance_pa_s_m-3"])
            for source in definition["segments"]
        )
        losses[name] = max(target_resistance - one_d_resistance, 0.0)
    return losses


def stabilize_time_settings(cfg: dict[str, Any], scenario: str) -> None:
    cfg["time"]["step_size"] = min(float(cfg["time"]["step_size"]), 2.5e-4)
    cfg["time"]["min_step"] = min(float(cfg["time"]["min_step"]), 1.5625e-5)
    if scenario != "smoke":
        return
    cfg["time"]["duration"] = min(float(cfg["time"]["duration"]), 2.5e-2)


def add_aorta_segments(
    cfg: dict[str, Any],
    aorta_spec: dict[str, Any],
    source_cfg: dict[str, Any],
    loss_resistances: dict[str, float],
) -> None:
    arch_pressure = node_pressure(source_cfg, "aortic_arch")
    arch_magnitude = node_pressure_magnitude(source_cfg, "aortic_arch")
    add_node(
        cfg,
        "coupled_aao_arch",
        0.5 * (node_pressure(cfg, "aao") + arch_pressure),
        1.03 * max(node_pressure_magnitude(cfg, "aao"), arch_magnitude),
    )
    add_node(
        cfg,
        "coupled_dao_arch",
        arch_pressure,
        0.97 * max(arch_magnitude, node_pressure_magnitude(cfg, "dao")),
    )
    add_node(
        cfg,
        "coupled_bca_arch",
        arch_pressure,
        1.01 * max(arch_magnitude, node_pressure_magnitude(cfg, "bca")),
    )
    add_node(
        cfg,
        "coupled_lcca_arch",
        arch_pressure,
        0.99 * max(arch_magnitude, node_pressure_magnitude(cfg, "lcca")),
    )
    add_node(
        cfg,
        "coupled_lsa_arch",
        arch_pressure,
        0.98 * max(arch_magnitude, node_pressure_magnitude(cfg, "lsa")),
    )
    add_node(
        cfg,
        "coupled_dao_out",
        0.5 * (arch_pressure + node_pressure(cfg, "dao")),
        max(arch_magnitude, node_pressure_magnitude(cfg, "dao")),
    )
    add_node(
        cfg,
        "coupled_bca_out",
        0.5 * (arch_pressure + node_pressure(cfg, "bca")),
        max(arch_magnitude, node_pressure_magnitude(cfg, "bca")),
    )
    add_node(
        cfg,
        "coupled_lcca_out",
        0.5 * (arch_pressure + node_pressure(cfg, "lcca")),
        max(arch_magnitude, node_pressure_magnitude(cfg, "lcca")),
    )

    for segment in aorta_spec["topology"]["segments"]:
        source = segment["source_segment"]
        node_1, node_2 = AORTA_NODE_MAP[source]
        add_vessel_block(
            cfg,
            name=SEGMENT_NAME_MAP[source],
            segment=segment,
            node_1=node_1,
            node_2=node_2,
        )

    add_aortic_junction_block(cfg, aorta_spec=aorta_spec)
    rewire_lsa_terminal_branch(cfg)

    for name, definition in AORTA_TERMINAL_LOSS_DEFINITIONS.items():
        add_resistance_loss_block(
            cfg,
            name=name,
            upstream=definition["upstream"],
            downstream=definition["downstream"],
            resistance=loss_resistances[name],
        )


def add_tcpc_segments(
    cfg: dict[str, Any],
    tcpc_spec: dict[str, Any],
    source_cfg: dict[str, Any],
) -> None:
    tcpc_pressure = float(source_cfg["variables_initialization"]["tcpc.blood_pressure"])
    tcpc_magnitude = float(source_cfg["variables_magnitudes"]["tcpc.blood_pressure"])
    add_node(
        cfg,
        "coupled_svc_tcpc",
        0.5 * (node_pressure(cfg, "svc") + tcpc_pressure),
        1.03 * max(node_pressure_magnitude(cfg, "svc"), tcpc_magnitude),
    )
    add_node(
        cfg,
        "coupled_ivc_tcpc",
        0.5 * (node_pressure(cfg, "ivc") + tcpc_pressure),
        0.97 * max(node_pressure_magnitude(cfg, "ivc"), tcpc_magnitude),
    )
    add_node(
        cfg,
        "coupled_rpa_tcpc",
        0.5 * (tcpc_pressure + node_pressure(cfg, "rpa")),
        1.01 * max(tcpc_magnitude, node_pressure_magnitude(cfg, "rpa")),
    )
    add_node(
        cfg,
        "coupled_lpa_tcpc",
        0.5 * (tcpc_pressure + node_pressure(cfg, "lpa")),
        0.99 * max(tcpc_magnitude, node_pressure_magnitude(cfg, "lpa")),
    )

    segments_by_source = {
        segment["source_segment"]: segment
        for segment in tcpc_spec["topology"]["segments"]
    }
    for segment in tcpc_spec["topology"]["segments"]:
        source = segment["source_segment"]
        if source not in TCPC_NODE_MAP:
            continue
        node_1, node_2 = TCPC_NODE_MAP[source]
        add_vessel_block(
            cfg,
            name=SEGMENT_NAME_MAP[source],
            segment=segment,
            node_1=node_1,
            node_2=node_2,
        )

    add_lpa_composite_block(cfg, segments_by_source=segments_by_source)
    add_tcpc_junction_block(cfg, tcpc_spec=tcpc_spec)


def add_metadata(cfg: dict[str, Any], scenario: str) -> None:
    cfg["model_family"] = "coupled_0d_1d"
    cfg["scenario"] = scenario
    cfg["generated_by"] = "scripts/modeling/build_coupled_configs.py"
    cfg["coupled_0d_1d"] = {
        "status": "paper_aligned_topology_candidate",
        "source_model": "models/full_0d",
        "aorta_openloop_spec": "models/coupled_0d_1d/configs/submodel_aorta_1d_openloop.jsonc",
        "tcpc_openloop_spec": "models/coupled_0d_1d/configs/submodel_tcpc_1d_openloop.jsonc",
        "topology_policy": [
            "replace aortic trunk, BCA, and left carotid shortcut resistors with true 1-D segment blocks",
            "replace the shared aortic arch pressure split with a massless total-pressure aortic junction",
            "keep DAo, BCA, and LCCA terminal loss blocks only as downstream afterload corrections",
            "retain the calibrated full 0-D LSA terminal branch as a non-1-D aortic outlet because no patient-specific LSA 1-D geometry is available",
            "replace SVC, IVC, and RPA TCPC conduit shortcuts with true 1-D segment blocks",
            "represent LPA I and LPA II as one six-cell tapered true 1-D composite to avoid an artificial massless internal junction",
            "replace the finite-storage TCPC star with a massless wall-pressure-blended dissipative total-pressure TCPC junction",
            "use a stiff-conduit TCPC wall scale, wall-pressure weight 0.75, and signed dynamic minor-loss coefficient 2.0 for the uncalibrated closed-loop startup model",
            "use log-area 1-D states so closed-loop Newton iterations remain in the positive-area domain",
            "do not prescribe both pressure and flow at a coupled 0-D/1-D boundary",
            "initialize 1-D areas from the nodal pressure state through the wall law",
        ],
        "limitations": [
            "aorta, SVC, IVC, and RPA source segments are represented by fixed 3-cell true 1-D blocks",
            "the LPA composite resolves source taper over six cells but still uses a one-dimensional centerline approximation",
            "the aortic junction is a no-loss total-pressure coupler; the TCPC junction is wall-pressure blended with signed dynamic minor losses, but still not Nektar's full characteristic/Riemann boundary solver or a 3-D TCPC model",
            "baseline is not calibrated yet",
        ],
    }


def build_config(source: Path, scenario: str) -> dict[str, Any]:
    source_cfg = load(source)
    cfg = deepcopy(source_cfg)
    aorta_spec = load(AORTA_SPEC)
    tcpc_spec = load(TCPC_SPEC)
    aorta_losses = aorta_loss_resistances(source_cfg, aorta_spec)
    remove_existing_lumped_paths(cfg)
    add_aorta_segments(cfg, aorta_spec, source_cfg, aorta_losses)
    add_tcpc_segments(cfg, tcpc_spec, source_cfg)
    stabilize_time_settings(cfg, scenario)
    add_metadata(cfg, scenario)
    return cfg


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build executable coupled 0-D/1-D closed-loop configs."
    )
    parser.add_argument("--check", action="store_true", help="verify generated configs are current")
    args = parser.parse_args()

    ok = True
    outputs: list[str] = []
    for scenario, (source, output) in SCENARIOS.items():
        cfg = build_config(source, scenario)
        ok = write_json(output, cfg, check=args.check) and ok
        outputs.append(str(output.relative_to(ROOT)))

    if args.check and not ok:
        raise SystemExit("coupled 0-D/1-D configs are stale")
    print(json.dumps({"configs": outputs}, indent=2))


if __name__ == "__main__":
    main()
