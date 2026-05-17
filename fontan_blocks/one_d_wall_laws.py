from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np


def _as_array(value: Any) -> np.ndarray:
    return np.asarray(value, dtype=float)


def _require_positive(name: str, value: Any) -> None:
    if np.any(_as_array(value) <= 0.0):
        raise ValueError(f"{name} must be positive")


def sqrt_pressure_from_area(
    area: Any,
    reference_area: float,
    wall_stiffness: float,
    external_pressure: float = 0.0,
) -> Any:
    """Pressure-area relation for an elastic 1-D vessel wall."""

    _require_positive("area", area)
    _require_positive("reference_area", reference_area)
    _require_positive("wall_stiffness", wall_stiffness)
    return external_pressure + wall_stiffness * (
        np.sqrt(area) - np.sqrt(reference_area)
    )


def area_from_sqrt_pressure(
    pressure: Any,
    reference_area: float,
    wall_stiffness: float,
    external_pressure: float = 0.0,
) -> Any:
    """Inverse of the square-root wall law."""

    _require_positive("reference_area", reference_area)
    _require_positive("wall_stiffness", wall_stiffness)
    radius_like = (
        np.sqrt(reference_area) + (_as_array(pressure) - external_pressure) / wall_stiffness
    )
    if np.any(radius_like <= 0.0):
        raise ValueError("pressure implies non-positive vessel area")
    return radius_like * radius_like


def dpressure_darea(area: Any, wall_stiffness: float) -> Any:
    """Derivative dP/dA for the square-root wall law."""

    _require_positive("area", area)
    _require_positive("wall_stiffness", wall_stiffness)
    return wall_stiffness / (2.0 * np.sqrt(area))


def sqrt_wall_stiffness_from_wave_speed(
    reference_area: float,
    density: float,
    wave_speed: float,
) -> float:
    """Return beta such that c(A0) equals the requested wave speed."""

    _require_positive("reference_area", reference_area)
    _require_positive("density", density)
    _require_positive("wave_speed", wave_speed)
    return 2.0 * density * wave_speed * wave_speed / np.sqrt(reference_area)


def wave_speed_from_area(area: Any, wall_stiffness: float, density: float) -> Any:
    """Moens-Korteweg-like wave speed implied by the wall law."""

    _require_positive("area", area)
    _require_positive("wall_stiffness", wall_stiffness)
    _require_positive("density", density)
    return np.sqrt(_as_array(area) * dpressure_darea(area, wall_stiffness) / density)


def characteristic_impedance(area: Any, wall_stiffness: float, density: float) -> Any:
    """Local characteristic impedance rho*c/A."""

    _require_positive("area", area)
    return density * wave_speed_from_area(area, wall_stiffness, density) / _as_array(area)


@dataclass(frozen=True)
class SquareRootWallLaw:
    """Convenience wrapper for the 1-D square-root pressure-area law."""

    reference_area: float
    wall_stiffness: float
    external_pressure: float = 0.0
    density: float = 1060.0

    def __post_init__(self) -> None:
        _require_positive("reference_area", self.reference_area)
        _require_positive("wall_stiffness", self.wall_stiffness)
        _require_positive("density", self.density)

    def pressure(self, area: Any) -> Any:
        return sqrt_pressure_from_area(
            area,
            self.reference_area,
            self.wall_stiffness,
            self.external_pressure,
        )

    def area(self, pressure: Any) -> Any:
        return area_from_sqrt_pressure(
            pressure,
            self.reference_area,
            self.wall_stiffness,
            self.external_pressure,
        )

    def dpressure_darea(self, area: Any) -> Any:
        return dpressure_darea(area, self.wall_stiffness)

    def wave_speed(self, area: Any) -> Any:
        return wave_speed_from_area(area, self.wall_stiffness, self.density)

    def characteristic_impedance(self, area: Any) -> Any:
        return characteristic_impedance(area, self.wall_stiffness, self.density)
