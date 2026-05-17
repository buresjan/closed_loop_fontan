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

from .one_d_geometry import staggered_face_average, stored_volume
from .one_d_junctions import (
    boundary_pressure_gradient,
    boundary_pressure_gradient_matrix,
)
from .one_d_wall_laws import (
    dpressure_darea,
    sqrt_pressure_from_area,
    wave_speed_from_area,
)

FIXED_3CELL_1D_VESSEL_BLOCK_TYPE_ID = "fixed_3cell_1d_vessel_block"
FIXED_3CELL_1D_LOG_AREA_VESSEL_BLOCK_TYPE_ID = (
    "fixed_3cell_1d_log_area_vessel_block"
)

AREA_IDS = ("area_01", "area_02", "area_03")
LOG_AREA_IDS = ("log_area_01", "log_area_02", "log_area_03")
FLOW_IDS = ("flow_00", "flow_01", "flow_02", "flow_03")
PRESSURE_1_ID = "pressure_1"
PRESSURE_2_ID = "pressure_2"
CELL_PRESSURE_ID = "cell_pressure"
CELL_AREA_ID = "cell_area"
FACE_FLOW_ID = "face_flow"
STORED_VOLUME_ID = "stored_volume"
MIN_AREA_ID = "min_area"
NEGATIVE_AREA_COUNT_ID = "negative_area_count"

NUMBER_OF_CELLS = 3


@dataclass(frozen=True)
class OneDVesselParameters:
    """Parameters for the local true 1-D vessel prototype."""

    length: float
    reference_area: float
    wall_stiffness: float
    external_pressure: float = 0.0
    density: float = 1060.0
    friction_coefficient: float = 0.0
    momentum_correction: float = 1.0

    def __post_init__(self) -> None:
        for name in [
            "length",
            "reference_area",
            "wall_stiffness",
            "density",
            "momentum_correction",
        ]:
            if getattr(self, name) <= 0.0:
                raise ValueError(f"{name} must be positive")
        if self.friction_coefficient < 0.0:
            raise ValueError("friction_coefficient must be non-negative")

    @property
    def dx(self) -> float:
        return self.length / NUMBER_OF_CELLS


@dataclass(frozen=True)
class OneDVesselResidual:
    area: np.ndarray
    flow: np.ndarray

    def as_vector(self) -> np.ndarray:
        return np.concatenate([self.area, self.flow])


@dataclass(frozen=True)
class OneDVesselJacobian:
    darea_darea: np.ndarray
    darea_dflow: np.ndarray
    dflow_darea: np.ndarray
    dflow_dflow: np.ndarray
    dflow_dpressure_1: np.ndarray
    dflow_dpressure_2: np.ndarray

    def as_matrix(self) -> np.ndarray:
        top = np.hstack([self.darea_darea, self.darea_dflow])
        bottom = np.hstack([self.dflow_darea, self.dflow_dflow])
        return np.vstack([top, bottom])


def _as_cells(values: Any, name: str) -> np.ndarray:
    result = np.asarray(values, dtype=float)
    if result.shape != (NUMBER_OF_CELLS,):
        raise ValueError(f"{name} must have shape ({NUMBER_OF_CELLS},)")
    return result


def _as_faces(values: Any, name: str) -> np.ndarray:
    result = np.asarray(values, dtype=float)
    if result.shape != (NUMBER_OF_CELLS + 1,):
        raise ValueError(f"{name} must have shape ({NUMBER_OF_CELLS + 1},)")
    return result


def face_area_matrix() -> np.ndarray:
    """Map three cell-centered values to four staggered face values."""

    return np.array(
        [
            [1.0, 0.0, 0.0],
            [0.5, 0.5, 0.0],
            [0.0, 0.5, 0.5],
            [0.0, 0.0, 1.0],
        ],
        dtype=float,
    )


def momentum_flux_gradient_matrix(dx: float) -> np.ndarray:
    """Differentiate face momentum fluxes on the staggered grid."""

    if dx <= 0.0:
        raise ValueError("dx must be positive")
    return np.array(
        [
            [-2.0 / dx, 2.0 / dx, 0.0, 0.0],
            [-0.5 / dx, 0.0, 0.5 / dx, 0.0],
            [0.0, -0.5 / dx, 0.0, 0.5 / dx],
            [0.0, 0.0, -2.0 / dx, 2.0 / dx],
        ],
        dtype=float,
    )


def cell_pressures(cell_area: Any, parameters: OneDVesselParameters) -> np.ndarray:
    return sqrt_pressure_from_area(
        _as_cells(cell_area, "cell_area"),
        parameters.reference_area,
        parameters.wall_stiffness,
        parameters.external_pressure,
    )


def face_areas(cell_area: Any) -> np.ndarray:
    return staggered_face_average(_as_cells(cell_area, "cell_area"))


def momentum_flux(
    face_flow: Any,
    face_area: Any,
    momentum_correction: float,
) -> np.ndarray:
    flows = _as_faces(face_flow, "face_flow")
    areas = _as_faces(face_area, "face_area")
    if np.any(areas <= 0.0):
        raise ValueError("face_area must be positive")
    return momentum_correction * flows * flows / areas


def linearized_characteristic_speeds(
    area: Any,
    flow: Any,
    parameters: OneDVesselParameters,
) -> tuple[np.ndarray, np.ndarray]:
    """Return u-c and u+c for the local nonlinear 1-D equations."""

    areas = np.asarray(area, dtype=float)
    flows = np.asarray(flow, dtype=float)
    if areas.shape != flows.shape:
        raise ValueError("area and flow must have the same shape")
    velocity = flows / areas
    wave_speed = wave_speed_from_area(
        areas,
        parameters.wall_stiffness,
        parameters.density,
    )
    return velocity - wave_speed, velocity + wave_speed


def negative_area_count(cell_area: Any) -> int:
    return int(np.count_nonzero(np.asarray(cell_area, dtype=float) <= 0.0))


def vessel_residual(
    current_area: Any,
    new_area: Any,
    current_flow: Any,
    new_flow: Any,
    current_pressure_1: float,
    new_pressure_1: float,
    current_pressure_2: float,
    new_pressure_2: float,
    dt: float,
    parameters: OneDVesselParameters,
) -> OneDVesselResidual:
    """Crank-Nicolson residual for a fixed 3-cell true 1-D vessel."""

    if dt <= 0.0:
        raise ValueError("dt must be positive")
    current_area = _as_cells(current_area, "current_area")
    new_area = _as_cells(new_area, "new_area")
    current_flow = _as_faces(current_flow, "current_flow")
    new_flow = _as_faces(new_flow, "new_flow")

    area_mid = 0.5 * (current_area + new_area)
    flow_mid = 0.5 * (current_flow + new_flow)
    pressure_1_mid = 0.5 * (current_pressure_1 + new_pressure_1)
    pressure_2_mid = 0.5 * (current_pressure_2 + new_pressure_2)

    dx = parameters.dx
    area_residual = (new_area - current_area) / dt
    area_residual += (flow_mid[1:] - flow_mid[:-1]) / dx

    pressure = cell_pressures(area_mid, parameters)
    pressure_gradient = boundary_pressure_gradient(
        pressure_1_mid,
        pressure,
        pressure_2_mid,
        dx,
    )
    face_area = face_areas(area_mid)
    convective_flux = momentum_flux(
        flow_mid,
        face_area,
        parameters.momentum_correction,
    )
    convective_gradient = momentum_flux_gradient_matrix(dx) @ convective_flux
    friction = parameters.friction_coefficient * flow_mid / face_area

    flow_residual = (new_flow - current_flow) / dt
    flow_residual += convective_gradient
    flow_residual += face_area * pressure_gradient / parameters.density
    flow_residual += friction

    return OneDVesselResidual(area=area_residual, flow=flow_residual)


def vessel_jacobian_new(
    current_area: Any,
    new_area: Any,
    current_flow: Any,
    new_flow: Any,
    current_pressure_1: float,
    new_pressure_1: float,
    current_pressure_2: float,
    new_pressure_2: float,
    dt: float,
    parameters: OneDVesselParameters,
) -> OneDVesselJacobian:
    """Jacobian of the residual with respect to new-time unknowns."""

    if dt <= 0.0:
        raise ValueError("dt must be positive")
    current_area = _as_cells(current_area, "current_area")
    new_area = _as_cells(new_area, "new_area")
    current_flow = _as_faces(current_flow, "current_flow")
    new_flow = _as_faces(new_flow, "new_flow")

    area_mid = 0.5 * (current_area + new_area)
    flow_mid = 0.5 * (current_flow + new_flow)
    pressure_1_mid = 0.5 * (current_pressure_1 + new_pressure_1)
    pressure_2_mid = 0.5 * (current_pressure_2 + new_pressure_2)

    dx = parameters.dx
    area_to_face = face_area_matrix()
    dface_dnew_area = 0.5 * area_to_face
    face_area = area_to_face @ area_mid
    pressure = cell_pressures(area_mid, parameters)
    pressure_gradient = boundary_pressure_gradient(
        pressure_1_mid,
        pressure,
        pressure_2_mid,
        dx,
    )

    darea_darea = np.eye(NUMBER_OF_CELLS) / dt
    darea_dflow = np.zeros((NUMBER_OF_CELLS, NUMBER_OF_CELLS + 1), dtype=float)
    for cell in range(NUMBER_OF_CELLS):
        darea_dflow[cell, cell] = -0.5 / dx
        darea_dflow[cell, cell + 1] = 0.5 / dx

    dflux_dnew_flow = np.diag(
        parameters.momentum_correction * flow_mid / face_area
    )
    dflux_dnew_area = (
        -parameters.momentum_correction
        * (flow_mid * flow_mid / (face_area * face_area))
    )[:, None] * dface_dnew_area
    flux_gradient = momentum_flux_gradient_matrix(dx)
    dconv_dnew_flow = flux_gradient @ dflux_dnew_flow
    dconv_dnew_area = flux_gradient @ dflux_dnew_area

    pressure_matrix = boundary_pressure_gradient_matrix(NUMBER_OF_CELLS, dx)
    dpressure_dnew_area = 0.5 * dpressure_darea(
        area_mid,
        parameters.wall_stiffness,
    )
    dgradient_dnew_area = pressure_matrix[:, 1:-1] @ np.diag(dpressure_dnew_area)

    dpressure_term_darea = (
        dface_dnew_area * pressure_gradient[:, None] / parameters.density
    )
    dpressure_term_darea += (
        face_area[:, None] * dgradient_dnew_area / parameters.density
    )

    dpressure_1 = np.zeros(NUMBER_OF_CELLS + 1, dtype=float)
    dpressure_1[0] = -face_area[0] / (parameters.density * dx)
    dpressure_2 = np.zeros(NUMBER_OF_CELLS + 1, dtype=float)
    dpressure_2[-1] = face_area[-1] / (parameters.density * dx)

    dfriction_dflow = np.diag(
        0.5 * parameters.friction_coefficient / face_area
    )
    dfriction_darea = (
        -parameters.friction_coefficient * flow_mid / (face_area * face_area)
    )[:, None] * dface_dnew_area

    dflow_dflow = np.eye(NUMBER_OF_CELLS + 1) / dt
    dflow_dflow += dconv_dnew_flow
    dflow_dflow += dfriction_dflow
    dflow_darea = dconv_dnew_area + dpressure_term_darea + dfriction_darea

    return OneDVesselJacobian(
        darea_darea=darea_darea,
        darea_dflow=darea_dflow,
        dflow_darea=dflow_darea,
        dflow_dflow=dflow_dflow,
        dflow_dpressure_1=dpressure_1,
        dflow_dpressure_2=dpressure_2,
    )


@register_type(FIXED_3CELL_1D_VESSEL_BLOCK_TYPE_ID)
@dataclass
class Fixed3CellOneDVesselBlock(Block):
    """Fixed-size true 1-D straight vessel prototype.

    The block is intentionally limited to three cells for Task 010. It solves
    finite-volume mass conservation plus nonlinear 1-D momentum with a
    pressure-area wall law, then couples terminal face flows to PhysioBlocks
    pressure nodes.
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
    density: Quantity[np.float64]
    friction_coefficient: Quantity[np.float64]
    momentum_correction: Quantity[np.float64]
    time: Time

    @property
    def dx(self) -> float:
        return self._parameters().dx

    def _parameters(self) -> OneDVesselParameters:
        return OneDVesselParameters(
            length=float(self.length.current),
            reference_area=float(self.reference_area.current),
            wall_stiffness=float(self.wall_stiffness.current),
            external_pressure=float(self.external_pressure.current),
            density=float(self.density.current),
            friction_coefficient=float(self.friction_coefficient.current),
            momentum_correction=float(self.momentum_correction.current),
        )

    def _areas(self) -> list[Quantity[np.float64]]:
        return [self.area_01, self.area_02, self.area_03]

    def _flows(self) -> list[Quantity[np.float64]]:
        return [self.flow_00, self.flow_01, self.flow_02, self.flow_03]

    def _current_areas(self) -> np.ndarray:
        return np.array([area.current for area in self._areas()], dtype=float)

    def _new_areas(self) -> np.ndarray:
        return np.array([area.new for area in self._areas()], dtype=float)

    def _mid_areas(self) -> np.ndarray:
        return np.array([mid_point(area) for area in self._areas()], dtype=float)

    def _current_flows(self) -> np.ndarray:
        return np.array([flow.current for flow in self._flows()], dtype=float)

    def _new_flows(self) -> np.ndarray:
        return np.array([flow.new for flow in self._flows()], dtype=float)

    def _mid_flows(self) -> np.ndarray:
        return np.array([mid_point(flow) for flow in self._flows()], dtype=float)

    def _residual(self) -> OneDVesselResidual:
        return vessel_residual(
            self._current_areas(),
            self._new_areas(),
            self._current_flows(),
            self._new_flows(),
            self.pressure_1.current,
            self.pressure_1.new,
            self.pressure_2.current,
            self.pressure_2.new,
            self.time.dt,
            self._parameters(),
        )

    def _jacobian(self) -> OneDVesselJacobian:
        return vessel_jacobian_new(
            self._current_areas(),
            self._new_areas(),
            self._current_flows(),
            self._new_flows(),
            self.pressure_1.current,
            self.pressure_1.new,
            self.pressure_2.current,
            self.pressure_2.new,
            self.time.dt,
            self._parameters(),
        )

    @declares_internal_equation(AREA_IDS[0], starting_index=0)
    @declares_internal_equation(AREA_IDS[1], starting_index=1)
    @declares_internal_equation(AREA_IDS[2], starting_index=2)
    def area_residual(self) -> np.ndarray:
        return self._residual().area

    @area_residual.partial_derivative(AREA_IDS[0])
    def area_residual_darea_01(self) -> np.ndarray:
        return self._jacobian().darea_darea[:, 0]

    @area_residual.partial_derivative(AREA_IDS[1])
    def area_residual_darea_02(self) -> np.ndarray:
        return self._jacobian().darea_darea[:, 1]

    @area_residual.partial_derivative(AREA_IDS[2])
    def area_residual_darea_03(self) -> np.ndarray:
        return self._jacobian().darea_darea[:, 2]

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

    @declares_internal_equation(FLOW_IDS[0], starting_index=0)
    @declares_internal_equation(FLOW_IDS[1], starting_index=1)
    @declares_internal_equation(FLOW_IDS[2], starting_index=2)
    @declares_internal_equation(FLOW_IDS[3], starting_index=3)
    def flow_residual(self) -> np.ndarray:
        return self._residual().flow

    @flow_residual.partial_derivative(AREA_IDS[0])
    def flow_residual_darea_01(self) -> np.ndarray:
        return self._jacobian().dflow_darea[:, 0]

    @flow_residual.partial_derivative(AREA_IDS[1])
    def flow_residual_darea_02(self) -> np.ndarray:
        return self._jacobian().dflow_darea[:, 1]

    @flow_residual.partial_derivative(AREA_IDS[2])
    def flow_residual_darea_03(self) -> np.ndarray:
        return self._jacobian().dflow_darea[:, 2]

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
        return mid_point(self.flow_03)

    @flux_2.partial_derivative(FLOW_IDS[3])
    def flux_2_dflow_03(self) -> float:
        return 0.5

    @declares_saved_quantity(CELL_PRESSURE_ID, size=NUMBER_OF_CELLS)
    def cell_pressure(self) -> np.ndarray:
        return cell_pressures(self._mid_areas(), self._parameters())

    @declares_saved_quantity(CELL_AREA_ID, size=NUMBER_OF_CELLS)
    def cell_area(self) -> np.ndarray:
        return self._mid_areas()

    @declares_saved_quantity(FACE_FLOW_ID, size=NUMBER_OF_CELLS + 1)
    def face_flow(self) -> np.ndarray:
        return self._mid_flows()

    @declares_saved_quantity(STORED_VOLUME_ID)
    def stored_volume(self) -> float:
        return stored_volume(self._mid_areas(), float(self.length.current))

    @declares_saved_quantity(MIN_AREA_ID)
    def min_area(self) -> float:
        return float(np.min(self._mid_areas()))

    @declares_saved_quantity(NEGATIVE_AREA_COUNT_ID)
    def negative_area_count(self) -> int:
        return negative_area_count(self._mid_areas())


@register_type(FIXED_3CELL_1D_LOG_AREA_VESSEL_BLOCK_TYPE_ID)
@dataclass
class Fixed3CellOneDLogAreaVesselBlock(Block):
    """Fixed-size true 1-D vessel with log-area state variables.

    This block solves the same finite-volume equations as
    ``Fixed3CellOneDVesselBlock`` but stores ``log(A)`` as the nonlinear state.
    The transformation keeps the executable coupled model inside the positive
    vessel-area domain during Newton iterations.
    """

    log_area_01: Quantity[np.float64]
    log_area_02: Quantity[np.float64]
    log_area_03: Quantity[np.float64]
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
    density: Quantity[np.float64]
    friction_coefficient: Quantity[np.float64]
    momentum_correction: Quantity[np.float64]
    time: Time

    @property
    def dx(self) -> float:
        return self._parameters().dx

    def _parameters(self) -> OneDVesselParameters:
        return OneDVesselParameters(
            length=float(self.length.current),
            reference_area=float(self.reference_area.current),
            wall_stiffness=float(self.wall_stiffness.current),
            external_pressure=float(self.external_pressure.current),
            density=float(self.density.current),
            friction_coefficient=float(self.friction_coefficient.current),
            momentum_correction=float(self.momentum_correction.current),
        )

    def _log_areas(self) -> list[Quantity[np.float64]]:
        return [self.log_area_01, self.log_area_02, self.log_area_03]

    def _flows(self) -> list[Quantity[np.float64]]:
        return [self.flow_00, self.flow_01, self.flow_02, self.flow_03]

    def _current_areas(self) -> np.ndarray:
        return np.exp([log_area.current for log_area in self._log_areas()])

    def _new_areas(self) -> np.ndarray:
        return np.exp([log_area.new for log_area in self._log_areas()])

    def _mid_areas(self) -> np.ndarray:
        return 0.5 * (self._current_areas() + self._new_areas())

    def _current_flows(self) -> np.ndarray:
        return np.array([flow.current for flow in self._flows()], dtype=float)

    def _new_flows(self) -> np.ndarray:
        return np.array([flow.new for flow in self._flows()], dtype=float)

    def _mid_flows(self) -> np.ndarray:
        return np.array([mid_point(flow) for flow in self._flows()], dtype=float)

    def _residual(self) -> OneDVesselResidual:
        return vessel_residual(
            self._current_areas(),
            self._new_areas(),
            self._current_flows(),
            self._new_flows(),
            self.pressure_1.current,
            self.pressure_1.new,
            self.pressure_2.current,
            self.pressure_2.new,
            self.time.dt,
            self._parameters(),
        )

    def _jacobian_area(self) -> OneDVesselJacobian:
        return vessel_jacobian_new(
            self._current_areas(),
            self._new_areas(),
            self._current_flows(),
            self._new_flows(),
            self.pressure_1.current,
            self.pressure_1.new,
            self.pressure_2.current,
            self.pressure_2.new,
            self.time.dt,
            self._parameters(),
        )

    def _darea_dlog_area(self) -> np.ndarray:
        return self._jacobian_area().darea_darea * self._new_areas()[None, :]

    def _dflow_dlog_area(self) -> np.ndarray:
        return self._jacobian_area().dflow_darea * self._new_areas()[None, :]

    @declares_internal_equation(LOG_AREA_IDS[0], starting_index=0)
    @declares_internal_equation(LOG_AREA_IDS[1], starting_index=1)
    @declares_internal_equation(LOG_AREA_IDS[2], starting_index=2)
    def area_residual(self) -> np.ndarray:
        return self._residual().area

    @area_residual.partial_derivative(LOG_AREA_IDS[0])
    def area_residual_dlog_area_01(self) -> np.ndarray:
        return self._darea_dlog_area()[:, 0]

    @area_residual.partial_derivative(LOG_AREA_IDS[1])
    def area_residual_dlog_area_02(self) -> np.ndarray:
        return self._darea_dlog_area()[:, 1]

    @area_residual.partial_derivative(LOG_AREA_IDS[2])
    def area_residual_dlog_area_03(self) -> np.ndarray:
        return self._darea_dlog_area()[:, 2]

    @area_residual.partial_derivative(FLOW_IDS[0])
    def area_residual_dflow_00(self) -> np.ndarray:
        return self._jacobian_area().darea_dflow[:, 0]

    @area_residual.partial_derivative(FLOW_IDS[1])
    def area_residual_dflow_01(self) -> np.ndarray:
        return self._jacobian_area().darea_dflow[:, 1]

    @area_residual.partial_derivative(FLOW_IDS[2])
    def area_residual_dflow_02(self) -> np.ndarray:
        return self._jacobian_area().darea_dflow[:, 2]

    @area_residual.partial_derivative(FLOW_IDS[3])
    def area_residual_dflow_03(self) -> np.ndarray:
        return self._jacobian_area().darea_dflow[:, 3]

    @declares_internal_equation(FLOW_IDS[0], starting_index=0)
    @declares_internal_equation(FLOW_IDS[1], starting_index=1)
    @declares_internal_equation(FLOW_IDS[2], starting_index=2)
    @declares_internal_equation(FLOW_IDS[3], starting_index=3)
    def flow_residual(self) -> np.ndarray:
        return self._residual().flow

    @flow_residual.partial_derivative(LOG_AREA_IDS[0])
    def flow_residual_dlog_area_01(self) -> np.ndarray:
        return self._dflow_dlog_area()[:, 0]

    @flow_residual.partial_derivative(LOG_AREA_IDS[1])
    def flow_residual_dlog_area_02(self) -> np.ndarray:
        return self._dflow_dlog_area()[:, 1]

    @flow_residual.partial_derivative(LOG_AREA_IDS[2])
    def flow_residual_dlog_area_03(self) -> np.ndarray:
        return self._dflow_dlog_area()[:, 2]

    @flow_residual.partial_derivative(FLOW_IDS[0])
    def flow_residual_dflow_00(self) -> np.ndarray:
        return self._jacobian_area().dflow_dflow[:, 0]

    @flow_residual.partial_derivative(FLOW_IDS[1])
    def flow_residual_dflow_01(self) -> np.ndarray:
        return self._jacobian_area().dflow_dflow[:, 1]

    @flow_residual.partial_derivative(FLOW_IDS[2])
    def flow_residual_dflow_02(self) -> np.ndarray:
        return self._jacobian_area().dflow_dflow[:, 2]

    @flow_residual.partial_derivative(FLOW_IDS[3])
    def flow_residual_dflow_03(self) -> np.ndarray:
        return self._jacobian_area().dflow_dflow[:, 3]

    @flow_residual.partial_derivative(PRESSURE_1_ID)
    def flow_residual_dpressure_1(self) -> np.ndarray:
        return self._jacobian_area().dflow_dpressure_1

    @flow_residual.partial_derivative(PRESSURE_2_ID)
    def flow_residual_dpressure_2(self) -> np.ndarray:
        return self._jacobian_area().dflow_dpressure_2

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

    @declares_saved_quantity(AREA_IDS[0])
    def area_01(self) -> float:
        return float(self._mid_areas()[0])

    @declares_saved_quantity(AREA_IDS[1])
    def area_02(self) -> float:
        return float(self._mid_areas()[1])

    @declares_saved_quantity(AREA_IDS[2])
    def area_03(self) -> float:
        return float(self._mid_areas()[2])

    @declares_saved_quantity(CELL_PRESSURE_ID, size=NUMBER_OF_CELLS)
    def cell_pressure(self) -> np.ndarray:
        return cell_pressures(self._mid_areas(), self._parameters())

    @declares_saved_quantity(CELL_AREA_ID, size=NUMBER_OF_CELLS)
    def cell_area(self) -> np.ndarray:
        return self._mid_areas()

    @declares_saved_quantity(FACE_FLOW_ID, size=NUMBER_OF_CELLS + 1)
    def face_flow(self) -> np.ndarray:
        return self._mid_flows()

    @declares_saved_quantity(STORED_VOLUME_ID)
    def stored_volume(self) -> float:
        return stored_volume(self._mid_areas(), float(self.length.current))

    @declares_saved_quantity(MIN_AREA_ID)
    def min_area(self) -> float:
        return float(np.min(self._mid_areas()))

    @declares_saved_quantity(NEGATIVE_AREA_COUNT_ID)
    def negative_area_count(self) -> int:
        return negative_area_count(self._mid_areas())
