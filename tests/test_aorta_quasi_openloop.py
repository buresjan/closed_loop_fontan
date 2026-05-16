from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from scripts.quasi.evaluate_aorta_quasi_openloop import (
    best_phase_shift_nrmse,
    diagnose_failure,
    normalized_rmse,
)
from scripts.quasi.run_aorta_quasi_openloop import build_config

ROOT = Path(__file__).resolve().parents[1]


def test_openloop_config_contains_prescribed_inflow_and_terminal_pressure_boundaries():
    config = build_config("paper_closedloop", cycles=2)

    assert config["diagnostic_metadata"]["task"] == "008.8"
    assert "aao_inflow.blood_flow" in config["parameters"]
    assert config["parameters"]["aao_inflow.blood_flow"]["type"] == "piecewise_linear_periodic"
    assert config["net"]["boundaries_conditions"]["aao"][0]["condition_type"] == "blood_flow"
    assert config["net"]["boundaries_conditions"]["svc"][0]["condition_type"] == "blood_pressure"
    assert config["net"]["boundaries_conditions"]["ivc"][0]["condition_type"] == "blood_pressure"

    blocks = config["net"]["blocks"]
    assert "quasi_aao_arch_rl_01" in blocks
    assert "quasi_dao_rl_06" in blocks
    assert "lower_ra4" in blocks
    assert "upper_rv1" in blocks
    assert "valve_arterial" not in blocks
    assert "cavity" not in blocks


def test_openloop_config_fixture_is_current_if_present():
    fixture = ROOT / "models/quasi_0d_1d/configs/submodel_aorta_quasi_openloop.jsonc"
    if not fixture.exists():
        pytest.skip("Task 008.8 fixture has not been generated yet")
    assert json.loads(fixture.read_text(encoding="utf-8")) == build_config("paper_closedloop", cycles=12)


def test_waveform_phase_shift_diagnostic_detects_timing_component():
    phase = np.linspace(0.0, 0.99, 100)
    target = np.sin(2.0 * np.pi * phase)
    model_phase = (phase + 0.2) % 1.0

    direct = normalized_rmse(phase, target, model_phase, target)
    shifted, _ = best_phase_shift_nrmse(phase, target, model_phase, target)

    assert shifted < direct


def test_failure_diagnosis_keeps_chain_and_lower_body_location_distinct():
    flow_rows = [
        {
            "canonical_name": "descending_aorta_flow",
            "normalized_rmse": 1.0,
            "sign_flipped_normalized_rmse": 0.9,
            "best_phase_shift_normalized_rmse": 0.9,
            "amplitude_relative_error": 0.1,
        },
        {
            "canonical_name": "lower_ra4_flow",
            "normalized_rmse": 0.4,
            "sign_flipped_normalized_rmse": 0.8,
            "best_phase_shift_normalized_rmse": 0.3,
            "amplitude_relative_error": 0.1,
        },
    ]
    pressure_rows = [
        {
            "canonical_name": "descending_aorta_pressure",
            "mean_error_mmHg": 0.0,
            "pulse_pressure_relative_error": 0.0,
        }
    ]
    drops = {
        "model_aao_to_dao_mean_drop_mmHg": 1.0,
        "target_aao_to_dao_mean_drop_mmHg": 1.0,
    }

    diagnosis = diagnose_failure(flow_rows, pressure_rows, drops)

    assert any("target-location mismatch" in item for item in diagnosis["likely_causes"])


def test_openloop_artifacts_report_required_diagnostics_if_present():
    metrics_path = ROOT / "models/quasi_0d_1d/calibration/aorta_quasi_openloop_metrics.json"
    report_path = ROOT / "models/quasi_0d_1d/calibration/aorta_quasi_openloop_report.md"
    if not metrics_path.exists() or not report_path.exists():
        pytest.skip("Task 008.8 diagnostic artifacts have not been generated yet")

    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    report = report_path.read_text(encoding="utf-8")

    assert metrics["task"] == "008.8"
    assert metrics["gate_status"]["status"] in {
        "pass_open_loop_aortic_diagnostic",
        "fail_open_loop_aortic_diagnostic",
    }
    flow_names = {row["canonical_name"] for row in metrics["flow_metrics"]}
    assert {"descending_aorta_flow", "lower_ra4_flow"} <= flow_names
    assert metrics["failure_diagnosis"]["likely_causes"]

    required_report_text = [
        "Task 008.8 status:",
        "Sign-flipped nRMSE",
        "Best phase-shift nRMSE",
        "`quasi_dao_rl_06.flux`",
        "`lower_ra4.flow`",
        "Failure Diagnosis",
    ]
    for text in required_report_text:
        assert text in report
