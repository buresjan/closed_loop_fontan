from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.modeling.build_quasi_configs import (
    OLD_PARAMETER_PREFIXES,
    OLD_PRESSURE_VARIABLES,
    OLD_SHORTCUT_BLOCKS,
    OLD_SHORTCUT_NODES,
    OLD_VARIABLE_PREFIXES,
    build_all_configs,
)

ROOT = Path(__file__).resolve().parents[1]
QUASI = ROOT / "models/quasi_0d_1d"
QUASI_CONFIGS = QUASI / "configs"
FRAGMENT = QUASI / "config_fragments/quasi_vessel_chains_corrected.json"
CONFIG_NAMES = {
    "fontan_quasi_smoke.jsonc",
    "fontan_quasi_baseline.jsonc",
    "fontan_quasi_vasodilation.jsonc",
    "fontan_quasi_fenestration.jsonc",
    "fontan_quasi_lpa_obstruction.jsonc",
}


def load_config(name: str) -> dict:
    return json.loads((QUASI_CONFIGS / name).read_text())


def load_fragment() -> dict:
    return json.loads(FRAGMENT.read_text())


def chain_total(parameters: dict, chain: str, suffix: str) -> float:
    prefix = f"quasi_{chain}_"
    return sum(
        value
        for key, value in parameters.items()
        if key.startswith(prefix) and key.endswith(suffix)
    )


def fragment_chain_total(fragment: dict, chain: str, suffix: str) -> float:
    return sum(
        value
        for key, value in fragment["chains"][chain]["parameters"].items()
        if key.endswith(suffix)
    )


def lung_resistance(parameters: dict, side: str) -> float:
    return parameters[f"{side}.resistance_1"] + parameters[f"{side}.resistance_2"]


def test_quasi_configs_are_present_and_generated_from_builder():
    assert CONFIG_NAMES <= {path.name for path in QUASI_CONFIGS.glob("fontan_quasi_*.jsonc")}
    assert not list(QUASI_CONFIGS.glob("fontan_quasi_*_task*_*.jsonc"))
    generated = build_all_configs()
    assert set(generated) == CONFIG_NAMES
    for name, config in generated.items():
        assert load_config(name) == config


def test_quasi_configs_are_strict_json_and_forward_simulations():
    for name in CONFIG_NAMES:
        config = load_config(name)
        assert config["type"] == "forward_simulation"
        assert config["net"]["type"] == "net"
        assert config["net"]["boundaries_conditions"] == {}


def test_quasi_configs_replace_shortcuts_with_hydraulic_chains():
    for name in CONFIG_NAMES:
        config = load_config(name)
        nodes = set(config["net"]["nodes"])
        blocks = config["net"]["blocks"]
        parameters = config["parameters"]
        variables = {
            *config["variables_initialization"],
            *config["variables_magnitudes"],
        }

        assert nodes.isdisjoint(OLD_SHORTCUT_NODES)
        assert set(blocks).isdisjoint(OLD_SHORTCUT_BLOCKS)
        assert not [
            key for key in parameters if key.startswith(OLD_PARAMETER_PREFIXES)
        ]
        assert not [
            key
            for key in variables
            if key.startswith(OLD_VARIABLE_PREFIXES) or key in OLD_PRESSURE_VARIABLES
        ]

        valve_rl_blocks = [
            block_name
            for block_name, block in blocks.items()
            if block["model_type"] == "valve_rl_block"
        ]
        assert valve_rl_blocks == ["valve_atrium", "valve_arterial"]


def test_quasi_baseline_chain_topology_and_totals_match_fragment():
    config = load_config("fontan_quasi_baseline.jsonc")
    fragment = load_fragment()
    nodes = set(config["net"]["nodes"])
    blocks = config["net"]["blocks"]
    parameters = config["parameters"]

    for chain_name, chain in fragment["chains"].items():
        assert set(chain["nodes"]) <= nodes
        for node in chain["nodes"][1:-1]:
            assert f"{node}.blood_pressure" in config["variables_initialization"]
            assert f"{node}.blood_pressure" in config["variables_magnitudes"]

        for block_name, block in chain["blocks"].items():
            assert blocks[block_name] == block

        assert chain_total(parameters, chain_name, ".resistance") == pytest.approx(
            fragment_chain_total(fragment, chain_name, ".resistance")
        )
        assert chain_total(parameters, chain_name, ".inductance") == pytest.approx(
            fragment_chain_total(fragment, chain_name, ".inductance")
        )
        assert chain_total(parameters, chain_name, ".capacitance") == pytest.approx(
            fragment_chain_total(fragment, chain_name, ".capacitance")
        )


def test_quasi_scenarios_change_expected_parameters():
    base = load_config("fontan_quasi_baseline.jsonc")["parameters"]
    vaso = load_config("fontan_quasi_vasodilation.jsonc")["parameters"]
    fen = load_config("fontan_quasi_fenestration.jsonc")["parameters"]
    lpa = load_config("fontan_quasi_lpa_obstruction.jsonc")["parameters"]

    assert lung_resistance(vaso, "right_lung") < lung_resistance(base, "right_lung")
    assert lung_resistance(vaso, "left_lung") < lung_resistance(base, "left_lung")
    assert fen["fenestration.resistance"] < base["fenestration.resistance"]
    assert lung_resistance(lpa, "left_lung") > lung_resistance(base, "left_lung")

    assert lpa["quasi_lpa.narrowing_resistance_scale"] == pytest.approx(2.0)
    assert chain_total(lpa, "lpa", ".resistance") == pytest.approx(
        2.0 * chain_total(base, "lpa", ".resistance")
    )


def test_quasi_docs_name_executable_configs_and_chain_counts():
    readme = (QUASI / "README.md").read_text()
    notes = (QUASI / "docs/implementation_notes.md").read_text()
    schematic = (QUASI / "docs/quasi_0d_1d_schematic.svg").read_text()

    for name in CONFIG_NAMES:
        assert name in readme
    for text in [
        "AAo/arch x4",
        "DAo x6",
        "SVC x3",
        "IVC x5",
        "RPA x3",
        "LPA x4",
    ]:
        assert text in readme
        assert text in notes
        assert text in schematic
    assert "Accepted quasi configs" in schematic
