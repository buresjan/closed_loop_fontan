from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.calibration.compare_quasi_to_full0d import (
    DEFAULT_FULL_DIRECT,
    DEFAULT_FULL_METRICS,
    DEFAULT_FULL_PAPER,
    DEFAULT_QUASI_DIRECT,
    DEFAULT_QUASI_METRICS,
    DEFAULT_QUASI_PAPER,
    DEFAULT_WAVEFORMS,
    DEFAULT_AORTIC_PROFILE,
    FLOW_FRACTION_ABSOLUTE_TOLERANCE,
    FONTAN_TARGETS,
    TARGET_RELATIVE_ERROR_TOLERANCE,
    evaluate,
    full_reference_scores,
    superiority_gate_definition,
)

ROOT = Path(__file__).resolve().parents[1]


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def current_status() -> dict:
    return evaluate(
        full_direct=load(DEFAULT_FULL_DIRECT),
        quasi_direct=load(DEFAULT_QUASI_DIRECT),
        full_paper=load(DEFAULT_FULL_PAPER),
        quasi_paper=load(DEFAULT_QUASI_PAPER),
        full_metrics=load(DEFAULT_FULL_METRICS),
        quasi_metrics=load(DEFAULT_QUASI_METRICS),
        waveforms=load(DEFAULT_WAVEFORMS),
        aortic_profile=load(DEFAULT_AORTIC_PROFILE),
    )


def test_superiority_gate_definition_is_frozen_and_strict():
    gate = superiority_gate_definition()

    assert gate["status"] == "frozen"
    assert gate["tolerances"]["target_relative_error_non_regression"] == pytest.approx(0.005)
    assert TARGET_RELATIVE_ERROR_TOLERANCE == pytest.approx(0.005)
    assert FLOW_FRACTION_ABSOLUTE_TOLERANCE == pytest.approx(0.005)
    assert set(FONTAN_TARGETS) == {
        "rpa_pressure",
        "lpa_pressure",
        "svc_flow",
        "rpa_flow",
        "lpa_flow",
        "rpa_flow_fraction",
    }
    assert "descending_aorta_pressure" in gate["soft_problematic_targets"]
    assert "ivc_flow" in gate["soft_problematic_targets"]
    assert gate["aortic_flow_waveform_targets"] == [
        "ascending_aorta_flow",
        "descending_aorta_chain_health_flow",
    ]
    assert gate["aortic_signal_policy"].endswith("aortic_signal_policy.json")


def test_full0d_reference_scores_match_frozen_values():
    reference = full_reference_scores(
        load(DEFAULT_FULL_DIRECT),
        load(DEFAULT_FULL_PAPER),
        load(DEFAULT_WAVEFORMS),
    )

    scores = reference["scores"]
    assert scores["direct_score"] == pytest.approx(0.061385711944231244)
    assert scores["hard_clinical_summary_score"] == pytest.approx(0.04326800942219066)
    assert scores["paper_model_score"] == pytest.approx(0.07926178853036234)
    assert scores["aortic_flow_waveform_nrmse"]["ascending_aorta_flow"] == pytest.approx(0.5717890388728804)
    assert scores["aortic_flow_waveform_nrmse"]["descending_aorta_chain_health_flow"] == pytest.approx(0.433747643475799)


def test_current_quasi_is_superior_under_frozen_gate():
    status = current_status()

    assert status["status"] == "accepted_superior_to_full_0d"
    assert status["accepted_as_superior"] is True
    assert status["group_pass"]["stability"] is True
    assert status["group_pass"]["quasi_specific_vascular_improvement"] is True
    assert status["group_pass"]["score_non_regression"] is True
    assert status["group_pass"]["pump_non_regression"] is True
    assert status["group_pass"]["fontan_pulmonary_non_regression"] is True
    assert status["group_pass"]["aortic_waveform_no_regression"] is True

    failed_pump = {
        row["target_name"]
        for row in status["gates"]["pump_non_regression"]
        if not row["pass"]
    }
    assert failed_pump == set()


def test_tracked_gate_outputs_match_current_evaluation():
    status_path = ROOT / "models/quasi_0d_1d/calibration/current_quasi_gate_status.json"
    if not status_path.exists():
        pytest.skip("generated superiority outputs have not been written yet")

    tracked = load(status_path)
    evaluated = current_status()

    assert tracked["status"] == evaluated["status"]
    assert tracked["accepted_as_superior"] == evaluated["accepted_as_superior"]
    assert tracked["failed_groups"] == evaluated["failed_groups"]
