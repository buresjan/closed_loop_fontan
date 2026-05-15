#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import math
from copy import deepcopy
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
TARGETS = ROOT / "data/processed/aramburu_2024/targets/summary_targets.csv"

DEFAULT_FACTORS: dict[str, float] = {
    "heart_rate_bpm": 69.93006993006986,
    "heart_geometry_scale": 0.715,
    "heart_contractility_scale": 0.42,
    "aortic_trunk_resistance_scale": 0.40,
    "upper_systemic_resistance_scale": 0.50,
    "lower_systemic_resistance_scale": 0.90,
    "right_pulmonary_resistance_scale": 0.45,
    "left_pulmonary_resistance_scale": 0.65,
    "tcpc_entry_resistance_scale": 0.55,
    "pressure_initialization_shift_mmHg": 5.5,
    "active_atrium_unstressed_volume_ml": 40.0,
    "settling_duration_s": 20.0,
}

AORTIC_TRUNK_RESISTANCES = ["aao_arch.resistance"]
UPPER_SYSTEMIC_RESISTANCES = [
    "arch_bca.resistance",
    "upper_bca_to_ca1.resistance",
    "arch_lcca.resistance",
    "upper_lcca_to_ca1.resistance",
    "arch_lsa.resistance",
    "upper_lsa_to_ca1.resistance",
    "upper_rc1.resistance",
    "upper_rv1.resistance",
]
LOWER_SYSTEMIC_RESISTANCES = [
    "arch_dao.resistance",
    "lower_ra4.resistance",
    "lower_rc2.resistance",
    "lower_rv2.resistance",
]
RIGHT_PULMONARY_RESISTANCES = [
    "right_lung.resistance_1",
    "right_lung.resistance_2",
    "rpa_conduit_out.resistance",
]
LEFT_PULMONARY_RESISTANCES = [
    "left_lung.resistance_1",
    "left_lung.resistance_2",
    "lpa_conduit_out.resistance",
]
RIGHT_PULMONARY_CONDUCTANCES = [
    "rpa_conduit_rl.conductance",
    "rpa_conduit_rl.backward_conductance",
]
LEFT_PULMONARY_CONDUCTANCES = [
    "lpa_conduit_rl.conductance",
    "lpa_conduit_rl.backward_conductance",
]
TCPC_ENTRY_RESISTANCES = [
    "svc_conduit_junction.resistance",
    "ivc_conduit_junction.resistance",
]
TCPC_ENTRY_CONDUCTANCES = [
    "svc_conduit_rl.conductance",
    "svc_conduit_rl.backward_conductance",
    "ivc_conduit_rl.conductance",
    "ivc_conduit_rl.backward_conductance",
]

TARGET_MAP = [
    ("EDV_ml", "edv", "max", "ml", 3.0),
    ("ESV_ml", "esv", "min", "ml", 3.0),
    ("SV_from_volume_ml", "stroke_volume", "edv_minus_esv", "ml", 4.0),
    (
        "CO_from_valve_arterial.flux_L_min",
        "cardiac_output",
        "from_stroke_volume",
        "L/min",
        4.0,
    ),
    ("mean_aao_pressure_mmHg", "ascending_aorta_pressure", "mean", "mmHg", 2.0),
    ("mean_aortic_arch_pressure_mmHg", "aortic_arch_pressure", "mean", "mmHg", 2.0),
    ("mean_dao_pressure_mmHg", "descending_aorta_pressure", "mean", "mmHg", 1.0),
    ("mean_svc_pressure_mmHg", "svc_pressure", "mean", "mmHg", 2.0),
    ("mean_ivc_pressure_mmHg", "ivc_pressure", "mean", "mmHg", 2.0),
    ("mean_rpa_pressure_mmHg", "rpa_pressure", "mean", "mmHg", 2.0),
    ("mean_lpa_pressure_mmHg", "lpa_pressure", "mean", "mmHg", 2.0),
    (
        "mean_right_lung_pressure_mid_mmHg",
        "wedge_pressure",
        "mean",
        "mmHg",
        1.0,
    ),
    ("mean_svc_conduit_rl.flux_ml_s", "svc_flow", "beat_integral", "ml/s", 2.0),
    ("mean_ivc_conduit_rl.flux_ml_s", "ivc_flow", "beat_integral", "ml/s", 1.5),
    ("mean_rpa_conduit_out.flow_ml_s", "rpa_flow", "beat_integral", "ml/s", 2.0),
    ("mean_lpa_conduit_out.flow_ml_s", "lpa_flow", "beat_integral", "ml/s", 2.0),
    ("rpa_flow_fraction", "rpa_flow_fraction", "rpa_over_rpa_plus_lpa", "1", 3.0),
]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def load_summary_targets(source_id: str = "direct_measurement") -> dict[tuple[str, str], dict[str, Any]]:
    df = pd.read_csv(TARGETS)
    df = df[df["source_id"] == source_id]
    return {
        (str(row.canonical_name), str(row.statistic)): row._asdict()
        for row in df.itertuples(index=False)
    }


def scale_parameters(params: dict[str, Any], names: list[str], scale: float) -> None:
    for name in names:
        if name in params:
            params[name] *= scale


def inverse_scale_parameters(params: dict[str, Any], names: list[str], scale: float) -> None:
    for name in names:
        if name in params:
            params[name] /= scale


def has_calibration_sentinels(
    config: dict[str, Any],
    factors: dict[str, float] | None = None,
) -> bool:
    factors = dict(DEFAULT_FACTORS if factors is None else factors)
    params = config.get("parameters", {})
    sentinel_values = {
        "heart_rate": factors["heart_rate_bpm"],
        "active_atrium.unstressed_volume": (
            factors["active_atrium_unstressed_volume_ml"] * 1e-6
        ),
    }
    for name, target in sentinel_values.items():
        if name not in params:
            return False
        if not math.isclose(float(params[name]), target, rel_tol=1e-12, abs_tol=1e-15):
            return False
    return True


def apply_calibration_factors(
    config: dict[str, Any],
    factors: dict[str, float] | None = None,
    *,
    keep_short_smoke: bool = True,
) -> dict[str, Any]:
    factors = dict(DEFAULT_FACTORS if factors is None else factors)
    calibrated = deepcopy(config)
    if has_calibration_sentinels(calibrated, factors):
        return calibrated

    params = calibrated["parameters"]

    params["heart_rate"] = factors["heart_rate_bpm"]
    params["heart_radius"] *= factors["heart_geometry_scale"]
    params["heart_thickness"] *= factors["heart_geometry_scale"]
    params["heart_contractility"] *= factors["heart_contractility_scale"]
    params["active_atrium.unstressed_volume"] = (
        factors["active_atrium_unstressed_volume_ml"] * 1e-6
    )

    scale_parameters(
        params,
        AORTIC_TRUNK_RESISTANCES,
        factors["aortic_trunk_resistance_scale"],
    )
    scale_parameters(
        params,
        UPPER_SYSTEMIC_RESISTANCES,
        factors["upper_systemic_resistance_scale"],
    )
    scale_parameters(
        params,
        LOWER_SYSTEMIC_RESISTANCES,
        factors["lower_systemic_resistance_scale"],
    )
    scale_parameters(
        params,
        RIGHT_PULMONARY_RESISTANCES,
        factors["right_pulmonary_resistance_scale"],
    )
    scale_parameters(
        params,
        LEFT_PULMONARY_RESISTANCES,
        factors["left_pulmonary_resistance_scale"],
    )
    inverse_scale_parameters(
        params,
        RIGHT_PULMONARY_CONDUCTANCES,
        factors["right_pulmonary_resistance_scale"],
    )
    inverse_scale_parameters(
        params,
        LEFT_PULMONARY_CONDUCTANCES,
        factors["left_pulmonary_resistance_scale"],
    )
    scale_parameters(
        params,
        TCPC_ENTRY_RESISTANCES,
        factors["tcpc_entry_resistance_scale"],
    )
    inverse_scale_parameters(
        params,
        TCPC_ENTRY_CONDUCTANCES,
        factors["tcpc_entry_resistance_scale"],
    )

    shift_pa = factors["pressure_initialization_shift_mmHg"] * 133.33
    for name, value in list(calibrated["variables_initialization"].items()):
        if name.endswith("blood_pressure") or name.endswith("pressure_mid"):
            calibrated["variables_initialization"][name] = max(float(value) - shift_pa, 1.0)

    if not keep_short_smoke or float(calibrated["time"]["duration"]) >= 1.0:
        calibrated["time"]["duration"] = factors["settling_duration_s"]

    return calibrated


def target_value(
    targets: dict[tuple[str, str], dict[str, Any]],
    canonical_name: str,
    statistic: str,
    expected_unit: str,
) -> float:
    row = targets[(canonical_name, statistic)]
    value = float(row["value"])
    unit = str(row["unit"])
    if statistic == "beat_integral" and expected_unit == "ml/s":
        return value / float(row["cycle_length_s"])
    if unit == expected_unit:
        return value
    raise ValueError(f"Unsupported target unit conversion {unit} -> {expected_unit}")


def comparison_rows(
    metrics: dict[str, Any],
    source_id: str = "direct_measurement",
) -> list[dict[str, Any]]:
    targets = load_summary_targets(source_id)
    rows: list[dict[str, Any]] = []
    for metric, canonical, statistic, unit, weight in TARGET_MAP:
        if metric not in metrics:
            continue
        if (canonical, statistic) not in targets:
            continue
        target = target_value(targets, canonical, statistic, unit)
        model = float(metrics[metric])
        error = model - target
        rel_error = error / target if abs(target) > 1e-12 else math.nan
        rows.append(
            {
                "metric": metric,
                "target_name": canonical,
                "target_statistic": statistic,
                "model_value": model,
                "target_value": target,
                "unit": unit,
                "error": error,
                "relative_error": rel_error,
                "absolute_relative_error": abs(rel_error),
                "weight": weight,
                "source_id": source_id,
            }
        )
    return rows


def weighted_rms(rows: list[dict[str, Any]]) -> float:
    numerator = sum(row["weight"] * row["relative_error"] ** 2 for row in rows)
    denominator = sum(row["weight"] for row in rows)
    return math.sqrt(numerator / denominator)


def penalty_rows(metrics: dict[str, Any]) -> list[dict[str, Any]]:
    checks = [
        ("periodicity_cavity_volume", 0.02),
        ("periodicity_valve_arterial.flux", 0.02),
        ("periodicity_valve_atrium.flux", 0.02),
        ("tcpc_cycle_balance_rel", 1e-2),
        ("atrium_cycle_balance_rel", 1e-2),
        ("ventricle_cycle_balance_rel", 1e-2),
    ]
    rows = []
    for metric, threshold in checks:
        value = float(metrics.get(metric, math.nan))
        rows.append(
            {
                "metric": metric,
                "value": value,
                "threshold": threshold,
                "pass": bool(value <= threshold),
            }
        )
    return rows


def write_comparison_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate full 0-D calibration metrics.")
    parser.add_argument("metrics", type=Path)
    parser.add_argument("--source-id", default="direct_measurement")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    rows = comparison_rows(load_json(args.metrics), args.source_id)
    payload = {
        "weighted_rms_relative_error": weighted_rms(rows),
        "targets": rows,
        "penalties": penalty_rows(load_json(args.metrics)),
    }
    text = json.dumps(payload, indent=2)
    print(text)
    if args.out:
        args.out.write_text(text + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
