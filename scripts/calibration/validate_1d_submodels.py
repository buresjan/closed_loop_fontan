#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import gzip
import json
import math
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
CONFIGS = [
    ROOT / "models/coupled_0d_1d/configs/submodel_aorta_1d_openloop.jsonc",
    ROOT / "models/coupled_0d_1d/configs/submodel_tcpc_1d_openloop.jsonc",
    ROOT / "models/coupled_0d_1d/configs/submodel_aorta_tcpc_1d_openloop.jsonc",
]
REPORT_OUT = ROOT / "models/coupled_0d_1d/reference_outputs/openloop_1d_validation.json"


def repo_path(value: str) -> Path:
    return ROOT / value


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT))


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def numeric_column(rows: list[dict[str, str]], column: str) -> list[float]:
    if not rows:
        raise ValueError(f"No rows available for column {column}")
    if column not in rows[0]:
        raise KeyError(f"Column {column} not found")
    return [float(row[column]) for row in rows]


def mean(values: list[float]) -> float:
    return sum(values) / len(values)


def rmse(reference: list[float], target: list[float]) -> float:
    if len(reference) != len(target):
        raise ValueError("reference and target columns must have the same length")
    return math.sqrt(mean([(r - t) * (r - t) for r, t in zip(reference, target)]))


def max_abs(values: list[float]) -> float:
    return max(abs(value) for value in values)


def waveform_metrics(
    reference_rows: list[dict[str, str]],
    clinical_rows: list[dict[str, str]],
    signal: dict[str, Any],
) -> dict[str, Any]:
    reference = numeric_column(reference_rows, signal["reference_column"])
    clinical = numeric_column(clinical_rows, signal["clinical_column"])
    if len(reference) != len(clinical):
        raise ValueError(
            f"{signal['name']} row count mismatch: {len(reference)} vs {len(clinical)}"
        )
    errors = [r - c for r, c in zip(reference, clinical)]
    mean_abs_error = abs(mean(reference) - mean(clinical))
    rmse_error = rmse(reference, clinical)
    clinical_amplitude = max(clinical) - min(clinical)
    normalized_rmse = (
        rmse_error / clinical_amplitude
        if clinical_amplitude > 0.0
        else math.inf
    )
    passed = (
        mean_abs_error <= float(signal["mean_abs_tolerance"])
        and rmse_error <= float(signal["rmse_tolerance"])
    )
    return {
        "name": signal["name"],
        "quantity": signal["quantity"],
        "unit": signal["unit"],
        "reference_column": signal["reference_column"],
        "clinical_column": signal["clinical_column"],
        "reference_mean": mean(reference),
        "clinical_mean": mean(clinical),
        "mean_abs_error": mean_abs_error,
        "rmse": rmse_error,
        "clinical_amplitude": clinical_amplitude,
        "normalized_rmse": normalized_rmse,
        "max_abs_error": max_abs(errors),
        "mean_abs_tolerance": signal["mean_abs_tolerance"],
        "rmse_tolerance": signal["rmse_tolerance"],
        "passed": passed,
    }


def flow_fraction_metrics(
    reference_rows: list[dict[str, str]],
    clinical_rows: list[dict[str, str]],
    reference_rpa: str,
    reference_lpa: str,
) -> dict[str, Any]:
    ref_rpa = numeric_column(reference_rows, reference_rpa)
    ref_lpa = numeric_column(reference_rows, reference_lpa)
    clinical_rpa = numeric_column(clinical_rows, "rpa_flow_ml_s")
    clinical_lpa = numeric_column(clinical_rows, "lpa_flow_ml_s")
    ref_fraction = mean(ref_rpa) / (mean(ref_rpa) + mean(ref_lpa))
    clinical_fraction = mean(clinical_rpa) / (mean(clinical_rpa) + mean(clinical_lpa))
    error = abs(ref_fraction - clinical_fraction)
    return {
        "name": "rpa_flow_fraction",
        "unit": "1",
        "reference_value": ref_fraction,
        "clinical_value": clinical_fraction,
        "abs_error": error,
        "tolerance": 0.08,
        "passed": error <= 0.08,
    }


def validate_input_paths(config: dict[str, Any]) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    for item in config.get("inputs", []):
        for key in ["path", "parameter_path", "waveform_path"]:
            if key not in item:
                continue
            path = repo_path(item[key])
            checks.append(
                {
                    "name": item["name"],
                    "path": item[key],
                    "exists": path.exists(),
                    "passed": path.exists(),
                }
            )
    return checks


def validate_geometry(config: dict[str, Any]) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    for segment in config["topology"]["segments"]:
        domain_path = repo_path(segment["nektar_domain_file"])
        domain_exists = domain_path.exists()
        length = float(segment["length_m"])
        radius_in = float(segment["radius_in_m"])
        radius_out = float(segment["radius_out_m"])
        distances = [float(value) for value in segment["nektar_distance_m"]]
        domain_length = distances[-1] - distances[0]
        length_error = abs(length - domain_length)
        positive = (
            length > 0.0
            and radius_in > 0.0
            and radius_out > 0.0
            and float(segment["reference_area_m2"]) > 0.0
            and float(segment["wall_stiffness_pa_m-1"]) > 0.0
        )
        checks.append(
            {
                "segment_id": segment["segment_id"],
                "source_segment": segment["source_segment"],
                "domain_file": segment["nektar_domain_file"],
                "domain_exists": domain_exists,
                "length_m": length,
                "domain_length_m": domain_length,
                "length_abs_error_m": length_error,
                "positive_geometry": positive,
                "passed": domain_exists and positive and length_error <= 1e-12,
            }
        )
    return checks


def validate_domain_samples(config: dict[str, Any]) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    required = ["time_s", "position_index", "distance_m", "pressure_pa", "flow_m3_s", "area_m2"]
    for segment in config["topology"]["segments"]:
        path = repo_path(segment["nektar_domain_file"])
        rows = read_csv_rows(path)
        columns = set(rows[0]) if rows else set()
        areas = numeric_column(rows, "area_m2")
        flows = numeric_column(rows, "flow_m3_s")
        checks.append(
            {
                "segment_id": segment["segment_id"],
                "row_count": len(rows),
                "required_columns_present": all(column in columns for column in required),
                "min_area_m2": min(areas),
                "max_abs_flow_m3_s": max_abs(flows),
                "passed": (
                    len(rows) > 0
                    and all(column in columns for column in required)
                    and min(areas) > 0.0
                ),
            }
        )
    return checks


def validate_waveforms(config: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    reference_rows = read_csv_rows(repo_path(config["validation"]["reference_table"]))
    clinical_rows = read_csv_rows(repo_path(config["validation"]["clinical_table"]))
    signals = [
        waveform_metrics(reference_rows, clinical_rows, signal)
        for signal in config["validation"]["signals"]
    ]
    fractions: list[dict[str, Any]] = []
    kind = config["validation"]["kind"]
    if kind == "aorta":
        pass
    elif kind == "tcpc":
        fractions.append(
            flow_fraction_metrics(reference_rows, clinical_rows, "qrpa_ml_per_s", "qlpa_ml_per_s")
        )
    elif kind == "combined":
        fractions.append(
            flow_fraction_metrics(reference_rows, clinical_rows, "rpa_flow_ml_s", "lpa_flow_ml_s")
        )
    else:
        raise ValueError(f"Unsupported validation kind {kind}")
    return signals, fractions


def mass_balance(config: dict[str, Any]) -> dict[str, Any]:
    kind = config["validation"]["kind"]
    if kind == "tcpc":
        clinical = read_csv_rows(repo_path(config["validation"]["clinical_table"]))
        reference = read_csv_rows(repo_path(config["validation"]["reference_table"]))
        inflow = mean(numeric_column(clinical, "ivc_flow_ml_s")) + mean(
            numeric_column(clinical, "svc_flow_ml_s")
        )
        outflow = mean(numeric_column(reference, "qrpa_ml_per_s")) + mean(
            numeric_column(reference, "qlpa_ml_per_s")
        )
        tolerance = 5.0
    elif kind == "combined":
        reference = read_csv_rows(repo_path(config["validation"]["reference_table"]))
        inflow = mean(numeric_column(reference, "ivc_flow_ml_s")) + mean(
            numeric_column(reference, "svc_flow_ml_s")
        )
        outflow = mean(numeric_column(reference, "rpa_flow_ml_s")) + mean(
            numeric_column(reference, "lpa_flow_ml_s")
        )
        tolerance = 5.0
    elif kind == "aorta":
        clinical = read_csv_rows(repo_path(config["validation"]["clinical_table"]))
        reference = read_csv_rows(repo_path(config["validation"]["reference_table"]))
        inflow = mean(numeric_column(clinical, "ascending_aorta_flow_ml_s"))
        outflow = mean(numeric_column(reference, "qdao_ml_per_s"))
        tolerance = 30.0
    else:
        raise ValueError(f"Unsupported validation kind {kind}")
    error = abs(inflow - outflow)
    return {
        "kind": kind,
        "inflow_mean_ml_s": inflow,
        "outflow_mean_ml_s": outflow,
        "abs_error_ml_s": error,
        "tolerance_ml_s": tolerance,
        "passed": error <= tolerance,
        "notes": (
            "Aorta tolerance is broad because branch outlets carry the remaining "
            "inflow. TCPC/combined checks compare caval inflow against pulmonary outflow."
        ),
    }


def boundary_signs(config: dict[str, Any]) -> dict[str, Any]:
    reference_rows = read_csv_rows(repo_path(config["validation"]["reference_table"]))
    kind = config["validation"]["kind"]
    values: dict[str, float] = {}
    if kind == "aorta":
        values["descending_aorta_flow_mean_ml_s"] = mean(
            numeric_column(reference_rows, "qdao_ml_per_s")
        )
        passed = values["descending_aorta_flow_mean_ml_s"] > 0.0
    elif kind == "tcpc":
        values["rpa_flow_mean_ml_s"] = mean(numeric_column(reference_rows, "qrpa_ml_per_s"))
        values["lpa_flow_mean_ml_s"] = mean(numeric_column(reference_rows, "qlpa_ml_per_s"))
        passed = values["rpa_flow_mean_ml_s"] > 0.0 and values["lpa_flow_mean_ml_s"] > 0.0
    elif kind == "combined":
        values["descending_aorta_flow_mean_ml_s"] = mean(
            numeric_column(reference_rows, "descending_aorta_flow_ml_s")
        )
        values["rpa_flow_mean_ml_s"] = mean(numeric_column(reference_rows, "rpa_flow_ml_s"))
        values["lpa_flow_mean_ml_s"] = mean(numeric_column(reference_rows, "lpa_flow_ml_s"))
        passed = all(value > 0.0 for value in values.values())
    else:
        raise ValueError(f"Unsupported validation kind {kind}")
    return {"kind": kind, "values": values, "passed": passed}


def validate_config(path: Path) -> dict[str, Any]:
    config = json.loads(path.read_text(encoding="utf-8"))
    input_checks = validate_input_paths(config)
    geometry_checks = validate_geometry(config)
    domain_checks = validate_domain_samples(config)
    waveform_checks, fraction_checks = validate_waveforms(config)
    mass_check = mass_balance(config)
    sign_check = boundary_signs(config)
    all_checks = [
        *input_checks,
        *geometry_checks,
        *domain_checks,
        *waveform_checks,
        *fraction_checks,
        mass_check,
        sign_check,
    ]
    return {
        "config": rel(path),
        "submodel_id": config["submodel_id"],
        "status": config["status"],
        "segment_count": len(config["topology"]["segments"]),
        "input_checks": input_checks,
        "geometry_checks": geometry_checks,
        "domain_checks": domain_checks,
        "waveform_checks": waveform_checks,
        "flow_fraction_checks": fraction_checks,
        "mass_balance": mass_check,
        "boundary_signs": sign_check,
        "passed": all(bool(check["passed"]) for check in all_checks),
    }


def build_report(configs: list[Path]) -> dict[str, Any]:
    results = [validate_config(path) for path in configs]
    return {
        "generated_by": "scripts/calibration/validate_1d_submodels.py",
        "model_family": "coupled_0d_1d",
        "scope": (
            "Open-loop reference validation for the aorta, TCPC, and combined "
            "aorta-TCPC 1-D submodel specifications."
        ),
        "submodels": results,
        "passed": all(result["passed"] for result in results),
        "limitations": [
            "This validation screens reference open-loop Nektar/clinical data and geometry specs.",
            "It does not promote a closed-loop coupled Fontan model.",
            "It does not yet calibrate generated multi-segment local PhysioBlocks networks.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate coupled 1-D open-loop specs.")
    parser.add_argument("configs", nargs="*", type=Path, default=CONFIGS)
    parser.add_argument("--out", type=Path, default=REPORT_OUT)
    parser.add_argument("--check", action="store_true", help="verify existing report is current")
    args = parser.parse_args()

    configs = [path if path.is_absolute() else ROOT / path for path in args.configs]
    report = build_report(configs)
    text = json.dumps(report, indent=2) + "\n"
    out = args.out if args.out.is_absolute() else ROOT / args.out

    if args.check:
        if not out.exists() or out.read_text(encoding="utf-8") != text:
            raise SystemExit("1-D open-loop validation report is stale")
    else:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")

    print(
        json.dumps(
            {
                "report": rel(out),
                "passed": report["passed"],
                "submodels": {
                    result["submodel_id"]: result["passed"]
                    for result in report["submodels"]
                },
            },
            indent=2,
        )
    )
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
