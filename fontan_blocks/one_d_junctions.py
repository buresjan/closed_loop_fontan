from __future__ import annotations

from typing import Any

import numpy as np


def boundary_pressure_gradient(
    inlet_pressure: float,
    cell_pressure: Any,
    outlet_pressure: float,
    dx: float,
) -> np.ndarray:
    """Pressure gradient at staggered faces using half-cell boundary distances."""

    pressures = np.asarray(cell_pressure, dtype=float)
    if pressures.ndim != 1:
        raise ValueError("cell_pressure must be one-dimensional")
    if pressures.size < 1:
        raise ValueError("cell_pressure must not be empty")
    if dx <= 0.0:
        raise ValueError("dx must be positive")

    gradient = np.empty(pressures.size + 1, dtype=float)
    gradient[0] = (pressures[0] - inlet_pressure) / (0.5 * dx)
    gradient[-1] = (outlet_pressure - pressures[-1]) / (0.5 * dx)
    if pressures.size > 1:
        gradient[1:-1] = (pressures[1:] - pressures[:-1]) / dx
    return gradient


def boundary_pressure_gradient_matrix(number_of_cells: int, dx: float) -> np.ndarray:
    """Linear operator mapping [pin, p_cells..., pout] to face gradients."""

    if number_of_cells < 1:
        raise ValueError("number_of_cells must be at least 1")
    if dx <= 0.0:
        raise ValueError("dx must be positive")

    matrix = np.zeros((number_of_cells + 1, number_of_cells + 2), dtype=float)
    matrix[0, 0] = -2.0 / dx
    matrix[0, 1] = 2.0 / dx
    for face in range(1, number_of_cells):
        matrix[face, face] = -1.0 / dx
        matrix[face, face + 1] = 1.0 / dx
    matrix[-1, -2] = -2.0 / dx
    matrix[-1, -1] = 2.0 / dx
    return matrix


def port_fluxes(face_flow: Any) -> tuple[float, float]:
    """Return PhysioBlocks node fluxes for positive vessel flow left to right."""

    flows = np.asarray(face_flow, dtype=float)
    if flows.ndim != 1 or flows.size < 2:
        raise ValueError("face_flow must contain at least inlet and outlet flows")
    return -float(flows[0]), float(flows[-1])


def volume_balance_error(
    current_area: Any,
    new_area: Any,
    current_flow: Any,
    new_flow: Any,
    length: float,
    dt: float,
) -> float:
    """Check dV/dt = Qin - Qout for the finite-volume vessel."""

    current_area = np.asarray(current_area, dtype=float)
    new_area = np.asarray(new_area, dtype=float)
    current_flow = np.asarray(current_flow, dtype=float)
    new_flow = np.asarray(new_flow, dtype=float)
    if current_area.shape != new_area.shape:
        raise ValueError("current_area and new_area must have the same shape")
    if current_flow.shape != new_flow.shape:
        raise ValueError("current_flow and new_flow must have the same shape")
    if current_flow.size != current_area.size + 1:
        raise ValueError("flow array must have one more entry than area array")
    if length <= 0.0:
        raise ValueError("length must be positive")
    if dt <= 0.0:
        raise ValueError("dt must be positive")

    dx = length / current_area.size
    volume_rate = float(np.sum(new_area - current_area) * dx / dt)
    flow_mid = 0.5 * (current_flow + new_flow)
    return volume_rate - float(flow_mid[0] - flow_mid[-1])
