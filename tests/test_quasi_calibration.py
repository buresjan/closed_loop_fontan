from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.calibration.quasi import DEFAULT_QUASI_FACTORS

ROOT = Path(__file__).resolve().parents[1]
FULL_BASELINE = ROOT / "models/full_0d/configs/fontan_0d_baseline.jsonc"
QUASI_BASELINE = ROOT / "models/quasi_0d_1d/configs/fontan_quasi_baseline.jsonc"
FRAGMENT = ROOT / "models/quasi_0d_1d/config_fragments/quasi_vessel_chains.json"
FACTORS = ROOT / "models/quasi_0d_1d/calibration/calibration_factors.json"


def load(path: Path) -> dict:
    return json.loads(path.read_text())


def chain_total(parameters: dict, chain: str, suffix: str) -> float:
    prefix = f"quasi_{chain}_"
    return sum(
        value
        for key, value in parameters.items()
        if key.startswith(prefix) and key.endswith(suffix)
    )


def fragment_total(fragment: dict, chain: str, suffix: str) -> float:
    return sum(
        value
        for key, value in fragment["chains"][chain]["parameters"].items()
        if key.endswith(suffix)
    )


def test_task008_calibration_factors_are_tracked_and_applied():
    full = load(FULL_BASELINE)
    quasi = load(QUASI_BASELINE)
    tracked = load(FACTORS)["factors"]

    assert tracked == DEFAULT_QUASI_FACTORS
    assert quasi["parameters"]["heart_contractility"] == pytest.approx(
        full["parameters"]["heart_contractility"]
        * DEFAULT_QUASI_FACTORS["heart_contractility_scale"]
    )
    assert quasi["parameters"]["upper_rc1.resistance"] == pytest.approx(
        full["parameters"]["upper_rc1.resistance"]
        * DEFAULT_QUASI_FACTORS["upper_systemic_resistance_scale"]
    )
    assert quasi["parameters"]["lower_rc2.resistance"] == pytest.approx(
        full["parameters"]["lower_rc2.resistance"]
        * DEFAULT_QUASI_FACTORS["lower_systemic_resistance_scale"]
    )
    assert quasi["parameters"]["right_lung.resistance_1"] == pytest.approx(
        full["parameters"]["right_lung.resistance_1"]
        * DEFAULT_QUASI_FACTORS["pulmonary_bed_resistance_scale"]
    )


def test_task008_preserves_quasi_chain_totals():
    quasi = load(QUASI_BASELINE)
    fragment = load(FRAGMENT)
    params = quasi["parameters"]

    for chain in ["aao_arch", "dao", "svc", "ivc", "rpa", "lpa"]:
        assert chain_total(params, chain, ".resistance") == pytest.approx(
            fragment_total(fragment, chain, ".resistance")
        )
        assert chain_total(params, chain, ".inductance") == pytest.approx(
            fragment_total(fragment, chain, ".inductance")
        )
        assert chain_total(params, chain, ".capacitance") == pytest.approx(
            fragment_total(fragment, chain, ".capacitance")
        )
