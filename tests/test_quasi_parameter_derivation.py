from __future__ import annotations

import math
from numbers import Real
from pathlib import Path

import pytest
import yaml

from scripts.modeling.derive_quasi_vessel_parameters import (
    build_config_fragment,
    build_priors_payload,
    poiseuille_resistance_tapered,
)

ROOT = Path(__file__).resolve().parents[1]
PRIORS = ROOT / "models/quasi_0d_1d/calibration/parameter_priors.yaml"


def load_priors():
    return yaml.safe_load(PRIORS.read_text())


def assert_nested_equal_approx(observed, expected):
    if isinstance(expected, dict):
        assert isinstance(observed, dict)
        assert set(observed) == set(expected)
        for key in expected:
            assert_nested_equal_approx(observed[key], expected[key])
        return
    if isinstance(expected, list):
        assert isinstance(observed, list)
        assert len(observed) == len(expected)
        for observed_item, expected_item in zip(observed, expected):
            assert_nested_equal_approx(observed_item, expected_item)
        return
    if (
        isinstance(expected, Real)
        and isinstance(observed, Real)
        and not isinstance(expected, bool)
        and not isinstance(observed, bool)
    ):
        assert observed == pytest.approx(expected)
        return
    assert observed == expected


def test_tapered_poiseuille_resistance_matches_cylindrical_limit():
    length = 0.1
    radius = 0.005
    mu = 0.0035

    observed = poiseuille_resistance_tapered(length, radius, radius, mu)
    expected = 8.0 * mu * length / (math.pi * radius**4)

    assert observed == pytest.approx(expected)


def test_generated_quasi_priors_preserve_chain_totals_across_cells():
    priors = load_priors()

    assert set(priors["chains"]) == {"aao_arch", "dao", "svc", "ivc", "rpa", "lpa"}
    for chain in priors["chains"].values():
        cells = chain["cells"]
        totals = chain["totals"]
        assert len(cells) == chain["segment_count"]
        assert sum(cell["resistance_pa_s_m3"] for cell in cells) == pytest.approx(
            totals["selected_resistance_pa_s_m3"]
        )
        assert sum(cell["inertance_pa_s2_m3"] for cell in cells) == pytest.approx(
            totals["inertance_pa_s2_m3"]
        )
        assert sum(cell["capacitance_m3_pa"] for cell in cells) == pytest.approx(
            totals["capacitance_m3_pa"]
        )


def test_generated_quasi_priors_are_positive_and_unit_documented():
    priors = load_priors()

    assert {
        "resistance_pa_s_m3",
        "inertance_pa_s2_m3",
        "capacitance_m3_pa",
        "wave_speed_m_s",
    } <= set(priors["units"])
    for chain in priors["chains"].values():
        totals = chain["totals"]
        assert totals["selected_resistance_pa_s_m3"] > 0.0
        assert totals["geometry_resistance_pa_s_m3"] > 0.0
        assert totals["inertance_pa_s2_m3"] > 0.0
        assert totals["capacitance_m3_pa"] > 0.0
        assert chain["wave_speed_m_s"] > 0.0
        for cell in chain["cells"]:
            assert cell["resistance_pa_s_m3"] > 0.0
            assert cell["inertance_pa_s2_m3"] > 0.0
            assert cell["capacitance_m3_pa"] > 0.0


def test_aortic_chains_use_geometry_resistance_not_full_0d_drop():
    priors = load_priors()

    for key in ["aao_arch", "dao"]:
        totals = priors["chains"][key]["totals"]
        assert totals["selected_resistance_source"] == "geometry_poiseuille"
        assert totals["selected_resistance_pa_s_m3"] == pytest.approx(
            totals["geometry_resistance_pa_s_m3"]
        )
        assert totals["selected_resistance_pa_s_m3"] < totals[
            "full_0d_resistance_prior_pa_s_m3"
        ]


def test_fontan_chains_keep_calibrated_pathway_resistance_as_first_pass_prior():
    priors = load_priors()

    for key in ["svc", "ivc", "rpa", "lpa"]:
        totals = priors["chains"][key]["totals"]
        assert totals["selected_resistance_source"] == "calibrated_full_0d_pathway"
        assert totals["selected_resistance_pa_s_m3"] == pytest.approx(
            totals["full_0d_resistance_prior_pa_s_m3"]
        )


def test_lpa_narrowing_has_explicit_parameter_and_fragment_metadata():
    priors = load_priors()
    fragment = build_config_fragment(priors)

    narrowing = priors["metadata"]["lpa_narrowing"]
    assert narrowing["parameter_name"] == "quasi_lpa.narrowing_radius_m"
    assert narrowing["radius_m"] == pytest.approx(0.003)
    assert narrowing["area_m2"] > 0.0
    assert fragment["parameters"]["quasi_lpa.narrowing_radius_m"] == pytest.approx(0.003)
    assert fragment["parameters"]["quasi_lpa.narrowing_resistance_scale"] == 1.0


def test_config_fragment_preserves_priors_and_uses_quasi_blocks():
    priors = load_priors()
    fragment = build_config_fragment(priors)

    for key, chain in fragment["chains"].items():
        assert len(chain["nodes"]) == priors["chains"][key]["segment_count"] + 1
        assert set(chain["blocks"])
        assert all(value > 0.0 for value in chain["parameters"].values())
        model_types = {block["model_type"] for block in chain["blocks"].values()}
        assert model_types == {"hydraulic_rl_block", "c_block"}


def test_derivation_payload_matches_tracked_priors():
    generated = build_priors_payload()
    tracked = load_priors()

    assert_nested_equal_approx(generated, tracked)
