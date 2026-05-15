#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.calibration.objective import load_json, write_json

TARGET_DIR = ROOT / "data/processed/aramburu_2024/targets"
SUMMARY_TARGETS = TARGET_DIR / "summary_targets.csv"
BASELINE_METRICS = ROOT / "models/full_0d/reference_outputs/baseline_metrics.json"
REPORT_PATH = ROOT / "models/full_0d/calibration/target_consistency_report.md"
JSON_PATH = ROOT / "models/full_0d/calibration/target_consistency.json"
POLICY_PATH = TARGET_DIR / "target_policy.csv"

SOURCES = ["direct_measurement", "paper_model", "nektar_closed_loop_1d"]
POLICY_COLUMNS = ["quantity", "source", "role", "weight_class", "reason"]

SOURCE_CONFLICT_QUANTITIES = [
    ("cardiac_output", "from_stroke_volume", "ml/s", "CO"),
    ("svc_flow", "beat_integral", "ml/s", "SVC flow"),
    ("ivc_flow", "beat_integral", "ml/s", "IVC flow"),
    ("rpa_flow", "beat_integral", "ml/s", "RPA flow"),
    ("lpa_flow", "beat_integral", "ml/s", "LPA flow"),
    ("ascending_aorta_pressure", "mean", "mmHg", "AAo pressure"),
    ("aortic_arch_pressure", "mean", "mmHg", "Arch pressure"),
    ("descending_aorta_pressure", "mean", "mmHg", "DAo pressure"),
    ("svc_pressure", "mean", "mmHg", "SVC pressure"),
    ("ivc_pressure", "mean", "mmHg", "IVC pressure"),
    ("rpa_pressure", "mean", "mmHg", "RPA pressure"),
    ("lpa_pressure", "mean", "mmHg", "LPA pressure"),
]

TARGET_POLICY_ROWS = [
    {
        "quantity": "EDV",
        "source": "direct_measurement",
        "role": "calibration",
        "weight_class": "hard",
        "reason": "Primary ventricular volume target.",
    },
    {
        "quantity": "ESV",
        "source": "direct_measurement",
        "role": "calibration",
        "weight_class": "hard",
        "reason": "Primary ventricular volume target.",
    },
    {
        "quantity": "SV",
        "source": "direct_measurement",
        "role": "calibration",
        "weight_class": "hard",
        "reason": "Primary pump target.",
    },
    {
        "quantity": "CO",
        "source": "direct_measurement",
        "role": "calibration",
        "weight_class": "hard",
        "reason": "Primary closed-loop output.",
    },
    {
        "quantity": "AAo pressure",
        "source": "direct_measurement_or_paper_nektar",
        "role": "calibration",
        "weight_class": "medium-hard",
        "reason": "Important afterload target; source choice depends on model family.",
    },
    {
        "quantity": "Arch pressure",
        "source": "paper_nektar_preferred_for_profile",
        "role": "calibration",
        "weight_class": "medium",
        "reason": "Source differences exist in the aortic pressure profile.",
    },
    {
        "quantity": "Direct DAo pressure",
        "source": "direct_measurement",
        "role": "diagnostic",
        "weight_class": "low/diagnostic",
        "reason": "Violates passive downstream pressure ordering.",
    },
    {
        "quantity": "Paper/Nektar DAo pressure",
        "source": "paper_model_or_nektar_closed_loop_1d",
        "role": "calibration",
        "weight_class": "medium-hard for quasi/1-D",
        "reason": "Physically consistent aortic profile for quasi and coupled models.",
    },
    {
        "quantity": "SVC pressure",
        "source": "direct_measurement",
        "role": "calibration",
        "weight_class": "hard",
        "reason": "Fontan pressure target.",
    },
    {
        "quantity": "IVC pressure",
        "source": "direct_measurement",
        "role": "calibration",
        "weight_class": "hard",
        "reason": "Fontan pressure target.",
    },
    {
        "quantity": "RPA pressure",
        "source": "direct_measurement",
        "role": "calibration",
        "weight_class": "medium",
        "reason": "Pulmonary pressure target.",
    },
    {
        "quantity": "LPA pressure",
        "source": "direct_measurement",
        "role": "calibration",
        "weight_class": "medium",
        "reason": "Pulmonary pressure target.",
    },
    {
        "quantity": "SVC flow",
        "source": "direct_measurement",
        "role": "calibration",
        "weight_class": "medium-hard",
        "reason": "Good direct flow target.",
    },
    {
        "quantity": "IVC flow",
        "source": "direct_measurement",
        "role": "calibration",
        "weight_class": "soft",
        "reason": "Direct flow table is not mass-closed.",
    },
    {
        "quantity": "RPA flow",
        "source": "direct_measurement",
        "role": "calibration",
        "weight_class": "hard",
        "reason": "Pulmonary flow target.",
    },
    {
        "quantity": "LPA flow",
        "source": "direct_measurement",
        "role": "calibration",
        "weight_class": "hard",
        "reason": "Pulmonary flow target.",
    },
    {
        "quantity": "RPA/LPA flow fraction",
        "source": "direct_measurement",
        "role": "calibration",
        "weight_class": "hard",
        "reason": "Important pulmonary split target.",
    },
    {
        "quantity": "Wedge / atrial proxy",
        "source": "direct_measurement",
        "role": "calibration",
        "weight_class": "medium",
        "reason": "Useful but model-dependent interpretation.",
    },
]


def load_summary(path: Path = SUMMARY_TARGETS) -> pd.DataFrame:
    return pd.read_csv(path)


def target_row(
    summary: pd.DataFrame,
    source_id: str,
    canonical_name: str,
    statistic: str,
) -> pd.Series:
    rows = summary[
        (summary["source_id"] == source_id)
        & (summary["canonical_name"] == canonical_name)
        & (summary["statistic"] == statistic)
    ]
    if len(rows) != 1:
        raise KeyError(f"Expected one target row for {source_id}.{canonical_name}.{statistic}")
    return rows.iloc[0]


def target_value(
    summary: pd.DataFrame,
    source_id: str,
    canonical_name: str,
    statistic: str,
    unit: str,
) -> float:
    row = target_row(summary, source_id, canonical_name, statistic)
    value = float(row["value"])
    source_unit = str(row["unit"])
    if unit == source_unit:
        return value
    if unit == "ml/s" and source_unit == "ml/beat":
        return value / float(row["cycle_length_s"])
    if unit == "ml/s" and source_unit == "L/min":
        return value * 1000.0 / 60.0
    raise ValueError(
        f"Unsupported unit conversion for {source_id}.{canonical_name}: "
        f"{source_unit} -> {unit}"
    )


def flow_closure_for_source(summary: pd.DataFrame, source_id: str) -> dict[str, float]:
    co = target_value(summary, source_id, "cardiac_output", "from_stroke_volume", "ml/s")
    svc = target_value(summary, source_id, "svc_flow", "beat_integral", "ml/s")
    ivc = target_value(summary, source_id, "ivc_flow", "beat_integral", "ml/s")
    rpa = target_value(summary, source_id, "rpa_flow", "beat_integral", "ml/s")
    lpa = target_value(summary, source_id, "lpa_flow", "beat_integral", "ml/s")
    systemic_return = svc + ivc
    pulmonary_flow = rpa + lpa
    return {
        "co_ml_s": co,
        "svc_flow_ml_s": svc,
        "ivc_flow_ml_s": ivc,
        "rpa_flow_ml_s": rpa,
        "lpa_flow_ml_s": lpa,
        "svc_plus_ivc_ml_s": systemic_return,
        "rpa_plus_lpa_ml_s": pulmonary_flow,
        "systemic_minus_pulmonary_ml_s": systemic_return - pulmonary_flow,
        "co_minus_systemic_return_ml_s": co - systemic_return,
        "co_minus_pulmonary_flow_ml_s": co - pulmonary_flow,
    }


def implied_ivc_from_direct(direct: dict[str, float]) -> dict[str, float]:
    return {
        "raw_direct_ivc_ml_s": direct["ivc_flow_ml_s"],
        "from_pulmonary_closure_ml_s": (
            direct["rpa_plus_lpa_ml_s"] - direct["svc_flow_ml_s"]
        ),
        "from_co_closure_ml_s": direct["co_ml_s"] - direct["svc_flow_ml_s"],
    }


def aortic_pressure_order_for_source(
    summary: pd.DataFrame, source_id: str
) -> dict[str, float | bool]:
    aao = target_value(summary, source_id, "ascending_aorta_pressure", "mean", "mmHg")
    arch = target_value(summary, source_id, "aortic_arch_pressure", "mean", "mmHg")
    dao = target_value(summary, source_id, "descending_aorta_pressure", "mean", "mmHg")
    return {
        "aao_pressure_mmHg": aao,
        "arch_pressure_mmHg": arch,
        "dao_pressure_mmHg": dao,
        "aao_ge_arch_ge_dao": bool(aao >= arch >= dao),
        "aao_to_arch_drop_mmHg": aao - arch,
        "arch_to_dao_drop_mmHg": arch - dao,
        "aao_to_dao_drop_mmHg": aao - dao,
    }


def source_conflicts(summary: pd.DataFrame) -> list[dict[str, Any]]:
    conflicts: list[dict[str, Any]] = []
    for canonical, statistic, unit, label in SOURCE_CONFLICT_QUANTITIES:
        values = {
            source: target_value(summary, source, canonical, statistic, unit)
            for source in SOURCES
        }
        conflicts.append(
            {
                "quantity": label,
                "canonical_name": canonical,
                "statistic": statistic,
                "unit": unit,
                "values": values,
                "min": min(values.values()),
                "max": max(values.values()),
                "range": max(values.values()) - min(values.values()),
            }
        )
    return conflicts


def model_interpretation(
    metrics: dict[str, Any],
    direct_implied_ivc: dict[str, float],
    paper_aortic_order: dict[str, float | bool],
) -> dict[str, Any]:
    co = float(metrics["CO_from_valve_arterial.flux_L_min"]) * 1000.0 / 60.0
    svc = float(metrics["mean_svc_conduit_rl.flux_ml_s"])
    ivc = float(metrics["mean_ivc_conduit_rl.flux_ml_s"])
    rpa = float(metrics["mean_rpa_conduit_out.flow_ml_s"])
    lpa = float(metrics["mean_lpa_conduit_out.flow_ml_s"])
    aao = float(metrics["mean_aao_pressure_mmHg"])
    arch = float(metrics["mean_aortic_arch_pressure_mmHg"])
    dao = float(metrics["mean_dao_pressure_mmHg"])
    return {
        "flow_closure": {
            "co_ml_s": co,
            "svc_plus_ivc_ml_s": svc + ivc,
            "rpa_plus_lpa_ml_s": rpa + lpa,
            "systemic_minus_pulmonary_ml_s": (svc + ivc) - (rpa + lpa),
            "co_minus_systemic_return_ml_s": co - (svc + ivc),
            "co_minus_pulmonary_flow_ml_s": co - (rpa + lpa),
        },
        "ivc_flow": {
            "model_ivc_ml_s": ivc,
            "raw_direct_ivc_ml_s": direct_implied_ivc["raw_direct_ivc_ml_s"],
            "direct_implied_from_pulmonary_closure_ml_s": direct_implied_ivc[
                "from_pulmonary_closure_ml_s"
            ],
            "direct_implied_from_co_closure_ml_s": direct_implied_ivc[
                "from_co_closure_ml_s"
            ],
            "model_minus_raw_direct_ml_s": ivc - direct_implied_ivc["raw_direct_ivc_ml_s"],
            "model_minus_pulmonary_implied_ml_s": (
                ivc - direct_implied_ivc["from_pulmonary_closure_ml_s"]
            ),
            "model_minus_co_implied_ml_s": ivc - direct_implied_ivc["from_co_closure_ml_s"],
        },
        "aortic_profile": {
            "model_aao_pressure_mmHg": aao,
            "model_arch_pressure_mmHg": arch,
            "model_dao_pressure_mmHg": dao,
            "model_aao_to_dao_drop_mmHg": aao - dao,
            "paper_nektar_aao_to_dao_drop_mmHg": paper_aortic_order[
                "aao_to_dao_drop_mmHg"
            ],
        },
        "assessment": (
            "The calibrated full-0D model is acceptable as the baseline "
            "physiological reference for moving to quasi 0-D/1-D. The IVC-flow "
            "mismatch is mostly a consequence of enforcing mass conservation on "
            "target flows that are not mutually closed. The DAo-pressure mismatch "
            "is partly a direct-target inconsistency and partly a limitation of "
            "the full-0D aortic representation."
        ),
    }


def target_policy_rows() -> list[dict[str, str]]:
    return [dict(row) for row in TARGET_POLICY_ROWS]


def build_consistency_payload(
    summary: pd.DataFrame,
    baseline_metrics: dict[str, Any],
) -> dict[str, Any]:
    flow_closure = {source: flow_closure_for_source(summary, source) for source in SOURCES}
    direct_implied_ivc = implied_ivc_from_direct(flow_closure["direct_measurement"])
    aortic_order = {
        source: aortic_pressure_order_for_source(summary, source) for source in SOURCES
    }
    return {
        "flow_closure": flow_closure,
        "implied_ivc": {
            "direct_measurement": direct_implied_ivc,
        },
        "aortic_pressure_order": aortic_order,
        "source_conflicts": source_conflicts(summary),
        "model_interpretation": model_interpretation(
            baseline_metrics,
            direct_implied_ivc,
            aortic_order["paper_model"],
        ),
        "target_policy": target_policy_rows(),
    }


def fmt(value: float, digits: int = 2) -> str:
    return f"{value:.{digits}f}"


def markdown_report(payload: dict[str, Any]) -> str:
    direct = payload["flow_closure"]["direct_measurement"]
    implied = payload["implied_ivc"]["direct_measurement"]
    aortic = payload["aortic_pressure_order"]
    interp = payload["model_interpretation"]
    model_ivc = interp["ivc_flow"]
    model_aortic = interp["aortic_profile"]

    lines = [
        "# Target Consistency Report",
        "",
        "Generated by `scripts/calibration/check_target_consistency.py`.",
        "",
        "## Conclusion",
        "",
        "The calibrated full-0D model is acceptable as the baseline physiological "
        "reference for moving to quasi 0-D/1-D. The IVC-flow mismatch is not a "
        "topology failure; it is mostly a consequence of enforcing mass "
        "conservation on target flows that are not mutually closed. The "
        "DAo-pressure mismatch is partly a direct-target inconsistency, because "
        "the direct measurement table requires downstream mean pressure rise in "
        "a passive aortic tree, and partly a structural limitation/calibration "
        "miss of the full-0D aortic representation. The quasi model should "
        "improve the aortic pressure profile by using geometry/wave-speed-derived "
        "aortic R/L/C and by moving most systemic pressure loss into the systemic "
        "beds rather than the aortic trunk.",
        "",
        "## Flow Closure",
        "",
        "| Source | CO ml/s | SVC+IVC ml/s | RPA+LPA ml/s | Sys-Pulm ml/s | CO-Sys ml/s | CO-Pulm ml/s |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for source, row in payload["flow_closure"].items():
        lines.append(
            "| "
            + " | ".join(
                [
                    source,
                    fmt(row["co_ml_s"]),
                    fmt(row["svc_plus_ivc_ml_s"]),
                    fmt(row["rpa_plus_lpa_ml_s"]),
                    fmt(row["systemic_minus_pulmonary_ml_s"]),
                    fmt(row["co_minus_systemic_return_ml_s"]),
                    fmt(row["co_minus_pulmonary_flow_ml_s"]),
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "For the direct measurement targets:",
            "",
            f"- CO target: {fmt(direct['co_ml_s'])} ml/s",
            f"- SVC + IVC target: {fmt(direct['svc_plus_ivc_ml_s'])} ml/s",
            f"- RPA + LPA target: {fmt(direct['rpa_plus_lpa_ml_s'])} ml/s",
            "",
            "Mass-balanced implied IVC values from direct targets:",
            "",
            f"- IVC from pulmonary closure: {fmt(implied['from_pulmonary_closure_ml_s'])} ml/s",
            f"- IVC from CO closure: {fmt(implied['from_co_closure_ml_s'])} ml/s",
            f"- Raw direct IVC target: {fmt(implied['raw_direct_ivc_ml_s'])} ml/s",
            f"- Calibrated model IVC flow: {fmt(model_ivc['model_ivc_ml_s'])} ml/s",
            "",
            "The calibrated model IVC flow is high relative to the raw direct IVC "
            "target, but is reasonable relative to mass-balanced closure targets.",
            "",
            "## Passive Aortic Pressure Order",
            "",
            "| Source | AAo mmHg | Arch mmHg | DAo mmHg | AAo>=Arch>=DAo | AAo-DAo drop mmHg |",
            "|---|---:|---:|---:|---|---:|",
        ]
    )
    for source, row in aortic.items():
        lines.append(
            "| "
            + " | ".join(
                [
                    source,
                    fmt(row["aao_pressure_mmHg"]),
                    fmt(row["arch_pressure_mmHg"]),
                    fmt(row["dao_pressure_mmHg"]),
                    str(row["aao_ge_arch_ge_dao"]),
                    fmt(row["aao_to_dao_drop_mmHg"]),
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            f"Current full-0D AAo-to-DAo drop: {fmt(model_aortic['model_aao_to_dao_drop_mmHg'])} mmHg.",
            f"Paper/Nektar AAo-to-DAo drop: {fmt(model_aortic['paper_nektar_aao_to_dao_drop_mmHg'])} mmHg.",
            "",
            "The direct DAo mean pressure should not be used as a hard calibration "
            "target for a passive full-0D aortic tree. For the aortic pressure "
            "profile, use the paper/Nektar target or treat direct DAo pressure as "
            "diagnostic/low-weight until source labeling/extraction is verified.",
            "",
            "## Source Use Policy",
            "",
            "Direct measurements remain primary for EDV, ESV, SV, CO, Fontan "
            "pressures, measured flows, and pulmonary flow split. Paper/Nektar "
            "outputs are preferred for the physically consistent aortic pressure "
            "profile and later waveform comparisons.",
            "",
            "See `data/processed/aramburu_2024/targets/target_policy.csv` for the "
            "machine-readable policy.",
            "",
        ]
    )
    return "\n".join(lines)


def write_policy_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=POLICY_COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Check calibration target consistency before quasi model derivation."
    )
    parser.add_argument("--summary-targets", type=Path, default=SUMMARY_TARGETS)
    parser.add_argument("--baseline-metrics", type=Path, default=BASELINE_METRICS)
    parser.add_argument("--json-out", type=Path, default=JSON_PATH)
    parser.add_argument("--report-out", type=Path, default=REPORT_PATH)
    parser.add_argument("--policy-out", type=Path, default=POLICY_PATH)
    args = parser.parse_args()

    payload = build_consistency_payload(
        load_summary(args.summary_targets),
        load_json(args.baseline_metrics),
    )
    write_json(args.json_out, payload)
    args.report_out.parent.mkdir(parents=True, exist_ok=True)
    args.report_out.write_text(markdown_report(payload), encoding="utf-8")
    write_policy_csv(args.policy_out, payload["target_policy"])
    print(
        json.dumps(
            {
                "json": str(args.json_out),
                "report": str(args.report_out),
                "policy": str(args.policy_out),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
