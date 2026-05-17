#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.calibration.quasi import apply_accepted_quasi_design

FULL_CONFIG_DIR = ROOT / "models/full_0d/configs"
QUASI_CONFIG_DIR = ROOT / "models/quasi_0d_1d/configs"
QUASI_FRAGMENT = (
    ROOT / "models/quasi_0d_1d/config_fragments/quasi_vessel_chains_corrected.json"
)

CONFIG_MAP = {
    "fontan_0d_smoke.jsonc": "fontan_quasi_smoke.jsonc",
    "fontan_0d_baseline.jsonc": "fontan_quasi_baseline.jsonc",
    "fontan_0d_vasodilation.jsonc": "fontan_quasi_vasodilation.jsonc",
    "fontan_0d_fenestration.jsonc": "fontan_quasi_fenestration.jsonc",
    "fontan_0d_lpa_obstruction.jsonc": "fontan_quasi_lpa_obstruction.jsonc",
}

OLD_SHORTCUT_NODES = {
    "svc_conduit",
    "ivc_conduit",
    "rpa_conduit",
    "lpa_conduit",
}

OLD_SHORTCUT_BLOCKS = {
    "aao_arch",
    "arch_dao",
    "svc_conduit_rl",
    "svc_conduit_junction",
    "svc_conduit_compliance",
    "ivc_conduit_rl",
    "ivc_conduit_junction",
    "ivc_conduit_compliance",
    "rpa_conduit_rl",
    "rpa_conduit_out",
    "rpa_conduit_compliance",
    "lpa_conduit_rl",
    "lpa_conduit_out",
    "lpa_conduit_compliance",
}

OLD_PARAMETER_PREFIXES = tuple(f"{name}." for name in OLD_SHORTCUT_BLOCKS)
OLD_VARIABLE_PREFIXES = tuple(f"{name}." for name in OLD_SHORTCUT_BLOCKS)
OLD_PRESSURE_VARIABLES = {
    f"{node}.blood_pressure" for node in OLD_SHORTCUT_NODES
}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def fontan_pathway_resistance(parameters: dict[str, float], side: str) -> float:
    if side in {"svc", "ivc"}:
        connector = parameters[f"{side}_conduit_junction.resistance"]
    else:
        connector = parameters[f"{side}_conduit_out.resistance"]
    return 1.0 / parameters[f"{side}_conduit_rl.conductance"] + connector


def remove_shortcut_topology(config: dict[str, Any]) -> None:
    net = config["net"]
    net["nodes"] = [
        node for node in net["nodes"] if node not in OLD_SHORTCUT_NODES
    ]
    for name in OLD_SHORTCUT_BLOCKS:
        net["blocks"].pop(name, None)

    parameters = config["parameters"]
    for key in list(parameters):
        if key.startswith(OLD_PARAMETER_PREFIXES):
            parameters.pop(key)

    for section_name in ["variables_initialization", "variables_magnitudes"]:
        section = config[section_name]
        for key in list(section):
            if key.startswith(OLD_VARIABLE_PREFIXES) or key in OLD_PRESSURE_VARIABLES:
                section.pop(key)


def interpolate_pressure(
    config: dict[str, Any],
    upstream: str,
    downstream: str,
    index: int,
    segment_count: int,
) -> float:
    variables = config["variables_initialization"]
    p1 = float(variables[f"{upstream}.blood_pressure"])
    p2 = float(variables[f"{downstream}.blood_pressure"])
    fraction = index / segment_count
    return p1 + fraction * (p2 - p1)


def add_internal_pressure_state(config: dict[str, Any], chain_nodes: list[str]) -> None:
    segment_count = len(chain_nodes) - 1
    upstream = chain_nodes[0]
    downstream = chain_nodes[-1]
    magnitudes = config["variables_magnitudes"]
    magnitude = max(
        float(magnitudes.get(f"{upstream}.blood_pressure", 0.0)),
        float(magnitudes.get(f"{downstream}.blood_pressure", 0.0)),
        2000.0,
    )

    for index, node in enumerate(chain_nodes[1:-1], start=1):
        pressure_key = f"{node}.blood_pressure"
        config["variables_initialization"][pressure_key] = interpolate_pressure(
            config,
            upstream,
            downstream,
            index,
            segment_count,
        )
        config["variables_magnitudes"][pressure_key] = magnitude


def add_quasi_chains(config: dict[str, Any], fragment: dict[str, Any]) -> None:
    net = config["net"]
    nodes = net["nodes"]
    for chain in fragment["chains"].values():
        for node in chain["nodes"][1:-1]:
            if node not in nodes:
                nodes.append(node)
        net["blocks"].update(copy.deepcopy(chain["blocks"]))
        config["parameters"].update(copy.deepcopy(chain["parameters"]))
        config["variables_initialization"].update(
            copy.deepcopy(chain["variables_initialization"])
        )
        config["variables_magnitudes"].update(copy.deepcopy(chain["variables_magnitudes"]))
        add_internal_pressure_state(config, chain["nodes"])

    config["parameters"].update(copy.deepcopy(fragment["parameters"]))


def apply_lpa_obstruction_scale(
    config: dict[str, Any],
    source_parameters: dict[str, float],
    baseline_lpa_pathway_resistance: float,
) -> None:
    current_lpa_pathway_resistance = fontan_pathway_resistance(source_parameters, "lpa")
    scale = current_lpa_pathway_resistance / baseline_lpa_pathway_resistance
    for key in list(config["parameters"]):
        if key.startswith("quasi_lpa_rl_") and key.endswith(".resistance"):
            config["parameters"][key] *= scale
    config["parameters"]["quasi_lpa.narrowing_resistance_scale"] = scale


def validate_quasi_config(config: dict[str, Any], fragment: dict[str, Any]) -> None:
    nodes = set(config["net"]["nodes"])
    blocks = config["net"]["blocks"]
    parameters = config["parameters"]
    variables = {
        *config["variables_initialization"],
        *config["variables_magnitudes"],
    }

    if nodes & OLD_SHORTCUT_NODES:
        raise ValueError(f"old conduit nodes remain: {sorted(nodes & OLD_SHORTCUT_NODES)}")
    if set(blocks) & OLD_SHORTCUT_BLOCKS:
        raise ValueError(
            f"old shortcut blocks remain: {sorted(set(blocks) & OLD_SHORTCUT_BLOCKS)}"
        )
    stale_parameters = [
        key for key in parameters if key.startswith(OLD_PARAMETER_PREFIXES)
    ]
    if stale_parameters:
        raise ValueError(f"old shortcut parameters remain: {stale_parameters}")
    stale_variables = [
        key
        for key in variables
        if key.startswith(OLD_VARIABLE_PREFIXES) or key in OLD_PRESSURE_VARIABLES
    ]
    if stale_variables:
        raise ValueError(f"old shortcut variables remain: {stale_variables}")

    for name, block in blocks.items():
        if block["model_type"] == "valve_rl_block" and name not in {
            "valve_atrium",
            "valve_arterial",
        }:
            raise ValueError(f"valve_rl_block used as non-valve conduit: {name}")

    for chain in fragment["chains"].values():
        missing_nodes = set(chain["nodes"]) - nodes
        if missing_nodes:
            raise ValueError(f"missing quasi chain nodes: {sorted(missing_nodes)}")
        missing_blocks = set(chain["blocks"]) - set(blocks)
        if missing_blocks:
            raise ValueError(f"missing quasi chain blocks: {sorted(missing_blocks)}")


def build_quasi_config(
    source_config: dict[str, Any],
    fragment: dict[str, Any],
    baseline_lpa_pathway_resistance: float,
    *,
    apply_task008_calibration: bool = True,
) -> dict[str, Any]:
    config = copy.deepcopy(source_config)
    source_parameters = copy.deepcopy(source_config["parameters"])
    remove_shortcut_topology(config)
    add_quasi_chains(config, fragment)
    apply_lpa_obstruction_scale(
        config,
        source_parameters,
        baseline_lpa_pathway_resistance,
    )
    if apply_task008_calibration:
        config = apply_accepted_quasi_design(config)
    validate_quasi_config(config, fragment)
    return config


def build_all_configs(*, apply_task008_calibration: bool = True) -> dict[str, dict[str, Any]]:
    fragment = load_json(QUASI_FRAGMENT)
    baseline = load_json(FULL_CONFIG_DIR / "fontan_0d_baseline.jsonc")
    baseline_lpa_pathway_resistance = fontan_pathway_resistance(
        baseline["parameters"],
        "lpa",
    )

    generated = {}
    for source_name, output_name in CONFIG_MAP.items():
        source = load_json(FULL_CONFIG_DIR / source_name)
        generated[output_name] = build_quasi_config(
            source,
            fragment,
            baseline_lpa_pathway_resistance,
            apply_task008_calibration=apply_task008_calibration,
        )
    return generated


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build runnable quasi 0-D/1-D PhysioBlocks configs."
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Validate generated configs against the tracked files without writing.",
    )
    parser.add_argument(
        "--uncalibrated",
        action="store_true",
        help="Build the raw quasi-chain configs without the accepted design/calibration factors.",
    )
    args = parser.parse_args()

    generated = build_all_configs(apply_task008_calibration=not args.uncalibrated)
    if args.check:
        for name, config in generated.items():
            tracked_path = QUASI_CONFIG_DIR / name
            tracked = load_json(tracked_path)
            if config != tracked:
                raise SystemExit(f"{tracked_path} is out of date")
        return

    for name, config in generated.items():
        write_json(QUASI_CONFIG_DIR / name, config)


if __name__ == "__main__":
    main()
