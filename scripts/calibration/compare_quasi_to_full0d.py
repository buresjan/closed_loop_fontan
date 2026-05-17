#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
CALIBRATION_DIR = ROOT / "models/quasi_0d_1d/calibration"

DEFAULT_FULL_DIRECT = ROOT / "models/full_0d/calibration/baseline_objective.json"
DEFAULT_QUASI_DIRECT = CALIBRATION_DIR / "baseline_objective.json"
DEFAULT_FULL_PAPER = ROOT / "models/full_0d/calibration/baseline_vs_paper.json"
DEFAULT_QUASI_PAPER = CALIBRATION_DIR / "baseline_vs_paper.json"
DEFAULT_FULL_METRICS = ROOT / "models/full_0d/reference_outputs/baseline_metrics.json"
DEFAULT_QUASI_METRICS = ROOT / "models/quasi_0d_1d/reference_outputs/baseline_metrics.json"
DEFAULT_WAVEFORMS = CALIBRATION_DIR / "baseline_waveforms_direct.json"
DEFAULT_SIGNAL_POLICY = CALIBRATION_DIR / "aortic_signal_policy.json"
DEFAULT_AORTIC_PROFILE = CALIBRATION_DIR / "aortic_profile.json"

PUMP_TARGETS = ("edv", "esv", "stroke_volume", "cardiac_output")
HARD_SCORE_TARGETS = (
    *PUMP_TARGETS,
    "rpa_pressure",
    "lpa_pressure",
    "svc_flow",
    "rpa_flow_fraction",
)
FONTAN_TARGETS = (
    "rpa_pressure",
    "lpa_pressure",
    "svc_flow",
    "rpa_flow",
    "lpa_flow",
    "rpa_flow_fraction",
)
AORTIC_FLOW_WAVEFORMS = ("ascending_aorta_flow", "descending_aorta_chain_health_flow")
FONTAN_WAVEFORMS = (
    "svc_pressure",
    "ivc_pressure",
    "rpa_pressure",
    "lpa_pressure",
    "svc_flow",
    "ivc_flow",
    "rpa_flow",
    "lpa_flow",
)
SOFT_PROBLEMATIC_TARGETS = ("descending_aorta_pressure", "ivc_flow")

TARGET_RELATIVE_ERROR_TOLERANCE = 0.005
FLOW_FRACTION_ABSOLUTE_TOLERANCE = 0.005
BALANCE_TOLERANCE = 0.01
PERIODICITY_TOLERANCE = 0.02


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def rows_by_target(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(row["target_name"]): row for row in payload["targets"]}


def rows_by_waveform(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(row["canonical_name"]): row for row in payload.get("waveforms", [])}


def aortic_flow_waveforms_from_policy(policy: dict[str, Any] | None = None) -> tuple[str, ...]:
    if policy is None:
        policy_path = DEFAULT_SIGNAL_POLICY
        policy = load_json(policy_path) if policy_path.exists() else None
    if policy is None:
        names = list(AORTIC_FLOW_WAVEFORMS)
    else:
        names = [
            str(row["canonical_name"])
            for row in policy.get("signals", [])
            if row.get("quantity") == "flow" and row.get("include_in_superiority_gate", False)
        ]
        if not names:
            names = list(AORTIC_FLOW_WAVEFORMS)
    return tuple(names)


def weighted_rms(rows: list[dict[str, Any]]) -> float:
    if not rows:
        return math.nan
    numerator = sum(float(row["weight"]) * abs(float(row["relative_error"])) ** 2 for row in rows)
    denominator = sum(float(row["weight"]) for row in rows)
    return math.sqrt(numerator / denominator)


def hard_score(payload: dict[str, Any]) -> float:
    rows = rows_by_target(payload)
    return weighted_rms([rows[name] for name in HARD_SCORE_TARGETS])


def is_finite_value(value: Any) -> bool:
    if isinstance(value, bool) or value is None or isinstance(value, str):
        return True
    if isinstance(value, int):
        return True
    if isinstance(value, float):
        return math.isfinite(value)
    if isinstance(value, list):
        return all(is_finite_value(item) for item in value)
    if isinstance(value, dict):
        return all(is_finite_value(item) for item in value.values())
    return True


def numeric_gate(name: str, value: float, threshold: float, *, lower_is_better: bool = True) -> dict[str, Any]:
    passed = value <= threshold if lower_is_better else value >= threshold
    margin = threshold - value if lower_is_better else value - threshold
    return {
        "name": name,
        "value": value,
        "threshold": threshold,
        "margin": margin,
        "pass": bool(passed),
    }


def score_gates(
    full_direct: dict[str, Any],
    quasi_direct: dict[str, Any],
    full_paper: dict[str, Any],
    quasi_paper: dict[str, Any],
) -> list[dict[str, Any]]:
    return [
        numeric_gate(
            "hard_clinical_summary_score",
            hard_score(quasi_direct),
            hard_score(full_direct),
        ),
        numeric_gate(
            "aggregate_direct_score",
            float(quasi_direct["weighted_rms_relative_error"]),
            float(full_direct["weighted_rms_relative_error"]),
        ),
        numeric_gate(
            "paper_model_score",
            float(quasi_paper["weighted_rms_relative_error"]),
            float(full_paper["weighted_rms_relative_error"]),
        ),
    ]


def relative_error_gate(target_name: str, full_row: dict[str, Any], quasi_row: dict[str, Any]) -> dict[str, Any]:
    full_error = abs(float(full_row["relative_error"]))
    quasi_error = abs(float(quasi_row["relative_error"]))
    threshold = full_error + TARGET_RELATIVE_ERROR_TOLERANCE
    return {
        "target_name": target_name,
        "gate_type": "relative_error_non_regression",
        "full_0d_error": full_error,
        "quasi_0d_1d_error": quasi_error,
        "tolerance": TARGET_RELATIVE_ERROR_TOLERANCE,
        "threshold": threshold,
        "margin": threshold - quasi_error,
        "pass": bool(quasi_error <= threshold),
    }


def flow_fraction_gate(full_row: dict[str, Any], quasi_row: dict[str, Any]) -> dict[str, Any]:
    full_error = abs(float(full_row["model_value"]) - float(full_row["target_value"]))
    quasi_error = abs(float(quasi_row["model_value"]) - float(quasi_row["target_value"]))
    threshold = full_error + FLOW_FRACTION_ABSOLUTE_TOLERANCE
    return {
        "target_name": "rpa_flow_fraction",
        "gate_type": "absolute_fraction_non_regression",
        "full_0d_error": full_error,
        "quasi_0d_1d_error": quasi_error,
        "tolerance": FLOW_FRACTION_ABSOLUTE_TOLERANCE,
        "threshold": threshold,
        "margin": threshold - quasi_error,
        "pass": bool(quasi_error <= threshold),
    }


def target_gates(
    full_direct: dict[str, Any],
    quasi_direct: dict[str, Any],
    names: tuple[str, ...],
) -> list[dict[str, Any]]:
    full_rows = rows_by_target(full_direct)
    quasi_rows = rows_by_target(quasi_direct)
    gates = []
    for name in names:
        if name == "rpa_flow_fraction":
            gates.append(flow_fraction_gate(full_rows[name], quasi_rows[name]))
        else:
            gates.append(relative_error_gate(name, full_rows[name], quasi_rows[name]))
    return gates


def stability_gates(quasi_direct: dict[str, Any], quasi_metrics: dict[str, Any], *payloads: dict[str, Any]) -> list[dict[str, Any]]:
    gates: list[dict[str, Any]] = [
        {
            "metric": "no_nan_or_inf_in_loaded_artifacts",
            "value": all(is_finite_value(payload) for payload in payloads),
            "threshold": True,
            "pass": all(is_finite_value(payload) for payload in payloads),
        }
    ]
    for row in quasi_direct.get("penalties", []):
        gates.append(
            {
                "metric": row["metric"],
                "value": float(row["value"]),
                "threshold": float(row["threshold"]),
                "pass": bool(row["pass"]),
            }
        )
    for metric in (
        "pass_no_nan",
        "pass_tcpc_balance",
        "pass_atrium_balance",
        "pass_ventricle_balance",
    ):
        gates.append(
            {
                "metric": metric,
                "value": bool(quasi_metrics.get(metric, False)),
                "threshold": True,
                "pass": bool(quasi_metrics.get(metric, False)),
            }
        )
    return gates


def waveform_gate(
    waveforms: dict[str, Any],
    policy: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    rows = rows_by_waveform(waveforms)
    gates = []
    for name in aortic_flow_waveforms_from_policy(policy):
        row = rows[name]
        value = float(row["normalized_rmse"])
        reference = float(row["reference_normalized_rmse"])
        gates.append(
            {
                "canonical_name": name,
                "signal_policy_id": row.get("signal_policy_id"),
                "comparison_role": row.get("comparison_role"),
                "gate_type": "aortic_flow_no_regression",
                "quasi_0d_1d_nrmse": value,
                "full_0d_nrmse": reference,
                "margin": reference - value,
                "pass": bool(value <= reference),
            }
        )
    return gates


def mean_waveform_score(rows: list[dict[str, Any]], key: str) -> float:
    values = [float(row[key]) for row in rows]
    return float(sum(values) / len(values)) if values else math.nan


def quasi_specific_improvement_gate(
    waveforms: dict[str, Any],
    aortic_profile: dict[str, Any] | None = None,
) -> dict[str, Any]:
    rows = rows_by_waveform(waveforms)
    dao_pressure = rows.get("descending_aorta_pressure")
    dao_flow = rows.get("descending_aorta_flow")
    fontan_rows = [rows[name] for name in FONTAN_WAVEFORMS if name in rows]

    candidates: list[dict[str, Any]] = []
    if dao_pressure is not None:
        margin = float(dao_pressure["reference_normalized_rmse"]) - float(dao_pressure["normalized_rmse"])
        candidates.append(
            {
                "name": "dao_pressure_waveform",
                "available": True,
                "quasi_0d_1d_nrmse": float(dao_pressure["normalized_rmse"]),
                "full_0d_nrmse": float(dao_pressure["reference_normalized_rmse"]),
                "margin": margin,
                "pass": bool(margin > 0.0),
            }
        )
    if dao_flow is not None:
        margin = float(dao_flow["reference_normalized_rmse"]) - float(
            dao_flow["normalized_rmse"]
        )
        amplitude_error = float(dao_flow["amplitude_relative_error"])
        candidates.append(
            {
                "name": "clinical_dao_flow_waveform",
                "available": True,
                "quasi_0d_1d_nrmse": float(dao_flow["normalized_rmse"]),
                "full_0d_nrmse": float(dao_flow["reference_normalized_rmse"]),
                "amplitude_relative_error": amplitude_error,
                "margin": margin,
                "pass": bool(margin > 0.0),
            }
        )
    if fontan_rows:
        quasi_score = mean_waveform_score(fontan_rows, "normalized_rmse")
        full_score = mean_waveform_score(fontan_rows, "reference_normalized_rmse")
        candidates.append(
            {
                "name": "fontan_waveform_mean_nrmse",
                "available": True,
                "canonical_names": [row["canonical_name"] for row in fontan_rows],
                "quasi_0d_1d_nrmse": quasi_score,
                "full_0d_nrmse": full_score,
                "margin": full_score - quasi_score,
                "pass": bool(quasi_score < full_score),
            }
        )
    if aortic_profile is None:
        candidates.append(
            {
                "name": "aortic_open_loop_profile",
                "available": False,
                "pass": False,
                "note": "No accepted open-loop aortic profile artifact is available.",
            }
        )
    else:
        candidates.append(
            {
                "name": "aortic_open_loop_profile",
                "available": True,
                "pass": bool(aortic_profile.get("pass", False)),
                "status": aortic_profile.get("status"),
                "source": aortic_profile.get("source"),
                "metrics": aortic_profile.get("metrics", {}),
            }
        )
    return {
        "name": "quasi_specific_vascular_improvement",
        "accepted_examples": [
            "dao_pressure_waveform",
            "clinical_dao_flow_waveform",
            "fontan_waveform_mean_nrmse",
            "aortic_open_loop_profile",
        ],
        "candidates": candidates,
        "pass": any(bool(candidate["pass"]) for candidate in candidates),
    }


def full_reference_scores(
    full_direct: dict[str, Any],
    full_paper: dict[str, Any],
    waveforms: dict[str, Any],
    policy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    waveform_rows = rows_by_waveform(waveforms)
    aortic_names = aortic_flow_waveforms_from_policy(policy)
    return {
        "artifact": "quasi_0d_1d_superiority_gate",
        "model_family": "full_0d",
        "reference_role": "frozen_superiority_baseline",
        "scores": {
            "direct_score": float(full_direct["weighted_rms_relative_error"]),
            "hard_clinical_summary_score": hard_score(full_direct),
            "paper_model_score": float(full_paper["weighted_rms_relative_error"]),
            "aortic_flow_waveform_nrmse": {
                name: float(waveform_rows[name]["reference_normalized_rmse"])
                for name in aortic_names
            },
        },
        "target_errors": {
            name: abs(float(rows_by_target(full_direct)[name]["relative_error"]))
            for name in (*PUMP_TARGETS, *FONTAN_TARGETS)
            if name != "rpa_flow_fraction"
        },
        "rpa_flow_fraction_absolute_error": abs(
            float(rows_by_target(full_direct)["rpa_flow_fraction"]["model_value"])
            - float(rows_by_target(full_direct)["rpa_flow_fraction"]["target_value"])
        ),
    }


def superiority_gate_definition(
    policy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    aortic_names = aortic_flow_waveforms_from_policy(policy)
    return {
        "artifact": "quasi_0d_1d_superiority_gate",
        "status": "frozen",
        "gate_profile": "frozen",
        "reference_model": "full_0d",
        "candidate_model_family": "quasi_0d_1d",
        "criteria": [
            "stability_and_balance_gates_pass",
            "hard_clinical_summary_score_not_worse_than_full_0d",
            "aggregate_direct_score_not_worse_than_full_0d",
            "paper_model_score_not_worse_than_full_0d",
            "pump_target_non_regression",
            "fontan_pulmonary_target_non_regression",
            "aortic_flow_waveform_no_regression",
            "at_least_one_quasi_specific_vascular_improvement",
        ],
        "tolerances": {
            "target_relative_error_non_regression": TARGET_RELATIVE_ERROR_TOLERANCE,
            "rpa_flow_fraction_absolute_non_regression": FLOW_FRACTION_ABSOLUTE_TOLERANCE,
            "periodicity": PERIODICITY_TOLERANCE,
            "cycle_balance": BALANCE_TOLERANCE,
        },
        "hard_score_targets": list(HARD_SCORE_TARGETS),
        "pump_non_regression_targets": list(PUMP_TARGETS),
        "fontan_pulmonary_non_regression_targets": list(FONTAN_TARGETS),
        "aortic_flow_waveform_targets": list(aortic_names),
        "aortic_signal_policy": str(DEFAULT_SIGNAL_POLICY),
        "soft_problematic_targets": list(SOFT_PROBLEMATIC_TARGETS),
        "notes": [
            "Direct DAo pressure and raw direct IVC flow cannot compensate for failed hard, paper, stability, or aortic-flow gates.",
            "A lower aggregate direct score is insufficient for superiority.",
            "Clinical DAo bed-entry flow is mapped separately from DAo chain-health flow; the chain-health flow remains in the aortic waveform gate.",
            "An accepted aortic profile artifact can satisfy the quasi-specific vascular-improvement criterion only if it reports a passed corrected aortic profile.",
        ],
    }


def evaluate(
    *,
    full_direct: dict[str, Any],
    quasi_direct: dict[str, Any],
    full_paper: dict[str, Any],
    quasi_paper: dict[str, Any],
    full_metrics: dict[str, Any],
    quasi_metrics: dict[str, Any],
    waveforms: dict[str, Any],
    policy: dict[str, Any] | None = None,
    aortic_profile: dict[str, Any] | None = None,
) -> dict[str, Any]:
    gates = {
        "stability": stability_gates(
            quasi_direct,
            quasi_metrics,
            full_direct,
            quasi_direct,
            full_paper,
            quasi_paper,
            full_metrics,
            quasi_metrics,
            waveforms,
        ),
        "score_non_regression": score_gates(full_direct, quasi_direct, full_paper, quasi_paper),
        "pump_non_regression": target_gates(full_direct, quasi_direct, PUMP_TARGETS),
        "fontan_pulmonary_non_regression": target_gates(full_direct, quasi_direct, FONTAN_TARGETS),
        "aortic_waveform_no_regression": waveform_gate(waveforms, policy),
        "quasi_specific_vascular_improvement": quasi_specific_improvement_gate(
            waveforms,
            aortic_profile,
        ),
    }
    group_pass = {
        "stability": all(row["pass"] for row in gates["stability"]),
        "score_non_regression": all(row["pass"] for row in gates["score_non_regression"]),
        "pump_non_regression": all(row["pass"] for row in gates["pump_non_regression"]),
        "fontan_pulmonary_non_regression": all(row["pass"] for row in gates["fontan_pulmonary_non_regression"]),
        "aortic_waveform_no_regression": all(row["pass"] for row in gates["aortic_waveform_no_regression"]),
        "quasi_specific_vascular_improvement": bool(gates["quasi_specific_vascular_improvement"]["pass"]),
    }
    accepted = all(group_pass.values())
    status = "accepted_superior_to_full_0d" if accepted else "not_superior_to_full_0d"
    return {
        "artifact": "quasi_0d_1d_superiority_status",
        "model_family": "quasi_0d_1d",
        "gate_profile": "frozen",
        "status": status,
        "accepted_as_superior": accepted,
        "gate_definition_file": str(CALIBRATION_DIR / "quasi_superiority_gate.json"),
        "scores": {
            "full_0d": full_reference_scores(
                full_direct,
                full_paper,
                waveforms,
                policy,
            )["scores"],
            "quasi_0d_1d": {
                "direct_score": float(quasi_direct["weighted_rms_relative_error"]),
                "hard_clinical_summary_score": hard_score(quasi_direct),
                "paper_model_score": float(quasi_paper["weighted_rms_relative_error"]),
                "aortic_flow_waveform_nrmse": {
                    row["canonical_name"]: float(row["quasi_0d_1d_nrmse"])
                    for row in gates["aortic_waveform_no_regression"]
                },
            },
        },
        "group_pass": group_pass,
        "failed_groups": [name for name, passed in group_pass.items() if not passed],
        "gates": gates,
    }


def write_markdown(path: Path, status: dict[str, Any]) -> None:
    scores = status["scores"]
    groups = status["group_pass"]
    failed = ", ".join(status["failed_groups"]) or "none"
    gate_profile = str(status.get("gate_profile", "frozen"))
    score_pass = {
        row["name"]: row["pass"]
        for row in status["gates"]["score_non_regression"]
    }
    waveform_rows = status["gates"]["aortic_waveform_no_regression"]
    aao = next(row for row in waveform_rows if row["canonical_name"] == "ascending_aorta_flow")
    dao = next(row for row in waveform_rows if row["canonical_name"] == "descending_aorta_chain_health_flow")
    waveform_summary_lines = [
        f"| AAo flow nRMSE | {aao['full_0d_nrmse']:.4f} | {aao['quasi_0d_1d_nrmse']:.4f} | {aao['pass']} |",
        f"| DAo chain-health flow nRMSE | {dao['full_0d_nrmse']:.4f} | {dao['quasi_0d_1d_nrmse']:.4f} | {dao['pass']} |",
    ]

    if status["accepted_as_superior"]:
        interpretation = (
            "The current quasi model is accepted as superior to the full 0-D "
            "reference under the frozen comparison gate. The acceptance depends "
            "on all hard clinical, paper-model, waveform, stability, balance, "
            "and quasi-specific vascular-improvement groups passing."
        )
    else:
        interpretation = (
            "The current quasi model is not superior to the full 0-D reference "
            "under the frozen comparison gate. Later quasi candidates must pass "
            "this same gate without relaxing thresholds or allowing soft/"
            "problematic targets to compensate for hard pump, paper-model, "
            "stability, or aortic-flow failures."
        )

    text = f"""# Current Quasi Superiority Gate Status

Status: `{status['status']}`

Gate profile: `{gate_profile}`

Accepted as superior: `{status['accepted_as_superior']}`

Failed gate groups: `{failed}`

## Summary Scores

| Score | Full 0-D reference | Current quasi | Pass |
|---|---:|---:|---|
| Hard clinical summary | {scores['full_0d']['hard_clinical_summary_score']:.4f} | {scores['quasi_0d_1d']['hard_clinical_summary_score']:.4f} | {score_pass['hard_clinical_summary_score']} |
| Aggregate direct | {scores['full_0d']['direct_score']:.4f} | {scores['quasi_0d_1d']['direct_score']:.4f} | {score_pass['aggregate_direct_score']} |
| Paper-model | {scores['full_0d']['paper_model_score']:.4f} | {scores['quasi_0d_1d']['paper_model_score']:.4f} | {score_pass['paper_model_score']} |
{chr(10).join(waveform_summary_lines)}

## Gate Groups

| Gate group | Pass |
|---|---|
| Stability and balance | {groups['stability']} |
| Score non-regression | {groups['score_non_regression']} |
| Pump target non-regression | {groups['pump_non_regression']} |
| Fontan/pulmonary target non-regression | {groups['fontan_pulmonary_non_regression']} |
| Aortic flow waveform no-regression | {groups['aortic_waveform_no_regression']} |
| Quasi-specific vascular improvement | {groups['quasi_specific_vascular_improvement']} |

## Interpretation

{interpretation}
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compare a quasi candidate against the frozen full 0-D superiority gate."
    )
    parser.add_argument("--full-direct", type=Path, default=DEFAULT_FULL_DIRECT)
    parser.add_argument("--quasi-direct", type=Path, default=DEFAULT_QUASI_DIRECT)
    parser.add_argument("--full-paper", type=Path, default=DEFAULT_FULL_PAPER)
    parser.add_argument("--quasi-paper", type=Path, default=DEFAULT_QUASI_PAPER)
    parser.add_argument("--full-metrics", type=Path, default=DEFAULT_FULL_METRICS)
    parser.add_argument("--quasi-metrics", type=Path, default=DEFAULT_QUASI_METRICS)
    parser.add_argument("--waveforms", type=Path, default=DEFAULT_WAVEFORMS)
    parser.add_argument("--signal-policy", type=Path, default=DEFAULT_SIGNAL_POLICY)
    parser.add_argument(
        "--aortic-profile",
        type=Path,
        default=DEFAULT_AORTIC_PROFILE,
        help="Optional open-loop aortic profile artifact for the quasi-specific improvement gate.",
    )
    parser.add_argument(
        "--gate-out",
        type=Path,
        default=CALIBRATION_DIR / "quasi_superiority_gate.json",
    )
    parser.add_argument(
        "--reference-out",
        type=Path,
        default=CALIBRATION_DIR / "full0d_reference_scores.json",
    )
    parser.add_argument(
        "--status-out",
        type=Path,
        default=CALIBRATION_DIR / "current_quasi_gate_status.json",
    )
    parser.add_argument(
        "--status-md-out",
        type=Path,
        default=CALIBRATION_DIR / "current_quasi_gate_status.md",
    )
    args = parser.parse_args()

    full_direct = load_json(args.full_direct)
    quasi_direct = load_json(args.quasi_direct)
    full_paper = load_json(args.full_paper)
    quasi_paper = load_json(args.quasi_paper)
    full_metrics = load_json(args.full_metrics)
    quasi_metrics = load_json(args.quasi_metrics)
    waveforms = load_json(args.waveforms)
    policy = load_json(args.signal_policy) if args.signal_policy.exists() else None
    aortic_profile = (
        load_json(args.aortic_profile)
        if args.aortic_profile is not None and args.aortic_profile.exists()
        else None
    )

    gate = superiority_gate_definition(policy)
    reference = full_reference_scores(
        full_direct,
        full_paper,
        waveforms,
        policy,
    )
    status = evaluate(
        full_direct=full_direct,
        quasi_direct=quasi_direct,
        full_paper=full_paper,
        quasi_paper=quasi_paper,
        full_metrics=full_metrics,
        quasi_metrics=quasi_metrics,
        waveforms=waveforms,
        policy=policy,
        aortic_profile=aortic_profile,
    )
    status["gate_definition_file"] = str(args.gate_out)

    write_json(args.gate_out, gate)
    write_json(args.reference_out, reference)
    write_json(args.status_out, status)
    write_markdown(args.status_md_out, status)
    print(json.dumps(status, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
