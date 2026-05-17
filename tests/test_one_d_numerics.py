from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

import fontan_blocks
from fontan_blocks.one_d import (
    AREA_IDS,
    CELL_AREA_ID,
    CELL_PRESSURE_ID,
    FACE_FLOW_ID,
    FIXED_3CELL_1D_LOG_AREA_VESSEL_BLOCK_TYPE_ID,
    FIXED_3CELL_1D_VESSEL_BLOCK_TYPE_ID,
    FLOW_IDS,
    LOG_AREA_IDS,
    MIN_AREA_ID,
    NEGATIVE_AREA_COUNT_ID,
    STORED_VOLUME_ID,
    Fixed3CellOneDLogAreaVesselBlock,
    Fixed3CellOneDVesselBlock,
    OneDVesselParameters,
    cell_pressures,
    face_areas,
    linearized_characteristic_speeds,
    negative_area_count,
    vessel_jacobian_new,
    vessel_residual,
)
from fontan_blocks.one_d_tapered import (
    FIXED_6CELL_TAPERED_1D_LOG_AREA_VESSEL_BLOCK_TYPE_ID,
    Fixed6CellTaperedOneDLogAreaVesselBlock,
    TaperedOneDVesselParameters,
    tapered_vessel_residual,
)
from fontan_blocks.one_d_geometry import UniformVesselGeometry, stored_volume
from fontan_blocks.one_d_junctions import port_fluxes, volume_balance_error
from fontan_blocks.one_d_wall_laws import (
    SquareRootWallLaw,
    area_from_sqrt_pressure,
    sqrt_wall_stiffness_from_wave_speed,
    wave_speed_from_area,
)
from fontan_blocks.one_d_total_pressure_junctions import (
    AORTIC_ARCH_TOTAL_PRESSURE_JUNCTION_BLOCK_TYPE_ID,
    TCPC_CHARACTERISTIC_TOTAL_PRESSURE_JUNCTION_BLOCK_TYPE_ID,
    TCPC_TOTAL_PRESSURE_JUNCTION_BLOCK_TYPE_ID,
    AorticArchTotalPressureJunctionBlock,
    TCPCCharacteristicTotalPressureJunctionBlock,
    TCPCTotalPressureJunctionBlock,
)
from physioblocks.computing import Quantity, mid_point
from physioblocks.description import BlockDescription, Net
from physioblocks.description.flux import get_flux_dof_register
from physioblocks.registers.type_register import get_registered_type, is_registered
from physioblocks.simulation import Time
from physioblocks.simulation.runtime import StaticSimulation
from physioblocks.simulation.setup import SimulationFactory

ROOT = Path(__file__).resolve().parents[1]


def q(current: float, new: float | None = None) -> Quantity:
    quantity = Quantity(current)
    if new is not None:
        quantity.update(new)
    return quantity


def t(dt: float) -> Time:
    time = Time(0.0)
    time.update(dt)
    return time


def sample_parameters() -> OneDVesselParameters:
    area = 3.0e-4
    beta = sqrt_wall_stiffness_from_wave_speed(area, 1060.0, 5.0)
    return OneDVesselParameters(
        length=0.30,
        reference_area=area,
        wall_stiffness=beta,
        external_pressure=1200.0,
        density=1060.0,
        friction_coefficient=2.0e-4,
        momentum_correction=1.1,
    )


def sample_state():
    return {
        "current_area": np.array([3.00e-4, 3.08e-4, 2.97e-4]),
        "new_area": np.array([3.02e-4, 3.06e-4, 2.99e-4]),
        "current_flow": np.array([1.0e-5, 1.2e-5, 0.9e-5, 0.8e-5]),
        "new_flow": np.array([1.1e-5, 1.1e-5, 1.0e-5, 0.9e-5]),
        "current_pressure_1": 1230.0,
        "new_pressure_1": 1235.0,
        "current_pressure_2": 1190.0,
        "new_pressure_2": 1188.0,
        "dt": 0.002,
    }


def sample_block() -> Fixed3CellOneDVesselBlock:
    params = sample_parameters()
    state = sample_state()
    return Fixed3CellOneDVesselBlock(
        area_01=q(state["current_area"][0], state["new_area"][0]),
        area_02=q(state["current_area"][1], state["new_area"][1]),
        area_03=q(state["current_area"][2], state["new_area"][2]),
        flow_00=q(state["current_flow"][0], state["new_flow"][0]),
        flow_01=q(state["current_flow"][1], state["new_flow"][1]),
        flow_02=q(state["current_flow"][2], state["new_flow"][2]),
        flow_03=q(state["current_flow"][3], state["new_flow"][3]),
        pressure_1=q(state["current_pressure_1"], state["new_pressure_1"]),
        pressure_2=q(state["current_pressure_2"], state["new_pressure_2"]),
        length=q(params.length),
        reference_area=q(params.reference_area),
        wall_stiffness=q(params.wall_stiffness),
        external_pressure=q(params.external_pressure),
        density=q(params.density),
        friction_coefficient=q(params.friction_coefficient),
        momentum_correction=q(params.momentum_correction),
        time=t(state["dt"]),
    )


def sample_log_area_block() -> Fixed3CellOneDLogAreaVesselBlock:
    params = sample_parameters()
    state = sample_state()
    return Fixed3CellOneDLogAreaVesselBlock(
        log_area_01=q(np.log(state["current_area"][0]), np.log(state["new_area"][0])),
        log_area_02=q(np.log(state["current_area"][1]), np.log(state["new_area"][1])),
        log_area_03=q(np.log(state["current_area"][2]), np.log(state["new_area"][2])),
        flow_00=q(state["current_flow"][0], state["new_flow"][0]),
        flow_01=q(state["current_flow"][1], state["new_flow"][1]),
        flow_02=q(state["current_flow"][2], state["new_flow"][2]),
        flow_03=q(state["current_flow"][3], state["new_flow"][3]),
        pressure_1=q(state["current_pressure_1"], state["new_pressure_1"]),
        pressure_2=q(state["current_pressure_2"], state["new_pressure_2"]),
        length=q(params.length),
        reference_area=q(params.reference_area),
        wall_stiffness=q(params.wall_stiffness),
        external_pressure=q(params.external_pressure),
        density=q(params.density),
        friction_coefficient=q(params.friction_coefficient),
        momentum_correction=q(params.momentum_correction),
        time=t(state["dt"]),
    )


def residual_vector(state, params):
    return vessel_residual(**state, parameters=params).as_vector()


def jacobian_matrix(state, params):
    jacobian = vessel_jacobian_new(**state, parameters=params)
    matrix = np.zeros((7, 9), dtype=float)
    matrix[:3, :3] = jacobian.darea_darea
    matrix[:3, 3:7] = jacobian.darea_dflow
    matrix[3:, :3] = jacobian.dflow_darea
    matrix[3:, 3:7] = jacobian.dflow_dflow
    matrix[3:, 7] = jacobian.dflow_dpressure_1
    matrix[3:, 8] = jacobian.dflow_dpressure_2
    return matrix


def build_vessel_simulation():
    get_flux_dof_register().update({"blood_flow": "blood_pressure"})
    net = Net()
    net.add_node("inlet")
    net.add_node("outlet")
    net.add_block(
        "vessel",
        BlockDescription(
            "vessel",
            Fixed3CellOneDVesselBlock,
            "blood_flow",
            global_ids={"time": "time"},
        ),
        {1: "inlet", 2: "outlet"},
    )
    return SimulationFactory(
        "fixed_3cell_1d_vessel",
        StaticSimulation,
        net=net,
    ).create_simulation()


def set_quantity(quantity: Quantity, current: float, new: float | None = None) -> None:
    quantity.initialize(current)
    if new is not None:
        quantity.update(new)


def initialize_vessel_simulation(simulation) -> None:
    block = sample_block()
    states = {
        "vessel.area_01": block.area_01,
        "vessel.area_02": block.area_02,
        "vessel.area_03": block.area_03,
        "vessel.flow_00": block.flow_00,
        "vessel.flow_01": block.flow_01,
        "vessel.flow_02": block.flow_02,
        "vessel.flow_03": block.flow_03,
        "inlet.blood_pressure": block.pressure_1,
        "outlet.blood_pressure": block.pressure_2,
    }
    for name, value in states.items():
        set_quantity(simulation.state[name], value.current, value.new)

    parameters = {
        "vessel.length": block.length,
        "vessel.reference_area": block.reference_area,
        "vessel.wall_stiffness": block.wall_stiffness,
        "vessel.external_pressure": block.external_pressure,
        "vessel.density": block.density,
        "vessel.friction_coefficient": block.friction_coefficient,
        "vessel.momentum_correction": block.momentum_correction,
    }
    for name, value in parameters.items():
        set_quantity(simulation.parameters[name], value.current)

    simulation.time_manager.time.update(block.time.new)


def test_square_root_wall_law_preserves_requested_wave_speed():
    reference_area = 3.0e-4
    density = 1060.0
    target_speed = 6.5
    beta = sqrt_wall_stiffness_from_wave_speed(
        reference_area,
        density,
        target_speed,
    )
    wall = SquareRootWallLaw(
        reference_area=reference_area,
        wall_stiffness=beta,
        external_pressure=900.0,
        density=density,
    )

    assert wall.pressure(reference_area) == pytest.approx(900.0)
    assert wall.area(900.0) == pytest.approx(reference_area)
    assert wave_speed_from_area(reference_area, beta, density) == pytest.approx(
        target_speed
    )


def test_uniform_geometry_and_face_interpolation_are_conservative():
    geometry = UniformVesselGeometry(
        length=0.30,
        number_of_cells=3,
        reference_area=3.0e-4,
    )

    np.testing.assert_allclose(geometry.cell_centers, [0.05, 0.15, 0.25])
    np.testing.assert_allclose(geometry.face_positions, [0.0, 0.1, 0.2, 0.3])
    assert geometry.reference_volume == pytest.approx(9.0e-5)
    np.testing.assert_allclose(
        face_areas([1.0, 2.0, 4.0]),
        [1.0, 1.5, 3.0, 4.0],
    )
    assert stored_volume([1.0, 2.0, 4.0], 0.30) == pytest.approx(0.70)


def test_zero_pressure_gradient_has_no_mass_or_momentum_drift():
    params = sample_parameters()
    area = np.full(3, params.reference_area)
    flow = np.zeros(4)
    pressure = params.external_pressure

    residual = vessel_residual(
        area,
        area,
        flow,
        flow,
        pressure,
        pressure,
        pressure,
        pressure,
        0.001,
        params,
    )

    np.testing.assert_allclose(residual.area, np.zeros(3), atol=1e-14)
    np.testing.assert_allclose(residual.flow, np.zeros(4), atol=1e-14)


def test_steady_pressure_drop_drives_positive_flow_acceleration():
    params = sample_parameters()
    inlet_pressure = 1230.0
    outlet_pressure = 1200.0
    cell_pressure = np.array([1225.0, 1215.0, 1205.0])
    area = area_from_sqrt_pressure(
        cell_pressure,
        params.reference_area,
        params.wall_stiffness,
        params.external_pressure,
    )
    flow = np.zeros(4)

    residual = vessel_residual(
        area,
        area,
        flow,
        flow,
        inlet_pressure,
        inlet_pressure,
        outlet_pressure,
        outlet_pressure,
        0.001,
        params,
    )

    assert np.all(residual.flow < 0.0)
    assert np.all(-residual.flow > 0.0)


def test_linearized_characteristic_speeds_match_wall_law_target():
    params = sample_parameters()
    area = np.full(3, params.reference_area)
    flow = np.zeros(3)

    left, right = linearized_characteristic_speeds(area, flow, params)

    np.testing.assert_allclose(left, np.full(3, -5.0))
    np.testing.assert_allclose(right, np.full(3, 5.0))


def test_volume_conservation_matches_inlet_minus_outlet_flow():
    params = sample_parameters()
    current_area = np.full(3, params.reference_area)
    flow = np.array([2.0e-6, 3.0e-6, 1.0e-6, -1.0e-6])
    dt = 0.005
    new_area = current_area - dt * (flow[1:] - flow[:-1]) / params.dx

    residual = vessel_residual(
        current_area,
        new_area,
        flow,
        flow,
        params.external_pressure,
        params.external_pressure,
        params.external_pressure,
        params.external_pressure,
        dt,
        params,
    )

    np.testing.assert_allclose(residual.area, np.zeros(3), atol=1e-16)
    assert volume_balance_error(
        current_area,
        new_area,
        flow,
        flow,
        params.length,
        dt,
    ) == pytest.approx(0.0, abs=1e-18)


def test_negative_area_diagnostic_is_separate_from_wall_law_evaluation():
    assert negative_area_count([3.0e-4, -1.0e-6, 0.0]) == 2


def test_vessel_jacobian_matches_finite_difference_of_new_unknowns():
    params = sample_parameters()
    state = sample_state()
    analytic = jacobian_matrix(state, params)

    base_vector = np.concatenate(
        [
            state["new_area"],
            state["new_flow"],
            [state["new_pressure_1"], state["new_pressure_2"]],
        ]
    )
    eps = np.array([1.0e-9] * 3 + [1.0e-8] * 4 + [1.0e-4] * 2)
    numeric = np.zeros_like(analytic)

    for column in range(base_vector.size):
        plus = base_vector.copy()
        minus = base_vector.copy()
        plus[column] += eps[column]
        minus[column] -= eps[column]

        state_plus = dict(state)
        state_minus = dict(state)
        state_plus["new_area"] = plus[:3]
        state_minus["new_area"] = minus[:3]
        state_plus["new_flow"] = plus[3:7]
        state_minus["new_flow"] = minus[3:7]
        state_plus["new_pressure_1"] = plus[7]
        state_minus["new_pressure_1"] = minus[7]
        state_plus["new_pressure_2"] = plus[8]
        state_minus["new_pressure_2"] = minus[8]

        numeric[:, column] = (
            residual_vector(state_plus, params)
            - residual_vector(state_minus, params)
        ) / (2.0 * eps[column])

    np.testing.assert_allclose(analytic, numeric, rtol=2e-5, atol=2e-7)


def test_fixed_3cell_true_1d_block_is_registered_and_declares_expected_state():
    assert fontan_blocks.Fixed3CellOneDVesselBlock is Fixed3CellOneDVesselBlock
    assert is_registered(FIXED_3CELL_1D_VESSEL_BLOCK_TYPE_ID)
    assert (
        get_registered_type(FIXED_3CELL_1D_VESSEL_BLOCK_TYPE_ID)
        is Fixed3CellOneDVesselBlock
    )

    internal_variables = {
        term.term_id: term.size for term in Fixed3CellOneDVesselBlock.internal_variables
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


def test_log_area_true_1d_block_preserves_positive_area_state():
    assert fontan_blocks.Fixed3CellOneDLogAreaVesselBlock is Fixed3CellOneDLogAreaVesselBlock
    assert is_registered(FIXED_3CELL_1D_LOG_AREA_VESSEL_BLOCK_TYPE_ID)
    assert (
        get_registered_type(FIXED_3CELL_1D_LOG_AREA_VESSEL_BLOCK_TYPE_ID)
        is Fixed3CellOneDLogAreaVesselBlock
    )

    internal_variables = {
        term.term_id: term.size
        for term in Fixed3CellOneDLogAreaVesselBlock.internal_variables
    }
    assert internal_variables == {
        "log_area_01": 1,
        "log_area_02": 1,
        "log_area_03": 1,
        "flow_00": 1,
        "flow_01": 1,
        "flow_02": 1,
        "flow_03": 1,
    }

    block = sample_log_area_block()
    params = sample_parameters()
    state = sample_state()
    residual = vessel_residual(**state, parameters=params)
    jacobian = vessel_jacobian_new(**state, parameters=params)

    np.testing.assert_allclose(
        Fixed3CellOneDLogAreaVesselBlock.area_residual(block),
        residual.area,
    )
    np.testing.assert_allclose(
        Fixed3CellOneDLogAreaVesselBlock.flow_residual(block),
        residual.flow,
    )
    np.testing.assert_allclose(
        block.area_residual_dlog_area_01(),
        jacobian.darea_darea[:, 0] * state["new_area"][0],
    )
    np.testing.assert_allclose(
        block.flow_residual_dlog_area_03(),
        jacobian.dflow_darea[:, 2] * state["new_area"][2],
    )
    assert Fixed3CellOneDLogAreaVesselBlock.area_01(block) > 0.0
    assert Fixed3CellOneDLogAreaVesselBlock.negative_area_count(block) == 0


def test_tapered_six_cell_log_area_block_is_registered_and_conservative():
    assert (
        fontan_blocks.Fixed6CellTaperedOneDLogAreaVesselBlock
        is Fixed6CellTaperedOneDLogAreaVesselBlock
    )
    assert is_registered(FIXED_6CELL_TAPERED_1D_LOG_AREA_VESSEL_BLOCK_TYPE_ID)
    assert (
        get_registered_type(FIXED_6CELL_TAPERED_1D_LOG_AREA_VESSEL_BLOCK_TYPE_ID)
        is Fixed6CellTaperedOneDLogAreaVesselBlock
    )

    internal_variables = {
        term.term_id: term.size
        for term in Fixed6CellTaperedOneDLogAreaVesselBlock.internal_variables
    }
    assert internal_variables == {
        "log_area_01": 1,
        "log_area_02": 1,
        "log_area_03": 1,
        "log_area_04": 1,
        "log_area_05": 1,
        "log_area_06": 1,
        "flow_00": 1,
        "flow_01": 1,
        "flow_02": 1,
        "flow_03": 1,
        "flow_04": 1,
        "flow_05": 1,
        "flow_06": 1,
    }

    reference_areas = np.array([7.0e-5, 6.7e-5, 6.4e-5, 5.2e-5, 4.8e-5, 4.4e-5])
    log_area = np.log(reference_areas)
    flow = np.zeros(7)
    params = TaperedOneDVesselParameters(
        cell_lengths=np.full(6, 0.004),
        reference_areas=reference_areas,
        wall_stiffnesses=np.full(6, 1.4e7),
        friction_coefficients=np.full(6, 2.0e-4),
        external_pressure=900.0,
        density=1060.0,
        momentum_correction=1.1,
    )

    residual = tapered_vessel_residual(
        log_area,
        log_area,
        flow,
        flow,
        900.0,
        900.0,
        900.0,
        900.0,
        0.001,
        params,
    )

    np.testing.assert_allclose(residual.area, np.zeros(6), atol=1e-14)
    np.testing.assert_allclose(residual.flow, np.zeros(7), atol=1e-14)


def pressure_for_total_pressure(target: float, flow: float, area: float, density: float) -> float:
    return target - 0.5 * density * (flow / area) ** 2


def test_total_pressure_junctions_are_registered():
    assert (
        fontan_blocks.AorticArchTotalPressureJunctionBlock
        is AorticArchTotalPressureJunctionBlock
    )
    assert (
        fontan_blocks.TCPCTotalPressureJunctionBlock
        is TCPCTotalPressureJunctionBlock
    )
    assert (
        fontan_blocks.TCPCCharacteristicTotalPressureJunctionBlock
        is TCPCCharacteristicTotalPressureJunctionBlock
    )
    assert is_registered(AORTIC_ARCH_TOTAL_PRESSURE_JUNCTION_BLOCK_TYPE_ID)
    assert is_registered(TCPC_TOTAL_PRESSURE_JUNCTION_BLOCK_TYPE_ID)
    assert is_registered(TCPC_CHARACTERISTIC_TOTAL_PRESSURE_JUNCTION_BLOCK_TYPE_ID)
    assert (
        get_registered_type(AORTIC_ARCH_TOTAL_PRESSURE_JUNCTION_BLOCK_TYPE_ID)
        is AorticArchTotalPressureJunctionBlock
    )
    assert (
        get_registered_type(TCPC_TOTAL_PRESSURE_JUNCTION_BLOCK_TYPE_ID)
        is TCPCTotalPressureJunctionBlock
    )
    assert (
        get_registered_type(TCPC_CHARACTERISTIC_TOTAL_PRESSURE_JUNCTION_BLOCK_TYPE_ID)
        is TCPCCharacteristicTotalPressureJunctionBlock
    )


def test_aortic_total_pressure_junction_is_mass_conserving_at_equilibrium():
    density = 1060.0
    area = 2.0e-4
    total_pressure = 1400.0
    aao_flow = 4.5e-5
    dao_flow = 2.0e-5
    bca_flow = 1.2e-5
    lcca_flow = 0.8e-5
    lsa_flow = 0.5e-5
    block = AorticArchTotalPressureJunctionBlock(
        aao_flow=q(aao_flow, aao_flow),
        dao_flow=q(dao_flow, dao_flow),
        bca_flow=q(bca_flow, bca_flow),
        lcca_flow=q(lcca_flow, lcca_flow),
        lsa_flow=q(lsa_flow, lsa_flow),
        pressure_aao=q(pressure_for_total_pressure(total_pressure, aao_flow, area, density)),
        pressure_dao=q(pressure_for_total_pressure(total_pressure, dao_flow, area, density)),
        pressure_bca=q(pressure_for_total_pressure(total_pressure, bca_flow, area, density)),
        pressure_lcca=q(pressure_for_total_pressure(total_pressure, lcca_flow, area, density)),
        pressure_lsa=q(total_pressure),
        log_area_aao=q(np.log(area), np.log(area)),
        log_area_dao=q(np.log(area), np.log(area)),
        log_area_bca=q(np.log(area), np.log(area)),
        log_area_lcca=q(np.log(area), np.log(area)),
        density=q(density),
    )

    assert AorticArchTotalPressureJunctionBlock.mass_residual(block) == pytest.approx(0.0)
    assert AorticArchTotalPressureJunctionBlock.dao_total_pressure_residual(block) == pytest.approx(0.0)
    assert AorticArchTotalPressureJunctionBlock.bca_total_pressure_residual(block) == pytest.approx(0.0)
    assert AorticArchTotalPressureJunctionBlock.lcca_total_pressure_residual(block) == pytest.approx(0.0)
    assert AorticArchTotalPressureJunctionBlock.lsa_static_pressure_residual(block) == pytest.approx(0.0)
    assert AorticArchTotalPressureJunctionBlock.flux_aao(block) == pytest.approx(-aao_flow)
    assert AorticArchTotalPressureJunctionBlock.flux_dao(block) == pytest.approx(dao_flow)
    assert AorticArchTotalPressureJunctionBlock.flux_bca(block) == pytest.approx(bca_flow)
    assert AorticArchTotalPressureJunctionBlock.flux_lcca(block) == pytest.approx(lcca_flow)
    assert AorticArchTotalPressureJunctionBlock.flux_lsa(block) == pytest.approx(lsa_flow)
    assert AorticArchTotalPressureJunctionBlock.mass_balance(block) == pytest.approx(0.0)
    assert AorticArchTotalPressureJunctionBlock.total_pressure_spread(block) == pytest.approx(0.0)

    eps = 1.0e-10
    base = AorticArchTotalPressureJunctionBlock.dao_total_pressure_residual(block)
    analytic = block.dao_total_pressure_residual_daao_flow()
    block.aao_flow.update(aao_flow + eps)
    finite_difference = (
        AorticArchTotalPressureJunctionBlock.dao_total_pressure_residual(block) - base
    ) / eps
    assert finite_difference == pytest.approx(
        analytic,
        rel=1.0e-5,
    )


def test_tcpc_total_pressure_junction_is_mass_conserving_at_equilibrium():
    density = 1060.0
    area = 2.0e-4
    total_pressure = 900.0
    svc_flow = 2.0e-5
    ivc_flow = 3.0e-5
    rpa_flow = 3.1e-5
    lpa_flow = 1.9e-5
    block = TCPCTotalPressureJunctionBlock(
        svc_flow=q(svc_flow, svc_flow),
        ivc_flow=q(ivc_flow, ivc_flow),
        rpa_flow=q(rpa_flow, rpa_flow),
        lpa_flow=q(lpa_flow, lpa_flow),
        pressure_svc=q(pressure_for_total_pressure(total_pressure, svc_flow, area, density)),
        pressure_ivc=q(pressure_for_total_pressure(total_pressure, ivc_flow, area, density)),
        pressure_rpa=q(pressure_for_total_pressure(total_pressure, rpa_flow, area, density)),
        pressure_lpa=q(pressure_for_total_pressure(total_pressure, lpa_flow, area, density)),
        log_area_svc=q(np.log(area), np.log(area)),
        log_area_ivc=q(np.log(area), np.log(area)),
        log_area_rpa=q(np.log(area), np.log(area)),
        log_area_lpa=q(np.log(area), np.log(area)),
        density=q(density),
    )

    assert TCPCTotalPressureJunctionBlock.mass_residual(block) == pytest.approx(0.0)
    assert TCPCTotalPressureJunctionBlock.svc_total_pressure_residual(block) == pytest.approx(0.0)
    assert TCPCTotalPressureJunctionBlock.ivc_total_pressure_residual(block) == pytest.approx(0.0)
    assert TCPCTotalPressureJunctionBlock.lpa_total_pressure_residual(block) == pytest.approx(0.0)
    assert TCPCTotalPressureJunctionBlock.flux_svc(block) == pytest.approx(-svc_flow)
    assert TCPCTotalPressureJunctionBlock.flux_ivc(block) == pytest.approx(-ivc_flow)
    assert TCPCTotalPressureJunctionBlock.flux_rpa(block) == pytest.approx(rpa_flow)
    assert TCPCTotalPressureJunctionBlock.flux_lpa(block) == pytest.approx(lpa_flow)
    assert TCPCTotalPressureJunctionBlock.mass_balance(block) == pytest.approx(0.0)
    assert TCPCTotalPressureJunctionBlock.total_pressure_spread(block) == pytest.approx(0.0)

    eps = 1.0e-10
    base = TCPCTotalPressureJunctionBlock.svc_total_pressure_residual(block)
    analytic = block.svc_total_pressure_residual_dsvc_flow()
    block.svc_flow.update(svc_flow + eps)
    finite_difference = (
        TCPCTotalPressureJunctionBlock.svc_total_pressure_residual(block) - base
    ) / eps
    assert finite_difference == pytest.approx(
        analytic,
        rel=1.0e-5,
    )


def test_tcpc_characteristic_junction_keeps_equilibrium_and_adds_impedance_slope():
    density = 1060.0
    area = 2.0e-4
    wall_stiffness = sqrt_wall_stiffness_from_wave_speed(area, density, 6.0)
    svc_flow = 2.0e-5
    ivc_flow = 2.0e-5
    rpa_flow = 2.0e-5
    lpa_flow = 2.0e-5
    block = TCPCCharacteristicTotalPressureJunctionBlock(
        svc_flow=q(svc_flow, svc_flow),
        ivc_flow=q(ivc_flow, ivc_flow),
        rpa_flow=q(rpa_flow, rpa_flow),
        lpa_flow=q(lpa_flow, lpa_flow),
        pressure_svc=q(0.0),
        pressure_ivc=q(0.0),
        pressure_rpa=q(0.0),
        pressure_lpa=q(0.0),
        log_area_svc=q(np.log(area), np.log(area)),
        log_area_ivc=q(np.log(area), np.log(area)),
        log_area_rpa=q(np.log(area), np.log(area)),
        log_area_lpa=q(np.log(area), np.log(area)),
        reference_area_svc=q(area),
        reference_area_ivc=q(area),
        reference_area_rpa=q(area),
        reference_area_lpa=q(area),
        wall_stiffness_svc=q(wall_stiffness),
        wall_stiffness_ivc=q(wall_stiffness),
        wall_stiffness_rpa=q(wall_stiffness),
        wall_stiffness_lpa=q(wall_stiffness),
        external_pressure_svc=q(0.0),
        external_pressure_ivc=q(0.0),
        external_pressure_rpa=q(0.0),
        external_pressure_lpa=q(0.0),
        density=q(density),
        wall_pressure_weight=q(1.0),
        characteristic_scale=q(1.0),
        loss_coefficient=q(0.0),
    )

    assert TCPCCharacteristicTotalPressureJunctionBlock.mass_residual(block) == pytest.approx(0.0)
    assert TCPCCharacteristicTotalPressureJunctionBlock.svc_total_pressure_residual(block) == pytest.approx(0.0)
    assert TCPCCharacteristicTotalPressureJunctionBlock.ivc_total_pressure_residual(block) == pytest.approx(0.0)
    assert TCPCCharacteristicTotalPressureJunctionBlock.lpa_total_pressure_residual(block) == pytest.approx(0.0)
    assert TCPCCharacteristicTotalPressureJunctionBlock.total_pressure_spread(block) == pytest.approx(0.0)

    characteristic_slope = density * 6.0 / area
    assert TCPCCharacteristicTotalPressureJunctionBlock.svc_characteristic_impedance(
        block
    ) == pytest.approx(characteristic_slope)
    assert block.svc_total_pressure_residual_dsvc_flow() > characteristic_slope

    eps = 1.0e-10
    base = TCPCCharacteristicTotalPressureJunctionBlock.svc_total_pressure_residual(block)
    analytic = block.svc_total_pressure_residual_dsvc_flow()
    block.svc_flow.update(svc_flow + eps)
    finite_difference = (
        TCPCCharacteristicTotalPressureJunctionBlock.svc_total_pressure_residual(block)
        - base
    ) / eps
    assert finite_difference == pytest.approx(
        analytic,
        rel=1.0e-5,
    )


def test_tcpc_characteristic_junction_signed_losses_follow_branch_orientation():
    density = 1060.0
    area = 2.0e-4
    wall_stiffness = sqrt_wall_stiffness_from_wave_speed(area, density, 6.0)
    flow = 2.0e-5
    block = TCPCCharacteristicTotalPressureJunctionBlock(
        svc_flow=q(flow, flow),
        ivc_flow=q(flow, flow),
        rpa_flow=q(flow, flow),
        lpa_flow=q(flow, flow),
        pressure_svc=q(0.0),
        pressure_ivc=q(0.0),
        pressure_rpa=q(0.0),
        pressure_lpa=q(0.0),
        log_area_svc=q(np.log(area), np.log(area)),
        log_area_ivc=q(np.log(area), np.log(area)),
        log_area_rpa=q(np.log(area), np.log(area)),
        log_area_lpa=q(np.log(area), np.log(area)),
        reference_area_svc=q(area),
        reference_area_ivc=q(area),
        reference_area_rpa=q(area),
        reference_area_lpa=q(area),
        wall_stiffness_svc=q(wall_stiffness),
        wall_stiffness_ivc=q(wall_stiffness),
        wall_stiffness_rpa=q(wall_stiffness),
        wall_stiffness_lpa=q(wall_stiffness),
        external_pressure_svc=q(0.0),
        external_pressure_ivc=q(0.0),
        external_pressure_rpa=q(0.0),
        external_pressure_lpa=q(0.0),
        density=q(density),
        wall_pressure_weight=q(0.75),
        characteristic_scale=q(0.0),
        loss_coefficient=q(2.0),
    )

    expected_loss = 0.5 * density * 2.0 * flow * flow / (area * area)
    assert TCPCCharacteristicTotalPressureJunctionBlock.svc_loss_pressure(
        block
    ) == pytest.approx(-expected_loss)
    assert TCPCCharacteristicTotalPressureJunctionBlock.ivc_loss_pressure(
        block
    ) == pytest.approx(-expected_loss)
    assert TCPCCharacteristicTotalPressureJunctionBlock.rpa_loss_pressure(
        block
    ) == pytest.approx(expected_loss)
    assert TCPCCharacteristicTotalPressureJunctionBlock.lpa_loss_pressure(
        block
    ) == pytest.approx(expected_loss)
    assert (
        TCPCCharacteristicTotalPressureJunctionBlock.svc_total_pressure_residual(
            block
        )
        < 0.0
    )
    assert TCPCCharacteristicTotalPressureJunctionBlock.lpa_total_pressure_residual(
        block
    ) == pytest.approx(0.0)


def test_direct_block_residuals_fluxes_derivatives_and_saved_quantities():
    block = sample_block()
    params = sample_parameters()
    state = sample_state()
    residual = vessel_residual(**state, parameters=params)
    jacobian = vessel_jacobian_new(**state, parameters=params)

    np.testing.assert_allclose(
        Fixed3CellOneDVesselBlock.area_residual(block),
        residual.area,
    )
    np.testing.assert_allclose(
        Fixed3CellOneDVesselBlock.flow_residual(block),
        residual.flow,
    )
    np.testing.assert_allclose(block.flow_residual_darea_02(), jacobian.dflow_darea[:, 1])
    np.testing.assert_allclose(block.flow_residual_dflow_03(), jacobian.dflow_dflow[:, 3])
    np.testing.assert_allclose(
        block.flow_residual_dpressure_1(),
        jacobian.dflow_dpressure_1,
    )
    assert Fixed3CellOneDVesselBlock.flux_1(block) == pytest.approx(
        -mid_point(block.flow_00)
    )
    assert Fixed3CellOneDVesselBlock.flux_2(block) == pytest.approx(
        mid_point(block.flow_03)
    )
    assert port_fluxes([1.0, 2.0, 3.0, 4.0]) == (-1.0, 4.0)
    np.testing.assert_allclose(
        Fixed3CellOneDVesselBlock.cell_pressure(block),
        cell_pressures(0.5 * (state["current_area"] + state["new_area"]), params),
    )
    np.testing.assert_allclose(
        Fixed3CellOneDVesselBlock.cell_area(block),
        0.5 * (state["current_area"] + state["new_area"]),
    )
    np.testing.assert_allclose(
        Fixed3CellOneDVesselBlock.face_flow(block),
        0.5 * (state["current_flow"] + state["new_flow"]),
    )
    assert Fixed3CellOneDVesselBlock.stored_volume(block) == pytest.approx(
        stored_volume(0.5 * (state["current_area"] + state["new_area"]), params.length)
    )
    assert Fixed3CellOneDVesselBlock.min_area(block) == pytest.approx(
        np.min(0.5 * (state["current_area"] + state["new_area"]))
    )
    assert Fixed3CellOneDVesselBlock.negative_area_count(block) == 0


def test_physioblocks_assembles_true_1d_vessel_residual_gradient_and_saved_quantities():
    simulation = build_vessel_simulation()
    initialize_vessel_simulation(simulation)
    params = sample_parameters()
    state = sample_state()
    residual = vessel_residual(**state, parameters=params)
    jacobian = vessel_jacobian_new(**state, parameters=params)

    assert simulation.state.size == 9
    for name in [*AREA_IDS, *FLOW_IDS]:
        assert simulation.state.get_variable_size(f"vessel.{name}") == 1

    assembled_residual = simulation.eq_system.compute_residual()
    gradient = simulation.eq_system.compute_gradient()

    np.testing.assert_allclose(assembled_residual[:3], residual.area)
    np.testing.assert_allclose(assembled_residual[3:7], residual.flow)
    assert assembled_residual[7] == pytest.approx(-mid_point(sample_block().flow_00))
    assert assembled_residual[8] == pytest.approx(mid_point(sample_block().flow_03))
    assert gradient.shape == (9, 9)
    assert gradient[
        0,
        simulation.state.get_variable_index("vessel.area_01"),
    ] == pytest.approx(jacobian.darea_darea[0, 0])
    assert gradient[
        1,
        simulation.state.get_variable_index("vessel.flow_02"),
    ] == pytest.approx(jacobian.darea_dflow[1, 2])
    assert gradient[
        3,
        simulation.state.get_variable_index("inlet.blood_pressure"),
    ] == pytest.approx(jacobian.dflow_dpressure_1[0])
    assert gradient[
        6,
        simulation.state.get_variable_index("outlet.blood_pressure"),
    ] == pytest.approx(jacobian.dflow_dpressure_2[-1])
    assert gradient[
        7,
        simulation.state.get_variable_index("vessel.flow_00"),
    ] == pytest.approx(-0.5)
    assert gradient[
        8,
        simulation.state.get_variable_index("vessel.flow_03"),
    ] == pytest.approx(0.5)

    simulation.saved_quantities.update()
    assert simulation.saved_quantities[f"vessel.{CELL_PRESSURE_ID}"].size == 3
    assert simulation.saved_quantities[f"vessel.{CELL_AREA_ID}"].size == 3
    assert simulation.saved_quantities[f"vessel.{FACE_FLOW_ID}"].size == 4
    assert simulation.saved_quantities[f"vessel.{STORED_VOLUME_ID}"].current > 0.0
    assert simulation.saved_quantities[f"vessel.{MIN_AREA_ID}"].current > 0.0
    assert simulation.saved_quantities[f"vessel.{NEGATIVE_AREA_COUNT_ID}"].current == 0
