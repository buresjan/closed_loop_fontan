#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.modeling.build_quasi_configs import build_all_configs, write_json

CONFIG_DIR = ROOT / "models/quasi_0d_1d/configs"
REFERENCE_DIR = ROOT / "models/quasi_0d_1d/reference_outputs"
CALIBRATION_DIR = ROOT / "models/quasi_0d_1d/calibration"

SCENARIOS = {
    "baseline": ("fontan_quasi_baseline.jsonc", "QuasiBaseline"),
    "vasodilation": ("fontan_quasi_vasodilation.jsonc", "QuasiVasodilation"),
    "fenestration": ("fontan_quasi_fenestration.jsonc", "QuasiFenestration"),
    "lpa_obstruction": ("fontan_quasi_lpa_obstruction.jsonc", "QuasiLPAObstruction"),
}


def run(cmd: list[str]) -> None:
    print("$ " + " ".join(cmd), flush=True)
    subprocess.run(cmd, cwd=ROOT, check=True)


def latest_main_csv(series: str) -> Path:
    paths = sorted((ROOT / "runs/simulations" / series).glob("*/main.csv"))
    if not paths:
        raise FileNotFoundError(f"No main.csv found for series {series}")
    return paths[-1]


def write_calibrated_configs() -> None:
    for name, config in build_all_configs().items():
        write_json(CONFIG_DIR / name, config)


def run_reference_scenarios() -> None:
    for key, (config_name, series) in SCENARIOS.items():
        config = CONFIG_DIR / config_name
        run([sys.executable, "scripts/run_one.py", str(config), "--series", series])
        run(
            [
                sys.executable,
                "scripts/metrics.py",
                str(latest_main_csv(series)),
                str(config),
                "--out",
                str(REFERENCE_DIR / f"{key}_metrics.json"),
            ]
        )

    compare_cmd = [
        sys.executable,
        "scripts/compare_scenarios.py",
        str(REFERENCE_DIR / "baseline_metrics.json"),
        str(REFERENCE_DIR / "vasodilation_metrics.json"),
        str(REFERENCE_DIR / "fenestration_metrics.json"),
        str(REFERENCE_DIR / "lpa_obstruction_metrics.json"),
    ]
    print("$ " + " ".join(compare_cmd), flush=True)
    with (REFERENCE_DIR / "scenario_comparison.txt").open(
        "w",
        encoding="utf-8",
    ) as f:
        subprocess.run(compare_cmd, cwd=ROOT, check=True, stdout=f)


def write_objective_reports() -> None:
    baseline = REFERENCE_DIR / "baseline_metrics.json"
    run(
        [
            sys.executable,
            "scripts/calibration/objective.py",
            str(baseline),
            "--out",
            str(CALIBRATION_DIR / "baseline_objective.json"),
        ]
    )
    run(
        [
            sys.executable,
            "scripts/calibration/compare_to_paper.py",
            str(baseline),
            "--source-id",
            "paper_model",
            "--out",
            str(CALIBRATION_DIR / "baseline_vs_paper.json"),
        ]
    )
    run([sys.executable, "scripts/calibration/map_aortic_signals.py"])
    run(
        [
            sys.executable,
            "scripts/calibration/compare_waveforms.py",
            str(latest_main_csv("QuasiBaseline")),
            str(CONFIG_DIR / "fontan_quasi_baseline.jsonc"),
            "--source-id",
            "direct_measurement",
            "--reference-csv",
            str(latest_main_csv("Baseline")),
            "--reference-config",
            str(ROOT / "models/full_0d/configs/fontan_0d_baseline.jsonc"),
            "--out",
            str(CALIBRATION_DIR / "baseline_waveforms_direct.json"),
        ]
    )
    run(
        [
            sys.executable,
            "scripts/calibration/quasi_non_regression.py",
            "--out",
            str(CALIBRATION_DIR / "non_regression_gate.json"),
        ]
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Apply and evaluate the selected quasi 0-D/1-D calibration."
    )
    parser.add_argument("--write-configs", action="store_true")
    parser.add_argument("--run-reference-scenarios", action="store_true")
    parser.add_argument("--write-objective-reports", action="store_true")
    args = parser.parse_args()

    if args.write_configs:
        write_calibrated_configs()
    if args.run_reference_scenarios:
        run_reference_scenarios()
    if args.write_objective_reports:
        write_objective_reports()
    if not (
        args.write_configs
        or args.run_reference_scenarios
        or args.write_objective_reports
    ):
        parser.error(
            "Choose --write-configs, --run-reference-scenarios, and/or "
            "--write-objective-reports"
        )


if __name__ == "__main__":
    main()
