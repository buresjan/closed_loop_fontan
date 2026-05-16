#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.metrics import MMHG_PER_PA, ML_PER_M3, with_resistor_flows
from scripts.quasi.run_aorta_quasi_openloop import DEFAULT_CONFIG, SOURCES, cycle_period

CALIBRATION_DIR = ROOT / "models/quasi_0d_1d/calibration"

PRESSURE_SIGNALS = {
    "ascending_aorta_pressure": ("aao.blood_pressure", "ascending_aorta_pressure_mmHg"),
    "aortic_arch_pressure": ("aortic_arch.blood_pressure", "aortic_arch_pressure_mmHg"),
    "descending_aorta_pressure": ("dao.blood_pressure", "descending_aorta_pressure_mmHg"),
}

FLOW_SIGNALS = {
    "ascending_aorta_flow": ("aao_inflow.blood_flow", "ascending_aorta_flow_ml_s"),
    "descending_aorta_flow": ("quasi_dao_rl_06.flux", "descending_aorta_flow_ml_s"),
    "lower_ra4_flow": ("lower_ra4.flow", "descending_aorta_flow_ml_s"),
}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def latest_main_csv(series: str) -> Path:
    paths = sorted((ROOT / "runs/simulations" / series).glob("*/main.csv"))
    if not paths:
        raise FileNotFoundError(f"No main.csv found for series {series}")
    return paths[-1]


def periodic_interp(
    source_phase: np.ndarray,
    source_values: np.ndarray,
    target_phase: np.ndarray,
    *,
    phase_shift: float = 0.0,
) -> np.ndarray:
    phase = (source_phase + phase_shift) % 1.0
    order = np.argsort(phase)
    phase = phase[order]
    values = source_values[order]
    phase_ext = np.concatenate(([phase[-1] - 1.0], phase, [phase[0] + 1.0]))
    values_ext = np.concatenate(([values[-1]], values, [values[0]]))
    return np.interp(target_phase, phase_ext, values_ext)


def normalized_rmse(
    target_phase: np.ndarray,
    target_values: np.ndarray,
    model_phase: np.ndarray,
    model_values: np.ndarray,
    *,
    phase_shift: float = 0.0,
) -> float:
    model_interp = periodic_interp(
        model_phase,
        model_values,
        target_phase,
        phase_shift=phase_shift,
    )
    amplitude = float(target_values.max() - target_values.min())
    denominator = amplitude if amplitude > 0.0 else max(abs(float(target_values.mean())), 1.0e-9)
    return float(np.sqrt(np.mean((model_interp - target_values) ** 2)) / denominator)


def best_phase_shift_nrmse(
    target_phase: np.ndarray,
    target_values: np.ndarray,
    model_phase: np.ndarray,
    model_values: np.ndarray,
) -> tuple[float, float]:
    shifts = np.linspace(0.0, 1.0, 101, endpoint=False)
    scores = [
        normalized_rmse(
            target_phase,
            target_values,
            model_phase,
            model_values,
            phase_shift=float(shift),
        )
        for shift in shifts
    ]
    idx = int(np.argmin(scores))
    return float(scores[idx]), float(shifts[idx])


def trapz(time: np.ndarray, values: np.ndarray) -> float:
    integrate = getattr(np, "trapezoid", None)
    if integrate is None:
        integrate = np.trapz
    return float(integrate(values, time))


def source_dataframe(source: str) -> tuple[pd.DataFrame, float]:
    df = pd.read_csv(SOURCES[source]["path"])
    period = cycle_period(df["time_s"])
    df = df.copy()
    df["phase"] = df["time_s"] / period
    return df, period


def model_last_cycle(csv_path: Path, config_path: Path, period: float) -> pd.DataFrame:
    cfg = load_json(config_path)
    df = with_resistor_flows(pd.read_csv(csv_path), cfg)
    sub = df[df["time"] >= df["time"].max() - period].copy()
    t0 = float(sub["time"].iloc[0])
    sub["phase"] = (sub["time"] - t0) / period
    return sub


def model_signal(sub: pd.DataFrame, column: str, scale: float) -> np.ndarray:
    if column not in sub:
        raise KeyError(f"Model output is missing column {column}")
    return sub[column].to_numpy(dtype=float) * scale


def target_signal(target: pd.DataFrame, column: str) -> np.ndarray:
    if column not in target:
        raise KeyError(f"Target source is missing column {column}")
    return target[column].to_numpy(dtype=float)


def pressure_metrics(target: pd.DataFrame, model: pd.DataFrame) -> list[dict[str, Any]]:
    rows = []
    for name, (model_col, target_col) in PRESSURE_SIGNALS.items():
        target_values = target_signal(target, target_col)
        model_values = model_signal(model, model_col, MMHG_PER_PA)
        target_pp = float(target_values.max() - target_values.min())
        model_pp = float(model_values.max() - model_values.min())
        rows.append(
            {
                "canonical_name": name,
                "target_mean_mmHg": float(target_values.mean()),
                "model_mean_mmHg": float(model_values.mean()),
                "mean_error_mmHg": float(model_values.mean() - target_values.mean()),
                "target_pulse_pressure_mmHg": target_pp,
                "model_pulse_pressure_mmHg": model_pp,
                "pulse_pressure_error_mmHg": model_pp - target_pp,
                "pulse_pressure_relative_error": (model_pp - target_pp) / target_pp if target_pp > 0.0 else math.nan,
            }
        )
    return rows


def flow_metrics(target: pd.DataFrame, model: pd.DataFrame) -> list[dict[str, Any]]:
    rows = []
    target_phase = target["phase"].to_numpy(dtype=float)
    model_phase = model["phase"].to_numpy(dtype=float)
    for name, (model_col, target_col) in FLOW_SIGNALS.items():
        target_values = target_signal(target, target_col)
        model_values = model_signal(model, model_col, ML_PER_M3)
        direct = normalized_rmse(target_phase, target_values, model_phase, model_values)
        flipped = normalized_rmse(target_phase, target_values, model_phase, -model_values)
        shifted, shift = best_phase_shift_nrmse(target_phase, target_values, model_phase, model_values)
        target_amp = float(target_values.max() - target_values.min())
        model_amp = float(model_values.max() - model_values.min())
        rows.append(
            {
                "canonical_name": name,
                "model_signal": model_col,
                "target_signal": target_col,
                "target_mean_ml_s": float(target_values.mean()),
                "model_mean_ml_s": float(model_values.mean()),
                "target_amplitude_ml_s": target_amp,
                "model_amplitude_ml_s": model_amp,
                "amplitude_relative_error": (model_amp - target_amp) / target_amp if target_amp > 0.0 else math.nan,
                "normalized_rmse": direct,
                "sign_flipped_normalized_rmse": flipped,
                "best_phase_shift_normalized_rmse": shifted,
                "best_phase_shift_fraction": shift,
            }
        )
    return rows


def pressure_drop_metrics(target: pd.DataFrame, model: pd.DataFrame) -> dict[str, Any]:
    target_aao = target_signal(target, "ascending_aorta_pressure_mmHg")
    target_arch = target_signal(target, "aortic_arch_pressure_mmHg")
    target_dao = target_signal(target, "descending_aorta_pressure_mmHg")
    model_aao = model_signal(model, "aao.blood_pressure", MMHG_PER_PA)
    model_arch = model_signal(model, "aortic_arch.blood_pressure", MMHG_PER_PA)
    model_dao = model_signal(model, "dao.blood_pressure", MMHG_PER_PA)
    return {
        "target_aao_to_arch_mean_drop_mmHg": float(target_aao.mean() - target_arch.mean()),
        "model_aao_to_arch_mean_drop_mmHg": float(model_aao.mean() - model_arch.mean()),
        "target_arch_to_dao_mean_drop_mmHg": float(target_arch.mean() - target_dao.mean()),
        "model_arch_to_dao_mean_drop_mmHg": float(model_arch.mean() - model_dao.mean()),
        "target_aao_to_dao_mean_drop_mmHg": float(target_aao.mean() - target_dao.mean()),
        "model_aao_to_dao_mean_drop_mmHg": float(model_aao.mean() - model_dao.mean()),
    }


def mass_balance_metrics(model: pd.DataFrame) -> dict[str, Any]:
    time = model["time"].to_numpy(dtype=float)
    q_in = model_signal(model, "aao_inflow.blood_flow", 1.0)
    q_bca = model_signal(model, "arch_bca.flow", 1.0)
    q_lcca = model_signal(model, "arch_lcca.flow", 1.0)
    q_lsa = model_signal(model, "arch_lsa.flow", 1.0)
    q_dao = model_signal(model, "quasi_dao_rl_06.flux", 1.0)
    q_upper_terminal = model_signal(model, "upper_rv1.flow", 1.0)
    q_lower_terminal = model_signal(model, "lower_rv2.flow", 1.0)
    chain_storage = trapz(time, q_in - q_bca - q_lcca - q_lsa - q_dao)
    terminal_storage = trapz(time, q_in - q_upper_terminal - q_lower_terminal)
    normalizer = trapz(time, np.abs(q_in)) + 1.0e-15
    return {
        "aortic_chain_storage_ml": chain_storage * ML_PER_M3,
        "aortic_chain_mass_balance_rel": abs(chain_storage) / normalizer,
        "aortic_tree_terminal_storage_ml": terminal_storage * ML_PER_M3,
        "aortic_tree_terminal_mass_balance_rel": abs(terminal_storage) / normalizer,
    }


def diagnose_failure(flow_rows: list[dict[str, Any]], pressure_rows: list[dict[str, Any]], drops: dict[str, Any]) -> dict[str, Any]:
    by_name = {row["canonical_name"]: row for row in flow_rows}
    dao = by_name["descending_aorta_flow"]
    lower = by_name["lower_ra4_flow"]
    pressure_failures = [
        row["canonical_name"]
        for row in pressure_rows
        if abs(float(row["mean_error_mmHg"])) > 5.0 or abs(float(row["pulse_pressure_relative_error"])) > 0.5
    ]
    causes = []
    if dao["sign_flipped_normalized_rmse"] < 0.8 * dao["normalized_rmse"]:
        causes.append("sign convention contributes to DAo chain-flow mismatch")
    if dao["best_phase_shift_normalized_rmse"] < 0.8 * dao["normalized_rmse"]:
        causes.append("timing/phase error contributes to DAo chain-flow mismatch")
    if abs(float(dao["amplitude_relative_error"])) > 0.5:
        causes.append("amplitude mismatch suggests R/L/C or terminal-load impedance problem")
    if lower["normalized_rmse"] < 0.6 * dao["normalized_rmse"]:
        causes.append("target-location mismatch: lower-body outflow is closer than DAo chain outlet")
    if pressure_failures or abs(float(drops["model_aao_to_dao_mean_drop_mmHg"] - drops["target_aao_to_dao_mean_drop_mmHg"])) > 5.0:
        causes.append("branch/load topology or resistance placement distorts the pressure profile")
    if not causes:
        causes.append("no single dominant failure mode identified")
    return {
        "likely_causes": causes,
        "pressure_failures": pressure_failures,
        "primary_interpretation": causes[0],
    }


def pass_fail(
    pressure_rows: list[dict[str, Any]],
    flow_rows: list[dict[str, Any]],
    balance: dict[str, Any],
) -> dict[str, Any]:
    by_flow = {row["canonical_name"]: row for row in flow_rows}
    pressure_pass = all(
        abs(float(row["mean_error_mmHg"])) <= 5.0
        and abs(float(row["pulse_pressure_relative_error"])) <= 0.5
        for row in pressure_rows
    )
    flow_pass = (
        by_flow["ascending_aorta_flow"]["normalized_rmse"] <= 0.05
        and by_flow["descending_aorta_flow"]["normalized_rmse"] <= 0.5
        and by_flow["lower_ra4_flow"]["normalized_rmse"] <= 0.5
    )
    balance_pass = balance["aortic_chain_mass_balance_rel"] <= 1.0e-2
    passed = pressure_pass and flow_pass and balance_pass
    return {
        "status": "pass_open_loop_aortic_diagnostic" if passed else "fail_open_loop_aortic_diagnostic",
        "pass": passed,
        "pressure_profile_pass": pressure_pass,
        "flow_waveform_pass": flow_pass,
        "mass_balance_pass": balance_pass,
        "thresholds": {
            "pressure_mean_abs_error_mmHg": 5.0,
            "pulse_pressure_relative_error_abs": 0.5,
            "aao_flow_nrmse": 0.05,
            "dao_chain_outlet_flow_nrmse": 0.5,
            "lower_ra4_flow_nrmse": 0.5,
            "aortic_chain_mass_balance_rel": 1.0e-2,
        },
    }


def write_waveform_csv(path: Path, target: pd.DataFrame, model: pd.DataFrame) -> None:
    target_phase = target["phase"].to_numpy(dtype=float)
    model_phase = model["phase"].to_numpy(dtype=float)
    rows = []
    signals = {
        "ascending_aorta_pressure_mmHg": ("aao.blood_pressure", MMHG_PER_PA),
        "aortic_arch_pressure_mmHg": ("aortic_arch.blood_pressure", MMHG_PER_PA),
        "descending_aorta_pressure_mmHg": ("dao.blood_pressure", MMHG_PER_PA),
        "ascending_aorta_flow_ml_s": ("aao_inflow.blood_flow", ML_PER_M3),
        "dao_chain_outlet_flow_ml_s": ("quasi_dao_rl_06.flux", ML_PER_M3),
        "lower_ra4_flow_ml_s": ("lower_ra4.flow", ML_PER_M3),
    }
    for idx, phase in enumerate(target_phase):
        row: dict[str, Any] = {
            "phase": phase,
            "target_time_s": float(target["time_s"].iloc[idx]),
        }
        for target_col in [
            "ascending_aorta_pressure_mmHg",
            "aortic_arch_pressure_mmHg",
            "descending_aorta_pressure_mmHg",
            "ascending_aorta_flow_ml_s",
            "descending_aorta_flow_ml_s",
        ]:
            row[f"target_{target_col}"] = float(target[target_col].iloc[idx])
        for out_col, (model_col, scale) in signals.items():
            row[f"model_{out_col}"] = float(periodic_interp(model_phase, model_signal(model, model_col, scale), np.array([phase]))[0])
        rows.append(row)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def write_report(path: Path, payload: dict[str, Any]) -> None:
    flows = {row["canonical_name"]: row for row in payload["flow_metrics"]}
    pressures = payload["pressure_metrics"]
    drops = payload["pressure_drop_metrics"]
    status = payload["gate_status"]
    causes = payload["failure_diagnosis"]["likely_causes"]
    lines = [
        "# Aorta Quasi Open-Loop Report",
        "",
        f"Task 008.8 status: `{status['status']}`",
        "",
        f"Source: `{payload['source']['label']}` (`{payload['source']['path']}`)",
        "",
        "## Pressure Diagnostics",
        "",
        "| Signal | Mean error (mmHg) | Pulse-pressure relative error |",
        "|---|---:|---:|",
    ]
    for row in pressures:
        lines.append(
            f"| {row['canonical_name']} | {row['mean_error_mmHg']:.3f} | {row['pulse_pressure_relative_error']:.3f} |"
        )
    lines.extend(
        [
            "",
            "## Flow Diagnostics",
            "",
            "| Signal | Model signal | nRMSE | Sign-flipped nRMSE | Best phase-shift nRMSE | Amplitude rel. error |",
            "|---|---|---:|---:|---:|---:|",
        ]
    )
    for row in payload["flow_metrics"]:
        lines.append(
            f"| {row['canonical_name']} | `{row['model_signal']}` | {row['normalized_rmse']:.3f} | "
            f"{row['sign_flipped_normalized_rmse']:.3f} | {row['best_phase_shift_normalized_rmse']:.3f} | "
            f"{row['amplitude_relative_error']:.3f} |"
        )
    lines.extend(
        [
            "",
            "## Pressure Drop And Balance",
            "",
            f"- Target AAo->DAo mean pressure drop: `{drops['target_aao_to_dao_mean_drop_mmHg']:.3f}` mmHg.",
            f"- Model AAo->DAo mean pressure drop: `{drops['model_aao_to_dao_mean_drop_mmHg']:.3f}` mmHg.",
            f"- Aortic chain mass-balance error: `{payload['mass_balance']['aortic_chain_mass_balance_rel']:.3e}`.",
            f"- Aortic tree terminal mass-balance error: `{payload['mass_balance']['aortic_tree_terminal_mass_balance_rel']:.3e}`.",
            "",
            "## Failure Diagnosis",
            "",
        ]
    )
    for cause in causes:
        lines.append(f"- {cause}.")
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "The open-loop harness reports DAo chain outlet flow and lower-body outflow separately.",
            "Do not substitute `lower_ra4.flow` for the DAo chain outlet unless a later signal-policy task explicitly approves that target location.",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def evaluate(csv_path: Path, config_path: Path, source: str) -> dict[str, Any]:
    target, period = source_dataframe(source)
    model = model_last_cycle(csv_path, config_path, period)
    pressures = pressure_metrics(target, model)
    flows = flow_metrics(target, model)
    drops = pressure_drop_metrics(target, model)
    balance = mass_balance_metrics(model)
    diagnosis = diagnose_failure(flows, pressures, drops)
    gate = pass_fail(pressures, flows, balance)
    return {
        "task": "008.8",
        "source": {
            "key": source,
            "source_id": SOURCES[source]["source_id"],
            "label": SOURCES[source]["label"],
            "path": str(SOURCES[source]["path"].relative_to(ROOT)),
            "cycle_period_s": period,
        },
        "model": {
            "csv": str(csv_path.relative_to(ROOT) if csv_path.is_relative_to(ROOT) else csv_path),
            "config": str(config_path.relative_to(ROOT) if config_path.is_relative_to(ROOT) else config_path),
        },
        "pressure_metrics": pressures,
        "flow_metrics": flows,
        "pressure_drop_metrics": drops,
        "mass_balance": balance,
        "failure_diagnosis": diagnosis,
        "gate_status": gate,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evaluate the quasi aortic open-loop diagnostic simulation."
    )
    parser.add_argument("--csv", type=Path)
    parser.add_argument("--series", default="AortaQuasiOpenLoop")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--source", choices=sorted(SOURCES), default="paper_closedloop")
    parser.add_argument("--metrics-out", type=Path, default=CALIBRATION_DIR / "aorta_quasi_openloop_metrics.json")
    parser.add_argument("--waveforms-out", type=Path, default=CALIBRATION_DIR / "aorta_quasi_openloop_waveforms.csv")
    parser.add_argument("--report-out", type=Path, default=CALIBRATION_DIR / "aorta_quasi_openloop_report.md")
    args = parser.parse_args()

    csv_path = args.csv or latest_main_csv(args.series)
    payload = evaluate(csv_path, args.config, args.source)
    target, period = source_dataframe(args.source)
    model = model_last_cycle(csv_path, args.config, period)
    write_json(args.metrics_out, payload)
    write_waveform_csv(args.waveforms_out, target, model)
    write_report(args.report_out, payload)
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
