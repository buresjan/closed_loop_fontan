from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from scripts.calibration.check_target_consistency import (
    POLICY_COLUMNS,
    TARGET_DIR,
    aortic_pressure_order_for_source,
    build_consistency_payload,
    flow_closure_for_source,
    implied_ivc_from_direct,
    load_summary,
    target_policy_rows,
)
from scripts.calibration.objective import load_json

ROOT = Path(__file__).resolve().parents[1]
BASELINE_METRICS = ROOT / "models/full_0d/reference_outputs/baseline_metrics.json"


def test_direct_flow_targets_are_not_mass_closed():
    summary = load_summary()
    direct = flow_closure_for_source(summary, "direct_measurement")

    assert direct["co_ml_s"] == pytest.approx(42.89037840614597)
    assert direct["svc_plus_ivc_ml_s"] == pytest.approx(39.43281591884167)
    assert direct["rpa_plus_lpa_ml_s"] == pytest.approx(41.30661158518376)
    assert direct["co_minus_systemic_return_ml_s"] == pytest.approx(3.4575624873043)


def test_direct_implied_ivc_values_are_mass_closure_dependent():
    summary = load_summary()
    direct = flow_closure_for_source(summary, "direct_measurement")
    implied = implied_ivc_from_direct(direct)

    assert implied["raw_direct_ivc_ml_s"] == pytest.approx(18.84377590619485)
    assert implied["from_pulmonary_closure_ml_s"] == pytest.approx(20.71757157253694)
    assert implied["from_co_closure_ml_s"] == pytest.approx(22.30133839349915)


def test_aortic_pressure_order_flags_direct_but_accepts_paper_and_nektar():
    summary = load_summary()

    direct = aortic_pressure_order_for_source(summary, "direct_measurement")
    paper = aortic_pressure_order_for_source(summary, "paper_model")
    nektar = aortic_pressure_order_for_source(summary, "nektar_closed_loop_1d")

    assert direct["aao_ge_arch_ge_dao"] is False
    assert paper["aao_ge_arch_ge_dao"] is True
    assert nektar["aao_ge_arch_ge_dao"] is True


def test_consistency_payload_has_required_top_level_sections():
    payload = build_consistency_payload(load_summary(), load_json(BASELINE_METRICS))

    assert {
        "flow_closure",
        "implied_ivc",
        "aortic_pressure_order",
        "source_conflicts",
        "model_interpretation",
        "target_policy",
    } <= set(payload)
    assert payload["model_interpretation"]["ivc_flow"][
        "model_ivc_ml_s"
    ] == pytest.approx(21.57354998245344)


def test_target_policy_schema_and_required_rows():
    rows = target_policy_rows()
    assert rows
    assert set(rows[0]) == set(POLICY_COLUMNS)
    keyed = {(row["quantity"], row["source"]): row for row in rows}

    assert keyed[("IVC flow", "direct_measurement")]["weight_class"] == "soft"
    assert keyed[("Direct DAo pressure", "direct_measurement")]["role"] == "diagnostic"
    assert (
        keyed[("Paper/Nektar DAo pressure", "paper_model_or_nektar_closed_loop_1d")][
            "weight_class"
        ]
        == "medium-hard for quasi/1-D"
    )


def test_tracked_target_policy_file_has_expected_schema():
    policy = pd.read_csv(TARGET_DIR / "target_policy.csv")

    assert list(policy.columns) == POLICY_COLUMNS
    assert {
        ("IVC flow", "direct_measurement"),
        ("Direct DAo pressure", "direct_measurement"),
        ("Paper/Nektar DAo pressure", "paper_model_or_nektar_closed_loop_1d"),
    } <= set(zip(policy["quantity"], policy["source"]))
