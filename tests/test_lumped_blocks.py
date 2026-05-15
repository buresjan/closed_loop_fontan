from __future__ import annotations

import fontan_blocks
from fontan_blocks.lumped import (
    HYDRAULIC_RESISTOR_BLOCK_TYPE_ID,
    HYDRAULIC_RL_BLOCK_TYPE_ID,
    HydraulicResistorBlock,
    HydraulicRLBlock,
)
from physioblocks.computing import Quantity
from physioblocks.registers.type_register import get_registered_type, is_registered
from physioblocks.simulation import Time


def q(current: float, new: float | None = None) -> Quantity:
    quantity = Quantity(current)
    if new is not None:
        quantity.update(new)
    return quantity


def t(dt: float) -> Time:
    time = Time(0.0)
    time.update(dt)
    return time


def test_hydraulic_lumped_blocks_are_exported_and_registered():
    assert fontan_blocks.HydraulicResistorBlock is HydraulicResistorBlock
    assert fontan_blocks.HydraulicRLBlock is HydraulicRLBlock
    assert is_registered(HYDRAULIC_RESISTOR_BLOCK_TYPE_ID)
    assert is_registered(HYDRAULIC_RL_BLOCK_TYPE_ID)
    assert (
        get_registered_type(HYDRAULIC_RESISTOR_BLOCK_TYPE_ID)
        is HydraulicResistorBlock
    )
    assert get_registered_type(HYDRAULIC_RL_BLOCK_TYPE_ID) is HydraulicRLBlock
    assert HydraulicRLBlock.has_internal_variable("flux")


def test_hydraulic_resistor_flux_orientation_node_1_to_node_2():
    block = HydraulicResistorBlock(
        pressure_1=q(1600.0),
        pressure_2=q(1200.0),
        resistance=q(100.0),
    )

    assert HydraulicResistorBlock.flux_1(block) == -4.0
    assert HydraulicResistorBlock.flux_2(block) == 4.0


def test_hydraulic_resistor_derivatives_follow_midpoint_discretization():
    block = HydraulicResistorBlock(
        pressure_1=q(0.0),
        pressure_2=q(0.0),
        resistance=q(200.0),
    )

    assert block.dflux_1_dpressure_1() == -0.0025
    assert block.dflux_1_dpressure_2() == 0.0025
    assert block.dflux_2_dpressure_1() == 0.0025
    assert block.dflux_2_dpressure_2() == -0.0025


def test_hydraulic_resistor_is_bidirectional():
    block = HydraulicResistorBlock(
        pressure_1=q(700.0),
        pressure_2=q(1000.0),
        resistance=q(100.0),
    )

    assert HydraulicResistorBlock.flux_1(block) == 3.0
    assert HydraulicResistorBlock.flux_2(block) == -3.0


def test_hydraulic_rl_residual_orientation_and_derivatives():
    block = HydraulicRLBlock(
        flux=q(1.0, 2.0),
        pressure_1=q(100.0),
        pressure_2=q(70.0),
        resistance=q(10.0),
        inductance=q(2.0),
        time=t(0.25),
    )

    assert HydraulicRLBlock.flux_residual(block) == -7.0
    assert block.flux_residual_dflux() == 13.0
    assert block.flux_residual_dpressure_1() == -0.5
    assert block.flux_residual_dpressure_2() == 0.5
    assert HydraulicRLBlock.flux_1(block) == -1.5
    assert HydraulicRLBlock.flux_2(block) == 1.5
    assert block.dflux_1_dflux() == -0.5
    assert block.dflux_2_dflux() == 0.5


def test_hydraulic_rl_is_symmetric_and_bidirectional_without_valve_behavior():
    forward = HydraulicRLBlock(
        flux=q(3.0),
        pressure_1=q(100.0),
        pressure_2=q(70.0),
        resistance=q(10.0),
        inductance=q(2.0),
        time=t(0.25),
    )
    backward = HydraulicRLBlock(
        flux=q(-3.0),
        pressure_1=q(70.0),
        pressure_2=q(100.0),
        resistance=q(10.0),
        inductance=q(2.0),
        time=t(0.25),
    )

    assert HydraulicRLBlock.flux_residual(forward) == 0.0
    assert HydraulicRLBlock.flux_residual(backward) == 0.0
    assert HydraulicRLBlock.flux_1(forward) == -3.0
    assert HydraulicRLBlock.flux_2(forward) == 3.0
    assert HydraulicRLBlock.flux_1(backward) == 3.0
    assert HydraulicRLBlock.flux_2(backward) == -3.0
