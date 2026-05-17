from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np


def _require_positive(name: str, value: float) -> None:
    if value <= 0.0:
        raise ValueError(f"{name} must be positive")


@dataclass(frozen=True)
class UniformVesselGeometry:
    """Uniform straight-vessel geometry for finite-volume 1-D prototypes."""

    length: float
    number_of_cells: int
    reference_area: float

    def __post_init__(self) -> None:
        _require_positive("length", self.length)
        _require_positive("reference_area", self.reference_area)
        if self.number_of_cells < 1:
            raise ValueError("number_of_cells must be at least 1")

    @property
    def dx(self) -> float:
        return self.length / self.number_of_cells

    @property
    def cell_centers(self) -> np.ndarray:
        return (np.arange(self.number_of_cells, dtype=float) + 0.5) * self.dx

    @property
    def face_positions(self) -> np.ndarray:
        return np.arange(self.number_of_cells + 1, dtype=float) * self.dx

    @property
    def reference_areas(self) -> np.ndarray:
        return np.full(self.number_of_cells, self.reference_area, dtype=float)

    @property
    def reference_volume(self) -> float:
        return self.length * self.reference_area


def staggered_face_average(cell_values: Any) -> np.ndarray:
    """Interpolate cell-centered values to staggered vessel faces."""

    values = np.asarray(cell_values, dtype=float)
    if values.ndim != 1:
        raise ValueError("cell_values must be one-dimensional")
    if values.size < 1:
        raise ValueError("cell_values must not be empty")

    faces = np.empty(values.size + 1, dtype=float)
    faces[0] = values[0]
    faces[-1] = values[-1]
    if values.size > 1:
        faces[1:-1] = 0.5 * (values[:-1] + values[1:])
    return faces


def stored_volume(cell_area: Any, length: float) -> float:
    """Compute the finite-volume vessel volume from cell-centered areas."""

    areas = np.asarray(cell_area, dtype=float)
    if areas.ndim != 1:
        raise ValueError("cell_area must be one-dimensional")
    _require_positive("length", length)
    return float(np.sum(areas) * length / areas.size)
