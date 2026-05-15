from __future__ import annotations

from copy import deepcopy
from typing import Any

DEFAULT_QUASI_FACTORS: dict[str, float] = {
    "heart_contractility_scale": 0.96,
    "upper_systemic_resistance_scale": 1.04,
    "lower_systemic_resistance_scale": 1.12,
    "pulmonary_bed_resistance_scale": 1.10,
}

UPPER_SYSTEMIC_RESISTANCES = [
    "arch_bca.resistance",
    "upper_bca_to_ca1.resistance",
    "arch_lcca.resistance",
    "upper_lcca_to_ca1.resistance",
    "arch_lsa.resistance",
    "upper_lsa_to_ca1.resistance",
    "upper_rc1.resistance",
    "upper_rv1.resistance",
]

LOWER_SYSTEMIC_RESISTANCES = [
    "lower_ra4.resistance",
    "lower_rc2.resistance",
    "lower_rv2.resistance",
]

PULMONARY_BED_RESISTANCES = [
    "right_lung.resistance_1",
    "right_lung.resistance_2",
    "left_lung.resistance_1",
    "left_lung.resistance_2",
]


def scale_parameters(params: dict[str, Any], names: list[str], scale: float) -> None:
    for name in names:
        if name in params:
            params[name] *= scale


def apply_quasi_calibration_factors(
    config: dict[str, Any],
    factors: dict[str, float] | None = None,
) -> dict[str, Any]:
    factors = dict(DEFAULT_QUASI_FACTORS if factors is None else factors)
    calibrated = deepcopy(config)
    params = calibrated["parameters"]

    params["heart_contractility"] *= factors["heart_contractility_scale"]
    scale_parameters(
        params,
        UPPER_SYSTEMIC_RESISTANCES,
        factors["upper_systemic_resistance_scale"],
    )
    scale_parameters(
        params,
        LOWER_SYSTEMIC_RESISTANCES,
        factors["lower_systemic_resistance_scale"],
    )
    scale_parameters(
        params,
        PULMONARY_BED_RESISTANCES,
        factors["pulmonary_bed_resistance_scale"],
    )

    return calibrated
