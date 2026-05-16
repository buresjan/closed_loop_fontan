#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
QUASI_DIR = ROOT / "models/quasi_0d_1d"
DEFAULT_CONFIG = QUASI_DIR / "configs/submodel_aorta_quasi_openloop.jsonc"
BASELINE_CONFIG = QUASI_DIR / "configs/fontan_quasi_baseline.jsonc"

PA_PER_MMHG = 133.322
M3_PER_ML = 1.0e-6

SOURCES = {
    "paper_closedloop": {
        "source_id": "paper_closedloop_1d",
        "path": ROOT / "data/processed/aramburu_2024/comparison/04_aorta_tcpc_closedloop_1d_last_cycle_clinical.csv",
        "label": "Paper/Nektar closed-loop 1-D",
    },
    "paper_openloop": {
        "source_id": "paper_openloop_1d",
        "path": ROOT / "data/processed/aramburu_2024/comparison/03_aorta_tcpc_1d_last_cycle_clinical.csv",
        "label": "Paper/Nektar aorta-TCPC 1-D",
    },
    "direct": {
        "source_id": "direct_measurement",
        "path": ROOT / "data/processed/aramburu_2024/comparison/measurements_last_cycle_clinical.csv",
        "label": "Direct measurement",
    },
}

PRESSURE_NODES = [
    "aao",
    "quasi_aao_arch_p_01",
    "quasi_aao_arch_p_02",
    "quasi_aao_arch_p_03",
    "aortic_arch",
    "bca",
    "lcca",
    "lsa",
    "upper_art",
    "upper_ven",
    "dao",
    "quasi_dao_p_01",
    "quasi_dao_p_02",
    "quasi_dao_p_03",
    "quasi_dao_p_04",
    "quasi_dao_p_05",
    "lower_art",
    "lower_ven",
    "svc",
    "ivc",
]

AORTIC_BLOCKS = [
    "aao_compliance",
    "aortic_arch_compliance",
    "dao_compliance",
    "bca_compliance",
    "lcca_compliance",
    "lsa_compliance",
    "upper_ca1",
    "upper_cv1",
    "lower_ca2",
    "lower_cv2",
    "arch_bca",
    "upper_bca_to_ca1",
    "arch_lcca",
    "upper_lcca_to_ca1",
    "arch_lsa",
    "upper_lsa_to_ca1",
    "upper_rc1",
    "upper_rv1",
    "lower_ra4",
    "lower_rc2",
    "lower_rv2",
]

WATCH_QUANTITIES = [
    "aao_inflow.blood_flow",
    "svc.blood_pressure",
    "ivc.blood_pressure",
]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def source_table(source: str) -> pd.DataFrame:
    return pd.read_csv(SOURCES[source]["path"])


def cycle_period(times: pd.Series) -> float:
    values = times.to_numpy(dtype=float)
    dt = float(np.median(np.diff(values)))
    return float(len(values) * dt)


def pressure_pa(value_mm_hg: float) -> float:
    return float(value_mm_hg) * PA_PER_MMHG


def mean_pressure_pa(df: pd.DataFrame, column: str) -> float:
    return pressure_pa(float(df[column].mean()))


def pressure_initial_conditions(df: pd.DataFrame) -> dict[str, float]:
    first = df.iloc[0]
    mean = {
        "aao": mean_pressure_pa(df, "ascending_aorta_pressure_mmHg"),
        "aortic_arch": mean_pressure_pa(df, "aortic_arch_pressure_mmHg"),
        "dao": mean_pressure_pa(df, "descending_aorta_pressure_mmHg"),
        "svc": mean_pressure_pa(df, "svc_pressure_mmHg"),
        "ivc": mean_pressure_pa(df, "ivc_pressure_mmHg"),
    }
    initial = {
        "aao": pressure_pa(first["ascending_aorta_pressure_mmHg"]),
        "aortic_arch": pressure_pa(first["aortic_arch_pressure_mmHg"]),
        "dao": pressure_pa(first["descending_aorta_pressure_mmHg"]),
        "svc": mean["svc"],
        "ivc": mean["ivc"],
    }
    for index, node in enumerate(["quasi_aao_arch_p_01", "quasi_aao_arch_p_02", "quasi_aao_arch_p_03"], start=1):
        alpha = index / 4.0
        initial[node] = (1.0 - alpha) * initial["aao"] + alpha * initial["aortic_arch"]
    for index, node in enumerate(["quasi_dao_p_01", "quasi_dao_p_02", "quasi_dao_p_03", "quasi_dao_p_04", "quasi_dao_p_05"], start=1):
        alpha = index / 6.0
        initial[node] = (1.0 - alpha) * initial["aortic_arch"] + alpha * initial["dao"]
    for node in ["bca", "lcca", "lsa", "upper_art"]:
        initial[node] = initial["aortic_arch"]
    for node in ["lower_art"]:
        initial[node] = initial["dao"]
    initial["upper_ven"] = initial["svc"]
    initial["lower_ven"] = initial["ivc"]
    return initial


def copy_block(config: dict[str, Any], block_name: str) -> dict[str, Any]:
    return json.loads(json.dumps(config["net"]["blocks"][block_name]))


def build_config(source: str = "paper_closedloop", cycles: int = 12) -> dict[str, Any]:
    baseline = load_json(BASELINE_CONFIG)
    df = source_table(source)
    period = cycle_period(df["time_s"])
    step_size = float(np.median(np.diff(df["time_s"].to_numpy(dtype=float))))
    pressure_init = pressure_initial_conditions(df)

    blocks: dict[str, Any] = {}
    parameters: dict[str, Any] = {}
    variables_initialization: dict[str, float] = {}
    variables_magnitudes: dict[str, float] = {}

    for name, block in baseline["net"]["blocks"].items():
        if name.startswith("quasi_aao_arch_") or name.startswith("quasi_dao_"):
            blocks[name] = copy_block(baseline, name)
    for name in AORTIC_BLOCKS:
        blocks[name] = copy_block(baseline, name)

    parameter_names = {"zero_capacitance"}
    for block in blocks.values():
        for key, value in block.items():
            if key in {"resistance", "inductance", "capacitance"}:
                parameter_names.add(value)
    for block_name in blocks:
        prefix = f"{block_name}."
        parameter_names.update(
            name for name in baseline["parameters"] if name.startswith(prefix)
        )
    for name in sorted(parameter_names):
        if name in baseline["parameters"]:
            parameters[name] = baseline["parameters"][name]

    flow_points = (df["ascending_aorta_flow_ml_s"].to_numpy(dtype=float) * M3_PER_ML).tolist()
    time_points = df["time_s"].to_numpy(dtype=float).tolist()
    parameters["aao_inflow.blood_flow"] = {
        "type": "piecewise_linear_periodic",
        "period": period,
        "points_abscissas": time_points,
        "points_ordinates": flow_points,
    }
    parameters["svc.blood_pressure"] = mean_pressure_pa(df, "svc_pressure_mmHg")
    parameters["ivc.blood_pressure"] = mean_pressure_pa(df, "ivc_pressure_mmHg")

    mean_flow = float(df["ascending_aorta_flow_ml_s"].mean() * M3_PER_ML)
    for name in blocks:
        if name.startswith("quasi_aao_arch_rl_") or name.startswith("quasi_dao_rl_"):
            variables_initialization[f"{name}.flux"] = mean_flow
            variables_magnitudes[f"{name}.flux"] = max(abs(mean_flow), 1.0e-5)

    for node in PRESSURE_NODES:
        if node in {"svc", "ivc"}:
            continue
        variables_initialization[f"{node}.blood_pressure"] = pressure_init[node]
        variables_magnitudes[f"{node}.blood_pressure"] = 1.0e4

    output_functions = {
        name: {
            "type": "watch_quantity",
            "quantity": name,
        }
        for name in WATCH_QUANTITIES
    }

    return {
        "type": "forward_simulation",
        "time": {
            "type": "time",
            "step_size": step_size,
            "min_step": step_size / 8.0,
            "start": 0.0,
            "duration": cycles * period,
        },
        "solver": {
            "type": "linear_solver",
        },
        "plots": {},
        "net": {
            "type": "net",
            "flux_dof_definitions": {
                "blood_flow": "blood_pressure",
            },
            "nodes": PRESSURE_NODES,
            "blocks": blocks,
            "boundaries_conditions": {
                "aao": [
                    {
                        "type": "condition",
                        "condition_type": "blood_flow",
                        "condition_id": "aao_inflow.blood_flow",
                    }
                ],
                "svc": [
                    {
                        "type": "condition",
                        "condition_type": "blood_pressure",
                        "condition_id": "svc.blood_pressure",
                    }
                ],
                "ivc": [
                    {
                        "type": "condition",
                        "condition_type": "blood_pressure",
                        "condition_id": "ivc.blood_pressure",
                    }
                ],
            },
        },
        "parameters": parameters,
        "variables_initialization": variables_initialization,
        "variables_magnitudes": variables_magnitudes,
        "output_functions": output_functions,
        "diagnostic_metadata": {
            "task": "008.8",
            "source_key": source,
            "source_id": SOURCES[source]["source_id"],
            "source_label": SOURCES[source]["label"],
            "source_file": str(SOURCES[source]["path"].relative_to(ROOT)),
            "cycle_period_s": period,
            "cycles": cycles,
            "purpose": "Open-loop quasi aortic chain diagnostic with prescribed AAo inflow and systemic terminal loads.",
        },
    }


def run(cmd: list[str]) -> None:
    print("$ " + " ".join(cmd), flush=True)
    subprocess.run(cmd, cwd=ROOT, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build and optionally run the quasi aortic open-loop submodel."
    )
    parser.add_argument("--source", choices=sorted(SOURCES), default="paper_closedloop")
    parser.add_argument("--cycles", type=int, default=12)
    parser.add_argument("--out-config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--series", default="AortaQuasiOpenLoop")
    parser.add_argument("--skip-run", action="store_true")
    args = parser.parse_args()

    config = build_config(args.source, args.cycles)
    write_json(args.out_config, config)
    print(f"Wrote {args.out_config}")

    if not args.skip_run:
        run([sys.executable, "scripts/run_one.py", str(args.out_config), "--series", args.series])


if __name__ == "__main__":
    main()
