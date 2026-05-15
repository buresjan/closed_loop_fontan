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

WAVEFORMS = ROOT / "data/processed/aramburu_2024/targets/waveform_targets.csv"

MODEL_SIGNAL_MAP: dict[str, tuple[tuple[str, ...], float]] = {
    "ascending_aorta_pressure": (("aao.blood_pressure",), MMHG_PER_PA),
    "aortic_arch_pressure": (("aortic_arch.blood_pressure",), MMHG_PER_PA),
    "descending_aorta_pressure": (("dao.blood_pressure",), MMHG_PER_PA),
    "svc_pressure": (("svc.blood_pressure",), MMHG_PER_PA),
    "ivc_pressure": (("ivc.blood_pressure",), MMHG_PER_PA),
    "rpa_pressure": (("rpa.blood_pressure",), MMHG_PER_PA),
    "lpa_pressure": (("lpa.blood_pressure",), MMHG_PER_PA),
    "wedge_pressure": (("right_lung.pressure_mid",), MMHG_PER_PA),
    "ventricle_volume": (("cavity.volume",), ML_PER_M3),
    "ascending_aorta_flow": (
        ("quasi_aao_arch_rl_01.flux", "aao_arch.flow", "valve_arterial.flux"),
        ML_PER_M3,
    ),
    "descending_aorta_flow": (
        ("quasi_dao_rl_06.flux", "arch_dao.flow"),
        ML_PER_M3,
    ),
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


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def last_cycle(df: pd.DataFrame, period: float) -> pd.DataFrame:
    sub = df[df["time"] >= df["time"].max() - period].copy()
    t0 = float(sub["time"].iloc[0])
    sub["phase"] = (sub["time"] - t0) / period
    return sub


def model_waveform(
    csv_path: Path,
    config_path: Path,
    canonical_name: str,
) -> tuple[np.ndarray, np.ndarray] | None:
    cfg = load_json(config_path)
    df = with_resistor_flows(pd.read_csv(csv_path), cfg)
    sub = last_cycle(df, 60.0 / float(cfg["parameters"]["heart_rate"]))
    if canonical_name not in MODEL_SIGNAL_MAP:
        return None

    columns, scale = MODEL_SIGNAL_MAP[canonical_name]
    selected = next((col for col in columns if col in sub), None)
    if selected is None:
        return None
    return sub["phase"].to_numpy(), sub[selected].to_numpy() * scale


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
) -> dict[str, Any]:
    targets = pd.read_csv(WAVEFORMS)
    targets = targets[targets["source_id"] == source_id]
    rows = []
    for canonical_name in sorted(targets["canonical_name"].unique()):
        signal = model_waveform(csv_path, config_path, canonical_name)
        if signal is None:
            continue
        target_rows = targets[targets["canonical_name"] == canonical_name]
        row: dict[str, Any] = {
            "canonical_name": canonical_name,
            **waveform_row(target_rows, signal[0], signal[1]),
        }
        if reference_csv is not None and reference_config is not None:
            ref_signal = model_waveform(reference_csv, reference_config, canonical_name)
            if ref_signal is not None:
                reference = waveform_row(target_rows, ref_signal[0], ref_signal[1])
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
        "model_csv": str(csv_path),
        "model_config": str(config_path),
        "reference_csv": str(reference_csv) if reference_csv else None,
        "reference_config": str(reference_config) if reference_config else None,
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
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    payload = compare(
        args.csv,
        args.config,
        args.source_id,
        args.reference_csv,
        args.reference_config,
    )
    text = json.dumps(payload, indent=2, sort_keys=True)
    print(text)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
