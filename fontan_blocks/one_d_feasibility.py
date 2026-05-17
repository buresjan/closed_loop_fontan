from dataclasses import dataclass
from typing import Any

import numpy as np

from physioblocks.computing import Block, Quantity, diff, mid_point
from physioblocks.computing.models import (
    declares_flux,
    declares_internal_equation,
    declares_saved_quantity,
)
from physioblocks.registers import register_type
from physioblocks.simulation import Time

FIXED_3CELL_1D_PROBE_BLOCK_TYPE_ID = "fixed_3cell_1d_probe_block"

AREA_IDS = ("area_01", "area_02", "area_03")
FLOW_IDS = ("flow_00", "flow_01", "flow_02", "flow_03")
PRESSURE_1_ID = "pressure_1"
PRESSURE_2_ID = "pressure_2"
CELL_PRESSURE_ID = "cell_pressure"
MIN_AREA_ID = "min_area"
MAX_AREA_ID = "max_area"


@register_type(FIXED_3CELL_1D_PROBE_BLOCK_TYPE_ID)
@dataclass
class Fixed3Cell1DProbeBlock(Block):
    """Feasibility-only fixed-size 1-D vessel probe.

    This block is intentionally not a production vessel model. It tests whether
    PhysioBlocks can assemble fixed-size vector residuals, scalar state terms,
    node flux coupling, and vector saved quantities without internal changes.
    """

    area_01: Quantity[np.float64]
    area_02: Quantity[np.float64]
    area_03: Quantity[np.float64]
    flow_00: Quantity[np.float64]
    flow_01: Quantity[np.float64]
    flow_02: Quantity[np.float64]
    flow_03: Quantity[np.float64]
    pressure_1: Quantity[np.float64]
    pressure_2: Quantity[np.float64]
    length: Quantity[np.float64]
    reference_area: Quantity[np.float64]
    wall_stiffness: Quantity[np.float64]
    external_pressure: Quantity[np.float64]
    resistance: Quantity[np.float64]
    inertance: Quantity[np.float64]
    number_of_cells: Quantity[np.float64]
    time: Time

    @property
    def dx(self) -> float:
        return float(self.length.current) / 3.0

    def _areas(self) -> list[Quantity[np.float64]]:
        return [self.area_01, self.area_02, self.area_03]

    def _flows(self) -> list[Quantity[np.float64]]:
        return [self.flow_00, self.flow_01, self.flow_02, self.flow_03]

    def _cell_pressure(self, area: Quantity[np.float64]) -> Any:
        area_mid = mid_point(area)
        return (
            self.external_pressure.current
            + self.wall_stiffness.current
            * (np.sqrt(area_mid) - np.sqrt(self.reference_area.current))
        )

    def _cell_pressures(self) -> np.ndarray:
        return np.array([self._cell_pressure(area) for area in self._areas()])

    def _dpressure_darea(self, area: Quantity[np.float64]) -> Any:
        return self.wall_stiffness.current / (4.0 * np.sqrt(mid_point(area)))

    def _area_basis(self, index: int, value: float) -> np.ndarray:
        result = np.zeros(3)
        result[index] = value
        return result

    def _flow_basis(self, index: int, value: float) -> np.ndarray:
        result = np.zeros(4)
        result[index] = value
        return result

    @declares_internal_equation(AREA_IDS[0], starting_index=0)
    @declares_internal_equation(AREA_IDS[1], starting_index=1)
    @declares_internal_equation(AREA_IDS[2], starting_index=2)
    def area_residual(self) -> np.ndarray:
        flows = self._flows()
        residual = []
        for index, area in enumerate(self._areas()):
            storage = diff(area) * self.time.inv_dt
            transport = (mid_point(flows[index + 1]) - mid_point(flows[index])) / self.dx
            residual.append(storage + transport)
        return np.array(residual)

    @area_residual.partial_derivative(AREA_IDS[0])
    def area_residual_darea_01(self) -> np.ndarray:
        return self._area_basis(0, self.time.inv_dt)

    @area_residual.partial_derivative(AREA_IDS[1])
    def area_residual_darea_02(self) -> np.ndarray:
        return self._area_basis(1, self.time.inv_dt)

    @area_residual.partial_derivative(AREA_IDS[2])
    def area_residual_darea_03(self) -> np.ndarray:
        return self._area_basis(2, self.time.inv_dt)

    @area_residual.partial_derivative(FLOW_IDS[0])
    def area_residual_dflow_00(self) -> np.ndarray:
        return self._area_basis(0, -0.5 / self.dx)

    @area_residual.partial_derivative(FLOW_IDS[1])
    def area_residual_dflow_01(self) -> np.ndarray:
        return np.array([0.5 / self.dx, -0.5 / self.dx, 0.0])

    @area_residual.partial_derivative(FLOW_IDS[2])
    def area_residual_dflow_02(self) -> np.ndarray:
        return np.array([0.0, 0.5 / self.dx, -0.5 / self.dx])

    @area_residual.partial_derivative(FLOW_IDS[3])
    def area_residual_dflow_03(self) -> np.ndarray:
        return self._area_basis(2, 0.5 / self.dx)

    @declares_internal_equation(FLOW_IDS[0], starting_index=0)
    @declares_internal_equation(FLOW_IDS[1], starting_index=1)
    @declares_internal_equation(FLOW_IDS[2], starting_index=2)
    @declares_internal_equation(FLOW_IDS[3], starting_index=3)
    def flow_residual(self) -> np.ndarray:
        cell_pressures = self._cell_pressures()
        face_left = [
            mid_point(self.pressure_1),
            cell_pressures[0],
            cell_pressures[1],
            cell_pressures[2],
        ]
        face_right = [
            cell_pressures[0],
            cell_pressures[1],
            cell_pressures[2],
            mid_point(self.pressure_2),
        ]
        residual = []
        for index, flow in enumerate(self._flows()):
            residual.append(
                self.inertance.current * self.time.inv_dt * diff(flow)
                + self.resistance.current * mid_point(flow)
                - face_left[index]
                + face_right[index]
            )
        return np.array(residual)

    @flow_residual.partial_derivative(FLOW_IDS[0])
    def flow_residual_dflow_00(self) -> np.ndarray:
        return self._flow_basis(
            0,
            self.inertance.current * self.time.inv_dt
            + 0.5 * self.resistance.current,
        )

    @flow_residual.partial_derivative(FLOW_IDS[1])
    def flow_residual_dflow_01(self) -> np.ndarray:
        return self._flow_basis(
            1,
            self.inertance.current * self.time.inv_dt
            + 0.5 * self.resistance.current,
        )

    @flow_residual.partial_derivative(FLOW_IDS[2])
    def flow_residual_dflow_02(self) -> np.ndarray:
        return self._flow_basis(
            2,
            self.inertance.current * self.time.inv_dt
            + 0.5 * self.resistance.current,
        )

    @flow_residual.partial_derivative(FLOW_IDS[3])
    def flow_residual_dflow_03(self) -> np.ndarray:
        return self._flow_basis(
            3,
            self.inertance.current * self.time.inv_dt
            + 0.5 * self.resistance.current,
        )

    @flow_residual.partial_derivative(AREA_IDS[0])
    def flow_residual_darea_01(self) -> np.ndarray:
        dpressure = self._dpressure_darea(self.area_01)
        return np.array([dpressure, -dpressure, 0.0, 0.0])

    @flow_residual.partial_derivative(AREA_IDS[1])
    def flow_residual_darea_02(self) -> np.ndarray:
        dpressure = self._dpressure_darea(self.area_02)
        return np.array([0.0, dpressure, -dpressure, 0.0])

    @flow_residual.partial_derivative(AREA_IDS[2])
    def flow_residual_darea_03(self) -> np.ndarray:
        dpressure = self._dpressure_darea(self.area_03)
        return np.array([0.0, 0.0, dpressure, -dpressure])

    @flow_residual.partial_derivative(PRESSURE_1_ID)
    def flow_residual_dpressure_1(self) -> np.ndarray:
        return np.array([-0.5, 0.0, 0.0, 0.0])

    @flow_residual.partial_derivative(PRESSURE_2_ID)
    def flow_residual_dpressure_2(self) -> np.ndarray:
        return np.array([0.0, 0.0, 0.0, 0.5])

    @declares_flux(1, PRESSURE_1_ID)
    def flux_1(self) -> Any:
        return -mid_point(self.flow_00)

    @flux_1.partial_derivative(FLOW_IDS[0])
    def flux_1_dflow_00(self) -> float:
        return -0.5

    @declares_flux(2, PRESSURE_2_ID)
    def flux_2(self) -> Any:
        return mid_point(self.flow_03)

    @flux_2.partial_derivative(FLOW_IDS[3])
    def flux_2_dflow_03(self) -> float:
        return 0.5

    @declares_saved_quantity(CELL_PRESSURE_ID, size=3)
    def cell_pressure(self) -> np.ndarray:
        return self._cell_pressures()

    @declares_saved_quantity(MIN_AREA_ID)
    def min_area(self) -> Any:
        return np.min([area.current for area in self._areas()])

    @declares_saved_quantity(MAX_AREA_ID)
    def max_area(self) -> Any:
        return np.max([area.current for area in self._areas()])
