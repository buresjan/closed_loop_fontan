from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

import fontan_blocks
from fontan_blocks.one_d_feasibility import (
    AREA_IDS,
    FIXED_3CELL_1D_PROBE_BLOCK_TYPE_ID,
    FLOW_IDS,
    Fixed3Cell1DProbeBlock,
)
from physioblocks.computing import Quantity, mid_point
from physioblocks.description import BlockDescription, Net
from physioblocks.description.flux import get_flux_dof_register
from physioblocks.registers.type_register import get_registered_type, is_registered
from physioblocks.simulation import Time
from physioblocks.simulation.runtime import StaticSimulation
from physioblocks.simulation.setup import SimulationFactory

ROOT = Path(__file__).resolve().parents[1]
FEASIBILITY_MEMO = (
    ROOT / "models/coupled_0d_1d/docs/physioblocks_feasibility.md"
)


def q(current: float, new: float | None = None) -> Quantity:
    quantity = Quantity(current)
    if new is not None:
        quantity.update(new)
    return quantity


def time(dt: float) -> Time:
    value = Time(0.0)
    value.update(dt)
    return value


def sample_block() -> Fixed3Cell1DProbeBlock:
    return Fixed3Cell1DProbeBlock(
        area_01=q(2.0, 2.1),
        area_02=q(3.0, 2.9),
        area_03=q(4.0, 4.2),
        flow_00=q(1.0, 1.2),
        flow_01=q(1.5, 1.4),
        flow_02=q(2.0, 2.2),
        flow_03=q(2.5, 2.4),
        pressure_1=q(20.0),
        pressure_2=q(12.0),
        length=q(3.0),
        reference_area=q(1.0),
        wall_stiffness=q(4.0),
        external_pressure=q(10.0),
        resistance=q(2.0),
        inertance=q(0.5),
        number_of_cells=q(3.0),
        time=time(0.5),
    )


def expected_cell_pressures(block: Fixed3Cell1DProbeBlock) -> np.ndarray:
    return np.array(
        [
            block.external_pressure.current
            + block.wall_stiffness.current
            * (np.sqrt(mid_point(area)) - np.sqrt(block.reference_area.current))
            for area in [block.area_01, block.area_02, block.area_03]
        ]
    )


def expected_area_residual(block: Fixed3Cell1DProbeBlock) -> np.ndarray:
    areas = [block.area_01, block.area_02, block.area_03]
    flows = [block.flow_00, block.flow_01, block.flow_02, block.flow_03]
    return np.array(
        [
            (area.new - area.current) * block.time.inv_dt
            + (mid_point(flows[index + 1]) - mid_point(flows[index])) / block.dx
            for index, area in enumerate(areas)
        ]
    )


def expected_flow_residual(block: Fixed3Cell1DProbeBlock) -> np.ndarray:
    cell_pressure = expected_cell_pressures(block)
    face_left = [
        mid_point(block.pressure_1),
        cell_pressure[0],
        cell_pressure[1],
        cell_pressure[2],
    ]
    face_right = [
        cell_pressure[0],
        cell_pressure[1],
        cell_pressure[2],
        mid_point(block.pressure_2),
    ]
    flows = [block.flow_00, block.flow_01, block.flow_02, block.flow_03]
    return np.array(
        [
            block.inertance.current * block.time.inv_dt * (flow.new - flow.current)
            + block.resistance.current * mid_point(flow)
            - face_left[index]
            + face_right[index]
            for index, flow in enumerate(flows)
        ]
    )


def build_probe_simulation():
    get_flux_dof_register().update({"blood_flow": "blood_pressure"})
    net = Net()
    net.add_node("inlet")
    net.add_node("outlet")
    net.add_block(
        "probe",
        BlockDescription(
            "probe",
            Fixed3Cell1DProbeBlock,
            "blood_flow",
            global_ids={"time": "time"},
        ),
        {1: "inlet", 2: "outlet"},
    )
    return SimulationFactory(
        "fixed_size_probe",
        StaticSimulation,
        net=net,
    ).create_simulation()


def set_quantity(quantity: Quantity, current: float, new: float | None = None) -> None:
    quantity.initialize(current)
    if new is not None:
        quantity.update(new)


def initialize_probe_simulation(simulation) -> None:
    block = sample_block()
    values = {
        "probe.area_01": block.area_01,
        "probe.area_02": block.area_02,
        "probe.area_03": block.area_03,
        "probe.flow_00": block.flow_00,
        "probe.flow_01": block.flow_01,
        "probe.flow_02": block.flow_02,
        "probe.flow_03": block.flow_03,
        "inlet.blood_pressure": block.pressure_1,
        "outlet.blood_pressure": block.pressure_2,
    }
    for name, value in values.items():
        set_quantity(simulation.state[name], value.current, value.new)

    parameters = {
        "probe.length": block.length,
        "probe.reference_area": block.reference_area,
        "probe.wall_stiffness": block.wall_stiffness,
        "probe.external_pressure": block.external_pressure,
        "probe.resistance": block.resistance,
        "probe.inertance": block.inertance,
        "probe.number_of_cells": block.number_of_cells,
    }
    for name, value in parameters.items():
        set_quantity(simulation.parameters[name], value.current, value.new)

    simulation.time_manager.time.update(block.time.new)


def test_fixed_3cell_probe_is_registered_as_local_extension():
    assert fontan_blocks.Fixed3Cell1DProbeBlock is Fixed3Cell1DProbeBlock
    assert is_registered(FIXED_3CELL_1D_PROBE_BLOCK_TYPE_ID)
    assert (
        get_registered_type(FIXED_3CELL_1D_PROBE_BLOCK_TYPE_ID)
        is Fixed3Cell1DProbeBlock
    )


def test_probe_declares_fixed_scalar_terms_not_config_sized_state():
    internal_variables = {
        term.term_id: term.size for term in Fixed3Cell1DProbeBlock.internal_variables
    }

    assert internal_variables == {
        "area_01": 1,
        "area_02": 1,
        "area_03": 1,
        "flow_00": 1,
        "flow_01": 1,
        "flow_02": 1,
        "flow_03": 1,
    }
    assert "number_of_cells" in Fixed3Cell1DProbeBlock.local_ids
    assert "number_of_cells" not in internal_variables


def test_direct_probe_residuals_fluxes_and_saved_quantities():
    block = sample_block()

    np.testing.assert_allclose(
        Fixed3Cell1DProbeBlock.area_residual(block),
        expected_area_residual(block),
    )
    np.testing.assert_allclose(
        Fixed3Cell1DProbeBlock.flow_residual(block),
        expected_flow_residual(block),
    )
    assert Fixed3Cell1DProbeBlock.flux_1(block) == pytest.approx(
        -mid_point(block.flow_00)
    )
    assert Fixed3Cell1DProbeBlock.flux_2(block) == pytest.approx(
        mid_point(block.flow_03)
    )
    np.testing.assert_allclose(
        Fixed3Cell1DProbeBlock.cell_pressure(block),
        expected_cell_pressures(block),
    )
    assert Fixed3Cell1DProbeBlock.min_area(block) == pytest.approx(2.0)
    assert Fixed3Cell1DProbeBlock.max_area(block) == pytest.approx(4.0)


def test_direct_probe_derivatives_have_expected_shapes_and_values():
    block = sample_block()
    flow_diag = block.inertance.current * block.time.inv_dt + 0.5 * block.resistance.current
    dpressure_darea_01 = block.wall_stiffness.current / (
        4.0 * np.sqrt(mid_point(block.area_01))
    )

    np.testing.assert_allclose(block.area_residual_darea_01(), [2.0, 0.0, 0.0])
    np.testing.assert_allclose(block.area_residual_dflow_01(), [0.5, -0.5, 0.0])
    np.testing.assert_allclose(block.flow_residual_dflow_00(), [flow_diag, 0.0, 0.0, 0.0])
    np.testing.assert_allclose(
        block.flow_residual_darea_01(),
        [dpressure_darea_01, -dpressure_darea_01, 0.0, 0.0],
    )
    np.testing.assert_allclose(block.flow_residual_dpressure_1(), [-0.5, 0.0, 0.0, 0.0])
    np.testing.assert_allclose(block.flow_residual_dpressure_2(), [0.0, 0.0, 0.0, 0.5])


def test_physioblocks_assembles_fixed_size_probe_state_residual_gradient_and_fluxes():
    simulation = build_probe_simulation()
    initialize_probe_simulation(simulation)
    block = sample_block()

    assert simulation.state.size == 9
    for name in [*AREA_IDS, *FLOW_IDS]:
        assert simulation.state.get_variable_size(f"probe.{name}") == 1

    residual = simulation.eq_system.compute_residual()
    gradient = simulation.eq_system.compute_gradient()

    np.testing.assert_allclose(residual[:3], expected_area_residual(block))
    np.testing.assert_allclose(residual[3:7], expected_flow_residual(block))
    assert residual[7] == pytest.approx(-mid_point(block.flow_00))
    assert residual[8] == pytest.approx(mid_point(block.flow_03))
    assert gradient.shape == (9, 9)
    assert gradient[0, simulation.state.get_variable_index("probe.area_01")] == pytest.approx(2.0)
    assert gradient[0, simulation.state.get_variable_index("probe.flow_00")] == pytest.approx(-0.5)
    assert gradient[0, simulation.state.get_variable_index("probe.flow_01")] == pytest.approx(0.5)
    assert gradient[3, simulation.state.get_variable_index("inlet.blood_pressure")] == pytest.approx(-0.5)
    assert gradient[6, simulation.state.get_variable_index("outlet.blood_pressure")] == pytest.approx(0.5)
    assert gradient[7, simulation.state.get_variable_index("probe.flow_00")] == pytest.approx(-0.5)
    assert gradient[8, simulation.state.get_variable_index("probe.flow_03")] == pytest.approx(0.5)


def test_saved_vector_quantity_assembles_and_updates():
    simulation = build_probe_simulation()
    initialize_probe_simulation(simulation)

    simulation.saved_quantities.update()

    assert simulation.saved_quantities["probe.cell_pressure"].size == 3
    np.testing.assert_allclose(
        simulation.saved_quantities["probe.cell_pressure"].current,
        expected_cell_pressures(sample_block()),
    )
    assert simulation.saved_quantities["probe.min_area"].current == pytest.approx(2.0)
    assert simulation.saved_quantities["probe.max_area"].current == pytest.approx(4.0)


def test_config_number_of_cells_parameter_does_not_resize_state():
    simulation = build_probe_simulation()
    set_quantity(simulation.parameters["probe.number_of_cells"], 99.0)

    fixed_internal_state = [
        name for name in simulation.state.variables if name.startswith("probe.")
    ]

    assert len(fixed_internal_state) == 7
    assert "probe.area_04" not in simulation.state.variables
    assert simulation.state.size == 9


def test_feasibility_memo_records_decision_and_rejected_alternatives():
    text = FEASIBILITY_MEMO.read_text()

    assert "Proceed locally for Task 010." in text
    assert "Do not fork PhysioBlocks at the start of Task 010." in text
    assert "Monolithic Config-Sized 1-D Block" in text
    assert "Concrete PhysioBlocks API Changes If Needed Later" in text
