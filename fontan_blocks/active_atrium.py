from dataclasses import dataclass
from typing import Any

import numpy as np

from physioblocks.computing import Block, Quantity
from physioblocks.computing.models import declares_flux, declares_saved_quantity
from physioblocks.registers import register_type
from physioblocks.simulation import Time

ACTIVE_ATRIUM_BLOCK_TYPE_ID = "time_varying_elastance_atrium_block"

PRESSURE_ID = "pressure"


@register_type(ACTIVE_ATRIUM_BLOCK_TYPE_ID)
@dataclass
class TimeVaryingElastanceAtriumBlock(Block):
    """One-node atrial chamber with prescribed time-varying elastance."""

    pressure: Quantity[np.float64]
    pressure_external: Quantity[np.float64]
    elastance_min: Quantity[np.float64]
    elastance_max: Quantity[np.float64]
    unstressed_volume: Quantity[np.float64]
    activation_start: Quantity[np.float64]
    activation_peak: Quantity[np.float64]
    activation_end: Quantity[np.float64]
    heartbeat_duration: Quantity[np.float64]
    time: Time

    def _phase(self, value: Any) -> float:
        period = max(float(self.heartbeat_duration.current), 1e-12)
        return (float(value) % period) / period

    def _activation_at(self, value: Any) -> float:
        phase = self._phase(value)
        start = float(self.activation_start.current)
        peak = float(self.activation_peak.current)
        end = float(self.activation_end.current)

        if phase < start or phase >= end:
            return 0.0
        if phase <= peak:
            width = max(peak - start, 1e-12)
            s = (phase - start) / width
            return 0.5 * (1.0 - np.cos(np.pi * s))

        width = max(end - peak, 1e-12)
        s = (phase - peak) / width
        return 0.5 * (1.0 + np.cos(np.pi * s))

    def _elastance_at(self, value: Any) -> float:
        e_min = float(self.elastance_min.current)
        e_max = float(self.elastance_max.current)
        return max(e_min + (e_max - e_min) * self._activation_at(value), 1e-12)

    def _volume_at(self, pressure: Any, value: Any) -> float:
        transmural_pressure = float(pressure) - float(self.pressure_external.current)
        return float(self.unstressed_volume.current) + transmural_pressure / self._elastance_at(value)

    @declares_flux(1, PRESSURE_ID)
    def flux(self) -> Any:
        if self.time.dt == 0.0:
            return 0.0
        volume_new = self._volume_at(self.pressure.new, self.time.new)
        volume_current = self._volume_at(self.pressure.current, self.time.current)
        return -(volume_new - volume_current) * self.time.inv_dt

    @flux.partial_derivative(PRESSURE_ID)
    def dflux_dpressure(self) -> Any:
        if self.time.dt == 0.0:
            return 0.0
        return -self.time.inv_dt / self._elastance_at(self.time.new)

    @declares_saved_quantity("volume")
    def volume(self) -> Any:
        return self._volume_at(self.pressure.current, self.time.current)

    @declares_saved_quantity("activation")
    def activation(self) -> Any:
        return self._activation_at(self.time.current)

    @declares_saved_quantity("elastance")
    def elastance(self) -> Any:
        return self._elastance_at(self.time.current)
