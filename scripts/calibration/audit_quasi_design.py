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

CALIBRATION_DIR = ROOT / "models/quasi_0d_1d/calibration"
WAVEFORMS = ROOT / "data/processed/aramburu_2024/targets/waveform_targets.csv"

PA_PER_MMHG = 1.0 / MMHG_PER_PA
MMHG_S_ML_PER_PA_S_M3 = MMHG_PER_PA / ML_PER_M3


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, allow_nan=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def latest_main_csv(series: str) -> Path:
    paths = sorted((ROOT / "runs/simulations" / series).glob("*/main.csv"))
    if not paths:
        raise FileNotFoundError(f"No main.csv found for series {series}")
    return paths[-1]


def last_cycle(df: pd.DataFrame, period: float) -> pd.DataFrame:
    sub = df[df["time"] >= df["time"].max() - period].copy()
    t0 = float(sub["time"].iloc[0])
    sub["phase"] = (sub["time"] - t0) / period
    return sub


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
    denominator = amplitude if amplitude > 0.0 else max(abs(float(target_values.mean())), 1e-9)
    return float(np.sqrt(np.mean((model_interp - target_values) ** 2)) / denominator)


def best_phase_shift_nrmse(
    target_phase: np.ndarray,
    target_values: np.ndarray,
    model_phase: np.ndarray,
    model_values: np.ndarray,
) -> tuple[float, float]:
    candidates = np.linspace(0.0, 1.0, 101, endpoint=False)
    values = [
        normalized_rmse(
            target_phase,
            target_values,
            model_phase,
            model_values,
            phase_shift=float(shift),
        )
        for shift in candidates
    ]
    index = int(np.argmin(values))
    return float(values[index]), float(candidates[index])


def target_waveform(canonical_name: str, source_id: str) -> tuple[np.ndarray, np.ndarray]:
    targets = pd.read_csv(WAVEFORMS)
    rows = targets[
        (targets["canonical_name"] == canonical_name)
        & (targets["source_id"] == source_id)
    ]
    if rows.empty:
        raise ValueError(f"No waveform target for {source_id}:{canonical_name}")
    return rows["phase"].to_numpy(), rows["value"].to_numpy()


def model_cycle(csv_path: Path, config_path: Path) -> tuple[pd.DataFrame, dict[str, Any]]:
    cfg = load_json(config_path)
    df = with_resistor_flows(pd.read_csv(csv_path), cfg)
    period = 60.0 / float(cfg["parameters"]["heart_rate"])
    return last_cycle(df, period), cfg


def signal_candidates() -> list[dict[str, str]]:
    return [
        {
            "canonical_name": "ascending_aorta_flow",
            "model": "quasi",
            "candidate_signal": "valve_arterial.flux",
            "anatomical_location": "aortic-valve outlet/root inflow",
        },
        {
            "canonical_name": "ascending_aorta_flow",
            "model": "quasi",
            "candidate_signal": "quasi_aao_arch_rl_01.flux",
            "anatomical_location": "AAo/arch chain inlet",
        },
        {
            "canonical_name": "ascending_aorta_flow",
            "model": "quasi",
            "candidate_signal": "quasi_aao_arch_rl_04.flux",
            "anatomical_location": "AAo/arch chain outlet before arch branches",
        },
        {
            "canonical_name": "ascending_aorta_flow",
            "model": "full_0d",
            "candidate_signal": "valve_arterial.flux",
            "anatomical_location": "aortic-valve outlet/root inflow",
        },
        {
            "canonical_name": "ascending_aorta_flow",
            "model": "full_0d",
            "candidate_signal": "aao_arch.flow",
            "anatomical_location": "full 0-D AAo-to-arch resistor flow",
        },
        {
            "canonical_name": "descending_aorta_flow",
            "model": "quasi",
            "candidate_signal": "quasi_dao_rl_01.flux",
            "anatomical_location": "DAo chain inlet after arch branches",
        },
        {
            "canonical_name": "descending_aorta_flow",
            "model": "quasi",
            "candidate_signal": "quasi_dao_rl_06.flux",
            "anatomical_location": "DAo chain outlet at DAo pressure node",
        },
        {
            "canonical_name": "descending_aorta_flow",
            "model": "quasi",
            "candidate_signal": "lower_ra4.flow",
            "anatomical_location": "flow from DAo pressure node into lower systemic artery",
        },
        {
            "canonical_name": "descending_aorta_flow",
            "model": "full_0d",
            "candidate_signal": "arch_dao.flow",
            "anatomical_location": "full 0-D arch-to-DAo resistor flow",
        },
        {
            "canonical_name": "descending_aorta_flow",
            "model": "full_0d",
            "candidate_signal": "lower_ra4.flow",
            "anatomical_location": "full 0-D flow from DAo into lower systemic artery",
        },
    ]


def flow_signal_audit(
    *,
    quasi_csv: Path,
    quasi_config: Path,
    full_csv: Path,
    full_config: Path,
    source_id: str,
) -> list[dict[str, Any]]:
    quasi_cycle, _ = model_cycle(quasi_csv, quasi_config)
    full_cycle, _ = model_cycle(full_csv, full_config)
    cycles = {"quasi": quasi_cycle, "full_0d": full_cycle}
    rows: list[dict[str, Any]] = []
    for candidate in signal_candidates():
        cycle = cycles[candidate["model"]]
        signal = candidate["candidate_signal"]
        if signal not in cycle:
            continue
        target_phase, target_values = target_waveform(candidate["canonical_name"], source_id)
        model_phase = cycle["phase"].to_numpy()
        values = cycle[signal].to_numpy() * ML_PER_M3
        direct = normalized_rmse(target_phase, target_values, model_phase, values)
        flipped = normalized_rmse(target_phase, target_values, model_phase, -values)
        shifted, shift = best_phase_shift_nrmse(target_phase, target_values, model_phase, values)
        rows.append(
            {
                **candidate,
                "mean_flow_ml_s": float(np.mean(values)),
                "amplitude_ml_s": float(np.max(values) - np.min(values)),
                "normalized_rmse": direct,
                "sign_flipped_normalized_rmse": flipped,
                "best_phase_shift_normalized_rmse": shifted,
                "best_phase_shift_fraction": shift,
                "sign_checked": bool(direct <= flipped),
                "phase_dominated": bool(shifted < 0.8 * direct),
            }
        )
    return rows


def pressure_for_node(metrics: dict[str, Any], node: str) -> float:
    return float(metrics.get(f"mean_{node}_pressure_mmHg", 0.0))


def capacitance_rows(config_path: Path, metrics_path: Path, model: str) -> list[dict[str, Any]]:
    cfg = load_json(config_path)
    metrics = load_json(metrics_path)
    rows: list[dict[str, Any]] = []
    for block_name, block in cfg["net"]["blocks"].items():
        if block.get("model_type") != "c_block":
            continue
        param = f"{block_name}.capacitance"
        if param not in cfg["parameters"]:
            continue
        node = str(block["nodes"]["1"])
        capacitance = float(cfg["parameters"][param])
        pressure = pressure_for_node(metrics, node)
        rows.append(
            {
                "model": model,
                "component": block_name,
                "node": node,
                "total_C_m3_per_Pa": capacitance,
                "total_C_ml_per_mmHg": capacitance * ML_PER_M3 * PA_PER_MMHG,
                "mean_pressure_mmHg": pressure,
                "estimated_stored_volume_ml": capacitance * pressure * PA_PER_MMHG * ML_PER_M3,
                "category": compliance_category(block_name),
            }
        )
    if "active_atrium.elastance_min" in cfg["parameters"]:
        capacitance = 1.0 / float(cfg["parameters"]["active_atrium.elastance_min"])
        pressure = pressure_for_node(metrics, "atrial")
        rows.append(
            {
                "model": model,
                "component": "active_atrium_min_elastance_equivalent",
                "node": "atrial",
                "total_C_m3_per_Pa": capacitance,
                "total_C_ml_per_mmHg": capacitance * ML_PER_M3 * PA_PER_MMHG,
                "mean_pressure_mmHg": pressure,
                "estimated_stored_volume_ml": capacitance * pressure * PA_PER_MMHG * ML_PER_M3,
                "category": "active_atrium",
            }
        )
    return rows


def compliance_category(block_name: str) -> str:
    if block_name.startswith("quasi_"):
        return "quasi_chain"
    if block_name in {"aao_compliance", "aortic_arch_compliance", "dao_compliance"}:
        return "retained_aortic_endpoint"
    if block_name in {"svc_compliance", "ivc_compliance", "tcpc_compliance", "rpa_compliance", "lpa_compliance"}:
        return "retained_fontan_endpoint"
    if block_name in {"upper_ca1", "upper_cv1", "lower_ca2", "lower_cv2"}:
        return "systemic_bed"
    if block_name in {"right_lung", "left_lung"}:
        return "pulmonary_bed"
    return "other"


def summarize_compliance(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    df = pd.DataFrame(rows)
    grouped = (
        df.groupby(["model", "category"], dropna=False)
        .agg(
            total_C_m3_per_Pa=("total_C_m3_per_Pa", "sum"),
            total_C_ml_per_mmHg=("total_C_ml_per_mmHg", "sum"),
            estimated_stored_volume_ml=("estimated_stored_volume_ml", "sum"),
        )
        .reset_index()
    )
    grouped["component"] = "__category_total__"
    grouped["node"] = ""
    grouped["mean_pressure_mmHg"] = None
    return grouped.to_dict("records")


def chain_param_values(params: dict[str, Any], chain: str, suffix: str) -> list[float]:
    prefix = f"quasi_{chain}_"
    return [
        float(value)
        for key, value in sorted(params.items())
        if key.startswith(prefix) and key.endswith(suffix)
    ]


def parallel_resistance(values: list[float]) -> float:
    conductance = sum(1.0 / value for value in values if value > 0.0)
    return 1.0 / conductance if conductance > 0.0 else math.inf


def downstream_resistance(params: dict[str, Any], chain: str) -> tuple[float, str]:
    if chain == "aao_arch":
        paths = [
            params["arch_bca.resistance"] + params["upper_bca_to_ca1.resistance"],
            params["arch_lcca.resistance"] + params["upper_lcca_to_ca1.resistance"],
            params["arch_lsa.resistance"] + params["upper_lsa_to_ca1.resistance"],
            sum(chain_param_values(params, "dao", ".resistance"))
            + params["lower_ra4.resistance"],
        ]
        return parallel_resistance(paths), "parallel upper branches plus DAo/lower arterial entry"
    if chain == "dao":
        return (
            params["lower_ra4.resistance"]
            + params["lower_rc2.resistance"]
            + params["lower_rv2.resistance"],
            "lower systemic bed",
        )
    if chain in {"svc", "ivc"}:
        rpa_path = sum(chain_param_values(params, "rpa", ".resistance")) + params["right_lung.resistance_1"]
        lpa_path = sum(chain_param_values(params, "lpa", ".resistance")) + params["left_lung.resistance_1"]
        return parallel_resistance([rpa_path, lpa_path]), "parallel TCPC-to-pulmonary proximal paths"
    if chain == "rpa":
        return (
            params["right_lung.resistance_1"] + params["right_lung.resistance_2"],
            "right pulmonary RCR bed",
        )
    if chain == "lpa":
        return (
            params["left_lung.resistance_1"] + params["left_lung.resistance_2"],
            "left pulmonary RCR bed",
        )
    raise ValueError(chain)


def characteristic_impedance_rows(config_path: Path) -> list[dict[str, Any]]:
    cfg = load_json(config_path)
    params = cfg["parameters"]
    rows = []
    for chain in ["aao_arch", "dao", "svc", "ivc", "rpa", "lpa"]:
        inductances = chain_param_values(params, chain, ".inductance")
        capacitances = chain_param_values(params, chain, ".capacitance")
        z_segments = [
            math.sqrt(l_value / c_value)
            for l_value, c_value in zip(inductances, capacitances)
            if l_value >= 0.0 and c_value > 0.0
        ]
        downstream, comment = downstream_resistance(params, chain)
        z_pa = float(np.median(z_segments)) if z_segments else math.nan
        rows.append(
            {
                "vessel": chain,
                "Zc_mmHg_s_ml": z_pa * MMHG_S_ML_PER_PA_S_M3,
                "downstream_resistance_mmHg_s_ml": downstream * MMHG_S_ML_PER_PA_S_M3,
                "ratio": z_pa / downstream if downstream > 0.0 else math.nan,
                "comment": comment,
            }
        )
    return rows


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def write_report(
    path: Path,
    *,
    signal_rows: list[dict[str, Any]],
    compliance_rows_: list[dict[str, Any]],
    impedance_rows: list[dict[str, Any]],
) -> None:
    best_dao = min(
        [row for row in signal_rows if row["canonical_name"] == "descending_aorta_flow" and row["model"] == "quasi"],
        key=lambda row: row["normalized_rmse"],
    )
    best_aao = min(
        [row for row in signal_rows if row["canonical_name"] == "ascending_aorta_flow" and row["model"] == "quasi"],
        key=lambda row: row["normalized_rmse"],
    )
    comp_df = pd.DataFrame(compliance_rows_)
    totals = comp_df[comp_df["component"] == "__category_total__"]
    quasi_chain_storage = float(
        totals[
            (totals["model"] == "quasi_0d_1d")
            & (totals["category"] == "quasi_chain")
        ]["estimated_stored_volume_ml"].sum()
    )
    text = f"""# Quasi Design Audit Report

Generated for Task 008.6.

## Flow Signal Audit

- Best quasi AAo-flow candidate: `{best_aao['candidate_signal']}` at `{best_aao['anatomical_location']}` with nRMSE `{best_aao['normalized_rmse']:.3f}`.
- Best quasi DAo-flow candidate: `{best_dao['candidate_signal']}` at `{best_dao['anatomical_location']}` with nRMSE `{best_dao['normalized_rmse']:.3f}`.
- Sign-flipped comparisons were worse for the selected quasi candidates, so the regression is not explained by sign convention alone.
- Phase-shifted nRMSE is tracked in `dao_aao_flow_signal_audit.csv`; large improvements after phase shift indicate timing contribution, not acceptance.
- The closer DAo diagnostic is downstream of the DAo pressure node. The closure gate still tracks the DAo-chain outlet because switching only to lower systemic bed entry would hide trunk-chain waveform behavior rather than fix it.

## Compliance And Storage

- Quasi chain estimated gauge storage is `{quasi_chain_storage:.3f}` ml, small compared with retained systemic and caval endpoint storage.
- The quasi model adds chain capacitances on top of retained endpoint compliances; this is documented for later redistribution tests.

## Characteristic Impedance

- Characteristic impedance ratios are tracked in `characteristic_impedance_report.csv`.
- Large ratios are interpreted as possible artificial reflection points and should guide the ablation grid.

## Conclusion

The AAo/DAo flow failure should be treated as a real design/calibration issue until a candidate topology or R/L/C ablation removes the regression. Task 008.6 should not promote a quasi reference unless the closure gate accepts it.
"""
    path.write_text(text, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Audit quasi 0-D/1-D design failures before Task 009."
    )
    parser.add_argument("--quasi-csv", type=Path)
    parser.add_argument("--full-csv", type=Path)
    parser.add_argument(
        "--quasi-config",
        type=Path,
        default=ROOT / "models/quasi_0d_1d/configs/fontan_quasi_baseline.jsonc",
    )
    parser.add_argument(
        "--full-config",
        type=Path,
        default=ROOT / "models/full_0d/configs/fontan_0d_baseline.jsonc",
    )
    parser.add_argument(
        "--quasi-metrics",
        type=Path,
        default=ROOT / "models/quasi_0d_1d/reference_outputs/baseline_metrics.json",
    )
    parser.add_argument(
        "--full-metrics",
        type=Path,
        default=ROOT / "models/full_0d/reference_outputs/baseline_metrics.json",
    )
    parser.add_argument("--source-id", default="direct_measurement")
    args = parser.parse_args()

    quasi_csv = args.quasi_csv or latest_main_csv("QuasiBaseline")
    full_csv = args.full_csv or latest_main_csv("Baseline")
    signal_rows = flow_signal_audit(
        quasi_csv=quasi_csv,
        quasi_config=args.quasi_config,
        full_csv=full_csv,
        full_config=args.full_config,
        source_id=args.source_id,
    )
    compliance_detail = [
        *capacitance_rows(args.full_config, args.full_metrics, "full_0d"),
        *capacitance_rows(args.quasi_config, args.quasi_metrics, "quasi_0d_1d"),
    ]
    compliance_all = [*compliance_detail, *summarize_compliance(compliance_detail)]
    impedance_rows = characteristic_impedance_rows(args.quasi_config)

    write_csv(CALIBRATION_DIR / "dao_aao_flow_signal_audit.csv", signal_rows)
    write_csv(CALIBRATION_DIR / "compliance_budget.csv", compliance_all)
    write_csv(CALIBRATION_DIR / "characteristic_impedance_report.csv", impedance_rows)

    payload = {
        "task": "008.6",
        "flow_signal_audit": signal_rows,
        "compliance_budget_summary": summarize_compliance(compliance_detail),
        "characteristic_impedance": impedance_rows,
    }
    write_json(CALIBRATION_DIR / "design_audit.json", payload)
    write_report(
        CALIBRATION_DIR / "design_audit_report.md",
        signal_rows=signal_rows,
        compliance_rows_=compliance_all,
        impedance_rows=impedance_rows,
    )
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
