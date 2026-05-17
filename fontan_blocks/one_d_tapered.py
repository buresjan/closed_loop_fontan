from dataclasses import dataclass
from typing import Any

import numpy as np

from physioblocks.computing import Block, Quantity, mid_point
from physioblocks.computing.models import (
    declares_flux,
    declares_internal_equation,
    declares_saved_quantity,
)
from physioblocks.registers import register_type
from physioblocks.simulation import Time

from .one_d_wall_laws import sqrt_pressure_from_area

FIXED_6CELL_TAPERED_1D_LOG_AREA_VESSEL_BLOCK_TYPE_ID = (
    "fixed_6cell_tapered_1d_log_area_vessel_block"
)

NUMBER_OF_CELLS = 6
LOG_AREA_IDS = tuple(f"log_area_{idx:02d}" for idx in range(1, NUMBER_OF_CELLS + 1))
AREA_IDS = tuple(f"area_{idx:02d}" for idx in range(1, NUMBER_OF_CELLS + 1))
FLOW_IDS = tuple(f"flow_{idx:02d}" for idx in range(NUMBER_OF_CELLS + 1))
CELL_PRESSURE_ID = "cell_pressure"
CELL_AREA_ID = "cell_area"
FACE_FLOW_ID = "face_flow"
STORED_VOLUME_ID = "stored_volume"
MIN_AREA_ID = "min_area"
NEGATIVE_AREA_COUNT_ID = "negative_area_count"
PRESSURE_1_ID = "pressure_1"
PRESSURE_2_ID = "pressure_2"


def _as_array(values: Any, name: str, size: int) -> np.ndarray:
    result = np.asarray(values, dtype=float)
    if result.shape != (size,):
        raise ValueError(f"{name} must have shape ({size},)")
    return result


def _face_average(values: np.ndarray) -> np.ndarray:
    faces = np.empty(values.size + 1, dtype=float)
    faces[0] = values[0]
    faces[-1] = values[-1]
    faces[1:-1] = 0.5 * (values[:-1] + values[1:])
    return faces


def _pressure_gradient(
    inlet_pressure: float,
    cell_pressure: np.ndarray,
    outlet_pressure: float,
    cell_lengths: np.ndarray,
) -> np.ndarray:
    gradient = np.empty(cell_pressure.size + 1, dtype=float)
    gradient[0] = (cell_pressure[0] - inlet_pressure) / (0.5 * cell_lengths[0])
    gradient[-1] = (outlet_pressure - cell_pressure[-1]) / (0.5 * cell_lengths[-1])
    gradient[1:-1] = (cell_pressure[1:] - cell_pressure[:-1]) / (
        0.5 * (cell_lengths[:-1] + cell_lengths[1:])
    )
    return gradient


def _face_gradient(face_values: np.ndarray, cell_lengths: np.ndarray) -> np.ndarray:
    positions = np.concatenate([[0.0], np.cumsum(cell_lengths)])
    gradient = np.empty_like(face_values)
    gradient[0] = (face_values[1] - face_values[0]) / (positions[1] - positions[0])
    gradient[-1] = (face_values[-1] - face_values[-2]) / (
        positions[-1] - positions[-2]
    )
    gradient[1:-1] = (face_values[2:] - face_values[:-2]) / (
        positions[2:] - positions[:-2]
    )
    return gradient


@dataclass(frozen=True)
class TaperedOneDVesselParameters:
    cell_lengths: np.ndarray
    reference_areas: np.ndarray
    wall_stiffnesses: np.ndarray
    friction_coefficients: np.ndarray
    external_pressure: float = 0.0
    density: float = 1060.0
    momentum_correction: float = 1.0

    def __post_init__(self) -> None:
        for name in [
            "cell_lengths",
            "reference_areas",
            "wall_stiffnesses",
            "friction_coefficients",
        ]:
            value = _as_array(getattr(self, name), name, NUMBER_OF_CELLS)
            if np.any(value <= 0.0):
                raise ValueError(f"{name} must be positive")
            object.__setattr__(self, name, value)
        if self.density <= 0.0:
            raise ValueError("density must be positive")
        if self.momentum_correction <= 0.0:
            raise ValueError("momentum_correction must be positive")

    @property
    def length(self) -> float:
        return float(np.sum(self.cell_lengths))


@dataclass(frozen=True)
class TaperedOneDVesselResidual:
    area: np.ndarray
    flow: np.ndarray

    def as_vector(self) -> np.ndarray:
        return np.concatenate([self.area, self.flow])


@dataclass(frozen=True)
class TaperedOneDVesselJacobian:
    darea_dlog_area: np.ndarray
    darea_dflow: np.ndarray
    dflow_dlog_area: np.ndarray
    dflow_dflow: np.ndarray
    dflow_dpressure_1: np.ndarray
    dflow_dpressure_2: np.ndarray


def tapered_vessel_residual(
    current_log_area: Any,
    new_log_area: Any,
    current_flow: Any,
    new_flow: Any,
    current_pressure_1: float,
    new_pressure_1: float,
    current_pressure_2: float,
    new_pressure_2: float,
    dt: float,
    parameters: TaperedOneDVesselParameters,
) -> TaperedOneDVesselResidual:
    if dt <= 0.0:
        raise ValueError("dt must be positive")
    current_log_area = _as_array(current_log_area, "current_log_area", NUMBER_OF_CELLS)
    new_log_area = _as_array(new_log_area, "new_log_area", NUMBER_OF_CELLS)
    current_flow = _as_array(current_flow, "current_flow", NUMBER_OF_CELLS + 1)
    new_flow = _as_array(new_flow, "new_flow", NUMBER_OF_CELLS + 1)

    current_area = np.exp(current_log_area)
    new_area = np.exp(new_log_area)
    area_mid = 0.5 * (current_area + new_area)
    flow_mid = 0.5 * (current_flow + new_flow)
    pressure_1_mid = 0.5 * (current_pressure_1 + new_pressure_1)
    pressure_2_mid = 0.5 * (current_pressure_2 + new_pressure_2)

    area_residual = (new_area - current_area) / dt
    area_residual += (flow_mid[1:] - flow_mid[:-1]) / parameters.cell_lengths

    pressure = sqrt_pressure_from_area(
        area_mid,
        parameters.reference_areas,
        parameters.wall_stiffnesses,
        parameters.external_pressure,
    )
    face_area = _face_average(area_mid)
    pressure_gradient = _pressure_gradient(
        pressure_1_mid,
        pressure,
        pressure_2_mid,
        parameters.cell_lengths,
    )
    convective_flux = parameters.momentum_correction * flow_mid * flow_mid / face_area
    convective_gradient = _face_gradient(convective_flux, parameters.cell_lengths)
    face_friction = _face_average(parameters.friction_coefficients)

    flow_residual = (new_flow - current_flow) / dt
    flow_residual += convective_gradient
    flow_residual += face_area * pressure_gradient / parameters.density
    flow_residual += face_friction * flow_mid / face_area
    return TaperedOneDVesselResidual(area=area_residual, flow=flow_residual)


def tapered_vessel_jacobian_new(
    current_log_area: Any,
    new_log_area: Any,
    current_flow: Any,
    new_flow: Any,
    current_pressure_1: float,
    new_pressure_1: float,
    current_pressure_2: float,
    new_pressure_2: float,
    dt: float,
    parameters: TaperedOneDVesselParameters,
) -> TaperedOneDVesselJacobian:
    """Numerical Jacobian with respect to new-time unknowns.

    The fixed six-cell tapered block is used only for the coupled LPA composite
    path. A numerical local Jacobian keeps the generated block compact while
    preserving the exact residual used by the solver.
    """

    base_log_area = _as_array(new_log_area, "new_log_area", NUMBER_OF_CELLS)
    base_flow = _as_array(new_flow, "new_flow", NUMBER_OF_CELLS + 1)
    base = np.concatenate([base_log_area, base_flow, [new_pressure_1, new_pressure_2]])
    eps = np.concatenate(
        [
            np.full(NUMBER_OF_CELLS, 1.0e-6),
            np.maximum(np.abs(base_flow) * 1.0e-5, 1.0e-10),
            np.array([1.0e-3, 1.0e-3]),
        ]
    )
    matrix = np.empty((2 * NUMBER_OF_CELLS + 1, base.size), dtype=float)

    for column in range(base.size):
        plus = base.copy()
        minus = base.copy()
        plus[column] += eps[column]
        minus[column] -= eps[column]
        plus_residual = tapered_vessel_residual(
            current_log_area,
            plus[:NUMBER_OF_CELLS],
            current_flow,
            plus[NUMBER_OF_CELLS : 2 * NUMBER_OF_CELLS + 1],
            current_pressure_1,
            plus[-2],
            current_pressure_2,
            plus[-1],
            dt,
            parameters,
        ).as_vector()
        minus_residual = tapered_vessel_residual(
            current_log_area,
            minus[:NUMBER_OF_CELLS],
            current_flow,
            minus[NUMBER_OF_CELLS : 2 * NUMBER_OF_CELLS + 1],
            current_pressure_1,
            minus[-2],
            current_pressure_2,
            minus[-1],
            dt,
            parameters,
        ).as_vector()
        matrix[:, column] = (plus_residual - minus_residual) / (2.0 * eps[column])

    return TaperedOneDVesselJacobian(
        darea_dlog_area=matrix[:NUMBER_OF_CELLS, :NUMBER_OF_CELLS],
        darea_dflow=matrix[:NUMBER_OF_CELLS, NUMBER_OF_CELLS : 2 * NUMBER_OF_CELLS + 1],
        dflow_dlog_area=matrix[NUMBER_OF_CELLS:, :NUMBER_OF_CELLS],
        dflow_dflow=matrix[
            NUMBER_OF_CELLS:, NUMBER_OF_CELLS : 2 * NUMBER_OF_CELLS + 1
        ],
        dflow_dpressure_1=matrix[NUMBER_OF_CELLS:, -2],
        dflow_dpressure_2=matrix[NUMBER_OF_CELLS:, -1],
    )


@register_type(FIXED_6CELL_TAPERED_1D_LOG_AREA_VESSEL_BLOCK_TYPE_ID)
@dataclass
class Fixed6CellTaperedOneDLogAreaVesselBlock(Block):
    log_area_01: Quantity[np.float64]
    log_area_02: Quantity[np.float64]
    log_area_03: Quantity[np.float64]
    log_area_04: Quantity[np.float64]
    log_area_05: Quantity[np.float64]
    log_area_06: Quantity[np.float64]
    flow_00: Quantity[np.float64]
    flow_01: Quantity[np.float64]
    flow_02: Quantity[np.float64]
    flow_03: Quantity[np.float64]
    flow_04: Quantity[np.float64]
    flow_05: Quantity[np.float64]
    flow_06: Quantity[np.float64]
    pressure_1: Quantity[np.float64]
    pressure_2: Quantity[np.float64]
    cell_length_01: Quantity[np.float64]
    cell_length_02: Quantity[np.float64]
    cell_length_03: Quantity[np.float64]
    cell_length_04: Quantity[np.float64]
    cell_length_05: Quantity[np.float64]
    cell_length_06: Quantity[np.float64]
    reference_area_01: Quantity[np.float64]
    reference_area_02: Quantity[np.float64]
    reference_area_03: Quantity[np.float64]
    reference_area_04: Quantity[np.float64]
    reference_area_05: Quantity[np.float64]
    reference_area_06: Quantity[np.float64]
    wall_stiffness_01: Quantity[np.float64]
    wall_stiffness_02: Quantity[np.float64]
    wall_stiffness_03: Quantity[np.float64]
    wall_stiffness_04: Quantity[np.float64]
    wall_stiffness_05: Quantity[np.float64]
    wall_stiffness_06: Quantity[np.float64]
    friction_coefficient_01: Quantity[np.float64]
    friction_coefficient_02: Quantity[np.float64]
    friction_coefficient_03: Quantity[np.float64]
    friction_coefficient_04: Quantity[np.float64]
    friction_coefficient_05: Quantity[np.float64]
    friction_coefficient_06: Quantity[np.float64]
    external_pressure: Quantity[np.float64]
    density: Quantity[np.float64]
    momentum_correction: Quantity[np.float64]
    time: Time

    def _log_areas(self) -> list[Quantity[np.float64]]:
        return [
            self.log_area_01,
            self.log_area_02,
            self.log_area_03,
            self.log_area_04,
            self.log_area_05,
            self.log_area_06,
        ]

    def _flows(self) -> list[Quantity[np.float64]]:
        return [
            self.flow_00,
            self.flow_01,
            self.flow_02,
            self.flow_03,
            self.flow_04,
            self.flow_05,
            self.flow_06,
        ]

    def _quantity_array(self, prefix: str) -> np.ndarray:
        return np.array(
            [getattr(self, f"{prefix}_{idx:02d}").current for idx in range(1, 7)],
            dtype=float,
        )

    def _parameters(self) -> TaperedOneDVesselParameters:
        return TaperedOneDVesselParameters(
            cell_lengths=self._quantity_array("cell_length"),
            reference_areas=self._quantity_array("reference_area"),
            wall_stiffnesses=self._quantity_array("wall_stiffness"),
            friction_coefficients=self._quantity_array("friction_coefficient"),
            external_pressure=float(self.external_pressure.current),
            density=float(self.density.current),
            momentum_correction=float(self.momentum_correction.current),
        )

    def _current_log_areas(self) -> np.ndarray:
        return np.array([area.current for area in self._log_areas()], dtype=float)

    def _new_log_areas(self) -> np.ndarray:
        return np.array([area.new for area in self._log_areas()], dtype=float)

    def _mid_areas(self) -> np.ndarray:
        return 0.5 * (np.exp(self._current_log_areas()) + np.exp(self._new_log_areas()))

    def _current_flows(self) -> np.ndarray:
        return np.array([flow.current for flow in self._flows()], dtype=float)

    def _new_flows(self) -> np.ndarray:
        return np.array([flow.new for flow in self._flows()], dtype=float)

    def _mid_flows(self) -> np.ndarray:
        return np.array([mid_point(flow) for flow in self._flows()], dtype=float)

    def _residual(self) -> TaperedOneDVesselResidual:
        return tapered_vessel_residual(
            self._current_log_areas(),
            self._new_log_areas(),
            self._current_flows(),
            self._new_flows(),
            self.pressure_1.current,
            self.pressure_1.new,
            self.pressure_2.current,
            self.pressure_2.new,
            self.time.dt,
            self._parameters(),
        )

    def _jacobian(self) -> TaperedOneDVesselJacobian:
        return tapered_vessel_jacobian_new(
            self._current_log_areas(),
            self._new_log_areas(),
            self._current_flows(),
            self._new_flows(),
            self.pressure_1.current,
            self.pressure_1.new,
            self.pressure_2.current,
            self.pressure_2.new,
            self.time.dt,
            self._parameters(),
        )

    @declares_internal_equation(LOG_AREA_IDS[0], starting_index=0)
    @declares_internal_equation(LOG_AREA_IDS[1], starting_index=1)
    @declares_internal_equation(LOG_AREA_IDS[2], starting_index=2)
    @declares_internal_equation(LOG_AREA_IDS[3], starting_index=3)
    @declares_internal_equation(LOG_AREA_IDS[4], starting_index=4)
    @declares_internal_equation(LOG_AREA_IDS[5], starting_index=5)
    def area_residual(self) -> np.ndarray:
        return self._residual().area

    @area_residual.partial_derivative(LOG_AREA_IDS[0])
    def area_residual_dlog_area_01(self) -> np.ndarray:
        return self._jacobian().darea_dlog_area[:, 0]

    @area_residual.partial_derivative(LOG_AREA_IDS[1])
    def area_residual_dlog_area_02(self) -> np.ndarray:
        return self._jacobian().darea_dlog_area[:, 1]

    @area_residual.partial_derivative(LOG_AREA_IDS[2])
    def area_residual_dlog_area_03(self) -> np.ndarray:
        return self._jacobian().darea_dlog_area[:, 2]

    @area_residual.partial_derivative(LOG_AREA_IDS[3])
    def area_residual_dlog_area_04(self) -> np.ndarray:
        return self._jacobian().darea_dlog_area[:, 3]

    @area_residual.partial_derivative(LOG_AREA_IDS[4])
    def area_residual_dlog_area_05(self) -> np.ndarray:
        return self._jacobian().darea_dlog_area[:, 4]

    @area_residual.partial_derivative(LOG_AREA_IDS[5])
    def area_residual_dlog_area_06(self) -> np.ndarray:
        return self._jacobian().darea_dlog_area[:, 5]

    @area_residual.partial_derivative(FLOW_IDS[0])
    def area_residual_dflow_00(self) -> np.ndarray:
        return self._jacobian().darea_dflow[:, 0]

    @area_residual.partial_derivative(FLOW_IDS[1])
    def area_residual_dflow_01(self) -> np.ndarray:
        return self._jacobian().darea_dflow[:, 1]

    @area_residual.partial_derivative(FLOW_IDS[2])
    def area_residual_dflow_02(self) -> np.ndarray:
        return self._jacobian().darea_dflow[:, 2]

    @area_residual.partial_derivative(FLOW_IDS[3])
    def area_residual_dflow_03(self) -> np.ndarray:
        return self._jacobian().darea_dflow[:, 3]

    @area_residual.partial_derivative(FLOW_IDS[4])
    def area_residual_dflow_04(self) -> np.ndarray:
        return self._jacobian().darea_dflow[:, 4]

    @area_residual.partial_derivative(FLOW_IDS[5])
    def area_residual_dflow_05(self) -> np.ndarray:
        return self._jacobian().darea_dflow[:, 5]

    @area_residual.partial_derivative(FLOW_IDS[6])
    def area_residual_dflow_06(self) -> np.ndarray:
        return self._jacobian().darea_dflow[:, 6]

    @declares_internal_equation(FLOW_IDS[0], starting_index=0)
    @declares_internal_equation(FLOW_IDS[1], starting_index=1)
    @declares_internal_equation(FLOW_IDS[2], starting_index=2)
    @declares_internal_equation(FLOW_IDS[3], starting_index=3)
    @declares_internal_equation(FLOW_IDS[4], starting_index=4)
    @declares_internal_equation(FLOW_IDS[5], starting_index=5)
    @declares_internal_equation(FLOW_IDS[6], starting_index=6)
    def flow_residual(self) -> np.ndarray:
        return self._residual().flow

    @flow_residual.partial_derivative(LOG_AREA_IDS[0])
    def flow_residual_dlog_area_01(self) -> np.ndarray:
        return self._jacobian().dflow_dlog_area[:, 0]

    @flow_residual.partial_derivative(LOG_AREA_IDS[1])
    def flow_residual_dlog_area_02(self) -> np.ndarray:
        return self._jacobian().dflow_dlog_area[:, 1]

    @flow_residual.partial_derivative(LOG_AREA_IDS[2])
    def flow_residual_dlog_area_03(self) -> np.ndarray:
        return self._jacobian().dflow_dlog_area[:, 2]

    @flow_residual.partial_derivative(LOG_AREA_IDS[3])
    def flow_residual_dlog_area_04(self) -> np.ndarray:
        return self._jacobian().dflow_dlog_area[:, 3]

    @flow_residual.partial_derivative(LOG_AREA_IDS[4])
    def flow_residual_dlog_area_05(self) -> np.ndarray:
        return self._jacobian().dflow_dlog_area[:, 4]

    @flow_residual.partial_derivative(LOG_AREA_IDS[5])
    def flow_residual_dlog_area_06(self) -> np.ndarray:
        return self._jacobian().dflow_dlog_area[:, 5]

    @flow_residual.partial_derivative(FLOW_IDS[0])
    def flow_residual_dflow_00(self) -> np.ndarray:
        return self._jacobian().dflow_dflow[:, 0]

    @flow_residual.partial_derivative(FLOW_IDS[1])
    def flow_residual_dflow_01(self) -> np.ndarray:
        return self._jacobian().dflow_dflow[:, 1]

    @flow_residual.partial_derivative(FLOW_IDS[2])
    def flow_residual_dflow_02(self) -> np.ndarray:
        return self._jacobian().dflow_dflow[:, 2]

    @flow_residual.partial_derivative(FLOW_IDS[3])
    def flow_residual_dflow_03(self) -> np.ndarray:
        return self._jacobian().dflow_dflow[:, 3]

    @flow_residual.partial_derivative(FLOW_IDS[4])
    def flow_residual_dflow_04(self) -> np.ndarray:
        return self._jacobian().dflow_dflow[:, 4]

    @flow_residual.partial_derivative(FLOW_IDS[5])
    def flow_residual_dflow_05(self) -> np.ndarray:
        return self._jacobian().dflow_dflow[:, 5]

    @flow_residual.partial_derivative(FLOW_IDS[6])
    def flow_residual_dflow_06(self) -> np.ndarray:
        return self._jacobian().dflow_dflow[:, 6]

    @flow_residual.partial_derivative(PRESSURE_1_ID)
    def flow_residual_dpressure_1(self) -> np.ndarray:
        return self._jacobian().dflow_dpressure_1

    @flow_residual.partial_derivative(PRESSURE_2_ID)
    def flow_residual_dpressure_2(self) -> np.ndarray:
        return self._jacobian().dflow_dpressure_2

    @declares_flux(1, PRESSURE_1_ID)
    def flux_1(self) -> Any:
        return -mid_point(self.flow_00)

    @flux_1.partial_derivative(FLOW_IDS[0])
    def flux_1_dflow_00(self) -> float:
        return -0.5

    @declares_flux(2, PRESSURE_2_ID)
    def flux_2(self) -> Any:
        return mid_point(self.flow_06)

    @flux_2.partial_derivative(FLOW_IDS[6])
    def flux_2_dflow_06(self) -> float:
        return 0.5

    @declares_saved_quantity(AREA_IDS[0])
    def area_01(self) -> float:
        return float(self._mid_areas()[0])

    @declares_saved_quantity(AREA_IDS[1])
    def area_02(self) -> float:
        return float(self._mid_areas()[1])

    @declares_saved_quantity(AREA_IDS[2])
    def area_03(self) -> float:
        return float(self._mid_areas()[2])

    @declares_saved_quantity(AREA_IDS[3])
    def area_04(self) -> float:
        return float(self._mid_areas()[3])

    @declares_saved_quantity(AREA_IDS[4])
    def area_05(self) -> float:
        return float(self._mid_areas()[4])

    @declares_saved_quantity(AREA_IDS[5])
    def area_06(self) -> float:
        return float(self._mid_areas()[5])

    @declares_saved_quantity(CELL_PRESSURE_ID, size=NUMBER_OF_CELLS)
    def cell_pressure(self) -> np.ndarray:
        return sqrt_pressure_from_area(
            self._mid_areas(),
            self._parameters().reference_areas,
            self._parameters().wall_stiffnesses,
            self._parameters().external_pressure,
        )

    @declares_saved_quantity(CELL_AREA_ID, size=NUMBER_OF_CELLS)
    def cell_area(self) -> np.ndarray:
        return self._mid_areas()

    @declares_saved_quantity(FACE_FLOW_ID, size=NUMBER_OF_CELLS + 1)
    def face_flow(self) -> np.ndarray:
        return self._mid_flows()

    @declares_saved_quantity(STORED_VOLUME_ID)
    def stored_volume(self) -> float:
        return float(np.sum(self._mid_areas() * self._parameters().cell_lengths))

    @declares_saved_quantity(MIN_AREA_ID)
    def min_area(self) -> float:
        return float(np.min(self._mid_areas()))

    @declares_saved_quantity(NEGATIVE_AREA_COUNT_ID)
    def negative_area_count(self) -> int:
        return int(np.count_nonzero(self._mid_areas() <= 0.0))
