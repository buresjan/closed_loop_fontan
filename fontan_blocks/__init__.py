"""Local PhysioBlocks extensions for the closed-loop Fontan model."""

from .active_atrium import TimeVaryingElastanceAtriumBlock
from .lumped import HydraulicResistorBlock, HydraulicRLBlock
from .one_d import Fixed3CellOneDLogAreaVesselBlock, Fixed3CellOneDVesselBlock
from .one_d_feasibility import Fixed3Cell1DProbeBlock
from .one_d_total_pressure_junctions import (
    AorticArchTotalPressureJunctionBlock,
    TCPCCharacteristicTotalPressureJunctionBlock,
    TCPCTotalPressureJunctionBlock,
)
from .one_d_tapered import Fixed6CellTaperedOneDLogAreaVesselBlock

__all__ = [
    "AorticArchTotalPressureJunctionBlock",
    "Fixed3Cell1DProbeBlock",
    "Fixed3CellOneDLogAreaVesselBlock",
    "Fixed3CellOneDVesselBlock",
    "Fixed6CellTaperedOneDLogAreaVesselBlock",
    "HydraulicResistorBlock",
    "HydraulicRLBlock",
    "TCPCCharacteristicTotalPressureJunctionBlock",
    "TCPCTotalPressureJunctionBlock",
    "TimeVaryingElastanceAtriumBlock",
]
