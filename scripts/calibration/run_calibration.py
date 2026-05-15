#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.calibration.objective import (
    DEFAULT_FACTORS,
    apply_calibration_factors,
    has_calibration_sentinels,
    load_json,
    write_json,
)

CONFIG_DIR = ROOT / "models/full_0d/configs"
REFERENCE_DIR = ROOT / "models/full_0d/reference_outputs"

SCENARIOS = {
    "baseline": ("fontan_0d_baseline.jsonc", "Baseline"),
    "vasodilation": ("fontan_0d_vasodilation.jsonc", "Vasodilation"),
    "fenestration": ("fontan_0d_fenestration.jsonc", "Fenestration"),
    "lpa_obstruction": ("fontan_0d_lpa_obstruction.jsonc", "LPAObstruction"),
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
    for path in sorted(CONFIG_DIR.glob("fontan_0d_*.jsonc")):
        current = load_json(path)
        if has_calibration_sentinels(current, DEFAULT_FACTORS):
            print(f"{path.relative_to(ROOT)} already has Task 004 calibration sentinels")
            continue
        cfg = apply_calibration_factors(current, DEFAULT_FACTORS)
        write_json(path, cfg)


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


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Apply and evaluate the selected full 0-D calibration factors."
    )
    parser.add_argument("--write-configs", action="store_true")
    parser.add_argument("--run-reference-scenarios", action="store_true")
    args = parser.parse_args()

    if args.write_configs:
        write_calibrated_configs()
    if args.run_reference_scenarios:
        run_reference_scenarios()
    if not args.write_configs and not args.run_reference_scenarios:
        parser.error("Choose --write-configs and/or --run-reference-scenarios")


if __name__ == "__main__":
    main()
