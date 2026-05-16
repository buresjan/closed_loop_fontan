#!/usr/bin/env python3
from __future__ import annotations

import argparse
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
from scripts.calibration.map_aortic_signals import load_policy, waveform_signal_specs

WAVEFORMS = ROOT / "data/processed/aramburu_2024/targets/waveform_targets.csv"

NON_AORTIC_MODEL_SIGNAL_MAP: dict[str, tuple[tuple[str, ...], float]] = {
    "svc_pressure": (("svc.blood_pressure",), MMHG_PER_PA),
    "ivc_pressure": (("ivc.blood_pressure",), MMHG_PER_PA),
    "rpa_pressure": (("rpa.blood_pressure",), MMHG_PER_PA),
    "lpa_pressure": (("lpa.blood_pressure",), MMHG_PER_PA),
    "wedge_pressure": (("right_lung.pressure_mid",), MMHG_PER_PA),
    "ventricle_volume": (("cavity.volume",), ML_PER_M3),
    "svc_flow": (
        ("quasi_svc_rl_03.flux", "svc_conduit_rl.flux"),
        ML_PER_M3,
    ),
    "ivc_flow": (
        ("quasi_ivc_rl_05.flux", "ivc_conduit_rl.flux"),
        ML_PER_M3,
    ),
    "rpa_flow": (
        ("quasi_rpa_rl_03.flux", "rpa_conduit_out.flow"),
        ML_PER_M3,
    ),
    "lpa_flow": (
        ("quasi_lpa_rl_04.flux", "lpa_conduit_out.flow"),
        ML_PER_M3,
    ),
}


def base_signal_specs() -> dict[str, dict[str, Any]]:
    return {
        name: {
            "columns": columns,
            "scale": scale,
            "target_canonical_name": name,
            "signal_policy_id": None,
            "comparison_role": "standard_waveform",
            "include_in_no_strong_regression": True,
            "include_in_superiority_gate": False,
        }
        for name, (columns, scale) in NON_AORTIC_MODEL_SIGNAL_MAP.items()
    }


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def display_path(path: Path | None) -> str | None:
    if path is None:
        return None
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def last_cycle(df: pd.DataFrame, period: float) -> pd.DataFrame:
    sub = df[df["time"] >= df["time"].max() - period].copy()
    t0 = float(sub["time"].iloc[0])
    sub["phase"] = (sub["time"] - t0) / period
    return sub


def model_waveform(
    csv_path: Path,
    config_path: Path,
    canonical_name: str,
    specs: dict[str, dict[str, Any]] | None = None,
) -> tuple[np.ndarray, np.ndarray, str] | None:
    cfg = load_json(config_path)
    df = with_resistor_flows(pd.read_csv(csv_path), cfg)
    sub = last_cycle(df, 60.0 / float(cfg["parameters"]["heart_rate"]))
    if specs is None:
        specs = {**base_signal_specs(), **waveform_signal_specs(cfg, config_path=config_path)}
    if canonical_name not in specs:
        return None

    spec = specs[canonical_name]
    columns = spec["columns"]
    scale = spec["scale"]
    selected = next((col for col in columns if col in sub), None)
    if selected is None:
        return None
    return sub["phase"].to_numpy(), sub[selected].to_numpy() * scale, selected


def waveform_row(
    target_rows: pd.DataFrame,
    model_phase: np.ndarray,
    model_values: np.ndarray,
) -> dict[str, float]:
    target_phase = target_rows["phase"].to_numpy()
    target_values = target_rows["value"].to_numpy()
    model_interp = np.interp(target_phase, model_phase, model_values)

    target_amplitude = float(target_values.max() - target_values.min())
    model_amplitude = float(model_interp.max() - model_interp.min())
    denominator = target_amplitude if target_amplitude > 0.0 else max(
        abs(float(target_values.mean())),
        1e-9,
    )
    rmse = float(np.sqrt(np.mean((model_interp - target_values) ** 2)))
    target_peak = float(target_phase[np.argmax(target_values)])
    model_peak = float(target_phase[np.argmax(model_interp)])
    raw_peak_error = abs(model_peak - target_peak)
    peak_error = min(raw_peak_error, 1.0 - raw_peak_error)

    return {
        "normalized_rmse": rmse / denominator,
        "model_amplitude": model_amplitude,
        "target_amplitude": target_amplitude,
        "amplitude_relative_error": (
            (model_amplitude - target_amplitude) / target_amplitude
            if target_amplitude > 0.0
            else math.nan
        ),
        "model_peak_phase": model_peak,
        "target_peak_phase": target_peak,
        "peak_phase_error": peak_error,
    }


def compare(
    csv_path: Path,
    config_path: Path,
    source_id: str,
    reference_csv: Path | None = None,
    reference_config: Path | None = None,
    policy_path: Path | None = None,
) -> dict[str, Any]:
    policy = load_policy(policy_path) if policy_path is not None else load_policy()
    targets = pd.read_csv(WAVEFORMS)
    targets = targets[targets["source_id"] == source_id]
    model_config = load_json(config_path)
    model_specs = {**base_signal_specs(), **waveform_signal_specs(model_config, config_path=config_path, policy=policy)}
    reference_specs = None
    if reference_config is not None:
        ref_config = load_json(reference_config)
        reference_specs = {
            **base_signal_specs(),
            **waveform_signal_specs(ref_config, config_path=reference_config, policy=policy),
        }
    rows = []
    for canonical_name in sorted(model_specs):
        spec = model_specs[canonical_name]
        target_canonical_name = spec["target_canonical_name"]
        target_rows = targets[targets["canonical_name"] == target_canonical_name]
        if target_rows.empty:
            continue
        signal = model_waveform(csv_path, config_path, canonical_name, model_specs)
        if signal is None:
            continue
        row: dict[str, Any] = {
            "canonical_name": canonical_name,
            "target_canonical_name": target_canonical_name,
            "model_signal": signal[2],
            "signal_policy_id": spec["signal_policy_id"],
            "comparison_role": spec["comparison_role"],
            "include_in_no_strong_regression": spec["include_in_no_strong_regression"],
            "include_in_superiority_gate": spec["include_in_superiority_gate"],
            **waveform_row(target_rows, signal[0], signal[1]),
        }
        if reference_csv is not None and reference_config is not None and reference_specs is not None:
            ref_signal = model_waveform(
                reference_csv,
                reference_config,
                canonical_name,
                reference_specs,
            )
            if ref_signal is not None:
                reference = waveform_row(target_rows, ref_signal[0], ref_signal[1])
                row["reference_signal"] = ref_signal[2]
                row["reference_normalized_rmse"] = reference["normalized_rmse"]
                row["reference_amplitude_relative_error"] = reference[
                    "amplitude_relative_error"
                ]
                row["reference_peak_phase_error"] = reference["peak_phase_error"]
                row["improves_normalized_rmse"] = (
                    row["normalized_rmse"] < reference["normalized_rmse"]
                )
        rows.append(row)

    return {
        "source_id": source_id,
        "model_csv": display_path(csv_path),
        "model_config": display_path(config_path),
        "reference_csv": display_path(reference_csv),
        "reference_config": display_path(reference_config),
        "aortic_signal_policy": display_path(
            policy_path or ROOT / "models/quasi_0d_1d/calibration/aortic_signal_policy.json"
        ),
        "waveforms": rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compare last-cycle model waveforms against processed targets."
    )
    parser.add_argument("csv", type=Path)
    parser.add_argument("config", type=Path)
    parser.add_argument("--source-id", default="direct_measurement")
    parser.add_argument("--reference-csv", type=Path)
    parser.add_argument("--reference-config", type=Path)
    parser.add_argument("--policy", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    payload = compare(
        args.csv,
        args.config,
        args.source_id,
        args.reference_csv,
        args.reference_config,
        args.policy,
    )
    text = json.dumps(payload, indent=2, sort_keys=True)
    print(text)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
