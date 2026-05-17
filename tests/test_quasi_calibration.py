from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.calibration.quasi import (
    ACCEPTED_ACTIVE_ATRIUM_ELASTANCE_SCALE,
    ACCEPTED_ACTIVE_ATRIUM_UNSTRESSED_VOLUME_SCALE,
    ACCEPTED_AORTIC_ENDPOINT_COMPLIANCE_SCALE,
    ACCEPTED_CAVAL_COMPLIANCE_SCALE,
    ACCEPTED_HEART_RADIUS_SCALE,
    ACCEPTED_LOWER_SYSTEMIC_PROXIMAL_FRACTION,
    ACCEPTED_LOWER_SYSTEMIC_RESISTANCE_SCALE,
    ACCEPTED_LOWER_VENOUS_COMPLIANCE_SCALE,
    ACCEPTED_QUASI_FACTORS,
    ACCEPTED_TERMINAL_ARTERIAL_COMPLIANCE_SCALE,
    ACCEPTED_UPPER_VENOUS_COMPLIANCE_SCALE,
    AORTIC_ENDPOINT_COMPLIANCES,
    LOWER_SYSTEMIC_RESISTANCES,
    TERMINAL_ARTERIAL_COMPLIANCES,
)

ROOT = Path(__file__).resolve().parents[1]
FULL_BASELINE = ROOT / "models/full_0d/configs/fontan_0d_baseline.jsonc"
QUASI_BASELINE = ROOT / "models/quasi_0d_1d/configs/fontan_quasi_baseline.jsonc"
FRAGMENT = ROOT / "models/quasi_0d_1d/config_fragments/quasi_vessel_chains_corrected.json"
CALIBRATION_FACTORS = ROOT / "models/quasi_0d_1d/calibration/calibration_factors.json"


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


def pulmonary_total(parameters: dict, side: str) -> float:
    return (
        parameters[f"{side}_lung.resistance_1"]
        + parameters[f"{side}_lung.resistance_2"]
    )


def pulmonary_proximal_fraction(parameters: dict, side: str) -> float:
    return parameters[f"{side}_lung.resistance_1"] / pulmonary_total(parameters, side)


def test_accepted_calibration_factors_are_tracked():
    tracked = load(CALIBRATION_FACTORS)

    assert tracked["accepted_as_superior"] is True
    assert tracked["factors"] == ACCEPTED_QUASI_FACTORS


def test_accepted_calibration_factors_are_applied():
    full = load(FULL_BASELINE)
    quasi = load(QUASI_BASELINE)

    assert quasi["parameters"]["heart_contractility"] == pytest.approx(
        full["parameters"]["heart_contractility"]
        * ACCEPTED_QUASI_FACTORS["heart_contractility_scale"]
    )
    assert quasi["parameters"]["upper_rc1.resistance"] == pytest.approx(
        full["parameters"]["upper_rc1.resistance"]
        * ACCEPTED_QUASI_FACTORS["upper_systemic_resistance_scale"]
    )
    assert sum(quasi["parameters"][name] for name in LOWER_SYSTEMIC_RESISTANCES) == (
        pytest.approx(
            sum(full["parameters"][name] for name in LOWER_SYSTEMIC_RESISTANCES)
            * ACCEPTED_QUASI_FACTORS["lower_systemic_resistance_scale"]
            * ACCEPTED_LOWER_SYSTEMIC_RESISTANCE_SCALE
        )
    )
    assert quasi["parameters"]["lower_ra4.resistance"] / sum(
        quasi["parameters"][name] for name in LOWER_SYSTEMIC_RESISTANCES
    ) == pytest.approx(
        ACCEPTED_LOWER_SYSTEMIC_PROXIMAL_FRACTION
    )
    assert pulmonary_total(quasi["parameters"], "right") == pytest.approx(
        pulmonary_total(full["parameters"], "right")
        * ACCEPTED_QUASI_FACTORS["right_pulmonary_total_resistance_scale"]
    )
    assert pulmonary_total(quasi["parameters"], "left") == pytest.approx(
        pulmonary_total(full["parameters"], "left")
        * ACCEPTED_QUASI_FACTORS["left_pulmonary_total_resistance_scale"]
    )
    assert pulmonary_proximal_fraction(quasi["parameters"], "right") == pytest.approx(
        ACCEPTED_QUASI_FACTORS["right_pulmonary_proximal_fraction"]
    )
    assert pulmonary_proximal_fraction(quasi["parameters"], "left") == pytest.approx(
        ACCEPTED_QUASI_FACTORS["left_pulmonary_proximal_fraction"]
    )
    for name in AORTIC_ENDPOINT_COMPLIANCES:
        assert quasi["parameters"][name] == pytest.approx(
            full["parameters"][name] * ACCEPTED_AORTIC_ENDPOINT_COMPLIANCE_SCALE
        )
    for name in TERMINAL_ARTERIAL_COMPLIANCES:
        assert quasi["parameters"][name] == pytest.approx(
            full["parameters"][name] * ACCEPTED_TERMINAL_ARTERIAL_COMPLIANCE_SCALE
        )
    assert quasi["parameters"]["upper_cv1.capacitance"] == pytest.approx(
        full["parameters"]["upper_cv1.capacitance"]
        * ACCEPTED_UPPER_VENOUS_COMPLIANCE_SCALE
    )
    assert quasi["parameters"]["lower_cv2.capacitance"] == pytest.approx(
        full["parameters"]["lower_cv2.capacitance"]
        * ACCEPTED_LOWER_VENOUS_COMPLIANCE_SCALE
    )
    assert quasi["parameters"]["svc_compliance.capacitance"] == pytest.approx(
        full["parameters"]["svc_compliance.capacitance"]
        * ACCEPTED_CAVAL_COMPLIANCE_SCALE
    )
    assert quasi["parameters"]["ivc_compliance.capacitance"] == pytest.approx(
        full["parameters"]["ivc_compliance.capacitance"]
        * ACCEPTED_CAVAL_COMPLIANCE_SCALE
    )
    assert quasi["parameters"]["active_atrium.unstressed_volume"] == pytest.approx(
        full["parameters"]["active_atrium.unstressed_volume"]
        * ACCEPTED_ACTIVE_ATRIUM_UNSTRESSED_VOLUME_SCALE
    )
    assert quasi["parameters"]["active_atrium.elastance_min"] == pytest.approx(
        full["parameters"]["active_atrium.elastance_min"]
        * ACCEPTED_ACTIVE_ATRIUM_ELASTANCE_SCALE
    )
    assert quasi["parameters"]["active_atrium.elastance_max"] == pytest.approx(
        full["parameters"]["active_atrium.elastance_max"]
        * ACCEPTED_ACTIVE_ATRIUM_ELASTANCE_SCALE
    )
    assert quasi["parameters"]["heart_radius"] == pytest.approx(
        full["parameters"]["heart_radius"] * ACCEPTED_HEART_RADIUS_SCALE
    )
    assert quasi["parameters"]["heart_thickness"] == pytest.approx(
        full["parameters"]["heart_thickness"] * ACCEPTED_HEART_RADIUS_SCALE
    )


def test_accepted_model_preserves_corrected_quasi_chain_totals():
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
