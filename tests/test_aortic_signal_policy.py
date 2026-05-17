from __future__ import annotations

import json
from pathlib import Path

from scripts.calibration.compare_waveforms import compare

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICY_PATH = ROOT / "models/quasi_0d_1d/calibration/aortic_signal_policy.json"


def load_policy(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def aortic_superiority_waveforms(policy: dict) -> tuple[str, ...]:
    return tuple(
        row["canonical_name"]
        for row in policy["signals"]
        if row.get("quantity") == "flow" and row.get("include_in_superiority_gate")
    )


def test_policy_defines_clinical_and_chain_health_dao_signals():
    policy = load_policy(DEFAULT_POLICY_PATH)
    signals = {row["signal_id"]: row for row in policy["signals"]}

    assert policy["status"] == "active"
    assert policy["phase_policy"]["phase_shifted_nrmse_use"] == "diagnostic_only"
    assert signals["Q_AAo"]["model_columns"]["quasi_0d_1d"] == ["valve_arterial.flux"]
    assert signals["Q_DAo"]["model_columns"]["quasi_0d_1d"] == ["lower_ra4.flow"]
    assert signals["Q_DAo"]["comparison_role"] == "soft_target"
    assert signals["Q_DAo"]["evidence"]["accepted_quasi"][
        "model_signal"
    ] == "lower_ra4.flow"
    assert signals["Q_DAo_chain_health"]["model_columns"]["quasi_0d_1d"] == [
        "quasi_dao_rl_06.flux"
    ]
    assert signals["Q_DAo_chain_health"]["include_in_no_strong_regression"] is True
    assert signals["Q_DAo_chain_health"]["evidence"]["accepted_quasi"][
        "improves_normalized_rmse"
    ] is True
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
        ROOT / tracked["model_csv"],
        ROOT / tracked["model_config"],
        "direct_measurement",
        ROOT / tracked["reference_csv"],
        ROOT / tracked["reference_config"],
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
