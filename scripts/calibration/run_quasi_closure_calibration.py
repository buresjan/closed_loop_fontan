#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
CALIBRATION_DIR = ROOT / "models/quasi_0d_1d/calibration"

ACCEPTED_STATUS = "accepted_superior_to_full_0d"
NON_SUPERIOR_STATUS = "stable_quasi_development_scaffold_not_scientifically_superior"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_summary(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def numeric(row: dict[str, str], key: str) -> float:
    try:
        return float(row[key])
    except (KeyError, TypeError, ValueError):
        return float("inf")


def ok_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    return [row for row in rows if row.get("status") == "ok"]


def best_by(rows: list[dict[str, str]], key: str) -> dict[str, str]:
    return min(ok_rows(rows), key=lambda row: numeric(row, key))


def accepted_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    return [
        row
        for row in ok_rows(rows)
        if row.get("candidate") != "task0085_reference"
        if str(row.get("accepted_as_superior")).lower() == "true"
    ]


def final_decision(rows: list[dict[str, str]], design_audit: dict[str, Any]) -> dict[str, Any]:
    accepted = accepted_rows(rows)
    reference = next(row for row in rows if row["candidate"] == "task0085_reference")
    candidate_rows = [
        row
        for row in ok_rows(rows)
        if row.get("candidate") != "task0085_reference"
    ]
    score_pool = candidate_rows or [reference]
    best_hard = best_by(score_pool, "hard_score")
    best_waveform = best_by(score_pool, "waveform_regression_rms")
    best_direct = best_by(score_pool, "direct_score")

    if accepted:
        promoted = min(accepted, key=lambda row: numeric(row, "hard_score"))
        status = ACCEPTED_STATUS
        promoted_candidate = promoted["candidate"]
        rationale = "A Task 008.6 candidate passed hard, paper, waveform, and stability gates."
    else:
        promoted = None
        status = NON_SUPERIOR_STATUS
        promoted_candidate = None
        rationale = (
            "No Task 008.6 candidate passed all closure gates. Full 0-D remains "
            "the calibrated reference; quasi remains a stable development scaffold."
        )

    return {
        "task": "008.6",
        "status": status,
        "promoted_candidate": promoted_candidate,
        "rationale": rationale,
        "reference": reference,
        "best_candidates": {
            "best_hard_score": best_hard,
            "best_waveform_regression_rms": best_waveform,
            "best_direct_score": best_direct,
        },
        "candidate_count": len(candidate_rows),
        "failed_candidate_count": len(rows) - len(ok_rows(rows)),
        "design_audit_inputs": {
            "flow_signal_rows": len(design_audit.get("flow_signal_audit", [])),
            "compliance_summary_rows": len(design_audit.get("compliance_budget_summary", [])),
            "impedance_rows": len(design_audit.get("characteristic_impedance", [])),
        },
    }


def write_markdown(path: Path, decision: dict[str, Any]) -> None:
    best = decision["best_candidates"]
    reference = decision["reference"]
    hard = best["best_hard_score"]
    wave = best["best_waveform_regression_rms"]
    direct = best["best_direct_score"]

    promoted = decision["promoted_candidate"] or "none"
    text = f"""# Quasi Final Decision

Task 008.6 status: `{decision['status']}`

Promoted candidate: `{promoted}`

## Rationale

{decision['rationale']}

## Reference

Task 008.5 remains the canonical quasi state unless a promoted candidate is
listed above.

| Candidate | Hard score | Direct score | Paper score | Failed hard gates | Failed waveform gates |
|---|---:|---:|---:|---|---|
| {reference['candidate']} | {float(reference['hard_score']):.4f} | {float(reference['direct_score']):.4f} | {float(reference['paper_score']):.4f} | {reference['failed_hard_gates']} | {reference['failed_waveform_gates']} |

## Best Task 008.6 Candidates

| Criterion | Candidate | Value | Failed hard gates | Failed waveform gates |
|---|---|---:|---|---|
| Hard clinical score | {hard['candidate']} | {float(hard['hard_score']):.4f} | {hard['failed_hard_gates']} | {hard['failed_waveform_gates']} |
| Waveform regression RMS | {wave['candidate']} | {float(wave['waveform_regression_rms']):.4f} | {wave['failed_hard_gates']} | {wave['failed_waveform_gates']} |
| Aggregate direct score | {direct['candidate']} | {float(direct['direct_score']):.4f} | {direct['failed_hard_gates']} | {direct['failed_waveform_gates']} |

## Interpretation

The Task 008.6 matrix evaluated {decision['candidate_count']} candidates. No
candidate satisfied the hard, paper-comparison, waveform, stability, and
mass-balance gates together.

The best hard-score and aggregate-direct candidates still fail hard pump or
proximal pulmonary pressure gates. The best waveform candidate reduces the
waveform regression RMS but still fails AAo/DAo flow and hard-target gates.

No tracked quasi config, schematic, or implementation topology is promoted by
this closure. Candidate configs and runs remain under `runs/quasi_0086/` for
inspection only.

Task 009 can proceed with full 0-D as the calibrated reference and quasi as a
stable non-superior intermediate scaffold.
"""
    path.write_text(text, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Close Task 008.6 by choosing whether to promote a quasi candidate."
    )
    parser.add_argument(
        "--summary",
        type=Path,
        default=CALIBRATION_DIR / "quasi_ablation_summary.csv",
    )
    parser.add_argument(
        "--design-audit",
        type=Path,
        default=CALIBRATION_DIR / "design_audit.json",
    )
    args = parser.parse_args()

    rows = read_summary(args.summary)
    design_audit = load_json(args.design_audit)
    decision = final_decision(rows, design_audit)
    write_json(CALIBRATION_DIR / "quasi_final_decision.json", decision)
    write_markdown(CALIBRATION_DIR / "quasi_final_decision.md", decision)
    print(json.dumps(decision, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
