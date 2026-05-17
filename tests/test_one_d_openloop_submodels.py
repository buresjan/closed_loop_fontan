from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = ROOT / "models/coupled_0d_1d/configs"
REPORT = ROOT / "models/coupled_0d_1d/reference_outputs/openloop_1d_validation.json"
GEOMETRY = ROOT / "models/coupled_0d_1d/calibration/one_d_openloop_geometry.json"
DOC = ROOT / "models/coupled_0d_1d/docs/openloop_1d_submodels.md"

CONFIGS = {
    "submodel_aorta_1d_openloop": CONFIG_DIR / "submodel_aorta_1d_openloop.jsonc",
    "submodel_tcpc_1d_openloop": CONFIG_DIR / "submodel_tcpc_1d_openloop.jsonc",
    "submodel_aorta_tcpc_1d_openloop": CONFIG_DIR / "submodel_aorta_tcpc_1d_openloop.jsonc",
}


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_openloop_configs_are_strict_json_reference_specs():
    for submodel_id, path in CONFIGS.items():
        payload = load(path)

        assert payload["type"] == "open_loop_1d_submodel"
        assert payload["model_family"] == "coupled_0d_1d"
        assert payload["status"] == "reference_validation_spec"
        assert payload["submodel_id"] == submodel_id
        assert payload["run_with"] == "python3 scripts/calibration/validate_1d_submodels.py"
        assert payload["topology"]["segments"]
        assert payload["validation"]["signals"]


def test_openloop_topology_uses_source_geometry_without_added_lsa():
    aorta = load(CONFIGS["submodel_aorta_1d_openloop"])
    tcpc = load(CONFIGS["submodel_tcpc_1d_openloop"])
    combined = load(CONFIGS["submodel_aorta_tcpc_1d_openloop"])

    assert [segment["source_segment"] for segment in aorta["topology"]["segments"]] == [
        "Ascending aorta",
        "Thoracic aorta",
        "Brachiocephalic",
        "Carotic left",
    ]
    assert all("lsa" not in segment["segment_id"] for segment in aorta["topology"]["segments"])
    assert [segment["source_segment"] for segment in tcpc["topology"]["segments"]] == [
        "IVC",
        "RPA",
        "LPA I",
        "LPA II",
        "SVC",
    ]
    assert len(combined["topology"]["segments"]) == 9
    assert [segment["domain_no"] for segment in combined["topology"]["segments"]] == list(
        range(1, 10)
    )


def test_openloop_segments_are_fixed_3cell_true_1d_specs():
    for path in CONFIGS.values():
        payload = load(path)
        for segment in payload["topology"]["segments"]:
            assert segment["length_m"] > 0.0
            assert segment["radius_in_m"] > 0.0
            assert segment["radius_out_m"] > 0.0
            assert segment["reference_area_m2"] > 0.0
            assert segment["wall_stiffness_pa_m-1"] > 0.0
            assert segment["prototype_block"]["model_type"] == "fixed_3cell_1d_vessel_block"
            assert segment["prototype_block"]["cell_count"] == 3
            assert len(segment["cells"]) == 3
            assert all(cell["reference_area_m2"] > 0.0 for cell in segment["cells"])


def test_openloop_validation_report_passes_all_submodels():
    report = load(REPORT)

    assert report["passed"] is True
    assert {item["submodel_id"] for item in report["submodels"]} == set(CONFIGS)
    for submodel in report["submodels"]:
        assert submodel["passed"] is True
        assert all(item["passed"] for item in submodel["input_checks"])
        assert all(item["passed"] for item in submodel["geometry_checks"])
        assert all(item["passed"] for item in submodel["domain_checks"])
        assert all(item["passed"] for item in submodel["waveform_checks"])
        assert submodel["mass_balance"]["passed"] is True
        assert submodel["boundary_signs"]["passed"] is True


def test_openloop_artifacts_are_documented_and_regenerable():
    assert GEOMETRY.exists()
    assert REPORT.exists()
    text = DOC.read_text(encoding="utf-8")
    for path in [*CONFIGS.values(), GEOMETRY, REPORT]:
        relative = str(path.relative_to(ROOT))
        assert relative in text

    subprocess.run(
        ["python3", "scripts/modeling/derive_1d_geometry.py", "--check"],
        cwd=ROOT,
        check=True,
    )
    subprocess.run(
        ["python3", "scripts/calibration/validate_1d_submodels.py", "--check"],
        cwd=ROOT,
        check=True,
    )
