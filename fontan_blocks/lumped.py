from dataclasses import dataclass
from typing import Any

import numpy as np

from physioblocks.computing import Block, Quantity, diff, mid_point
from physioblocks.computing.models import declares_flux, declares_internal_equation
from physioblocks.registers import register_type
from physioblocks.simulation import Time

HYDRAULIC_RESISTOR_BLOCK_TYPE_ID = "hydraulic_resistor_block"
HYDRAULIC_RL_BLOCK_TYPE_ID = "hydraulic_rl_block"

FLOW_ID = "flux"
PRESSURE_1_ID = "pressure_1"
PRESSURE_2_ID = "pressure_2"


@register_type(HYDRAULIC_RESISTOR_BLOCK_TYPE_ID)
@dataclass
class HydraulicResistorBlock(Block):
    """Two-node hydraulic resistor with positive flow from local node 1 to 2."""

    pressure_1: Quantity[np.float64]
    pressure_2: Quantity[np.float64]
    resistance: Quantity[np.float64]

    def _flow(self) -> Any:
        return (
            mid_point(self.pressure_1) - mid_point(self.pressure_2)
        ) / self.resistance.current

    @declares_flux(1, PRESSURE_1_ID)
    def flux_1(self) -> Any:
        return -self._flow()

    @flux_1.partial_derivative(PRESSURE_1_ID)
    def dflux_1_dpressure_1(self) -> Any:
        return -0.5 / self.resistance.current

    @flux_1.partial_derivative(PRESSURE_2_ID)
    def dflux_1_dpressure_2(self) -> Any:
        return 0.5 / self.resistance.current

    @declares_flux(2, PRESSURE_2_ID)
    def flux_2(self) -> Any:
        return self._flow()

    @flux_2.partial_derivative(PRESSURE_1_ID)
    def dflux_2_dpressure_1(self) -> Any:
        return 0.5 / self.resistance.current

    @flux_2.partial_derivative(PRESSURE_2_ID)
    def dflux_2_dpressure_2(self) -> Any:
        return -0.5 / self.resistance.current


@register_type(HYDRAULIC_RL_BLOCK_TYPE_ID)
@dataclass
class HydraulicRLBlock(Block):
    """Two-node symmetric hydraulic resistor-inertance link."""

    flux: Quantity[np.float64]
    pressure_1: Quantity[np.float64]
    pressure_2: Quantity[np.float64]
    resistance: Quantity[np.float64]
    inductance: Quantity[np.float64]
    time: Time

    @declares_internal_equation(FLOW_ID)
    def flux_residual(self) -> Any:
        return (
            self.inductance.current * self.time.inv_dt * diff(self.flux)
            + self.resistance.current * mid_point(self.flux)
            - mid_point(self.pressure_1)
            + mid_point(self.pressure_2)
        )

    @flux_residual.partial_derivative(FLOW_ID)
    def flux_residual_dflux(self) -> Any:
        return (
            self.inductance.current * self.time.inv_dt
            + 0.5 * self.resistance.current
        )

    @flux_residual.partial_derivative(PRESSURE_1_ID)
    def flux_residual_dpressure_1(self) -> Any:
        return -0.5

    @flux_residual.partial_derivative(PRESSURE_2_ID)
    def flux_residual_dpressure_2(self) -> Any:
        return 0.5

    @declares_flux(1, PRESSURE_1_ID)
    def flux_1(self) -> Any:
        return -mid_point(self.flux)

    @flux_1.partial_derivative(FLOW_ID)
    def dflux_1_dflux(self) -> Any:
        return -0.5

    @declares_flux(2, PRESSURE_2_ID)
    def flux_2(self) -> Any:
        return mid_point(self.flux)

    @flux_2.partial_derivative(FLOW_ID)
    def dflux_2_dflux(self) -> Any:
        return 0.5
