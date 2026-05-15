from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
from pandas.testing import assert_frame_equal

from scripts.calibration.extract_targets import (
    PROCESSED_ROOT,
    SUMMARY_COLUMNS,
    WAVEFORM_COLUMNS,
    WAVEFORM_METADATA_COLUMNS,
    build_target_package,
    cycle_length_s,
    periodic_beat_integral,
    validate_measurement_unit_conversions,
)

TARGET_DIR = PROCESSED_ROOT / "targets"


def test_measurement_unit_conversion_validation():
    clinical = pd.DataFrame(
        {
            "time_s": [0.0, 0.1],
            "ivc_pressure_mmHg": [1.0, 2.0],
            "ivc_flow_ml_s": [3.0, 4.0],
            "ventricle_volume_ml": [5.0, 6.0],
        }
    )
    si = pd.DataFrame(
        {
            "time_s": [0.0, 0.1],
            "ivc_pressure_pa": [133.33, 266.66],
            "ivc_flow_m3_s": [3.0e-6, 4.0e-6],
            "ventricle_volume_m3": [5.0e-6, 6.0e-6],
        }
    )

    checks = validate_measurement_unit_conversions(clinical, si)

    assert {row["clinical_column"] for row in checks} == set(clinical.columns)
    assert all(row["max_abs_error"] < 1e-18 for row in checks)


def test_cycle_length_uses_nonduplicated_periodic_grid():
    time_s = pd.Series([0.0, 0.1, 0.2])

    assert cycle_length_s(time_s) == pytest.approx(0.3)


def test_periodic_beat_integral_includes_wraparound_interval():
    time_s = pd.Series([0.0, 0.1, 0.2])
    values = pd.Series([10.0, 10.0, 10.0])

    assert periodic_beat_integral(time_s, values) == pytest.approx(3.0)


def test_target_package_has_expected_schema_and_core_targets():
    summary = pd.read_csv(TARGET_DIR / "summary_targets.csv")
    waveforms = pd.read_csv(TARGET_DIR / "waveform_targets.csv")
    waveform_metadata = pd.read_csv(TARGET_DIR / "waveform_metadata.csv")

    assert list(summary.columns) == SUMMARY_COLUMNS
    assert list(waveforms.columns) == WAVEFORM_COLUMNS
    assert list(waveform_metadata.columns) == WAVEFORM_METADATA_COLUMNS
    assert {
        "direct_measurement",
        "paper_output",
        "nektar_comparison_output",
    } <= set(summary["source_type"])
    direct = summary[summary["source_id"] == "direct_measurement"]
    assert {
        ("cycle_length", "period"),
        ("heart_rate", "derived_from_cycle_length"),
        ("edv", "max"),
        ("esv", "min"),
        ("stroke_volume", "edv_minus_esv"),
        ("cardiac_output", "from_stroke_volume"),
        ("rpa_flow_fraction", "rpa_over_rpa_plus_lpa"),
        ("lpa_flow_fraction", "lpa_over_rpa_plus_lpa"),
        ("rpa_lpa_flow_ratio", "rpa_over_lpa"),
        ("ivc_pressure", "mean"),
        ("ivc_flow", "beat_integral"),
    } <= set(zip(direct["canonical_name"], direct["statistic"]))
    assert waveforms["phase"].between(0.0, 1.0).all()
    assert (waveform_metadata["normalization_scale"] > 0.0).all()


def test_tracked_targets_are_reproducible_from_processed_data(tmp_path: Path):
    build_target_package(PROCESSED_ROOT, tmp_path)

    for name in [
        "summary_targets.csv",
        "waveform_metadata.csv",
        "waveform_targets.csv",
    ]:
        expected = pd.read_csv(TARGET_DIR / name)
        actual = pd.read_csv(tmp_path / name)
        assert_frame_equal(actual, expected, check_dtype=False, rtol=1e-12, atol=1e-12)
