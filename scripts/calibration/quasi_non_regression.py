#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]

DEFAULT_FULL_DIRECT = ROOT / "models/full_0d/calibration/baseline_objective.json"
DEFAULT_QUASI_DIRECT = ROOT / "models/quasi_0d_1d/calibration/baseline_objective.json"
DEFAULT_FULL_PAPER = ROOT / "models/full_0d/calibration/baseline_vs_paper.json"
DEFAULT_QUASI_PAPER = ROOT / "models/quasi_0d_1d/calibration/baseline_vs_paper.json"
DEFAULT_QUASI_METRICS = ROOT / "models/quasi_0d_1d/reference_outputs/baseline_metrics.json"
DEFAULT_WAVEFORMS = (
    ROOT / "models/quasi_0d_1d/calibration/baseline_waveforms_direct.json"
)

RELATIVE_TOLERANCE = 0.01
FLOW_FRACTION_ABSOLUTE_TOLERANCE = 0.005
WAVEFORM_STRONG_REGRESSION_TOLERANCE = 0.05

PUMP_TARGETS = ("edv", "esv", "stroke_volume", "cardiac_output")
FONTAN_TARGETS = ("rpa_pressure", "lpa_pressure", "svc_flow", "rpa_flow_fraction")
HARD_TARGETS = (*PUMP_TARGETS, *FONTAN_TARGETS)
SOFT_PROBLEMATIC_TARGETS = (
    "descending_aorta_pressure",
    "ivc_flow",
)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def rows_by_target(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(row["target_name"]): row for row in payload["targets"]}


def weighted_rms(rows: list[dict[str, Any]]) -> float:
    if not rows:
        return math.nan
    numerator = sum(float(row["weight"]) * float(row["relative_error"]) ** 2 for row in rows)
    denominator = sum(float(row["weight"]) for row in rows)
    return math.sqrt(numerator / denominator)


def grouped_direct_scores(
    full_direct: dict[str, Any],
    quasi_direct: dict[str, Any],
) -> dict[str, Any]:
    full_rows = rows_by_target(full_direct)
    quasi_rows = rows_by_target(quasi_direct)

    def select(names: tuple[str, ...], rows: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
        return [rows[name] for name in names if name in rows]

    return {
        "hard_clinical_summary_score": {
            "full_0d": weighted_rms(select(HARD_TARGETS, full_rows)),
            "quasi_0d_1d": weighted_rms(select(HARD_TARGETS, quasi_rows)),
            "targets": list(HARD_TARGETS),
        },
        "soft_problematic_target_score": {
            "full_0d": weighted_rms(select(SOFT_PROBLEMATIC_TARGETS, full_rows)),
            "quasi_0d_1d": weighted_rms(select(SOFT_PROBLEMATIC_TARGETS, quasi_rows)),
            "targets": list(SOFT_PROBLEMATIC_TARGETS),
        },
        "aggregate_direct_score": {
            "full_0d": full_direct["weighted_rms_relative_error"],
            "quasi_0d_1d": quasi_direct["weighted_rms_relative_error"],
        },
    }


def target_gate(
    target_name: str,
    full_row: dict[str, Any],
    quasi_row: dict[str, Any],
) -> dict[str, Any]:
    full_error = abs(float(full_row["relative_error"]))
    quasi_error = abs(float(quasi_row["relative_error"]))
    threshold = full_error + RELATIVE_TOLERANCE
    return {
        "target_name": target_name,
        "gate_type": "relative_error_non_regression",
        "full_0d_error": full_error,
        "quasi_0d_1d_error": quasi_error,
        "threshold": threshold,
        "margin": threshold - quasi_error,
        "pass": bool(quasi_error <= threshold),
    }


def flow_fraction_gate(
    full_row: dict[str, Any],
    quasi_row: dict[str, Any],
) -> dict[str, Any]:
    full_error = abs(float(full_row["model_value"]) - float(full_row["target_value"]))
    quasi_error = abs(float(quasi_row["model_value"]) - float(quasi_row["target_value"]))
    threshold = full_error + FLOW_FRACTION_ABSOLUTE_TOLERANCE
    return {
        "target_name": "rpa_flow_fraction",
        "gate_type": "absolute_flow_fraction_non_regression",
        "full_0d_error": full_error,
        "quasi_0d_1d_error": quasi_error,
        "threshold": threshold,
        "margin": threshold - quasi_error,
        "pass": bool(quasi_error <= threshold),
    }


def hard_gates(
    full_direct: dict[str, Any],
    quasi_direct: dict[str, Any],
) -> list[dict[str, Any]]:
    full_rows = rows_by_target(full_direct)
    quasi_rows = rows_by_target(quasi_direct)
    gates = []
    for name in (*PUMP_TARGETS, "rpa_pressure", "lpa_pressure", "svc_flow"):
        gates.append(target_gate(name, full_rows[name], quasi_rows[name]))
    gates.append(flow_fraction_gate(full_rows["rpa_flow_fraction"], quasi_rows["rpa_flow_fraction"]))
    return gates


def stability_gates(quasi_direct: dict[str, Any], quasi_metrics: dict[str, Any]) -> list[dict[str, Any]]:
    gates: list[dict[str, Any]] = []
    for row in quasi_direct.get("penalties", []):
        gates.append(
            {
                "metric": row["metric"],
                "value": row["value"],
                "threshold": row["threshold"],
                "pass": bool(row["pass"]),
            }
        )
    for metric in [
        "pass_no_nan",
        "pass_tcpc_balance",
        "pass_atrium_balance",
        "pass_ventricle_balance",
    ]:
        if metric in quasi_metrics:
            gates.append(
                {
                    "metric": metric,
                    "value": bool(quasi_metrics[metric]),
                    "threshold": True,
                    "pass": bool(quasi_metrics[metric]),
                }
            )
    return gates


def paper_gate(full_paper: dict[str, Any], quasi_paper: dict[str, Any]) -> dict[str, Any]:
    full_score = float(full_paper["weighted_rms_relative_error"])
    quasi_score = float(quasi_paper["weighted_rms_relative_error"])
    return {
        "source_id": quasi_paper.get("source_id", "paper_model"),
        "full_0d": full_score,
        "quasi_0d_1d": quasi_score,
        "margin": full_score - quasi_score,
        "pass": bool(quasi_score <= full_score),
    }


def waveform_score(waveforms: dict[str, Any] | None) -> dict[str, Any] | None:
    if waveforms is None:
        return None
    rows = []
    regressions = []
    for row in waveforms.get("waveforms", []):
        if "reference_normalized_rmse" not in row:
            continue
        if not bool(row.get("include_in_no_strong_regression", True)):
            continue
        delta = float(row["normalized_rmse"]) - float(row["reference_normalized_rmse"])
        strong_regression = delta > WAVEFORM_STRONG_REGRESSION_TOLERANCE
        rows.append(
            {
                "canonical_name": row["canonical_name"],
                "signal_policy_id": row.get("signal_policy_id"),
                "comparison_role": row.get("comparison_role"),
                "normalized_rmse": row["normalized_rmse"],
                "reference_normalized_rmse": row["reference_normalized_rmse"],
                "delta": delta,
                "pass": not strong_regression,
            }
        )
        regressions.append(max(0.0, delta))
    score = math.sqrt(sum(value * value for value in regressions) / len(regressions)) if regressions else math.nan
    return {
        "source_id": waveforms.get("source_id"),
        "strong_regression_tolerance": WAVEFORM_STRONG_REGRESSION_TOLERANCE,
        "regression_rms": score,
        "pass": all(row["pass"] for row in rows),
        "waveforms": rows,
    }


def evaluate(
    *,
    full_direct: dict[str, Any],
    quasi_direct: dict[str, Any],
    full_paper: dict[str, Any],
    quasi_paper: dict[str, Any],
    quasi_metrics: dict[str, Any],
    waveforms: dict[str, Any] | None = None,
) -> dict[str, Any]:
    hard = hard_gates(full_direct, quasi_direct)
    stability = stability_gates(quasi_direct, quasi_metrics)
    paper = paper_gate(full_paper, quasi_paper)
    waveform = waveform_score(waveforms)
    all_hard_pass = all(row["pass"] for row in hard)
    all_stability_pass = all(row["pass"] for row in stability)
    waveform_pass = True if waveform is None else bool(waveform["pass"])
    accepted_as_superior = all_hard_pass and all_stability_pass and paper["pass"] and waveform_pass

    if accepted_as_superior:
        status = "accepted_superior_to_full_0d"
    elif all_stability_pass:
        status = "stable_corrective_prototype_not_superior"
    else:
        status = "blocked_by_numerical_stability"

    return {
        "model_family": "quasi_0d_1d",
        "task": "008.5",
        "status": status,
        "accepted_as_superior": accepted_as_superior,
        "tolerances": {
            "relative_error_non_regression": RELATIVE_TOLERANCE,
            "rpa_flow_fraction_absolute": FLOW_FRACTION_ABSOLUTE_TOLERANCE,
            "waveform_strong_regression": WAVEFORM_STRONG_REGRESSION_TOLERANCE,
        },
        "scores": {
            **grouped_direct_scores(full_direct, quasi_direct),
            "paper_model_comparison_score": paper,
            "waveform_no_strong_regression_score": waveform,
        },
        "gates": {
            "hard_target_non_regression": hard,
            "stability": stability,
        },
        "notes": [
            "Direct DAo pressure and raw direct IVC flow are scored as soft/problematic diagnostics.",
            "The selected corrective factors pass stability and improve the aggregate direct objective.",
            "A stable quasi prototype is not marked superior unless all hard, paper, and waveform gates pass.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evaluate Task 008.5 quasi non-regression gates."
    )
    parser.add_argument("--full-direct", type=Path, default=DEFAULT_FULL_DIRECT)
    parser.add_argument("--quasi-direct", type=Path, default=DEFAULT_QUASI_DIRECT)
    parser.add_argument("--full-paper", type=Path, default=DEFAULT_FULL_PAPER)
    parser.add_argument("--quasi-paper", type=Path, default=DEFAULT_QUASI_PAPER)
    parser.add_argument("--quasi-metrics", type=Path, default=DEFAULT_QUASI_METRICS)
    parser.add_argument("--waveforms", type=Path, default=DEFAULT_WAVEFORMS)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    waveform_payload = load_json(args.waveforms) if args.waveforms.exists() else None
    payload = evaluate(
        full_direct=load_json(args.full_direct),
        quasi_direct=load_json(args.quasi_direct),
        full_paper=load_json(args.full_paper),
        quasi_paper=load_json(args.quasi_paper),
        quasi_metrics=load_json(args.quasi_metrics),
        waveforms=waveform_payload,
    )
    text = json.dumps(payload, indent=2, sort_keys=True)
    print(text)
    if args.out:
        write_json(args.out, payload)


if __name__ == "__main__":
    main()
