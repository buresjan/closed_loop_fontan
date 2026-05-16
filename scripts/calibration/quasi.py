from __future__ import annotations

from copy import deepcopy
from typing import Any

DEFAULT_QUASI_FACTORS: dict[str, float] = {
    "heart_contractility_scale": 0.96,
    "upper_systemic_resistance_scale": 1.00,
    "lower_systemic_resistance_scale": 1.12,
    "right_pulmonary_total_resistance_scale": 1.15,
    "left_pulmonary_total_resistance_scale": 1.15,
    "right_pulmonary_proximal_fraction": 0.50,
    "left_pulmonary_proximal_fraction": 0.50,
    "aao_arch_resistance_scale": 1.00,
    "aao_arch_inductance_scale": 1.00,
    "aao_arch_capacitance_scale": 1.00,
    "dao_resistance_scale": 1.00,
    "dao_inductance_scale": 1.00,
    "dao_capacitance_scale": 1.00,
    "svc_resistance_scale": 1.00,
    "svc_inductance_scale": 1.00,
    "svc_capacitance_scale": 1.00,
    "ivc_resistance_scale": 1.00,
    "ivc_inductance_scale": 1.00,
    "ivc_capacitance_scale": 1.00,
    "rpa_resistance_scale": 1.00,
    "rpa_inductance_scale": 1.00,
    "rpa_capacitance_scale": 1.00,
    "lpa_resistance_scale": 1.00,
    "lpa_inductance_scale": 1.00,
    "lpa_capacitance_scale": 1.00,
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

QUASI_CHAINS = ("aao_arch", "dao", "svc", "ivc", "rpa", "lpa")


def scale_parameters(params: dict[str, Any], names: list[str], scale: float) -> None:
    for name in names:
        if name in params:
            params[name] *= scale


def apply_pulmonary_split(
    params: dict[str, Any],
    side: str,
    *,
    total_resistance_scale: float,
    proximal_fraction: float,
) -> None:
    r1_name = f"{side}_lung.resistance_1"
    r2_name = f"{side}_lung.resistance_2"
    if r1_name not in params or r2_name not in params:
        return
    if not 0.0 < proximal_fraction < 1.0:
        raise ValueError(
            f"{side} pulmonary proximal fraction must be between 0 and 1"
        )
    total = (params[r1_name] + params[r2_name]) * total_resistance_scale
    params[r1_name] = total * proximal_fraction
    params[r2_name] = total * (1.0 - proximal_fraction)


def scale_quasi_chain(
    params: dict[str, Any],
    chain: str,
    *,
    resistance_scale: float,
    inductance_scale: float,
    capacitance_scale: float,
) -> None:
    prefix = f"quasi_{chain}_"
    for name in list(params):
        if not name.startswith(prefix):
            continue
        if name.endswith(".resistance"):
            params[name] *= resistance_scale
        elif name.endswith(".inductance"):
            params[name] *= inductance_scale
        elif name.endswith(".capacitance"):
            params[name] *= capacitance_scale


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
    apply_pulmonary_split(
        params,
        "right",
        total_resistance_scale=factors["right_pulmonary_total_resistance_scale"],
        proximal_fraction=factors["right_pulmonary_proximal_fraction"],
    )
    apply_pulmonary_split(
        params,
        "left",
        total_resistance_scale=factors["left_pulmonary_total_resistance_scale"],
        proximal_fraction=factors["left_pulmonary_proximal_fraction"],
    )
    for chain in QUASI_CHAINS:
        scale_quasi_chain(
            params,
            chain,
            resistance_scale=factors[f"{chain}_resistance_scale"],
            inductance_scale=factors[f"{chain}_inductance_scale"],
            capacitance_scale=factors[f"{chain}_capacitance_scale"],
        )

    return calibrated
