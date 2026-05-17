from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = ROOT / "models/coupled_0d_1d/configs"

COUPLED_CONFIGS = {
    "smoke": CONFIG_DIR / "fontan_coupled_0d_1d_smoke.jsonc",
    "baseline": CONFIG_DIR / "fontan_coupled_0d_1d_baseline.jsonc",
    "vasodilation": CONFIG_DIR / "fontan_coupled_0d_1d_vasodilation.jsonc",
    "fenestration": CONFIG_DIR / "fontan_coupled_0d_1d_fenestration.jsonc",
    "lpa_obstruction": CONFIG_DIR / "fontan_coupled_0d_1d_lpa_obstruction.jsonc",
}

REMOVED_BLOCKS = {
    "aao_arch",
    "aortic_arch_compliance",
    "arch_dao",
    "arch_bca",
    "arch_lcca",
    "svc_conduit_compliance",
    "ivc_conduit_compliance",
    "rpa_conduit_compliance",
    "lpa_conduit_compliance",
    "svc_conduit_rl",
    "ivc_conduit_rl",
    "rpa_conduit_rl",
    "lpa_conduit_rl",
    "svc_conduit_junction",
    "ivc_conduit_junction",
    "rpa_conduit_out",
    "lpa_conduit_out",
}

REMOVED_NODES = {
    "aortic_arch",
    "svc_conduit",
    "ivc_conduit",
    "rpa_conduit",
    "lpa_conduit",
}

EXPECTED_1D_BLOCKS = {
    "coupled_aao",
    "coupled_dao",
    "coupled_bca",
    "coupled_lcca",
    "coupled_ivc",
    "coupled_svc",
    "coupled_rpa",
}
EXPECTED_1D_BLOCK_TYPE = "fixed_3cell_1d_log_area_vessel_block"
EXPECTED_TAPERED_1D_BLOCKS = {"coupled_lpa"}
EXPECTED_TAPERED_1D_BLOCK_TYPE = "fixed_6cell_tapered_1d_log_area_vessel_block"

EXPECTED_LOSS_BLOCKS = {
    "coupled_dao_loss",
    "coupled_bca_loss",
    "coupled_lcca_loss",
}


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_coupled_closed_loop_configs_are_regenerable():
    subprocess.run(
        ["python3", "scripts/modeling/build_coupled_configs.py", "--check"],
        cwd=ROOT,
        check=True,
    )


def test_coupled_configs_replace_shortcuts_with_true_1d_blocks():
    for scenario, path in COUPLED_CONFIGS.items():
        payload = load(path)
        blocks = payload["net"]["blocks"]
        nodes = set(payload["net"]["nodes"])
        one_d_blocks = {
            name
            for name, block in blocks.items()
            if block.get("model_type") == EXPECTED_1D_BLOCK_TYPE
        }
        tapered_one_d_blocks = {
            name
            for name, block in blocks.items()
            if block.get("model_type") == EXPECTED_TAPERED_1D_BLOCK_TYPE
        }
        loss_blocks = {
            name
            for name, block in blocks.items()
            if name in EXPECTED_LOSS_BLOCKS and block.get("model_type") == "rc_block"
        }

        assert payload["model_family"] == "coupled_0d_1d"
        assert payload["scenario"] == scenario
        assert one_d_blocks == EXPECTED_1D_BLOCKS
        assert tapered_one_d_blocks == EXPECTED_TAPERED_1D_BLOCKS
        assert loss_blocks == EXPECTED_LOSS_BLOCKS
        assert not (REMOVED_BLOCKS & set(blocks))
        assert not (REMOVED_NODES & nodes)
        assert "coupled_lpa_junction" not in nodes
        assert "coupled_aao_arch" in nodes
        assert "coupled_dao_arch" in nodes
        assert "coupled_bca_arch" in nodes
        assert "coupled_lcca_arch" in nodes
        assert "coupled_lsa_arch" in nodes
        assert "coupled_bca_out" in nodes
        assert "lsa" in nodes
        assert "coupled_rpa_tcpc" in nodes
        assert "coupled_lpa_tcpc" in nodes
        assert "coupled_aao_loss" not in blocks
        assert all(
            "aortic_arch" not in block.get("nodes", {}).values()
            for block in blocks.values()
        )
        assert (
            blocks["coupled_aortic_arch_junction"]["model_type"]
            == "aortic_arch_total_pressure_junction_block"
        )
        assert blocks["coupled_aortic_arch_junction"]["nodes"] == {
            "1": "coupled_aao_arch",
            "2": "coupled_dao_arch",
            "3": "coupled_bca_arch",
            "4": "coupled_lcca_arch",
            "5": "coupled_lsa_arch",
        }
        assert blocks["arch_lsa"]["nodes"] == {
            "1": "lsa",
            "2": "coupled_lsa_arch",
        }
        assert blocks["lsa_compliance"]["nodes"] == {"1": "lsa"}
        assert blocks["upper_lsa_to_ca1"]["nodes"] == {"1": "upper_art", "2": "lsa"}
        assert (
            blocks["coupled_tcpc_junction"]["model_type"]
            == "tcpc_characteristic_total_pressure_junction_block"
        )
        assert (
            blocks["coupled_tcpc_junction"]["characteristic_scale"]
            == "coupled_tcpc_junction.characteristic_scale"
        )
        assert (
            blocks["coupled_tcpc_junction"]["wall_pressure_weight"]
            == "coupled_tcpc_junction.wall_pressure_weight"
        )
        assert (
            blocks["coupled_tcpc_junction"]["loss_coefficient"]
            == "coupled_tcpc_junction.loss_coefficient"
        )
        assert (
            blocks["coupled_tcpc_junction"]["reference_area_svc"]
            == "coupled_svc.reference_area"
        )
        assert (
            blocks["coupled_tcpc_junction"]["reference_area_lpa"]
            == "coupled_lpa.reference_area_01"
        )
        assert (
            blocks["coupled_tcpc_junction"]["external_pressure_svc"]
            == "coupled_svc.external_pressure"
        )
        assert blocks["coupled_tcpc_junction"]["nodes"] == {
            "1": "coupled_svc_tcpc",
            "2": "coupled_ivc_tcpc",
            "3": "coupled_rpa_tcpc",
            "4": "coupled_lpa_tcpc",
        }
        assert "coupled_svc_loss" not in blocks
        assert "coupled_ivc_loss" not in blocks
        assert "coupled_rpa_loss" not in blocks
        assert "coupled_lpa_loss" not in blocks


def test_coupled_boundary_interfaces_are_pressure_coupled_not_prescribed():
    for path in COUPLED_CONFIGS.values():
        payload = load(path)
        assert "boundary_conditions" not in payload
        for block_name in EXPECTED_1D_BLOCKS | EXPECTED_TAPERED_1D_BLOCKS:
            block = payload["net"]["blocks"][block_name]
            assert block["nodes"]
            assert "pressure_1" not in block
            assert "pressure_2" not in block
            assert block["flux_type"] == "blood_flow"
            assert block["time"] == "time"


def test_coupled_flow_magnitudes_do_not_cancel_massless_junction_scaling():
    payload = load(COUPLED_CONFIGS["smoke"])
    magnitudes = payload["variables_magnitudes"]
    initialization = payload["variables_initialization"]

    assert magnitudes["coupled_lpa.flow_03"] != magnitudes["coupled_lpa.flow_04"]
    assert magnitudes["coupled_svc.flow_03"] != magnitudes["coupled_ivc.flow_03"]
    assert initialization["coupled_aao.flow_00"] > 0.0
    assert initialization["coupled_svc.flow_00"] > 0.0
    assert "coupled_aao.area_01" not in initialization
    assert "coupled_lpa.area_01" not in initialization
    assert initialization["coupled_aao.log_area_01"] < 0.0
    assert initialization["coupled_aao.log_area_01"] == initialization["coupled_aao.log_area_03"]
    assert initialization["coupled_lpa.log_area_01"] != initialization["coupled_lpa.log_area_06"]
    assert payload["parameters"]["coupled_rpa.external_pressure"] == payload["parameters"]["pleural.pressure"]
    assert payload["parameters"]["coupled_bca_loss.resistance"] > 1.0e6
    assert "coupled_tcpc_junction.compliance" not in payload["parameters"]
    assert "coupled_tcpc_junction.svc_resistance" not in payload["parameters"]
    assert "coupled_tcpc_junction.pressure" not in initialization
    assert "coupled_aortic_arch_junction.aao_flow" in initialization
    assert "coupled_aortic_arch_junction.lsa_flow" in initialization
    assert initialization["coupled_aortic_arch_junction.lsa_flow"] == pytest.approx(
        initialization["coupled_aortic_arch_junction.aao_flow"]
        - initialization["coupled_aortic_arch_junction.dao_flow"]
        - initialization["coupled_aortic_arch_junction.bca_flow"]
        - initialization["coupled_aortic_arch_junction.lcca_flow"]
    )
    assert "coupled_tcpc_junction.svc_flow" in initialization
    assert magnitudes["coupled_tcpc_junction.rpa_flow"] != magnitudes["coupled_rpa.flow_00"]
    assert magnitudes["coupled_tcpc_junction.lpa_flow"] != magnitudes["coupled_lpa.flow_00"]
    assert magnitudes["coupled_aortic_arch_junction.aao_flow"] != magnitudes["coupled_aao.flow_00"]
    assert magnitudes["coupled_aortic_arch_junction.dao_flow"] != magnitudes["coupled_dao.flow_00"]
    assert payload["parameters"]["coupled_lpa.cell_length_01"] > 0.0
    assert payload["parameters"]["coupled_lpa.reference_area_01"] > payload["parameters"]["coupled_lpa.reference_area_06"]
    assert payload["parameters"]["coupled_rpa.wall_stiffness"] > payload["parameters"]["coupled_aao.wall_stiffness"]
    assert payload["time"]["step_size"] <= 2.5e-4


def test_coupled_configs_record_scientific_limitations():
    payload = load(COUPLED_CONFIGS["baseline"])
    metadata = payload["coupled_0d_1d"]

    assert metadata["status"] == "paper_aligned_topology_candidate"
    assert "baseline is not calibrated yet" in metadata["limitations"]
    assert any("do not prescribe both pressure and flow" in item for item in metadata["topology_policy"])
    assert any("dissipative total-pressure TCPC junction" in item for item in metadata["topology_policy"])
    assert any("0-D LSA terminal branch" in item for item in metadata["topology_policy"])
