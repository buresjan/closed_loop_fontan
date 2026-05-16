from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FRAGMENTS = ROOT / "models/quasi_0d_1d/config_fragments"
CALIBRATION = ROOT / "models/quasi_0d_1d/calibration"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_corrected_aortic_fragment_is_blocked_design_artifact() -> None:
    base = load_json(FRAGMENTS / "quasi_vessel_chains.json")
    corrected = load_json(FRAGMENTS / "quasi_vessel_chains_corrected.json")

    metadata = corrected["metadata"]
    assert metadata["task"] == "008.10"
    assert metadata["status"] == "blocked_not_promoted"
    assert metadata["best_candidate"] == "ep02_r7_art05_frac95"

    for chain in ("aao_arch", "dao"):
        for key, value in base["chains"][chain]["parameters"].items():
            corrected_value = corrected["chains"][chain]["parameters"][key]
            if key.endswith(".resistance"):
                assert corrected_value == value * 7.0
            else:
                assert corrected_value == value

    for chain in ("svc", "ivc", "rpa", "lpa"):
        assert corrected["chains"][chain]["parameters"] == base["chains"][chain][
            "parameters"
        ]


def test_aortic_design_candidates_record_failed_clinical_gate() -> None:
    rows = list(
        csv.DictReader(
            (CALIBRATION / "aortic_chain_design_candidates.csv").open(
                newline="", encoding="utf-8"
            )
        )
    )
    assert rows
    assert not any(row["accepted"] == "True" for row in rows)

    best = next(row for row in rows if row["notes"] == "best_defensible_partial")
    assert best["candidate"] == "ep02_r7_art05_frac95"
    assert best["pass_closed_loop_stability"] == "True"
    assert best["pass_q_aao_not_worse"] == "True"
    assert best["pass_q_dao_chain_not_worse"] == "True"
    assert best["pass_q_dao_clinical_not_worse"] == "False"
    assert float(best["closed_loop_q_dao_clinical_nrmse"]) > float(
        best["full0d_q_dao_clinical_nrmse"]
    )


def test_aortic_design_report_marks_task_blocked() -> None:
    report = (CALIBRATION / "aortic_chain_design_report.md").read_text(
        encoding="utf-8"
    )
    assert "Task 008.10 status: `blocked_not_promoted`" in report
    assert "Task 008.10 is therefore not complete" in report
