from __future__ import annotations

import json
from pathlib import Path

from scripts.calibration.quasi_non_regression import HARD_TARGETS

ROOT = Path(__file__).resolve().parents[1]
GATE_REPORT = ROOT / "models/quasi_0d_1d/calibration/non_regression_gate.json"


def load(path: Path) -> dict:
    return json.loads(path.read_text())


def test_direct_dao_and_ivc_flow_are_not_hard_gates():
    assert "descending_aorta_pressure" not in HARD_TARGETS
    assert "ivc_flow" not in HARD_TARGETS


def test_quasi_non_regression_report_tracks_corrective_status():
    report = load(GATE_REPORT)

    assert report["task"] == "008.5"
    assert report["status"] == "stable_corrective_prototype_not_superior"
    assert report["accepted_as_superior"] is False

    hard_names = {
        row["target_name"]
        for row in report["gates"]["hard_target_non_regression"]
    }
    assert {
        "edv",
        "esv",
        "stroke_volume",
        "cardiac_output",
        "rpa_pressure",
        "lpa_pressure",
        "svc_flow",
        "rpa_flow_fraction",
    } <= hard_names
    assert "descending_aorta_pressure" not in hard_names
    assert "ivc_flow" not in hard_names

    assert all(row["pass"] for row in report["gates"]["stability"])
    assert report["scores"]["paper_model_comparison_score"]["pass"] is False
