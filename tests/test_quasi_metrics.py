from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from scripts.metrics import compute
from scripts.calibration.objective import comparison_rows

ROOT = Path(__file__).resolve().parents[1]
QUASI_BASELINE = ROOT / "models/quasi_0d_1d/configs/fontan_quasi_baseline.jsonc"
FULL_BASELINE = ROOT / "models/full_0d/configs/fontan_0d_baseline.jsonc"
COUPLED_SMOKE = ROOT / "models/coupled_0d_1d/configs/fontan_coupled_0d_1d_smoke.jsonc"


def config_with_unit_period(source: Path, tmp_path: Path) -> Path:
    config = json.loads(source.read_text())
    config["parameters"]["heart_rate"] = 60.0
    path = tmp_path / source.name
    path.write_text(json.dumps(config))
    return path


def write_csv(tmp_path: Path, data: dict[str, list[float]]) -> Path:
    path = tmp_path / "main.csv"
    pd.DataFrame(data).to_csv(path, index=False)
    return path


def test_quasi_metrics_report_vessel_inlet_outlet_and_storage(tmp_path):
    config = config_with_unit_period(QUASI_BASELINE, tmp_path)
    csv = write_csv(
        tmp_path,
        {
            "time": [0.0, 0.5, 1.0],
            "quasi_svc_rl_01.flux": [10e-6, 10e-6, 10e-6],
            "quasi_svc_rl_02.flux": [9.5e-6, 9.5e-6, 9.5e-6],
            "quasi_svc_rl_03.flux": [9e-6, 9e-6, 9e-6],
            "quasi_ivc_rl_01.flux": [20e-6, 20e-6, 20e-6],
            "quasi_ivc_rl_05.flux": [19e-6, 19e-6, 19e-6],
            "quasi_rpa_rl_01.flux": [16e-6, 16e-6, 16e-6],
            "quasi_rpa_rl_03.flux": [15e-6, 15e-6, 15e-6],
            "quasi_lpa_rl_01.flux": [14e-6, 14e-6, 14e-6],
            "quasi_lpa_rl_04.flux": [13e-6, 13e-6, 13e-6],
        },
    )

    metrics = compute(csv, config)

    assert metrics["mean_svc_inlet_flow_ml_s"] == pytest.approx(10.0)
    assert metrics["mean_svc_outlet_flow_ml_s"] == pytest.approx(9.0)
    assert metrics["integral_svc_inlet_flow_ml"] == pytest.approx(10.0)
    assert metrics["integral_svc_outlet_flow_ml"] == pytest.approx(9.0)
    assert metrics["svc_cycle_storage_ml"] == pytest.approx(1.0)
    assert metrics["svc_mass_balance_rel"] == pytest.approx(1.0 / 19.0)

    assert metrics["mean_quasi_svc_rl_02.flux_ml_s"] == pytest.approx(9.5)
    assert metrics["integral_quasi_svc_rl_02.flux_ml"] == pytest.approx(9.5)
    assert metrics["rpa_flow_fraction"] == pytest.approx(15.0 / 28.0)
    assert metrics["tcpc_cycle_balance_rel"] == pytest.approx(
        abs((10.0 + 20.0) - (15.0 + 13.0)) / (10.0 + 20.0 + 15.0 + 13.0)
    )
    assert metrics["tcpc_junction_cycle_balance_rel"] == pytest.approx(
        abs((9.0 + 19.0) - (16.0 + 14.0)) / (9.0 + 19.0 + 16.0 + 14.0)
    )


def test_full_0d_metrics_keep_legacy_conduit_flow_keys(tmp_path):
    config = config_with_unit_period(FULL_BASELINE, tmp_path)
    csv = write_csv(
        tmp_path,
        {
            "time": [0.0, 0.5, 1.0],
            "svc_conduit_rl.flux": [10e-6, 10e-6, 10e-6],
            "ivc_conduit_rl.flux": [20e-6, 20e-6, 20e-6],
            "rpa_conduit_rl.flux": [16e-6, 16e-6, 16e-6],
            "lpa_conduit_rl.flux": [14e-6, 14e-6, 14e-6],
            "svc_conduit.blood_pressure": [1600.0, 1600.0, 1600.0],
            "ivc_conduit.blood_pressure": [1600.0, 1600.0, 1600.0],
            "tcpc.blood_pressure": [1200.0, 1200.0, 1200.0],
            "rpa_conduit.blood_pressure": [1600.0, 1600.0, 1600.0],
            "lpa_conduit.blood_pressure": [1600.0, 1600.0, 1600.0],
            "rpa.blood_pressure": [1200.0, 1200.0, 1200.0],
            "lpa.blood_pressure": [1200.0, 1200.0, 1200.0],
        },
    )

    metrics = compute(csv, config)

    assert metrics["mean_svc_conduit_rl.flux_ml_s"] == pytest.approx(10.0)
    assert "mean_svc_conduit_junction.flow_ml_s" in metrics
    assert metrics["mean_svc_inlet_flow_ml_s"] == pytest.approx(
        metrics["mean_svc_conduit_rl.flux_ml_s"]
    )
    assert metrics["mean_svc_outlet_flow_ml_s"] == pytest.approx(
        metrics["mean_svc_conduit_junction.flow_ml_s"]
    )


def test_coupled_metrics_report_true_1d_flow_area_and_storage(tmp_path):
    config = config_with_unit_period(COUPLED_SMOKE, tmp_path)
    csv = write_csv(
        tmp_path,
        {
            "time": [0.0, 0.5, 1.0],
            "coupled_svc.flow_00": [10e-6, 10e-6, 10e-6],
            "coupled_svc.flow_01": [9.8e-6, 9.8e-6, 9.8e-6],
            "coupled_svc.flow_02": [9.3e-6, 9.3e-6, 9.3e-6],
            "coupled_svc.flow_03": [9e-6, 9e-6, 9e-6],
            "coupled_ivc.flow_00": [20e-6, 20e-6, 20e-6],
            "coupled_ivc.flow_03": [19e-6, 19e-6, 19e-6],
            "coupled_rpa.flow_00": [16e-6, 16e-6, 16e-6],
            "coupled_rpa.flow_03": [15e-6, 15e-6, 15e-6],
            "coupled_lpa.flow_00": [14e-6, 14e-6, 14e-6],
            "coupled_lpa.flow_01": [13.8e-6, 13.8e-6, 13.8e-6],
            "coupled_lpa.flow_02": [13.6e-6, 13.6e-6, 13.6e-6],
            "coupled_lpa.flow_03": [13.5e-6, 13.5e-6, 13.5e-6],
            "coupled_lpa.flow_04": [13.4e-6, 13.4e-6, 13.4e-6],
            "coupled_lpa.flow_05": [13.2e-6, 13.2e-6, 13.2e-6],
            "coupled_lpa.flow_06": [13e-6, 13e-6, 13e-6],
            "coupled_svc.area_01": [3.0e-4, 3.1e-4, 3.0e-4],
            "coupled_svc.area_02": [2.9e-4, 3.0e-4, 3.0e-4],
            "coupled_svc.area_03": [2.8e-4, 2.9e-4, 3.0e-4],
            "coupled_lpa.area_01": [7.0e-5, 7.1e-5, 7.0e-5],
            "coupled_lpa.area_02": [6.6e-5, 6.7e-5, 6.6e-5],
            "coupled_lpa.area_03": [6.2e-5, 6.3e-5, 6.2e-5],
            "coupled_lpa.area_04": [5.2e-5, 5.3e-5, 5.2e-5],
            "coupled_lpa.area_05": [4.8e-5, 4.9e-5, 4.8e-5],
            "coupled_lpa.area_06": [4.4e-5, 4.5e-5, 4.4e-5],
            "coupled_tcpc_junction.mass_balance": [0.0, 0.0, 0.0],
            "coupled_tcpc_junction.total_pressure_spread": [0.0, 10.0, 20.0],
            "coupled_aortic_arch_junction.mass_balance": [0.0, 0.0, 0.0],
            "coupled_aortic_arch_junction.total_pressure_spread": [0.0, 5.0, 10.0],
        },
    )

    metrics = compute(csv, config)

    assert metrics["mean_svc_inlet_flow_ml_s"] == pytest.approx(10.0)
    assert metrics["mean_svc_outlet_flow_ml_s"] == pytest.approx(9.0)
    assert metrics["svc_cycle_storage_ml"] == pytest.approx(1.0)
    assert metrics["mean_coupled_svc.flow_01_ml_s"] == pytest.approx(9.8)
    assert metrics["rpa_flow_fraction"] == pytest.approx(15.0 / 28.0)
    assert metrics["tcpc_cycle_balance_rel"] == pytest.approx(
        abs((10.0 + 20.0) - (15.0 + 13.0)) / (10.0 + 20.0 + 15.0 + 13.0)
    )
    assert metrics["tcpc_junction_cycle_balance_rel"] == pytest.approx(
        abs((9.0 + 19.0) - (16.0 + 14.0)) / (9.0 + 19.0 + 16.0 + 14.0)
    )
    assert metrics["min_coupled_svc_area_m2"] == pytest.approx(2.8e-4)
    assert metrics["min_coupled_lpa_area_m2"] == pytest.approx(4.4e-5)
    assert metrics["max_abs_coupled_tcpc_junction_mass_balance_ml_s"] == pytest.approx(
        0.0
    )
    assert metrics["max_abs_coupled_aortic_arch_junction_mass_balance_ml_s"] == pytest.approx(
        0.0
    )
    assert metrics["max_coupled_tcpc_junction_total_pressure_spread_mmHg"] == pytest.approx(
        20.0 * 0.00750062
    )
    assert metrics["mean_coupled_aortic_arch_junction_total_pressure_spread_mmHg"] == pytest.approx(
        5.0 * 0.00750062
    )
    assert metrics["negative_coupled_1d_area_count"] == 0
    assert metrics["pass_no_negative_coupled_1d_area"] is True


def test_calibration_objective_accepts_quasi_standard_flow_keys():
    metrics = {
        "mean_svc_outlet_flow_ml_s": 1.0,
        "mean_ivc_outlet_flow_ml_s": 1.0,
        "mean_rpa_outlet_flow_ml_s": 1.0,
        "mean_lpa_outlet_flow_ml_s": 1.0,
        "rpa_flow_fraction": 0.5,
    }

    rows = comparison_rows(metrics)
    metric_names = {row["metric"] for row in rows}

    assert {
        "mean_svc_outlet_flow_ml_s",
        "mean_ivc_outlet_flow_ml_s",
        "mean_rpa_outlet_flow_ml_s",
        "mean_lpa_outlet_flow_ml_s",
        "rpa_flow_fraction",
    } <= metric_names
