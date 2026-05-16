from __future__ import annotations

import json
from pathlib import Path

from scripts.calibration.compare_waveforms import compare
from scripts.calibration.map_aortic_signals import (
    DEFAULT_POLICY_PATH,
    aortic_superiority_waveforms,
    load_policy,
)

ROOT = Path(__file__).resolve().parents[1]


def test_task0089_policy_defines_clinical_and_chain_health_dao_signals():
    policy = load_policy(DEFAULT_POLICY_PATH)
    signals = {row["signal_id"]: row for row in policy["signals"]}

    assert policy["task"] == "008.9"
    assert policy["phase_policy"]["phase_shifted_nrmse_use"] == "diagnostic_only"
    assert signals["Q_AAo"]["model_columns"]["quasi_0d_1d"] == ["valve_arterial.flux"]
    assert signals["Q_DAo"]["model_columns"]["quasi_0d_1d"] == ["lower_ra4.flow"]
    assert signals["Q_DAo"]["comparison_role"] == "soft_target"
    assert signals["Q_DAo_chain_health"]["model_columns"]["quasi_0d_1d"] == [
        "quasi_dao_rl_06.flux"
    ]
    assert signals["Q_DAo_chain_health"]["include_in_no_strong_regression"] is True
    assert aortic_superiority_waveforms(policy) == (
        "ascending_aorta_flow",
        "descending_aorta_chain_health_flow",
    )


def test_waveform_report_uses_aortic_policy_rows():
    payload = json.loads(
        (
            ROOT / "models/quasi_0d_1d/calibration/baseline_waveforms_direct.json"
        ).read_text(encoding="utf-8")
    )
    rows = {row["canonical_name"]: row for row in payload["waveforms"]}

    assert rows["ascending_aorta_flow"]["signal_policy_id"] == "Q_AAo"
    assert rows["ascending_aorta_flow"]["model_signal"] == "valve_arterial.flux"
    assert rows["descending_aorta_flow"]["signal_policy_id"] == "Q_DAo"
    assert rows["descending_aorta_flow"]["model_signal"] == "lower_ra4.flow"
    assert rows["descending_aorta_flow"]["include_in_no_strong_regression"] is False
    assert rows["descending_aorta_chain_health_flow"]["signal_policy_id"] == (
        "Q_DAo_chain_health"
    )
    assert rows["descending_aorta_chain_health_flow"]["model_signal"] == (
        "quasi_dao_rl_06.flux"
    )
    assert rows["descending_aorta_chain_health_flow"]["target_canonical_name"] == (
        "descending_aorta_flow"
    )
    assert rows["descending_aorta_chain_health_flow"]["include_in_no_strong_regression"] is True


def test_compare_waveforms_regenerates_tracked_policy_mapping():
    tracked = json.loads(
        (
            ROOT / "models/quasi_0d_1d/calibration/baseline_waveforms_direct.json"
        ).read_text(encoding="utf-8")
    )
    regenerated = compare(
        ROOT / "runs/simulations/QuasiBaseline/eden_QuasiBaseline_2/main.csv",
        ROOT / "models/quasi_0d_1d/configs/fontan_quasi_baseline.jsonc",
        "direct_measurement",
        ROOT / "runs/simulations/Baseline/eden_Baseline_3/main.csv",
        ROOT / "models/full_0d/configs/fontan_0d_baseline.jsonc",
        DEFAULT_POLICY_PATH,
    )

    tracked_rows = {row["canonical_name"]: row for row in tracked["waveforms"]}
    regenerated_rows = {row["canonical_name"]: row for row in regenerated["waveforms"]}
    for name in [
        "ascending_aorta_flow",
        "descending_aorta_flow",
        "descending_aorta_chain_health_flow",
    ]:
        assert regenerated_rows[name]["model_signal"] == tracked_rows[name]["model_signal"]
        assert regenerated_rows[name]["reference_signal"] == tracked_rows[name]["reference_signal"]
        assert regenerated_rows[name]["signal_policy_id"] == tracked_rows[name]["signal_policy_id"]
