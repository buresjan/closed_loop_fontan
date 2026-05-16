from __future__ import annotations

import json

import pytest
import numpy as np

from scripts.calibration.audit_quasi_design import (
    best_phase_shift_nrmse,
    characteristic_impedance_rows,
    normalized_rmse,
)
from scripts.calibration.run_quasi_ablation_grid import (
    Candidate,
    apply_distributed_aortic_branches,
    apply_four_port_tcpc,
    candidate_config,
    scale_label,
)
from scripts.calibration.run_quasi_closure_calibration import (
    NON_SUPERIOR_STATUS,
    final_decision,
)


def test_normalized_rmse_and_phase_shift_helpers():
    phase = np.linspace(0.0, 0.9, 10)
    target = np.sin(2.0 * np.pi * phase)
    shifted_phase = (phase + 0.2) % 1.0

    assert normalized_rmse(phase, target, phase, target) == pytest.approx(0.0)

    direct = normalized_rmse(phase, target, shifted_phase, target)
    shifted, best_shift = best_phase_shift_nrmse(phase, target, shifted_phase, target)

    assert shifted < direct
    assert 0.0 <= best_shift < 1.0


def test_ablation_scale_labels_are_path_safe():
    assert scale_label(0.5) == "0_5"
    assert scale_label(2.0) == "2"


def test_distributed_aortic_branch_candidate_rewires_takeoffs():
    config = candidate_config(
        candidate=Candidate("test", "test", {"heart_contractility_scale": 1.0})
    )

    apply_distributed_aortic_branches(config, patient_geometry=True)

    assert config["net"]["blocks"]["arch_bca"]["nodes"]["1"] == "quasi_aao_arch_p_01"
    assert config["net"]["blocks"]["arch_lcca"]["nodes"]["1"] == "quasi_aao_arch_p_02"
    assert config["net"]["blocks"]["arch_lsa"]["nodes"]["1"] == "quasi_aao_arch_p_03"
    assert config["parameters"]["arch_lsa.resistance"] > 1.0e12


def test_four_port_tcpc_candidate_separates_limb_ports():
    config = candidate_config(
        candidate=Candidate("test", "test", {"heart_contractility_scale": 1.0})
    )

    apply_four_port_tcpc(config)

    for node in ["svc_port", "ivc_port", "rpa_port", "lpa_port"]:
        assert node in config["net"]["nodes"]
        assert f"{node}.blood_pressure" in config["variables_initialization"]

    assert config["net"]["blocks"]["quasi_svc_rl_03"]["nodes"]["2"] == "svc_port"
    assert config["net"]["blocks"]["quasi_ivc_rl_05"]["nodes"]["2"] == "ivc_port"
    assert config["net"]["blocks"]["quasi_rpa_rl_01"]["nodes"]["1"] == "rpa_port"
    assert config["net"]["blocks"]["quasi_lpa_rl_01"]["nodes"]["1"] == "lpa_port"
    assert config["net"]["blocks"]["svc_port_tcpc"]["model_type"] == "hydraulic_resistor_block"
    assert config["net"]["blocks"]["rpa_port_tcpc"]["nodes"] == {
        "1": "tcpc",
        "2": "rpa_port",
    }


def test_characteristic_impedance_report_has_all_quasi_chains(tmp_path):
    config = candidate_config(
        candidate=Candidate("test", "test", {"heart_contractility_scale": 1.0})
    )
    path = tmp_path / "candidate.json"
    path.write_text(json.dumps(config), encoding="utf-8")

    rows = characteristic_impedance_rows(path)

    assert {row["vessel"] for row in rows} == {
        "aao_arch",
        "dao",
        "svc",
        "ivc",
        "rpa",
        "lpa",
    }
    assert all(row["Zc_mmHg_s_ml"] >= 0.0 for row in rows)


def test_final_decision_keeps_non_superior_status_without_accepted_candidate():
    rows = [
        {
            "candidate": "task0085_reference",
            "status": "ok",
            "accepted_as_superior": "False",
            "hard_score": "0.05",
            "direct_score": "0.06",
            "paper_score": "0.08",
            "waveform_regression_rms": "0.3",
            "failed_hard_gates": "edv",
            "failed_waveform_gates": "ascending_aorta_flow",
        },
        {
            "candidate": "candidate_a",
            "status": "ok",
            "accepted_as_superior": "False",
            "hard_score": "0.04",
            "direct_score": "0.07",
            "paper_score": "0.09",
            "waveform_regression_rms": "0.4",
            "failed_hard_gates": "co",
            "failed_waveform_gates": "descending_aorta_flow",
        },
    ]

    decision = final_decision(rows, {"flow_signal_audit": []})

    assert decision["status"] == NON_SUPERIOR_STATUS
    assert decision["promoted_candidate"] is None
    assert decision["best_candidates"]["best_hard_score"]["candidate"] == "candidate_a"
