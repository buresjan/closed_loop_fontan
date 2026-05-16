#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
CALIBRATION_DIR = ROOT / "models/quasi_0d_1d/calibration"
DEFAULT_POLICY_PATH = CALIBRATION_DIR / "aortic_signal_policy.json"
DEFAULT_POLICY_MD_PATH = CALIBRATION_DIR / "aortic_signal_policy.md"

SCALE_KEYS = {
    "MMHG_PER_PA": 0.007500637554192106,
    "ML_PER_M3": 1.0e6,
}


def read_signal_audit(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    rows: dict[str, dict[str, Any]] = {}
    with path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            key = f"{row['model']}:{row['canonical_name']}:{row['candidate_signal']}"
            rows[key] = row
    return rows


def read_openloop_status(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def float_or_none(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def evidence_row(
    rows: dict[str, dict[str, Any]],
    model: str,
    canonical_name: str,
    signal: str,
) -> dict[str, Any]:
    row = rows.get(f"{model}:{canonical_name}:{signal}", {})
    return {
        "audit_canonical_name": canonical_name,
        "audit_model": model,
        "audit_signal": signal,
        "normalized_rmse": float_or_none(row.get("normalized_rmse")),
        "sign_flipped_normalized_rmse": float_or_none(
            row.get("sign_flipped_normalized_rmse")
        ),
        "best_phase_shift_normalized_rmse": float_or_none(
            row.get("best_phase_shift_normalized_rmse")
        ),
        "best_phase_shift_fraction": float_or_none(row.get("best_phase_shift_fraction")),
        "anatomical_location": row.get("anatomical_location"),
    }


def build_policy() -> dict[str, Any]:
    audit = read_signal_audit(CALIBRATION_DIR / "dao_aao_flow_signal_audit.csv")
    openloop = read_openloop_status(CALIBRATION_DIR / "aorta_quasi_openloop_metrics.json")
    return {
        "task": "008.9",
        "status": "active",
        "policy_version": 1,
        "created": "2026-05-15",
        "source_documents": [
            "models/quasi_0d_1d/calibration/dao_aao_flow_signal_audit.csv",
            "models/quasi_0d_1d/calibration/design_audit_report.md",
            "models/quasi_0d_1d/calibration/aorta_quasi_openloop_report.md",
            "data/processed/aramburu_2024/targets/waveform_metadata.csv",
        ],
        "phase_policy": {
            "phase_convention": (
                "All waveform targets use the processed Aramburu comparison-cycle "
                "phase from phase 0 to 1. No valve-event alignment or cross-correlation "
                "phase shift is applied before acceptance scoring."
            ),
            "phase_shifted_nrmse_use": "diagnostic_only",
            "acceptance_metric": "unshifted_normalized_rmse",
            "reason": (
                "The signal audit shows phase-shifted scores can improve substantially, "
                "but accepting a shifted score would hide timing errors."
            ),
        },
        "decision_points": {
            "q_dao_target_location": {
                "decision": (
                    "Use lower-body DAo outflow as the clinical waveform match in the "
                    "current lumped/quasi models."
                ),
                "selected_signal_id": "Q_DAo",
                "reason": (
                    "The tracked descending-aorta flow target is a lower-body aortic "
                    "measurement after arch branches. In the quasi topology, "
                    "lower_ra4.flow is the flow from the DAo pressure node into the "
                    "lower systemic artery and is the best anatomical clinical match. "
                    "The DAo chain outlet remains a separate trunk-chain health signal."
                ),
            },
            "dao_chain_health": {
                "decision": (
                    "Keep DAo chain outlet flow as a separate no-strong-regression "
                    "diagnostic."
                ),
                "selected_signal_id": "Q_DAo_chain_health",
                "reason": (
                    "Switching only to lower_ra4.flow would hide waveform behavior "
                    "inside the quasi DAo trunk."
                ),
            },
            "phase_shifted_nrmse": {
                "decision": "Use phase-shifted nRMSE only diagnostically.",
                "reason": (
                    "The accepted waveform metric remains unshifted nRMSE under the "
                    "shared target phase convention."
                ),
            },
            "phase_convention_consistency": {
                "decision": (
                    "Treat AAo and DAo target waveforms and model last-cycle outputs "
                    "as using the same cardiac-cycle phase convention."
                ),
                "reason": (
                    "The target metadata records processed comparison-cycle phase for "
                    "all waveform targets, and no later script applies a phase shift "
                    "for acceptance."
                ),
            },
        },
        "signals": [
            {
                "signal_id": "P_AAo",
                "canonical_name": "ascending_aorta_pressure",
                "target_canonical_name": "ascending_aorta_pressure",
                "quantity": "pressure",
                "unit": "mmHg",
                "model_unit": "Pa",
                "scale_key": "MMHG_PER_PA",
                "target_column": "ascending_aorta_pressure_mmHg",
                "model_columns": {
                    "full_0d": ["aao.blood_pressure"],
                    "quasi_0d_1d": ["aao.blood_pressure"],
                },
                "anatomical_interpretation": "ascending aorta/root pressure node",
                "comparison_role": "soft_target",
                "include_in_waveform_compare": True,
                "include_in_no_strong_regression": False,
                "include_in_superiority_gate": False,
                "preferred_target_sources": ["paper_model", "nektar_closed_loop_1d"],
                "reason": (
                    "Paper/Nektar aortic pressure profile is preferred for passive "
                    "aortic-profile checks; direct pressure remains useful context."
                ),
            },
            {
                "signal_id": "P_arch",
                "canonical_name": "aortic_arch_pressure",
                "target_canonical_name": "aortic_arch_pressure",
                "quantity": "pressure",
                "unit": "mmHg",
                "model_unit": "Pa",
                "scale_key": "MMHG_PER_PA",
                "target_column": "aortic_arch_pressure_mmHg",
                "model_columns": {
                    "full_0d": ["aortic_arch.blood_pressure"],
                    "quasi_0d_1d": ["aortic_arch.blood_pressure"],
                },
                "anatomical_interpretation": "aortic arch pressure node",
                "comparison_role": "soft_target",
                "include_in_waveform_compare": True,
                "include_in_no_strong_regression": False,
                "include_in_superiority_gate": False,
                "preferred_target_sources": ["paper_model", "nektar_closed_loop_1d"],
                "reason": "Used for passive aortic pressure-profile consistency.",
            },
            {
                "signal_id": "P_DAo",
                "canonical_name": "descending_aorta_pressure",
                "target_canonical_name": "descending_aorta_pressure",
                "quantity": "pressure",
                "unit": "mmHg",
                "model_unit": "Pa",
                "scale_key": "MMHG_PER_PA",
                "target_column": "descending_aorta_pressure_mmHg",
                "model_columns": {
                    "full_0d": ["dao.blood_pressure"],
                    "quasi_0d_1d": ["dao.blood_pressure"],
                },
                "anatomical_interpretation": "descending aorta pressure node",
                "comparison_role": "diagnostic",
                "include_in_waveform_compare": True,
                "include_in_no_strong_regression": False,
                "include_in_superiority_gate": False,
                "preferred_target_sources": ["paper_model", "nektar_closed_loop_1d"],
                "reason": (
                    "Direct DAo pressure violates passive pressure ordering in the "
                    "current target set, so it remains diagnostic/soft."
                ),
            },
            {
                "signal_id": "Q_AAo",
                "canonical_name": "ascending_aorta_flow",
                "target_canonical_name": "ascending_aorta_flow",
                "quantity": "flow",
                "unit": "ml/s",
                "model_unit": "m3/s",
                "scale_key": "ML_PER_M3",
                "target_column": "ascending_aorta_flow_ml_s",
                "model_columns": {
                    "full_0d": ["valve_arterial.flux"],
                    "quasi_0d_1d": ["valve_arterial.flux"],
                },
                "anatomical_interpretation": "aortic-valve outlet/root inflow",
                "comparison_role": "hard_gate",
                "include_in_waveform_compare": True,
                "include_in_no_strong_regression": True,
                "include_in_superiority_gate": True,
                "preferred_target_sources": ["direct_measurement", "paper_model"],
                "reason": (
                    "Q_ascAo is a root/ascending-aorta flow target. The aortic-valve "
                    "outlet is the shared full 0-D/quasi signal closest to that root "
                    "inflow location."
                ),
                "evidence": {
                    "quasi": evidence_row(
                        audit, "quasi", "ascending_aorta_flow", "valve_arterial.flux"
                    ),
                    "full_0d": evidence_row(
                        audit, "full_0d", "ascending_aorta_flow", "valve_arterial.flux"
                    ),
                },
            },
            {
                "signal_id": "Q_DAo",
                "canonical_name": "descending_aorta_flow",
                "target_canonical_name": "descending_aorta_flow",
                "quantity": "flow",
                "unit": "ml/s",
                "model_unit": "m3/s",
                "scale_key": "ML_PER_M3",
                "target_column": "descending_aorta_flow_ml_s",
                "model_columns": {
                    "full_0d": ["lower_ra4.flow"],
                    "quasi_0d_1d": ["lower_ra4.flow"],
                },
                "anatomical_interpretation": (
                    "flow from the DAo pressure node into the lower systemic artery"
                ),
                "comparison_role": "soft_target",
                "include_in_waveform_compare": True,
                "include_in_no_strong_regression": False,
                "include_in_superiority_gate": False,
                "preferred_target_sources": ["direct_measurement", "paper_model"],
                "reason": (
                    "This is the best clinical DAo waveform match in the current "
                    "lumped/quasi topology, but the measurement-location ambiguity "
                    "keeps it soft until later validation."
                ),
                "evidence": {
                    "quasi": evidence_row(
                        audit, "quasi", "descending_aorta_flow", "lower_ra4.flow"
                    ),
                    "full_0d": evidence_row(
                        audit, "full_0d", "descending_aorta_flow", "lower_ra4.flow"
                    ),
                    "openloop": {
                        "normalized_rmse": next(
                            (
                                row.get("normalized_rmse")
                                for row in openloop.get("flow_metrics", [])
                                if row.get("canonical_name") == "lower_ra4_flow"
                            ),
                            None,
                        )
                    },
                },
            },
            {
                "signal_id": "Q_DAo_chain_health",
                "canonical_name": "descending_aorta_chain_health_flow",
                "target_canonical_name": "descending_aorta_flow",
                "quantity": "flow",
                "unit": "ml/s",
                "model_unit": "m3/s",
                "scale_key": "ML_PER_M3",
                "target_column": "descending_aorta_flow_ml_s",
                "model_columns": {
                    "full_0d": ["arch_dao.flow"],
                    "quasi_0d_1d": ["quasi_dao_rl_06.flux"],
                },
                "anatomical_interpretation": (
                    "flow through the final DAo trunk/chain element before the DAo "
                    "pressure node"
                ),
                "comparison_role": "diagnostic",
                "include_in_waveform_compare": True,
                "include_in_no_strong_regression": True,
                "include_in_superiority_gate": True,
                "preferred_target_sources": ["direct_measurement", "paper_model"],
                "reason": (
                    "This is not the clinical DAo target, but it remains the health "
                    "check for the quasi aortic trunk. It prevents lower_ra4.flow "
                    "from hiding a broken DAo chain."
                ),
                "evidence": {
                    "quasi": evidence_row(
                        audit, "quasi", "descending_aorta_flow", "quasi_dao_rl_06.flux"
                    ),
                    "full_0d": evidence_row(
                        audit, "full_0d", "descending_aorta_flow", "arch_dao.flow"
                    ),
                    "openloop": {
                        "normalized_rmse": next(
                            (
                                row.get("normalized_rmse")
                                for row in openloop.get("flow_metrics", [])
                                if row.get("canonical_name") == "descending_aorta_flow"
                            ),
                            None,
                        )
                    },
                },
            },
        ],
    }


def load_policy(path: Path = DEFAULT_POLICY_PATH) -> dict[str, Any]:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return build_policy()


def signal_entries(policy: dict[str, Any]) -> list[dict[str, Any]]:
    return list(policy.get("signals", []))


def scale_value(entry: dict[str, Any]) -> float:
    return SCALE_KEYS[str(entry["scale_key"])]


def infer_model_family(config: dict[str, Any], config_path: Path | None = None) -> str:
    blocks = config.get("net", {}).get("blocks", {})
    if any(str(name).startswith("quasi_") for name in blocks):
        return "quasi_0d_1d"
    if config_path is not None and "quasi_0d_1d" in config_path.parts:
        return "quasi_0d_1d"
    return "full_0d"


def waveform_signal_specs(
    config: dict[str, Any],
    *,
    config_path: Path | None = None,
    policy: dict[str, Any] | None = None,
) -> dict[str, dict[str, Any]]:
    policy = load_policy() if policy is None else policy
    model_family = infer_model_family(config, config_path)
    specs: dict[str, dict[str, Any]] = {}
    for entry in signal_entries(policy):
        if not entry.get("include_in_waveform_compare", False):
            continue
        columns = entry.get("model_columns", {}).get(model_family)
        if not columns:
            continue
        specs[str(entry["canonical_name"])] = {
            "columns": tuple(str(col) for col in columns),
            "scale": scale_value(entry),
            "target_canonical_name": str(entry["target_canonical_name"]),
            "signal_policy_id": str(entry["signal_id"]),
            "comparison_role": str(entry["comparison_role"]),
            "include_in_no_strong_regression": bool(
                entry.get("include_in_no_strong_regression", False)
            ),
            "include_in_superiority_gate": bool(
                entry.get("include_in_superiority_gate", False)
            ),
        }
    return specs


def aortic_superiority_waveforms(policy: dict[str, Any] | None = None) -> tuple[str, ...]:
    policy = load_policy() if policy is None else policy
    return tuple(
        str(entry["canonical_name"])
        for entry in signal_entries(policy)
        if entry.get("quantity") == "flow" and entry.get("include_in_superiority_gate", False)
    )


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_markdown(path: Path, policy: dict[str, Any]) -> None:
    lines = [
        "# Aortic Signal Policy",
        "",
        f"Task 008.9 status: `{policy['status']}`",
        "",
        "This policy is the single source for aortic pressure/flow model columns used by later waveform and gate scripts.",
        "",
        "## Decisions",
        "",
    ]
    for key, decision in policy["decision_points"].items():
        lines.extend(
            [
                f"### {key}",
                "",
                f"- Decision: {decision['decision']}",
                f"- Reason: {decision['reason']}",
                "",
            ]
        )
    lines.extend(
        [
            "## Phase Policy",
            "",
            f"- Convention: {policy['phase_policy']['phase_convention']}",
            f"- Acceptance metric: `{policy['phase_policy']['acceptance_metric']}`.",
            f"- Phase-shifted nRMSE: `{policy['phase_policy']['phase_shifted_nrmse_use']}`.",
            "",
            "## Signals",
            "",
            "| ID | Canonical output | Target | Quasi model column | Full 0-D column | Role | Gate | Reason |",
            "|---|---|---|---|---|---|---|---|",
        ]
    )
    for entry in policy["signals"]:
        quasi = ", ".join(entry["model_columns"].get("quasi_0d_1d", []))
        full = ", ".join(entry["model_columns"].get("full_0d", []))
        gate = "yes" if entry.get("include_in_no_strong_regression") else "no"
        lines.append(
            f"| {entry['signal_id']} | `{entry['canonical_name']}` | "
            f"`{entry['target_column']}` | `{quasi}` | `{full}` | "
            f"{entry['comparison_role']} | {gate} | {entry['reason']} |"
        )
    lines.extend(
        [
            "",
            "## DAo Policy",
            "",
            "`Q_DAo` is the clinical descending-aorta flow target and maps to `lower_ra4.flow` in the current full 0-D and quasi models.",
            "`Q_DAo_chain_health` is the DAo trunk/chain diagnostic and maps to `quasi_dao_rl_06.flux` in the quasi model and `arch_dao.flow` in the full 0-D reference.",
            "Both are reported; only the chain-health signal remains in the aortic waveform no-regression gate.",
            "",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Write the Task 008.9 aortic signal policy artifacts."
    )
    parser.add_argument("--json-out", type=Path, default=DEFAULT_POLICY_PATH)
    parser.add_argument("--md-out", type=Path, default=DEFAULT_POLICY_MD_PATH)
    args = parser.parse_args()

    policy = build_policy()
    write_json(args.json_out, policy)
    write_markdown(args.md_out, policy)
    print(json.dumps(policy, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
