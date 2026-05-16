#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.calibration.compare_waveforms import compare as compare_waveforms
from scripts.calibration.objective import comparison_rows, weighted_rms
from scripts.calibration.quasi import DEFAULT_QUASI_FACTORS, apply_quasi_calibration_factors
from scripts.calibration.quasi_non_regression import evaluate as evaluate_gate
from scripts.metrics import compute as compute_metrics
from scripts.modeling.build_quasi_configs import (
    FULL_CONFIG_DIR,
    QUASI_FRAGMENT,
    build_quasi_config,
    fontan_pathway_resistance,
    load_json,
    validate_quasi_config,
)

CALIBRATION_DIR = ROOT / "models/quasi_0d_1d/calibration"
RUN_DIR = ROOT / "runs/quasi_0086"
CONFIG_DIR = RUN_DIR / "configs"
REPORT_DIR = RUN_DIR / "reports"


@dataclass(frozen=True)
class Candidate:
    name: str
    family: str
    factors: dict[str, float] = field(default_factory=dict)
    topology: str = "current"
    description: str = ""


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def latest_main_csv(series: str) -> Path:
    paths = sorted((ROOT / "runs/simulations" / series).glob("*/main.csv"))
    if not paths:
        raise FileNotFoundError(f"No main.csv found for series {series}")
    return paths[-1]


def run(cmd: list[str]) -> None:
    print("$ " + " ".join(cmd), flush=True)
    subprocess.run(cmd, cwd=ROOT, check=True)


def base_factors(overrides: dict[str, float] | None = None) -> dict[str, float]:
    factors = dict(DEFAULT_QUASI_FACTORS)
    if overrides:
        factors.update(overrides)
    return factors


def raw_quasi_baseline() -> dict[str, Any]:
    fragment = load_json(QUASI_FRAGMENT)
    source = load_json(FULL_CONFIG_DIR / "fontan_0d_baseline.jsonc")
    baseline_lpa_pathway_resistance = fontan_pathway_resistance(
        source["parameters"],
        "lpa",
    )
    return build_quasi_config(
        source,
        fragment,
        baseline_lpa_pathway_resistance,
        apply_task008_calibration=False,
    )


def scale_chain_resistance(config: dict[str, Any], chain: str, scale: float) -> None:
    prefix = f"quasi_{chain}_"
    for name in list(config["parameters"]):
        if name.startswith(prefix) and name.endswith(".resistance"):
            config["parameters"][name] *= scale


def chain_total_resistance(config: dict[str, Any], chain: str) -> float:
    prefix = f"quasi_{chain}_"
    return sum(
        float(value)
        for name, value in config["parameters"].items()
        if name.startswith(prefix) and name.endswith(".resistance")
    )


def set_block_node(config: dict[str, Any], block_name: str, local_node: str, node: str) -> None:
    config["net"]["blocks"][block_name]["nodes"][local_node] = node


def ensure_pressure_node(config: dict[str, Any], node: str, source_node: str = "tcpc") -> None:
    if node not in config["net"]["nodes"]:
        config["net"]["nodes"].append(node)
    source_key = f"{source_node}.blood_pressure"
    key = f"{node}.blood_pressure"
    config["variables_initialization"][key] = config["variables_initialization"][source_key]
    config["variables_magnitudes"][key] = config["variables_magnitudes"][source_key]


def apply_distributed_aortic_branches(config: dict[str, Any], *, patient_geometry: bool = False) -> None:
    set_block_node(config, "arch_bca", "1", "quasi_aao_arch_p_01")
    set_block_node(config, "arch_lcca", "1", "quasi_aao_arch_p_02")
    set_block_node(config, "arch_lsa", "1", "quasi_aao_arch_p_03")
    if patient_geometry:
        config["parameters"]["arch_lsa.resistance"] *= 1.0e6
        config["parameters"]["upper_lsa_to_ca1.resistance"] *= 1.0e6


def add_resistor_block(config: dict[str, Any], name: str, node_1: str, node_2: str, resistance: float) -> None:
    config["net"]["blocks"][name] = {
        "type": "block_description",
        "model_type": "hydraulic_resistor_block",
        "flux_type": "blood_flow",
        "resistance": f"{name}.resistance",
        "nodes": {
            "1": node_1,
            "2": node_2,
        },
    }
    config["parameters"][f"{name}.resistance"] = resistance


def apply_four_port_tcpc(config: dict[str, Any]) -> None:
    for node in ["svc_port", "ivc_port", "rpa_port", "lpa_port"]:
        ensure_pressure_node(config, node, "tcpc")

    rewires = {
        "svc": ("quasi_svc_rl_03", "2", "quasi_svc_c_03", "svc_port"),
        "ivc": ("quasi_ivc_rl_05", "2", "quasi_ivc_c_05", "ivc_port"),
        "rpa": ("quasi_rpa_rl_01", "1", None, "rpa_port"),
        "lpa": ("quasi_lpa_rl_01", "1", None, "lpa_port"),
    }
    for chain, (rl_block, local_node, c_block, port) in rewires.items():
        total = chain_total_resistance(config, chain)
        scale_chain_resistance(config, chain, 0.90)
        set_block_node(config, rl_block, local_node, port)
        if c_block is not None:
            set_block_node(config, c_block, "1", port)
        if chain in {"svc", "ivc"}:
            add_resistor_block(config, f"{chain}_port_tcpc", port, "tcpc", 0.10 * total)
        else:
            add_resistor_block(config, f"{chain}_port_tcpc", "tcpc", port, 0.10 * total)


def candidate_config(candidate: Candidate) -> dict[str, Any]:
    config = apply_quasi_calibration_factors(
        raw_quasi_baseline(),
        base_factors(candidate.factors),
    )
    if candidate.topology in {"aortic_distributed", "combined_distributed_four_port"}:
        apply_distributed_aortic_branches(config, patient_geometry=False)
    elif candidate.topology == "aortic_patient_geometry":
        apply_distributed_aortic_branches(config, patient_geometry=True)

    if candidate.topology in {"four_port_tcpc", "combined_distributed_four_port"}:
        apply_four_port_tcpc(config)

    validate_quasi_config(config, load_json(QUASI_FRAGMENT))
    return config


def scale_label(value: float) -> str:
    return f"{value:g}".replace(".", "_")


def candidate_matrix() -> list[Candidate]:
    candidates = [
        Candidate(
            "current_frozen_heart",
            "current_topology_frozen_heart",
            {"heart_contractility_scale": 1.0},
            description="Current topology with full 0-D heart contractility.",
        ),
        Candidate("current_heart_099", "current_topology_small_heart", {"heart_contractility_scale": 0.99}),
        Candidate("current_heart_101", "current_topology_small_heart", {"heart_contractility_scale": 1.01}),
    ]
    for value in [0.0, 0.5, 2.0]:
        candidates.append(
            Candidate(
                f"aortic_L{scale_label(value)}",
                "aortic_rlc_ablation",
                {
                    "aao_arch_inductance_scale": value,
                    "dao_inductance_scale": value,
                    "heart_contractility_scale": 1.0,
                },
            )
        )
    for value in [0.5, 2.0]:
        candidates.extend(
            [
                Candidate(
                    f"aortic_C{scale_label(value)}",
                    "aortic_rlc_ablation",
                    {
                        "aao_arch_capacitance_scale": value,
                        "dao_capacitance_scale": value,
                        "heart_contractility_scale": 1.0,
                    },
                ),
                Candidate(
                    f"aortic_R{scale_label(value)}",
                    "aortic_rlc_ablation",
                    {
                        "aao_arch_resistance_scale": value,
                        "dao_resistance_scale": value,
                        "heart_contractility_scale": 1.0,
                    },
                ),
            ]
        )
    candidates.extend(
        [
            Candidate(
                "caval_L0",
                "caval_rlc_ablation",
                {"svc_inductance_scale": 0.0, "ivc_inductance_scale": 0.0, "heart_contractility_scale": 1.0},
            ),
            Candidate(
                "caval_C0_5",
                "caval_rlc_ablation",
                {"svc_capacitance_scale": 0.5, "ivc_capacitance_scale": 0.5, "heart_contractility_scale": 1.0},
            ),
            Candidate(
                "caval_R2",
                "caval_rlc_ablation",
                {"svc_resistance_scale": 2.0, "ivc_resistance_scale": 2.0, "heart_contractility_scale": 1.0},
            ),
            Candidate(
                "pulmonary_L0",
                "pulmonary_rlc_ablation",
                {"rpa_inductance_scale": 0.0, "lpa_inductance_scale": 0.0, "heart_contractility_scale": 1.0},
            ),
            Candidate(
                "pulmonary_C0_5",
                "pulmonary_rlc_ablation",
                {"rpa_capacitance_scale": 0.5, "lpa_capacitance_scale": 0.5, "heart_contractility_scale": 1.0},
            ),
            Candidate(
                "pulmonary_R2",
                "pulmonary_rlc_ablation",
                {"rpa_resistance_scale": 2.0, "lpa_resistance_scale": 2.0, "heart_contractility_scale": 1.0},
            ),
            Candidate(
                "pulmonary_pf35",
                "pulmonary_split_ablation",
                {"right_pulmonary_proximal_fraction": 0.35, "left_pulmonary_proximal_fraction": 0.35, "heart_contractility_scale": 1.0},
            ),
            Candidate(
                "pulmonary_pf65",
                "pulmonary_split_ablation",
                {"right_pulmonary_proximal_fraction": 0.65, "left_pulmonary_proximal_fraction": 0.65, "heart_contractility_scale": 1.0},
            ),
            Candidate(
                "pulmonary_total130",
                "pulmonary_split_ablation",
                {"right_pulmonary_total_resistance_scale": 1.30, "left_pulmonary_total_resistance_scale": 1.30, "heart_contractility_scale": 1.0},
            ),
            Candidate(
                "aorta_distributed_branches",
                "topology_ablation",
                {"heart_contractility_scale": 1.0},
                topology="aortic_distributed",
            ),
            Candidate(
                "aorta_patient_geometry_branches",
                "topology_ablation",
                {"heart_contractility_scale": 1.0},
                topology="aortic_patient_geometry",
            ),
            Candidate(
                "four_port_tcpc",
                "topology_ablation",
                {"heart_contractility_scale": 1.0},
                topology="four_port_tcpc",
            ),
            Candidate(
                "combined_distributed_four_port",
                "combined_topology_ablation",
                {"heart_contractility_scale": 1.0},
                topology="combined_distributed_four_port",
            ),
        ]
    )
    return candidates


def score_from_rows(metrics: dict[str, Any], source_id: str = "direct_measurement") -> dict[str, Any]:
    rows = comparison_rows(metrics, source_id)
    return {
        "weighted_rms_relative_error": weighted_rms(rows),
        "targets": rows,
    }


def evaluate_candidate(candidate: Candidate, *, force: bool = False) -> dict[str, Any]:
    config_path = CONFIG_DIR / f"{candidate.name}.jsonc"
    metrics_path = REPORT_DIR / f"{candidate.name}_metrics.json"
    direct_path = REPORT_DIR / f"{candidate.name}_direct.json"
    paper_path = REPORT_DIR / f"{candidate.name}_paper.json"
    waveform_path = REPORT_DIR / f"{candidate.name}_waveforms.json"
    gate_path = REPORT_DIR / f"{candidate.name}_gate.json"
    series = f"Quasi0086_{candidate.name}"

    if force or not gate_path.exists():
        config = candidate_config(candidate)
        write_json(config_path, config)
        run([sys.executable, "scripts/run_one.py", str(config_path), "--series", series])
        csv_path = latest_main_csv(series)
        metrics = compute_metrics(csv_path, config_path)
        write_json(metrics_path, metrics)
        direct = score_from_rows(metrics, "direct_measurement")
        paper = score_from_rows(metrics, "paper_model")
        write_json(direct_path, direct)
        write_json(paper_path, paper)
        waveforms = compare_waveforms(
            csv_path,
            config_path,
            "direct_measurement",
            latest_main_csv("Baseline"),
            ROOT / "models/full_0d/configs/fontan_0d_baseline.jsonc",
        )
        write_json(waveform_path, waveforms)
        gate = evaluate_gate(
            full_direct=load_json(ROOT / "models/full_0d/calibration/baseline_objective.json"),
            quasi_direct=direct,
            full_paper=load_json(ROOT / "models/full_0d/calibration/baseline_vs_paper.json"),
            quasi_paper=paper,
            quasi_metrics=metrics,
            waveforms=waveforms,
        )
        gate["task"] = "008.6"
        write_json(gate_path, gate)

    metrics = load_json(metrics_path)
    direct = load_json(direct_path)
    paper = load_json(paper_path)
    gate = load_json(gate_path)
    waveform_failures = [
        row["canonical_name"]
        for row in gate["scores"]["waveform_no_strong_regression_score"]["waveforms"]
        if not row["pass"]
    ]
    hard_failures = [
        row["target_name"]
        for row in gate["gates"]["hard_target_non_regression"]
        if not row["pass"]
    ]
    return {
        "candidate": candidate.name,
        "family": candidate.family,
        "topology": candidate.topology,
        "status": "ok",
        "accepted_as_superior": gate["accepted_as_superior"],
        "direct_score": direct["weighted_rms_relative_error"],
        "hard_score": gate["scores"]["hard_clinical_summary_score"]["quasi_0d_1d"],
        "paper_score": paper["weighted_rms_relative_error"],
        "waveform_regression_rms": gate["scores"]["waveform_no_strong_regression_score"]["regression_rms"],
        "failed_hard_gates": ";".join(hard_failures),
        "failed_waveform_gates": ";".join(waveform_failures),
        "edv_ml": metrics.get("EDV_ml", ""),
        "esv_ml": metrics.get("ESV_ml", ""),
        "sv_ml": metrics.get("SV_from_volume_ml", ""),
        "co_l_min": metrics.get("CO_from_valve_arterial.flux_L_min", ""),
        "rpa_pressure_mmHg": metrics.get("mean_rpa_pressure_mmHg", ""),
        "lpa_pressure_mmHg": metrics.get("mean_lpa_pressure_mmHg", ""),
        "svc_flow_ml_s": metrics.get("mean_svc_outlet_flow_ml_s", ""),
        "rpa_flow_fraction": metrics.get("rpa_flow_fraction", ""),
    }


def reference_row() -> dict[str, Any]:
    gate = load_json(CALIBRATION_DIR / "non_regression_gate.json")
    metrics = load_json(ROOT / "models/quasi_0d_1d/reference_outputs/baseline_metrics.json")
    waveform_failures = [
        row["canonical_name"]
        for row in gate["scores"]["waveform_no_strong_regression_score"]["waveforms"]
        if not row["pass"]
    ]
    hard_failures = [
        row["target_name"]
        for row in gate["gates"]["hard_target_non_regression"]
        if not row["pass"]
    ]
    return {
        "candidate": "task0085_reference",
        "family": "canonical_reference",
        "topology": "current",
        "status": "ok",
        "accepted_as_superior": gate["accepted_as_superior"],
        "direct_score": gate["scores"]["aggregate_direct_score"]["quasi_0d_1d"],
        "hard_score": gate["scores"]["hard_clinical_summary_score"]["quasi_0d_1d"],
        "paper_score": gate["scores"]["paper_model_comparison_score"]["quasi_0d_1d"],
        "waveform_regression_rms": gate["scores"]["waveform_no_strong_regression_score"]["regression_rms"],
        "failed_hard_gates": ";".join(hard_failures),
        "failed_waveform_gates": ";".join(waveform_failures),
        "edv_ml": metrics.get("EDV_ml", ""),
        "esv_ml": metrics.get("ESV_ml", ""),
        "sv_ml": metrics.get("SV_from_volume_ml", ""),
        "co_l_min": metrics.get("CO_from_valve_arterial.flux_L_min", ""),
        "rpa_pressure_mmHg": metrics.get("mean_rpa_pressure_mmHg", ""),
        "lpa_pressure_mmHg": metrics.get("mean_lpa_pressure_mmHg", ""),
        "svc_flow_ml_s": metrics.get("mean_svc_outlet_flow_ml_s", ""),
        "rpa_flow_fraction": metrics.get("rpa_flow_fraction", ""),
    }


def write_summary(rows: list[dict[str, Any]], out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the Task 008.6 quasi design/correction ablation grid."
    )
    parser.add_argument("--force", action="store_true", help="Rerun candidates even if cached gate reports exist.")
    parser.add_argument("--limit", type=int, help="Run only the first N candidates after the reference row.")
    args = parser.parse_args()

    rows = [reference_row()]
    candidates = candidate_matrix()
    if args.limit is not None:
        candidates = candidates[: args.limit]
    for candidate in candidates:
        try:
            rows.append(evaluate_candidate(candidate, force=args.force))
        except Exception as exc:
            rows.append(
                {
                    **{key: "" for key in rows[0]},
                    "candidate": candidate.name,
                    "family": candidate.family,
                    "topology": candidate.topology,
                    "status": f"failed: {exc}",
                    "accepted_as_superior": False,
                }
            )
            print(f"Candidate {candidate.name} failed: {exc}", flush=True)
    write_summary(rows, CALIBRATION_DIR / "quasi_ablation_summary.csv")
    print(json.dumps(rows, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
