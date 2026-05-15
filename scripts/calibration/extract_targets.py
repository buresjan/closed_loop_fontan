#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[2]
PROCESSED_ROOT = ROOT / "data/processed/aramburu_2024"
TARGET_DIR = PROCESSED_ROOT / "targets"

DIRECT_MEASUREMENT_FILE = Path("comparison/measurements_last_cycle_clinical.csv")
DIRECT_MEASUREMENT_CLINICAL_FILE = Path("measurements_clinical.csv")
DIRECT_MEASUREMENT_SI_FILE = Path("measurements.csv")
PAPER_MODEL_FILE = Path("paper_results/model.csv")
NEKTAR_CLOSED_LOOP_FILE = Path(
    "comparison/04_aorta_tcpc_closedloop_1d_last_cycle_clinical.csv"
)

PRESSURE_SUFFIX = "_pressure_mmHg"
FLOW_SUFFIX = "_flow_ml_s"
VOLUME_SUFFIX = "_volume_ml"

SUMMARY_COLUMNS = [
    "target_id",
    "source_id",
    "source_type",
    "canonical_name",
    "quantity",
    "statistic",
    "value",
    "unit",
    "source_file",
    "source_columns",
    "cycle_length_s",
    "notes",
]

WAVEFORM_COLUMNS = [
    "source_id",
    "source_type",
    "signal_id",
    "canonical_name",
    "quantity",
    "unit",
    "phase",
    "time_s",
    "value",
]

WAVEFORM_METADATA_COLUMNS = [
    "signal_id",
    "source_id",
    "source_type",
    "canonical_name",
    "quantity",
    "unit",
    "source_file",
    "source_column",
    "sample_count",
    "cycle_length_s",
    "normalization_scale",
    "normalization_unit",
    "phase_alignment",
    "notes",
]

PAPER_COLUMN_MAP: dict[str, tuple[str, str, str, str]] = {
    "paao_mmhg": (
        "ascending_aorta_pressure",
        "pressure",
        "mmHg",
        "paper model ascending-aorta pressure",
    ),
    "qaao_ml_per_s": (
        "ascending_aorta_flow",
        "flow",
        "ml/s",
        "paper model ascending-aorta flow",
    ),
    "parch_mmhg": (
        "aortic_arch_pressure",
        "pressure",
        "mmHg",
        "paper model aortic-arch pressure",
    ),
    "pdao_mmhg": (
        "descending_aorta_pressure",
        "pressure",
        "mmHg",
        "paper model descending-aorta pressure",
    ),
    "qdao_ml_per_s": (
        "descending_aorta_flow",
        "flow",
        "ml/s",
        "paper model descending-aorta flow",
    ),
    "pivc_mmhg": ("ivc_pressure", "pressure", "mmHg", "paper model IVC pressure"),
    "qivc_ml_per_s": ("ivc_flow", "flow", "ml/s", "paper model IVC flow"),
    "psvc_mmhg": ("svc_pressure", "pressure", "mmHg", "paper model SVC pressure"),
    "qsvc_ml_per_s": ("svc_flow", "flow", "ml/s", "paper model SVC flow"),
    "prpa_mmhg": ("rpa_pressure", "pressure", "mmHg", "paper model RPA pressure"),
    "qrpa_ml_per_s": ("rpa_flow", "flow", "ml/s", "paper model RPA flow"),
    "plpa_mmhg": ("lpa_pressure", "pressure", "mmHg", "paper model LPA pressure"),
    "qlpa_ml_per_s": ("lpa_flow", "flow", "ml/s", "paper model LPA flow"),
    "pv_mmhg": (
        "ventricle_pressure",
        "pressure",
        "mmHg",
        "paper model ventricular pressure",
    ),
    "vv_ml": ("ventricle_volume", "volume", "ml", "paper model ventricular volume"),
    "pa_mmhg": ("atrium_pressure", "pressure", "mmHg", "paper model atrial pressure"),
    "va_ml": ("atrium_volume", "volume", "ml", "paper model atrial volume"),
    "qpa_ml_per_s": (
        "pulmonary_inflow",
        "flow",
        "ml/s",
        "paper model pulmonary inflow",
    ),
    "qmv_mmhg": (
        "mitral_valve_flow",
        "flow",
        "ml/s",
        "paper model mitral-valve flow; source header uses qmv_mmhg",
    ),
}


@dataclass(frozen=True)
class SourceSpec:
    source_id: str
    source_type: str
    relative_path: Path
    description: str
    column_map: dict[str, tuple[str, str, str, str]] | None = None
    time_column: str = "time_s"


@dataclass(frozen=True)
class SignalInfo:
    source_column: str
    canonical_name: str
    quantity: str
    unit: str
    notes: str


SOURCE_SPECS = [
    SourceSpec(
        "direct_measurement",
        "direct_measurement",
        DIRECT_MEASUREMENT_FILE,
        "Clinical measurement waveforms from Aramburu et al. measurements.mat, "
        "already sliced to the comparison cycle.",
    ),
    SourceSpec(
        "paper_model",
        "paper_output",
        PAPER_MODEL_FILE,
        "Closed-loop model output exported from the paper results workbook.",
        PAPER_COLUMN_MAP,
        "t_s",
    ),
    SourceSpec(
        "nektar_closed_loop_1d",
        "nektar_comparison_output",
        NEKTAR_CLOSED_LOOP_FILE,
        "Closed-loop aorta/TCPC 1-D comparison output converted from Nektar data.",
    ),
]


def read_csv(root: Path, relative_path: Path) -> pd.DataFrame:
    return pd.read_csv(root / relative_path)


def read_source(root: Path, spec: SourceSpec) -> pd.DataFrame:
    df = read_csv(root, spec.relative_path)
    if spec.time_column != "time_s":
        if spec.time_column not in df:
            raise ValueError(f"{spec.relative_path} is missing {spec.time_column}")
        df = df.rename(columns={spec.time_column: "time_s"})
    return df


def median_dt(time_s: pd.Series) -> float:
    diffs = np.diff(time_s.to_numpy(dtype=float))
    if len(diffs) == 0:
        raise ValueError("At least two time samples are required")
    if np.any(diffs <= 0.0):
        raise ValueError("Time samples must be strictly increasing")
    return float(np.median(diffs))


def cycle_length_s(time_s: pd.Series) -> float:
    """Return one-cycle length for a non-duplicated periodic sample grid."""

    return float(len(time_s) * median_dt(time_s))


def phase_values(time_s: pd.Series, period_s: float) -> np.ndarray:
    t = time_s.to_numpy(dtype=float)
    return (t - float(t[0])) / period_s


def periodic_beat_integral(time_s: pd.Series, values: pd.Series) -> float:
    """Integrate one periodic beat, including the wraparound segment."""

    period_s = cycle_length_s(time_s)
    t = time_s.to_numpy(dtype=float)
    y = values.to_numpy(dtype=float)
    shifted = t - float(t[0])
    t_periodic = np.concatenate([shifted, [period_s]])
    y_periodic = np.concatenate([y, [y[0]]])
    trapz = getattr(np, "trapezoid", None)
    if trapz is None:
        trapz = np.trapz
    return float(trapz(y_periodic, t_periodic))


def normalization_scale(values: pd.Series) -> float:
    y = values.to_numpy(dtype=float)
    span = float(np.nanmax(y) - np.nanmin(y))
    if span > 0.0:
        return span
    magnitude = float(np.nanmax(np.abs(y)))
    return magnitude if magnitude > 0.0 else 1.0


def clinical_signal_info(column: str) -> SignalInfo | None:
    if column == "time_s":
        return None
    if column.endswith(PRESSURE_SUFFIX):
        return SignalInfo(
            column,
            column.removesuffix("_mmHg"),
            "pressure",
            "mmHg",
            "clinical pressure waveform",
        )
    if column.endswith(FLOW_SUFFIX):
        return SignalInfo(
            column,
            column.removesuffix("_ml_s"),
            "flow",
            "ml/s",
            "clinical flow waveform",
        )
    if column.endswith(VOLUME_SUFFIX):
        return SignalInfo(
            column,
            column.removesuffix("_ml"),
            "volume",
            "ml",
            "clinical volume waveform",
        )
    return None


def source_signal_infos(df: pd.DataFrame, spec: SourceSpec) -> list[SignalInfo]:
    infos: list[SignalInfo] = []
    for column in df.columns:
        if spec.column_map is not None and column in spec.column_map:
            canonical, quantity, unit, notes = spec.column_map[column]
            infos.append(SignalInfo(column, canonical, quantity, unit, notes))
            continue
        info = clinical_signal_info(column)
        if info is not None:
            infos.append(info)
    return infos


def validate_measurement_unit_conversions(
    clinical: pd.DataFrame, si: pd.DataFrame
) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    for column in clinical.columns:
        if column == "time_s":
            si_column = "time_s"
            expected = clinical[column].to_numpy(dtype=float)
            unit_conversion = "identity"
        elif column.endswith("_mmHg"):
            si_column = column.removesuffix("_mmHg") + "_pa"
            expected = clinical[column].to_numpy(dtype=float) * 133.33
            unit_conversion = "Pa = mmHg * 133.33"
        elif column.endswith("_ml_s"):
            si_column = column.removesuffix("_ml_s") + "_m3_s"
            expected = clinical[column].to_numpy(dtype=float) * 1e-6
            unit_conversion = "m3/s = ml/s * 1e-6"
        elif column.endswith("_ml"):
            si_column = column.removesuffix("_ml") + "_m3"
            expected = clinical[column].to_numpy(dtype=float) * 1e-6
            unit_conversion = "m3 = ml * 1e-6"
        else:
            continue

        if si_column not in si:
            raise ValueError(f"Missing SI column {si_column} for clinical column {column}")
        observed = si[si_column].to_numpy(dtype=float)
        max_abs_error = float(np.max(np.abs(expected - observed)))
        checks.append(
            {
                "clinical_column": column,
                "si_column": si_column,
                "conversion": unit_conversion,
                "max_abs_error": max_abs_error,
            }
        )
        if not np.allclose(expected, observed, rtol=1e-12, atol=1e-12):
            raise ValueError(f"Clinical/SI conversion mismatch for {column}")
    return checks


def ensure_measurement_cycle_is_consistent(root: Path) -> None:
    clinical = read_csv(root, DIRECT_MEASUREMENT_CLINICAL_FILE)
    comparison = read_csv(root, DIRECT_MEASUREMENT_FILE)
    if list(clinical.columns) != list(comparison.columns):
        raise ValueError("Measurement clinical and comparison columns differ")
    if not np.allclose(
        clinical.to_numpy(dtype=float),
        comparison.to_numpy(dtype=float),
        rtol=1e-12,
        atol=1e-12,
    ):
        raise ValueError("Measurement clinical and comparison cycle values differ")


def summary_row(
    spec: SourceSpec,
    canonical_name: str,
    quantity: str,
    statistic: str,
    value: float,
    unit: str,
    source_columns: list[str],
    period_s: float,
    notes: str,
) -> dict[str, Any]:
    return {
        "target_id": f"{spec.source_id}.{canonical_name}.{statistic}",
        "source_id": spec.source_id,
        "source_type": spec.source_type,
        "canonical_name": canonical_name,
        "quantity": quantity,
        "statistic": statistic,
        "value": float(value),
        "unit": unit,
        "source_file": str(spec.relative_path),
        "source_columns": json.dumps(source_columns),
        "cycle_length_s": period_s,
        "notes": notes,
    }


def build_summary_rows(
    df: pd.DataFrame, spec: SourceSpec, infos: list[SignalInfo]
) -> list[dict[str, Any]]:
    period_s = cycle_length_s(df["time_s"])
    rows = [
        summary_row(
            spec,
            "cycle_length",
            "time",
            "period",
            period_s,
            "s",
            ["time_s"],
            period_s,
            "Derived as sample_count * median_dt because the terminal phase sample is not duplicated.",
        ),
        summary_row(
            spec,
            "heart_rate",
            "frequency",
            "derived_from_cycle_length",
            60.0 / period_s,
            "beats/min",
            ["time_s"],
            period_s,
            "Derived from one-cycle duration.",
        ),
    ]

    by_name = {info.canonical_name: info for info in infos}
    ventricle = by_name.get("ventricle_volume")
    if ventricle is not None:
        volume = df[ventricle.source_column]
        edv = float(volume.max())
        esv = float(volume.min())
        sv = edv - esv
        rows.extend(
            [
                summary_row(
                    spec,
                    "edv",
                    "volume",
                    "max",
                    edv,
                    ventricle.unit,
                    [ventricle.source_column],
                    period_s,
                    "End-diastolic volume proxy from maximum ventricular volume over the cycle.",
                ),
                summary_row(
                    spec,
                    "esv",
                    "volume",
                    "min",
                    esv,
                    ventricle.unit,
                    [ventricle.source_column],
                    period_s,
                    "End-systolic volume proxy from minimum ventricular volume over the cycle.",
                ),
                summary_row(
                    spec,
                    "stroke_volume",
                    "volume",
                    "edv_minus_esv",
                    sv,
                    ventricle.unit,
                    [ventricle.source_column],
                    period_s,
                    "Stroke volume derived from EDV minus ESV.",
                ),
                summary_row(
                    spec,
                    "cardiac_output",
                    "flow",
                    "from_stroke_volume",
                    sv * 60.0 / period_s / 1000.0,
                    "L/min",
                    [ventricle.source_column, "time_s"],
                    period_s,
                    "Cardiac output derived from stroke volume and cycle length.",
                ),
            ]
        )

    for info in infos:
        values = df[info.source_column]
        if info.quantity == "pressure":
            rows.append(
                summary_row(
                    spec,
                    info.canonical_name,
                    info.quantity,
                    "mean",
                    float(values.mean()),
                    info.unit,
                    [info.source_column],
                    period_s,
                    "Cycle mean pressure.",
                )
            )
        elif info.quantity == "flow":
            integral = periodic_beat_integral(df["time_s"], values)
            rows.append(
                summary_row(
                    spec,
                    info.canonical_name,
                    info.quantity,
                    "beat_integral",
                    integral,
                    "ml/beat",
                    [info.source_column, "time_s"],
                    period_s,
                    "Periodic trapezoid integral over one beat.",
                )
            )

    rpa = by_name.get("rpa_flow")
    lpa = by_name.get("lpa_flow")
    if rpa is not None and lpa is not None:
        rpa_integral = periodic_beat_integral(df["time_s"], df[rpa.source_column])
        lpa_integral = periodic_beat_integral(df["time_s"], df[lpa.source_column])
        denom = rpa_integral + lpa_integral
        if abs(denom) > 1e-12:
            rows.extend(
                [
                    summary_row(
                        spec,
                        "rpa_flow_fraction",
                        "dimensionless",
                        "rpa_over_rpa_plus_lpa",
                        rpa_integral / denom,
                        "1",
                        [rpa.source_column, lpa.source_column, "time_s"],
                        period_s,
                        "Pulmonary flow split from beat-integrated RPA and LPA flows.",
                    ),
                    summary_row(
                        spec,
                        "lpa_flow_fraction",
                        "dimensionless",
                        "lpa_over_rpa_plus_lpa",
                        lpa_integral / denom,
                        "1",
                        [rpa.source_column, lpa.source_column, "time_s"],
                        period_s,
                        "Pulmonary flow split from beat-integrated RPA and LPA flows.",
                    ),
                    summary_row(
                        spec,
                        "rpa_lpa_flow_ratio",
                        "dimensionless",
                        "rpa_over_lpa",
                        rpa_integral / lpa_integral,
                        "1",
                        [rpa.source_column, lpa.source_column, "time_s"],
                        period_s,
                        "RPA/LPA flow ratio from beat-integrated flows.",
                    ),
                ]
            )

    return rows


def build_waveform_rows(
    df: pd.DataFrame, spec: SourceSpec, infos: list[SignalInfo]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    period_s = cycle_length_s(df["time_s"])
    phase = phase_values(df["time_s"], period_s)
    waveform_rows: list[dict[str, Any]] = []
    metadata_rows: list[dict[str, Any]] = []
    phase_alignment = (
        "Source cycle starts at phase 0 from the processed Aramburu comparison "
        "tables; no valve-event or cross-correlation phase shift is applied."
    )
    for info in infos:
        signal_id = f"{spec.source_id}.{info.canonical_name}"
        values = df[info.source_column].to_numpy(dtype=float)
        metadata_rows.append(
            {
                "signal_id": signal_id,
                "source_id": spec.source_id,
                "source_type": spec.source_type,
                "canonical_name": info.canonical_name,
                "quantity": info.quantity,
                "unit": info.unit,
                "source_file": str(spec.relative_path),
                "source_column": info.source_column,
                "sample_count": len(df),
                "cycle_length_s": period_s,
                "normalization_scale": normalization_scale(df[info.source_column]),
                "normalization_unit": info.unit,
                "phase_alignment": phase_alignment,
                "notes": info.notes,
            }
        )
        for p, t, value in zip(phase, df["time_s"], values):
            waveform_rows.append(
                {
                    "source_id": spec.source_id,
                    "source_type": spec.source_type,
                    "signal_id": signal_id,
                    "canonical_name": info.canonical_name,
                    "quantity": info.quantity,
                    "unit": info.unit,
                    "phase": float(p),
                    "time_s": float(t),
                    "value": float(value),
                }
            )
    return waveform_rows, metadata_rows


def write_csv(path: Path, df: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)


def write_readme(path: Path) -> None:
    path.write_text(
        """# Aramburu 2024 Calibration Targets

This package is generated by `scripts/calibration/extract_targets.py` from the
standardized processed Aramburu data.

Files:

- `summary_targets.csv`: scalar targets for cycle length, heart rate, EDV, ESV,
  stroke volume, cardiac output, mean pressures, beat-integrated flows, and
  pulmonary flow split.
- `waveform_targets.csv`: long-form waveform values with source, canonical
  signal name, quantity, unit, phase, time, and value columns.
- `waveform_metadata.csv`: per-waveform source columns, phase-alignment
  assumptions, sample counts, cycle lengths, and normalization scales.
- `metadata.yaml`: source files, source types, target schemas, and measurement
  unit-conversion validation results.

The waveform phase convention uses the processed comparison-cycle start as
phase 0. No model-event phase shift is applied. Beat integrals use periodic
trapezoid integration and include the wraparound interval from the final sample
back to phase 1.0.
""",
        encoding="utf-8",
    )


def build_target_package(processed_root: Path, out_dir: Path) -> None:
    ensure_measurement_cycle_is_consistent(processed_root)
    clinical = read_csv(processed_root, DIRECT_MEASUREMENT_CLINICAL_FILE)
    si = read_csv(processed_root, DIRECT_MEASUREMENT_SI_FILE)
    conversion_checks = validate_measurement_unit_conversions(clinical, si)

    summary_rows: list[dict[str, Any]] = []
    waveform_rows: list[dict[str, Any]] = []
    waveform_metadata_rows: list[dict[str, Any]] = []

    for spec in SOURCE_SPECS:
        df = read_source(processed_root, spec)
        if "time_s" not in df:
            raise ValueError(f"{spec.relative_path} is missing time_s")
        infos = source_signal_infos(df, spec)
        summary_rows.extend(build_summary_rows(df, spec, infos))
        waveforms, waveform_metadata = build_waveform_rows(df, spec, infos)
        waveform_rows.extend(waveforms)
        waveform_metadata_rows.extend(waveform_metadata)

    summary = pd.DataFrame(summary_rows, columns=SUMMARY_COLUMNS)
    waveforms = pd.DataFrame(waveform_rows, columns=WAVEFORM_COLUMNS)
    waveform_metadata = pd.DataFrame(
        waveform_metadata_rows,
        columns=WAVEFORM_METADATA_COLUMNS,
    )

    out_dir.mkdir(parents=True, exist_ok=True)
    write_csv(out_dir / "summary_targets.csv", summary)
    write_csv(out_dir / "waveform_targets.csv", waveforms)
    write_csv(out_dir / "waveform_metadata.csv", waveform_metadata)
    write_readme(out_dir / "README.md")
    (out_dir / "metadata.yaml").write_text(
        yaml.safe_dump(
            {
                "generated_by": "scripts/calibration/extract_targets.py",
                "processed_root": str(processed_root.relative_to(ROOT))
                if processed_root.is_relative_to(ROOT)
                else str(processed_root),
                "phase_alignment": {
                    "assumption": "Each source table is one processed comparison cycle starting at phase 0.",
                    "cycle_length": "sample_count * median_dt; endpoint at phase 1 is not duplicated.",
                    "beat_integrals": "periodic trapezoid integration with final-to-first wraparound.",
                },
                "source_files": [
                    {
                        "source_id": spec.source_id,
                        "source_type": spec.source_type,
                        "path": str(spec.relative_path),
                        "time_column": spec.time_column,
                        "description": spec.description,
                    }
                    for spec in SOURCE_SPECS
                ]
                + [
                    {
                        "source_id": "direct_measurement_si_validation",
                        "source_type": "direct_measurement",
                        "path": str(DIRECT_MEASUREMENT_SI_FILE),
                        "description": "SI-unit measurement table used to validate clinical-unit conversions.",
                    },
                    {
                        "source_id": "direct_measurement_clinical_validation",
                        "source_type": "direct_measurement",
                        "path": str(DIRECT_MEASUREMENT_CLINICAL_FILE),
                        "description": "Clinical-unit measurement table checked against the comparison-cycle copy.",
                    },
                ],
                "schemas": {
                    "summary_targets": SUMMARY_COLUMNS,
                    "waveform_targets": WAVEFORM_COLUMNS,
                    "waveform_metadata": WAVEFORM_METADATA_COLUMNS,
                },
                "unit_validation": conversion_checks,
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract shared calibration targets from processed Aramburu data."
    )
    parser.add_argument(
        "--processed-root",
        type=Path,
        default=PROCESSED_ROOT,
        help="Processed Aramburu data directory.",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=TARGET_DIR,
        help="Target package output directory.",
    )
    args = parser.parse_args()
    build_target_package(args.processed_root, args.out_dir)
    print(f"Wrote calibration targets to {args.out_dir}")


if __name__ == "__main__":
    main()
