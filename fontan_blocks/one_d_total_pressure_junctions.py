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

AORTIC_ARCH_TOTAL_PRESSURE_JUNCTION_BLOCK_TYPE_ID = (
    "aortic_arch_total_pressure_junction_block"
)
TCPC_TOTAL_PRESSURE_JUNCTION_BLOCK_TYPE_ID = "tcpc_total_pressure_junction_block"
TCPC_CHARACTERISTIC_TOTAL_PRESSURE_JUNCTION_BLOCK_TYPE_ID = (
    "tcpc_characteristic_total_pressure_junction_block"
)

AAO_FLOW_ID = "aao_flow"
DAO_FLOW_ID = "dao_flow"
BCA_FLOW_ID = "bca_flow"
LCCA_FLOW_ID = "lcca_flow"
LSA_FLOW_ID = "lsa_flow"
SVC_FLOW_ID = "svc_flow"
IVC_FLOW_ID = "ivc_flow"
RPA_FLOW_ID = "rpa_flow"
LPA_FLOW_ID = "lpa_flow"

PRESSURE_AAO_ID = "pressure_aao"
PRESSURE_DAO_ID = "pressure_dao"
PRESSURE_BCA_ID = "pressure_bca"
PRESSURE_LCCA_ID = "pressure_lcca"
PRESSURE_LSA_ID = "pressure_lsa"
PRESSURE_SVC_ID = "pressure_svc"
PRESSURE_IVC_ID = "pressure_ivc"
PRESSURE_RPA_ID = "pressure_rpa"
PRESSURE_LPA_ID = "pressure_lpa"

LOG_AREA_AAO_ID = "log_area_aao"
LOG_AREA_DAO_ID = "log_area_dao"
LOG_AREA_BCA_ID = "log_area_bca"
LOG_AREA_LCCA_ID = "log_area_lcca"
LOG_AREA_SVC_ID = "log_area_svc"
LOG_AREA_IVC_ID = "log_area_ivc"
LOG_AREA_RPA_ID = "log_area_rpa"
LOG_AREA_LPA_ID = "log_area_lpa"

REFERENCE_AREA_SVC_ID = "reference_area_svc"
REFERENCE_AREA_IVC_ID = "reference_area_ivc"
REFERENCE_AREA_RPA_ID = "reference_area_rpa"
REFERENCE_AREA_LPA_ID = "reference_area_lpa"
WALL_STIFFNESS_SVC_ID = "wall_stiffness_svc"
WALL_STIFFNESS_IVC_ID = "wall_stiffness_ivc"
WALL_STIFFNESS_RPA_ID = "wall_stiffness_rpa"
WALL_STIFFNESS_LPA_ID = "wall_stiffness_lpa"
EXTERNAL_PRESSURE_SVC_ID = "external_pressure_svc"
EXTERNAL_PRESSURE_IVC_ID = "external_pressure_ivc"
EXTERNAL_PRESSURE_RPA_ID = "external_pressure_rpa"
EXTERNAL_PRESSURE_LPA_ID = "external_pressure_lpa"
WALL_PRESSURE_WEIGHT_ID = "wall_pressure_weight"
CHARACTERISTIC_SCALE_ID = "characteristic_scale"
LOSS_COEFFICIENT_ID = "loss_coefficient"
MASS_BALANCE_ID = "mass_balance"
TOTAL_PRESSURE_SPREAD_ID = "total_pressure_spread"

RIGHT_BOUNDARY_SIGN = 1.0
LEFT_BOUNDARY_SIGN = -1.0
INTO_BRANCH_SIGN = 1.0
INTO_JUNCTION_SIGN = -1.0
LOSS_FLOW_EPS = 1.0e-10


def _mid_area(log_area: Quantity[np.float64]) -> Any:
    return 0.5 * (np.exp(log_area.current) + np.exp(log_area.new))


def total_pressure(
    pressure: Quantity[np.float64],
    flow: Quantity[np.float64],
    log_area: Quantity[np.float64],
    density: Quantity[np.float64],
) -> Any:
    velocity = mid_point(flow) / _mid_area(log_area)
    return mid_point(pressure) + 0.5 * density.current * velocity * velocity


def total_pressure_dflow(
    flow: Quantity[np.float64],
    log_area: Quantity[np.float64],
    density: Quantity[np.float64],
) -> Any:
    area = _mid_area(log_area)
    return 0.5 * density.current * mid_point(flow) / (area * area)


def total_pressure_dlog_area(
    flow: Quantity[np.float64],
    log_area: Quantity[np.float64],
    density: Quantity[np.float64],
) -> Any:
    area = _mid_area(log_area)
    return (
        -0.5
        * density.current
        * mid_point(flow)
        * mid_point(flow)
        * np.exp(log_area.new)
        / (area * area * area)
    )


def velocity(flow: Quantity[np.float64], log_area: Quantity[np.float64]) -> Any:
    return mid_point(flow) / _mid_area(log_area)


def wall_pressure(
    log_area: Quantity[np.float64],
    reference_area: Quantity[np.float64],
    wall_stiffness: Quantity[np.float64],
    external_pressure: Quantity[np.float64],
) -> Any:
    area = _mid_area(log_area)
    return external_pressure.current + wall_stiffness.current * (
        np.sqrt(area) - np.sqrt(reference_area.current)
    )


def wall_total_pressure(
    flow: Quantity[np.float64],
    log_area: Quantity[np.float64],
    reference_area: Quantity[np.float64],
    wall_stiffness: Quantity[np.float64],
    external_pressure: Quantity[np.float64],
    density: Quantity[np.float64],
) -> Any:
    area = _mid_area(log_area)
    branch_velocity = mid_point(flow) / area
    return wall_pressure(
        log_area,
        reference_area,
        wall_stiffness,
        external_pressure,
    ) + 0.5 * density.current * branch_velocity * branch_velocity


def wall_total_pressure_dlog_area(
    flow: Quantity[np.float64],
    log_area: Quantity[np.float64],
    wall_stiffness: Quantity[np.float64],
    density: Quantity[np.float64],
) -> Any:
    area = _mid_area(log_area)
    wall_part = (
        wall_stiffness.current
        * np.exp(log_area.new)
        / (4.0 * np.sqrt(area))
    )
    return wall_part + total_pressure_dlog_area(flow, log_area, density)


def blended_total_pressure(
    pressure: Quantity[np.float64],
    flow: Quantity[np.float64],
    log_area: Quantity[np.float64],
    reference_area: Quantity[np.float64],
    wall_stiffness: Quantity[np.float64],
    external_pressure: Quantity[np.float64],
    density: Quantity[np.float64],
    wall_pressure_weight: Quantity[np.float64],
) -> Any:
    area = _mid_area(log_area)
    branch_velocity = mid_point(flow) / area
    branch_pressure = (
        wall_pressure_weight.current
        * wall_pressure(
            log_area,
            reference_area,
            wall_stiffness,
            external_pressure,
        )
        + (1.0 - wall_pressure_weight.current) * mid_point(pressure)
    )
    return branch_pressure + 0.5 * density.current * branch_velocity * branch_velocity


def blended_total_pressure_dlog_area(
    flow: Quantity[np.float64],
    log_area: Quantity[np.float64],
    wall_stiffness: Quantity[np.float64],
    density: Quantity[np.float64],
    wall_pressure_weight: Quantity[np.float64],
) -> Any:
    area = _mid_area(log_area)
    wall_part = (
        wall_pressure_weight.current
        * wall_stiffness.current
        * np.exp(log_area.new)
        / (4.0 * np.sqrt(area))
    )
    return wall_part + total_pressure_dlog_area(flow, log_area, density)


def characteristic_impedance(
    log_area: Quantity[np.float64],
    wall_stiffness: Quantity[np.float64],
    density: Quantity[np.float64],
) -> Any:
    area = np.exp(log_area.current)
    wave_speed = np.sqrt(
        wall_stiffness.current * np.sqrt(area) / (2.0 * density.current)
    )
    return density.current * wave_speed / area


def signed_minor_loss(
    flow: Quantity[np.float64],
    log_area: Quantity[np.float64],
    density: Quantity[np.float64],
    loss_coefficient: Quantity[np.float64],
    junction_to_branch_sign: float,
) -> Any:
    q_out = junction_to_branch_sign * mid_point(flow)
    area = _mid_area(log_area)
    smooth_abs_q = np.sqrt(q_out * q_out + LOSS_FLOW_EPS * LOSS_FLOW_EPS)
    return (
        0.5
        * density.current
        * loss_coefficient.current
        * q_out
        * smooth_abs_q
        / (area * area)
    )


def signed_minor_loss_dflow(
    flow: Quantity[np.float64],
    log_area: Quantity[np.float64],
    density: Quantity[np.float64],
    loss_coefficient: Quantity[np.float64],
    junction_to_branch_sign: float,
) -> Any:
    q_out = junction_to_branch_sign * mid_point(flow)
    area = _mid_area(log_area)
    smooth_abs_q = np.sqrt(q_out * q_out + LOSS_FLOW_EPS * LOSS_FLOW_EPS)
    dloss_dq = (
        0.5
        * density.current
        * loss_coefficient.current
        * (smooth_abs_q + q_out * q_out / smooth_abs_q)
        / (area * area)
    )
    return 0.5 * junction_to_branch_sign * dloss_dq


def signed_minor_loss_dlog_area(
    flow: Quantity[np.float64],
    log_area: Quantity[np.float64],
    density: Quantity[np.float64],
    loss_coefficient: Quantity[np.float64],
    junction_to_branch_sign: float,
) -> Any:
    loss = signed_minor_loss(
        flow,
        log_area,
        density,
        loss_coefficient,
        junction_to_branch_sign,
    )
    area = _mid_area(log_area)
    return -loss * np.exp(log_area.new) / area


def spread(values: list[Any]) -> float:
    floats = [float(value) for value in values]
    return max(floats) - min(floats)


@register_type(AORTIC_ARCH_TOTAL_PRESSURE_JUNCTION_BLOCK_TYPE_ID)
@dataclass
class AorticArchTotalPressureJunctionBlock(Block):
    """Massless paper-aligned aortic arch junction.

    Positive AAo flow enters the junction. Positive DAo, BCA, LCCA, and LSA
    flows leave the junction. DAo/BCA/LCCA use no-loss total-pressure
    compatibility against 1-D branch areas; the retained non-1-D LSA terminal
    outlet uses static pressure compatibility because no patient-specific LSA
    area is available.
    """

    aao_flow: Quantity[np.float64]
    dao_flow: Quantity[np.float64]
    bca_flow: Quantity[np.float64]
    lcca_flow: Quantity[np.float64]
    lsa_flow: Quantity[np.float64]
    pressure_aao: Quantity[np.float64]
    pressure_dao: Quantity[np.float64]
    pressure_bca: Quantity[np.float64]
    pressure_lcca: Quantity[np.float64]
    pressure_lsa: Quantity[np.float64]
    log_area_aao: Quantity[np.float64]
    log_area_dao: Quantity[np.float64]
    log_area_bca: Quantity[np.float64]
    log_area_lcca: Quantity[np.float64]
    density: Quantity[np.float64]

    def _h_aao(self) -> Any:
        return total_pressure(
            self.pressure_aao,
            self.aao_flow,
            self.log_area_aao,
            self.density,
        )

    def _h_dao(self) -> Any:
        return total_pressure(
            self.pressure_dao,
            self.dao_flow,
            self.log_area_dao,
            self.density,
        )

    def _h_bca(self) -> Any:
        return total_pressure(
            self.pressure_bca,
            self.bca_flow,
            self.log_area_bca,
            self.density,
        )

    def _h_lcca(self) -> Any:
        return total_pressure(
            self.pressure_lcca,
            self.lcca_flow,
            self.log_area_lcca,
            self.density,
        )

    @declares_internal_equation(AAO_FLOW_ID)
    def mass_residual(self) -> Any:
        return (
            mid_point(self.aao_flow)
            - mid_point(self.dao_flow)
            - mid_point(self.bca_flow)
            - mid_point(self.lcca_flow)
            - mid_point(self.lsa_flow)
        )

    @mass_residual.partial_derivative(AAO_FLOW_ID)
    def mass_residual_daao_flow(self) -> float:
        return 0.5

    @mass_residual.partial_derivative(DAO_FLOW_ID)
    def mass_residual_ddao_flow(self) -> float:
        return -0.5

    @mass_residual.partial_derivative(BCA_FLOW_ID)
    def mass_residual_dbca_flow(self) -> float:
        return -0.5

    @mass_residual.partial_derivative(LCCA_FLOW_ID)
    def mass_residual_dlcca_flow(self) -> float:
        return -0.5

    @mass_residual.partial_derivative(LSA_FLOW_ID)
    def mass_residual_dlsa_flow(self) -> float:
        return -0.5

    @declares_internal_equation(DAO_FLOW_ID)
    def dao_total_pressure_residual(self) -> Any:
        return self._h_aao() - self._h_dao()

    @dao_total_pressure_residual.partial_derivative(AAO_FLOW_ID)
    def dao_total_pressure_residual_daao_flow(self) -> Any:
        return total_pressure_dflow(self.aao_flow, self.log_area_aao, self.density)

    @dao_total_pressure_residual.partial_derivative(DAO_FLOW_ID)
    def dao_total_pressure_residual_ddao_flow(self) -> Any:
        return -total_pressure_dflow(self.dao_flow, self.log_area_dao, self.density)

    @dao_total_pressure_residual.partial_derivative(PRESSURE_AAO_ID)
    def dao_total_pressure_residual_dpressure_aao(self) -> float:
        return 0.5

    @dao_total_pressure_residual.partial_derivative(PRESSURE_DAO_ID)
    def dao_total_pressure_residual_dpressure_dao(self) -> float:
        return -0.5

    @dao_total_pressure_residual.partial_derivative(LOG_AREA_AAO_ID)
    def dao_total_pressure_residual_dlog_area_aao(self) -> Any:
        return total_pressure_dlog_area(
            self.aao_flow,
            self.log_area_aao,
            self.density,
        )

    @dao_total_pressure_residual.partial_derivative(LOG_AREA_DAO_ID)
    def dao_total_pressure_residual_dlog_area_dao(self) -> Any:
        return -total_pressure_dlog_area(
            self.dao_flow,
            self.log_area_dao,
            self.density,
        )

    @declares_internal_equation(BCA_FLOW_ID)
    def bca_total_pressure_residual(self) -> Any:
        return self._h_aao() - self._h_bca()

    @bca_total_pressure_residual.partial_derivative(AAO_FLOW_ID)
    def bca_total_pressure_residual_daao_flow(self) -> Any:
        return total_pressure_dflow(self.aao_flow, self.log_area_aao, self.density)

    @bca_total_pressure_residual.partial_derivative(BCA_FLOW_ID)
    def bca_total_pressure_residual_dbca_flow(self) -> Any:
        return -total_pressure_dflow(self.bca_flow, self.log_area_bca, self.density)

    @bca_total_pressure_residual.partial_derivative(PRESSURE_AAO_ID)
    def bca_total_pressure_residual_dpressure_aao(self) -> float:
        return 0.5

    @bca_total_pressure_residual.partial_derivative(PRESSURE_BCA_ID)
    def bca_total_pressure_residual_dpressure_bca(self) -> float:
        return -0.5

    @bca_total_pressure_residual.partial_derivative(LOG_AREA_AAO_ID)
    def bca_total_pressure_residual_dlog_area_aao(self) -> Any:
        return total_pressure_dlog_area(
            self.aao_flow,
            self.log_area_aao,
            self.density,
        )

    @bca_total_pressure_residual.partial_derivative(LOG_AREA_BCA_ID)
    def bca_total_pressure_residual_dlog_area_bca(self) -> Any:
        return -total_pressure_dlog_area(
            self.bca_flow,
            self.log_area_bca,
            self.density,
        )

    @declares_internal_equation(LCCA_FLOW_ID)
    def lcca_total_pressure_residual(self) -> Any:
        return self._h_aao() - self._h_lcca()

    @lcca_total_pressure_residual.partial_derivative(AAO_FLOW_ID)
    def lcca_total_pressure_residual_daao_flow(self) -> Any:
        return total_pressure_dflow(self.aao_flow, self.log_area_aao, self.density)

    @lcca_total_pressure_residual.partial_derivative(LCCA_FLOW_ID)
    def lcca_total_pressure_residual_dlcca_flow(self) -> Any:
        return -total_pressure_dflow(self.lcca_flow, self.log_area_lcca, self.density)

    @lcca_total_pressure_residual.partial_derivative(PRESSURE_AAO_ID)
    def lcca_total_pressure_residual_dpressure_aao(self) -> float:
        return 0.5

    @lcca_total_pressure_residual.partial_derivative(PRESSURE_LCCA_ID)
    def lcca_total_pressure_residual_dpressure_lcca(self) -> float:
        return -0.5

    @lcca_total_pressure_residual.partial_derivative(LOG_AREA_AAO_ID)
    def lcca_total_pressure_residual_dlog_area_aao(self) -> Any:
        return total_pressure_dlog_area(
            self.aao_flow,
            self.log_area_aao,
            self.density,
        )

    @lcca_total_pressure_residual.partial_derivative(LOG_AREA_LCCA_ID)
    def lcca_total_pressure_residual_dlog_area_lcca(self) -> Any:
        return -total_pressure_dlog_area(
            self.lcca_flow,
            self.log_area_lcca,
            self.density,
        )

    @declares_internal_equation(LSA_FLOW_ID)
    def lsa_static_pressure_residual(self) -> Any:
        return self._h_aao() - mid_point(self.pressure_lsa)

    @lsa_static_pressure_residual.partial_derivative(AAO_FLOW_ID)
    def lsa_static_pressure_residual_daao_flow(self) -> Any:
        return total_pressure_dflow(self.aao_flow, self.log_area_aao, self.density)

    @lsa_static_pressure_residual.partial_derivative(PRESSURE_AAO_ID)
    def lsa_static_pressure_residual_dpressure_aao(self) -> float:
        return 0.5

    @lsa_static_pressure_residual.partial_derivative(PRESSURE_LSA_ID)
    def lsa_static_pressure_residual_dpressure_lsa(self) -> float:
        return -0.5

    @lsa_static_pressure_residual.partial_derivative(LOG_AREA_AAO_ID)
    def lsa_static_pressure_residual_dlog_area_aao(self) -> Any:
        return total_pressure_dlog_area(
            self.aao_flow,
            self.log_area_aao,
            self.density,
        )

    @declares_flux(1, PRESSURE_AAO_ID)
    def flux_aao(self) -> Any:
        return -mid_point(self.aao_flow)

    @flux_aao.partial_derivative(AAO_FLOW_ID)
    def flux_aao_daao_flow(self) -> float:
        return -0.5

    @declares_flux(2, PRESSURE_DAO_ID)
    def flux_dao(self) -> Any:
        return mid_point(self.dao_flow)

    @flux_dao.partial_derivative(DAO_FLOW_ID)
    def flux_dao_ddao_flow(self) -> float:
        return 0.5

    @declares_flux(3, PRESSURE_BCA_ID)
    def flux_bca(self) -> Any:
        return mid_point(self.bca_flow)

    @flux_bca.partial_derivative(BCA_FLOW_ID)
    def flux_bca_dbca_flow(self) -> float:
        return 0.5

    @declares_flux(4, PRESSURE_LCCA_ID)
    def flux_lcca(self) -> Any:
        return mid_point(self.lcca_flow)

    @flux_lcca.partial_derivative(LCCA_FLOW_ID)
    def flux_lcca_dlcca_flow(self) -> float:
        return 0.5

    @declares_flux(5, PRESSURE_LSA_ID)
    def flux_lsa(self) -> Any:
        return mid_point(self.lsa_flow)

    @flux_lsa.partial_derivative(LSA_FLOW_ID)
    def flux_lsa_dlsa_flow(self) -> float:
        return 0.5

    @declares_saved_quantity(MASS_BALANCE_ID)
    def mass_balance(self) -> float:
        return float(
            mid_point(self.aao_flow)
            - mid_point(self.dao_flow)
            - mid_point(self.bca_flow)
            - mid_point(self.lcca_flow)
            - mid_point(self.lsa_flow)
        )

    @declares_saved_quantity("aao_total_pressure")
    def aao_total_pressure(self) -> float:
        return float(self._h_aao())

    @declares_saved_quantity("dao_total_pressure")
    def dao_total_pressure(self) -> float:
        return float(self._h_dao())

    @declares_saved_quantity("bca_total_pressure")
    def bca_total_pressure(self) -> float:
        return float(self._h_bca())

    @declares_saved_quantity("lcca_total_pressure")
    def lcca_total_pressure(self) -> float:
        return float(self._h_lcca())

    @declares_saved_quantity("lsa_static_pressure")
    def lsa_static_pressure(self) -> float:
        return float(mid_point(self.pressure_lsa))

    @declares_saved_quantity(TOTAL_PRESSURE_SPREAD_ID)
    def total_pressure_spread(self) -> float:
        return spread(
            [
                self._h_aao(),
                self._h_dao(),
                self._h_bca(),
                self._h_lcca(),
                mid_point(self.pressure_lsa),
            ]
        )

    @declares_saved_quantity("aao_velocity")
    def aao_velocity(self) -> float:
        return float(velocity(self.aao_flow, self.log_area_aao))

    @declares_saved_quantity("dao_velocity")
    def dao_velocity(self) -> float:
        return float(velocity(self.dao_flow, self.log_area_dao))

    @declares_saved_quantity("bca_velocity")
    def bca_velocity(self) -> float:
        return float(velocity(self.bca_flow, self.log_area_bca))

    @declares_saved_quantity("lcca_velocity")
    def lcca_velocity(self) -> float:
        return float(velocity(self.lcca_flow, self.log_area_lcca))


@register_type(TCPC_TOTAL_PRESSURE_JUNCTION_BLOCK_TYPE_ID)
@dataclass
class TCPCTotalPressureJunctionBlock(Block):
    """Massless paper-aligned TCPC four-port junction.

    Positive SVC and IVC flows enter the junction. Positive RPA and LPA flows
    leave the junction. The block enforces mass conservation and no-loss total
    pressure compatibility without finite junction storage.
    """

    svc_flow: Quantity[np.float64]
    ivc_flow: Quantity[np.float64]
    rpa_flow: Quantity[np.float64]
    lpa_flow: Quantity[np.float64]
    pressure_svc: Quantity[np.float64]
    pressure_ivc: Quantity[np.float64]
    pressure_rpa: Quantity[np.float64]
    pressure_lpa: Quantity[np.float64]
    log_area_svc: Quantity[np.float64]
    log_area_ivc: Quantity[np.float64]
    log_area_rpa: Quantity[np.float64]
    log_area_lpa: Quantity[np.float64]
    density: Quantity[np.float64]

    def _h_svc(self) -> Any:
        return total_pressure(
            self.pressure_svc,
            self.svc_flow,
            self.log_area_svc,
            self.density,
        )

    def _h_ivc(self) -> Any:
        return total_pressure(
            self.pressure_ivc,
            self.ivc_flow,
            self.log_area_ivc,
            self.density,
        )

    def _h_rpa(self) -> Any:
        return total_pressure(
            self.pressure_rpa,
            self.rpa_flow,
            self.log_area_rpa,
            self.density,
        )

    def _h_lpa(self) -> Any:
        return total_pressure(
            self.pressure_lpa,
            self.lpa_flow,
            self.log_area_lpa,
            self.density,
        )

    @declares_internal_equation(SVC_FLOW_ID)
    def mass_residual(self) -> Any:
        return (
            mid_point(self.svc_flow)
            + mid_point(self.ivc_flow)
            - mid_point(self.rpa_flow)
            - mid_point(self.lpa_flow)
        )

    @mass_residual.partial_derivative(SVC_FLOW_ID)
    def mass_residual_dsvc_flow(self) -> float:
        return 0.5

    @mass_residual.partial_derivative(IVC_FLOW_ID)
    def mass_residual_divc_flow(self) -> float:
        return 0.5

    @mass_residual.partial_derivative(RPA_FLOW_ID)
    def mass_residual_drpa_flow(self) -> float:
        return -0.5

    @mass_residual.partial_derivative(LPA_FLOW_ID)
    def mass_residual_dlpa_flow(self) -> float:
        return -0.5

    @declares_internal_equation(IVC_FLOW_ID)
    def ivc_total_pressure_residual(self) -> Any:
        return self._h_ivc() - self._h_rpa()

    @ivc_total_pressure_residual.partial_derivative(IVC_FLOW_ID)
    def ivc_total_pressure_residual_divc_flow(self) -> Any:
        return total_pressure_dflow(self.ivc_flow, self.log_area_ivc, self.density)

    @ivc_total_pressure_residual.partial_derivative(RPA_FLOW_ID)
    def ivc_total_pressure_residual_drpa_flow(self) -> Any:
        return -total_pressure_dflow(self.rpa_flow, self.log_area_rpa, self.density)

    @ivc_total_pressure_residual.partial_derivative(PRESSURE_IVC_ID)
    def ivc_total_pressure_residual_dpressure_ivc(self) -> float:
        return 0.0

    @ivc_total_pressure_residual.partial_derivative(PRESSURE_RPA_ID)
    def ivc_total_pressure_residual_dpressure_rpa(self) -> float:
        return 0.0

    @ivc_total_pressure_residual.partial_derivative(LOG_AREA_IVC_ID)
    def ivc_total_pressure_residual_dlog_area_ivc(self) -> Any:
        return total_pressure_dlog_area(
            self.ivc_flow,
            self.log_area_ivc,
            self.density,
        )

    @ivc_total_pressure_residual.partial_derivative(LOG_AREA_RPA_ID)
    def ivc_total_pressure_residual_dlog_area_rpa(self) -> Any:
        return -total_pressure_dlog_area(
            self.rpa_flow,
            self.log_area_rpa,
            self.density,
        )

    @declares_internal_equation(RPA_FLOW_ID)
    def svc_total_pressure_residual(self) -> Any:
        return self._h_svc() - self._h_rpa()

    @svc_total_pressure_residual.partial_derivative(SVC_FLOW_ID)
    def svc_total_pressure_residual_dsvc_flow(self) -> Any:
        return total_pressure_dflow(self.svc_flow, self.log_area_svc, self.density)

    @svc_total_pressure_residual.partial_derivative(RPA_FLOW_ID)
    def svc_total_pressure_residual_drpa_flow(self) -> Any:
        return -total_pressure_dflow(self.rpa_flow, self.log_area_rpa, self.density)

    @svc_total_pressure_residual.partial_derivative(PRESSURE_SVC_ID)
    def svc_total_pressure_residual_dpressure_svc(self) -> float:
        return 0.0

    @svc_total_pressure_residual.partial_derivative(PRESSURE_RPA_ID)
    def svc_total_pressure_residual_dpressure_rpa(self) -> float:
        return 0.0

    @svc_total_pressure_residual.partial_derivative(LOG_AREA_SVC_ID)
    def svc_total_pressure_residual_dlog_area_svc(self) -> Any:
        return total_pressure_dlog_area(
            self.svc_flow,
            self.log_area_svc,
            self.density,
        )

    @svc_total_pressure_residual.partial_derivative(LOG_AREA_RPA_ID)
    def svc_total_pressure_residual_dlog_area_rpa(self) -> Any:
        return -total_pressure_dlog_area(
            self.rpa_flow,
            self.log_area_rpa,
            self.density,
        )

    @declares_internal_equation(LPA_FLOW_ID)
    def lpa_total_pressure_residual(self) -> Any:
        return self._h_lpa() - self._h_rpa()

    @lpa_total_pressure_residual.partial_derivative(LPA_FLOW_ID)
    def lpa_total_pressure_residual_dlpa_flow(self) -> Any:
        return total_pressure_dflow(self.lpa_flow, self.log_area_lpa, self.density)

    @lpa_total_pressure_residual.partial_derivative(RPA_FLOW_ID)
    def lpa_total_pressure_residual_drpa_flow(self) -> Any:
        return -total_pressure_dflow(self.rpa_flow, self.log_area_rpa, self.density)

    @lpa_total_pressure_residual.partial_derivative(PRESSURE_LPA_ID)
    def lpa_total_pressure_residual_dpressure_lpa(self) -> float:
        return 0.0

    @lpa_total_pressure_residual.partial_derivative(PRESSURE_RPA_ID)
    def lpa_total_pressure_residual_dpressure_rpa(self) -> float:
        return 0.0

    @lpa_total_pressure_residual.partial_derivative(LOG_AREA_LPA_ID)
    def lpa_total_pressure_residual_dlog_area_lpa(self) -> Any:
        return total_pressure_dlog_area(
            self.lpa_flow,
            self.log_area_lpa,
            self.density,
        )

    @lpa_total_pressure_residual.partial_derivative(LOG_AREA_RPA_ID)
    def lpa_total_pressure_residual_dlog_area_rpa(self) -> Any:
        return -total_pressure_dlog_area(
            self.rpa_flow,
            self.log_area_rpa,
            self.density,
        )

    @declares_flux(1, PRESSURE_SVC_ID)
    def flux_svc(self) -> Any:
        return -mid_point(self.svc_flow)

    @flux_svc.partial_derivative(SVC_FLOW_ID)
    def flux_svc_dsvc_flow(self) -> float:
        return -0.5

    @declares_flux(2, PRESSURE_IVC_ID)
    def flux_ivc(self) -> Any:
        return -mid_point(self.ivc_flow)

    @flux_ivc.partial_derivative(IVC_FLOW_ID)
    def flux_ivc_divc_flow(self) -> float:
        return -0.5

    @declares_flux(3, PRESSURE_RPA_ID)
    def flux_rpa(self) -> Any:
        return mid_point(self.rpa_flow)

    @flux_rpa.partial_derivative(RPA_FLOW_ID)
    def flux_rpa_drpa_flow(self) -> float:
        return 0.5

    @declares_flux(4, PRESSURE_LPA_ID)
    def flux_lpa(self) -> Any:
        return mid_point(self.lpa_flow)

    @flux_lpa.partial_derivative(LPA_FLOW_ID)
    def flux_lpa_dlpa_flow(self) -> float:
        return 0.5

    @declares_saved_quantity(MASS_BALANCE_ID)
    def mass_balance(self) -> float:
        return float(
            mid_point(self.svc_flow)
            + mid_point(self.ivc_flow)
            - mid_point(self.rpa_flow)
            - mid_point(self.lpa_flow)
        )

    @declares_saved_quantity("svc_total_pressure")
    def svc_total_pressure(self) -> float:
        return float(self._h_svc())

    @declares_saved_quantity("ivc_total_pressure")
    def ivc_total_pressure(self) -> float:
        return float(self._h_ivc())

    @declares_saved_quantity("rpa_total_pressure")
    def rpa_total_pressure(self) -> float:
        return float(self._h_rpa())

    @declares_saved_quantity("lpa_total_pressure")
    def lpa_total_pressure(self) -> float:
        return float(self._h_lpa())

    def _loss_svc(self) -> float:
        return 0.0

    def _loss_ivc(self) -> float:
        return 0.0

    def _loss_rpa(self) -> float:
        return 0.0

    def _loss_lpa(self) -> float:
        return 0.0

    def _effective_h_svc(self) -> Any:
        return self._h_svc()

    def _effective_h_ivc(self) -> Any:
        return self._h_ivc()

    def _effective_h_rpa(self) -> Any:
        return self._h_rpa()

    def _effective_h_lpa(self) -> Any:
        return self._h_lpa()

    @declares_saved_quantity("svc_loss_pressure")
    def svc_loss_pressure(self) -> float:
        return float(self._loss_svc())

    @declares_saved_quantity("ivc_loss_pressure")
    def ivc_loss_pressure(self) -> float:
        return float(self._loss_ivc())

    @declares_saved_quantity("rpa_loss_pressure")
    def rpa_loss_pressure(self) -> float:
        return float(self._loss_rpa())

    @declares_saved_quantity("lpa_loss_pressure")
    def lpa_loss_pressure(self) -> float:
        return float(self._loss_lpa())

    @declares_saved_quantity("svc_effective_total_pressure")
    def svc_effective_total_pressure(self) -> float:
        return float(self._effective_h_svc())

    @declares_saved_quantity("ivc_effective_total_pressure")
    def ivc_effective_total_pressure(self) -> float:
        return float(self._effective_h_ivc())

    @declares_saved_quantity("rpa_effective_total_pressure")
    def rpa_effective_total_pressure(self) -> float:
        return float(self._effective_h_rpa())

    @declares_saved_quantity("lpa_effective_total_pressure")
    def lpa_effective_total_pressure(self) -> float:
        return float(self._effective_h_lpa())

    @declares_saved_quantity(TOTAL_PRESSURE_SPREAD_ID)
    def total_pressure_spread(self) -> float:
        return spread(
            [
                self._effective_h_svc(),
                self._effective_h_ivc(),
                self._effective_h_rpa(),
                self._effective_h_lpa(),
            ]
        )

    @declares_saved_quantity("svc_velocity")
    def svc_velocity(self) -> float:
        return float(velocity(self.svc_flow, self.log_area_svc))

    @declares_saved_quantity("ivc_velocity")
    def ivc_velocity(self) -> float:
        return float(velocity(self.ivc_flow, self.log_area_ivc))

    @declares_saved_quantity("rpa_velocity")
    def rpa_velocity(self) -> float:
        return float(velocity(self.rpa_flow, self.log_area_rpa))

    @declares_saved_quantity("lpa_velocity")
    def lpa_velocity(self) -> float:
        return float(velocity(self.lpa_flow, self.log_area_lpa))


@register_type(TCPC_CHARACTERISTIC_TOTAL_PRESSURE_JUNCTION_BLOCK_TYPE_ID)
@dataclass
class TCPCCharacteristicTotalPressureJunctionBlock(Block):
    """Massless TCPC junction with characteristic-stabilized compatibility.

    The Nektar implementation solves TCPC bijunction/union boundaries as local
    Riemann problems: incoming characteristic information from each 1-D branch
    is combined with mass conservation and total-pressure compatibility. This
    PhysioBlocks block keeps the same massless four-port topology as the
    no-loss algebraic candidate, but computes branch total pressure from a
    blend of nodal pressure and wall-law pressure implied by each terminal 1-D
    area. It also adds signed dynamic minor losses using the junction-to-branch
    flow direction. This matches the paper's branch-wall coupling more closely
    than using independent nodal pressures alone, while retaining an explicit
    TCPC dissipation term. Linearized characteristic impedance terms may be
    blended in; the terms vanish at steady flow and add pressure-flow slope
    near low or reversing flow, where a pure total-pressure equality is poorly
    conditioned.
    """

    svc_flow: Quantity[np.float64]
    ivc_flow: Quantity[np.float64]
    rpa_flow: Quantity[np.float64]
    lpa_flow: Quantity[np.float64]
    pressure_svc: Quantity[np.float64]
    pressure_ivc: Quantity[np.float64]
    pressure_rpa: Quantity[np.float64]
    pressure_lpa: Quantity[np.float64]
    log_area_svc: Quantity[np.float64]
    log_area_ivc: Quantity[np.float64]
    log_area_rpa: Quantity[np.float64]
    log_area_lpa: Quantity[np.float64]
    reference_area_svc: Quantity[np.float64]
    reference_area_ivc: Quantity[np.float64]
    reference_area_rpa: Quantity[np.float64]
    reference_area_lpa: Quantity[np.float64]
    wall_stiffness_svc: Quantity[np.float64]
    wall_stiffness_ivc: Quantity[np.float64]
    wall_stiffness_rpa: Quantity[np.float64]
    wall_stiffness_lpa: Quantity[np.float64]
    external_pressure_svc: Quantity[np.float64]
    external_pressure_ivc: Quantity[np.float64]
    external_pressure_rpa: Quantity[np.float64]
    external_pressure_lpa: Quantity[np.float64]
    density: Quantity[np.float64]
    wall_pressure_weight: Quantity[np.float64]
    characteristic_scale: Quantity[np.float64]
    loss_coefficient: Quantity[np.float64]

    def _h_svc(self) -> Any:
        return blended_total_pressure(
            self.pressure_svc,
            self.svc_flow,
            self.log_area_svc,
            self.reference_area_svc,
            self.wall_stiffness_svc,
            self.external_pressure_svc,
            self.density,
            self.wall_pressure_weight,
        )

    def _h_ivc(self) -> Any:
        return blended_total_pressure(
            self.pressure_ivc,
            self.ivc_flow,
            self.log_area_ivc,
            self.reference_area_ivc,
            self.wall_stiffness_ivc,
            self.external_pressure_ivc,
            self.density,
            self.wall_pressure_weight,
        )

    def _h_rpa(self) -> Any:
        return blended_total_pressure(
            self.pressure_rpa,
            self.rpa_flow,
            self.log_area_rpa,
            self.reference_area_rpa,
            self.wall_stiffness_rpa,
            self.external_pressure_rpa,
            self.density,
            self.wall_pressure_weight,
        )

    def _h_lpa(self) -> Any:
        return blended_total_pressure(
            self.pressure_lpa,
            self.lpa_flow,
            self.log_area_lpa,
            self.reference_area_lpa,
            self.wall_stiffness_lpa,
            self.external_pressure_lpa,
            self.density,
            self.wall_pressure_weight,
        )

    def _z_svc(self) -> Any:
        return characteristic_impedance(
            self.log_area_svc,
            self.wall_stiffness_svc,
            self.density,
        )

    def _z_ivc(self) -> Any:
        return characteristic_impedance(
            self.log_area_ivc,
            self.wall_stiffness_ivc,
            self.density,
        )

    def _z_rpa(self) -> Any:
        return characteristic_impedance(
            self.log_area_rpa,
            self.wall_stiffness_rpa,
            self.density,
        )

    def _z_lpa(self) -> Any:
        return characteristic_impedance(
            self.log_area_lpa,
            self.wall_stiffness_lpa,
            self.density,
        )

    def _characteristic_delta(
        self,
        flow: Quantity[np.float64],
        impedance: Any,
        boundary_sign: float,
    ) -> Any:
        return (
            self.characteristic_scale.current
            * boundary_sign
            * impedance
            * (flow.new - flow.current)
        )

    def _characteristic_delta_dflow(
        self,
        impedance: Any,
        boundary_sign: float,
    ) -> Any:
        return self.characteristic_scale.current * boundary_sign * impedance

    def _svc_delta(self) -> Any:
        return self._characteristic_delta(
            self.svc_flow,
            self._z_svc(),
            RIGHT_BOUNDARY_SIGN,
        )

    def _ivc_delta(self) -> Any:
        return self._characteristic_delta(
            self.ivc_flow,
            self._z_ivc(),
            RIGHT_BOUNDARY_SIGN,
        )

    def _rpa_delta(self) -> Any:
        return self._characteristic_delta(
            self.rpa_flow,
            self._z_rpa(),
            LEFT_BOUNDARY_SIGN,
        )

    def _lpa_delta(self) -> Any:
        return self._characteristic_delta(
            self.lpa_flow,
            self._z_lpa(),
            LEFT_BOUNDARY_SIGN,
        )

    def _loss_svc(self) -> Any:
        return signed_minor_loss(
            self.svc_flow,
            self.log_area_svc,
            self.density,
            self.loss_coefficient,
            INTO_JUNCTION_SIGN,
        )

    def _loss_ivc(self) -> Any:
        return signed_minor_loss(
            self.ivc_flow,
            self.log_area_ivc,
            self.density,
            self.loss_coefficient,
            INTO_JUNCTION_SIGN,
        )

    def _loss_rpa(self) -> Any:
        return signed_minor_loss(
            self.rpa_flow,
            self.log_area_rpa,
            self.density,
            self.loss_coefficient,
            INTO_BRANCH_SIGN,
        )

    def _loss_lpa(self) -> Any:
        return signed_minor_loss(
            self.lpa_flow,
            self.log_area_lpa,
            self.density,
            self.loss_coefficient,
            INTO_BRANCH_SIGN,
        )

    def _effective_h_svc(self) -> Any:
        return self._h_svc() + self._loss_svc()

    def _effective_h_ivc(self) -> Any:
        return self._h_ivc() + self._loss_ivc()

    def _effective_h_rpa(self) -> Any:
        return self._h_rpa() + self._loss_rpa()

    def _effective_h_lpa(self) -> Any:
        return self._h_lpa() + self._loss_lpa()

    @declares_internal_equation(SVC_FLOW_ID)
    def mass_residual(self) -> Any:
        return (
            mid_point(self.svc_flow)
            + mid_point(self.ivc_flow)
            - mid_point(self.rpa_flow)
            - mid_point(self.lpa_flow)
        )

    @mass_residual.partial_derivative(SVC_FLOW_ID)
    def mass_residual_dsvc_flow(self) -> float:
        return 0.5

    @mass_residual.partial_derivative(IVC_FLOW_ID)
    def mass_residual_divc_flow(self) -> float:
        return 0.5

    @mass_residual.partial_derivative(RPA_FLOW_ID)
    def mass_residual_drpa_flow(self) -> float:
        return -0.5

    @mass_residual.partial_derivative(LPA_FLOW_ID)
    def mass_residual_dlpa_flow(self) -> float:
        return -0.5

    @declares_internal_equation(IVC_FLOW_ID)
    def ivc_total_pressure_residual(self) -> Any:
        return (
            self._effective_h_ivc()
            - self._effective_h_rpa()
            + self._ivc_delta()
            - self._rpa_delta()
        )

    @ivc_total_pressure_residual.partial_derivative(IVC_FLOW_ID)
    def ivc_total_pressure_residual_divc_flow(self) -> Any:
        return total_pressure_dflow(
            self.ivc_flow,
            self.log_area_ivc,
            self.density,
        ) + signed_minor_loss_dflow(
            self.ivc_flow,
            self.log_area_ivc,
            self.density,
            self.loss_coefficient,
            INTO_JUNCTION_SIGN,
        ) + self._characteristic_delta_dflow(self._z_ivc(), RIGHT_BOUNDARY_SIGN)

    @ivc_total_pressure_residual.partial_derivative(RPA_FLOW_ID)
    def ivc_total_pressure_residual_drpa_flow(self) -> Any:
        return -total_pressure_dflow(
            self.rpa_flow,
            self.log_area_rpa,
            self.density,
        ) - signed_minor_loss_dflow(
            self.rpa_flow,
            self.log_area_rpa,
            self.density,
            self.loss_coefficient,
            INTO_BRANCH_SIGN,
        ) - self._characteristic_delta_dflow(self._z_rpa(), LEFT_BOUNDARY_SIGN)

    @ivc_total_pressure_residual.partial_derivative(PRESSURE_IVC_ID)
    def ivc_total_pressure_residual_dpressure_ivc(self) -> float:
        return 0.5 * (1.0 - self.wall_pressure_weight.current)

    @ivc_total_pressure_residual.partial_derivative(PRESSURE_RPA_ID)
    def ivc_total_pressure_residual_dpressure_rpa(self) -> float:
        return -0.5 * (1.0 - self.wall_pressure_weight.current)

    @ivc_total_pressure_residual.partial_derivative(LOG_AREA_IVC_ID)
    def ivc_total_pressure_residual_dlog_area_ivc(self) -> Any:
        return blended_total_pressure_dlog_area(
            self.ivc_flow,
            self.log_area_ivc,
            self.wall_stiffness_ivc,
            self.density,
            self.wall_pressure_weight,
        ) + signed_minor_loss_dlog_area(
            self.ivc_flow,
            self.log_area_ivc,
            self.density,
            self.loss_coefficient,
            INTO_JUNCTION_SIGN,
        )

    @ivc_total_pressure_residual.partial_derivative(LOG_AREA_RPA_ID)
    def ivc_total_pressure_residual_dlog_area_rpa(self) -> Any:
        return -blended_total_pressure_dlog_area(
            self.rpa_flow,
            self.log_area_rpa,
            self.wall_stiffness_rpa,
            self.density,
            self.wall_pressure_weight,
        ) - signed_minor_loss_dlog_area(
            self.rpa_flow,
            self.log_area_rpa,
            self.density,
            self.loss_coefficient,
            INTO_BRANCH_SIGN,
        )

    @declares_internal_equation(RPA_FLOW_ID)
    def svc_total_pressure_residual(self) -> Any:
        return (
            self._effective_h_svc()
            - self._effective_h_rpa()
            + self._svc_delta()
            - self._rpa_delta()
        )

    @svc_total_pressure_residual.partial_derivative(SVC_FLOW_ID)
    def svc_total_pressure_residual_dsvc_flow(self) -> Any:
        return total_pressure_dflow(
            self.svc_flow,
            self.log_area_svc,
            self.density,
        ) + signed_minor_loss_dflow(
            self.svc_flow,
            self.log_area_svc,
            self.density,
            self.loss_coefficient,
            INTO_JUNCTION_SIGN,
        ) + self._characteristic_delta_dflow(self._z_svc(), RIGHT_BOUNDARY_SIGN)

    @svc_total_pressure_residual.partial_derivative(RPA_FLOW_ID)
    def svc_total_pressure_residual_drpa_flow(self) -> Any:
        return -total_pressure_dflow(
            self.rpa_flow,
            self.log_area_rpa,
            self.density,
        ) - signed_minor_loss_dflow(
            self.rpa_flow,
            self.log_area_rpa,
            self.density,
            self.loss_coefficient,
            INTO_BRANCH_SIGN,
        ) - self._characteristic_delta_dflow(self._z_rpa(), LEFT_BOUNDARY_SIGN)

    @svc_total_pressure_residual.partial_derivative(PRESSURE_SVC_ID)
    def svc_total_pressure_residual_dpressure_svc(self) -> float:
        return 0.5 * (1.0 - self.wall_pressure_weight.current)

    @svc_total_pressure_residual.partial_derivative(PRESSURE_RPA_ID)
    def svc_total_pressure_residual_dpressure_rpa(self) -> float:
        return -0.5 * (1.0 - self.wall_pressure_weight.current)

    @svc_total_pressure_residual.partial_derivative(LOG_AREA_SVC_ID)
    def svc_total_pressure_residual_dlog_area_svc(self) -> Any:
        return blended_total_pressure_dlog_area(
            self.svc_flow,
            self.log_area_svc,
            self.wall_stiffness_svc,
            self.density,
            self.wall_pressure_weight,
        ) + signed_minor_loss_dlog_area(
            self.svc_flow,
            self.log_area_svc,
            self.density,
            self.loss_coefficient,
            INTO_JUNCTION_SIGN,
        )

    @svc_total_pressure_residual.partial_derivative(LOG_AREA_RPA_ID)
    def svc_total_pressure_residual_dlog_area_rpa(self) -> Any:
        return -blended_total_pressure_dlog_area(
            self.rpa_flow,
            self.log_area_rpa,
            self.wall_stiffness_rpa,
            self.density,
            self.wall_pressure_weight,
        ) - signed_minor_loss_dlog_area(
            self.rpa_flow,
            self.log_area_rpa,
            self.density,
            self.loss_coefficient,
            INTO_BRANCH_SIGN,
        )

    @declares_internal_equation(LPA_FLOW_ID)
    def lpa_total_pressure_residual(self) -> Any:
        return (
            self._effective_h_lpa()
            - self._effective_h_rpa()
            + self._lpa_delta()
            - self._rpa_delta()
        )

    @lpa_total_pressure_residual.partial_derivative(LPA_FLOW_ID)
    def lpa_total_pressure_residual_dlpa_flow(self) -> Any:
        return total_pressure_dflow(
            self.lpa_flow,
            self.log_area_lpa,
            self.density,
        ) + signed_minor_loss_dflow(
            self.lpa_flow,
            self.log_area_lpa,
            self.density,
            self.loss_coefficient,
            INTO_BRANCH_SIGN,
        ) + self._characteristic_delta_dflow(self._z_lpa(), LEFT_BOUNDARY_SIGN)

    @lpa_total_pressure_residual.partial_derivative(RPA_FLOW_ID)
    def lpa_total_pressure_residual_drpa_flow(self) -> Any:
        return -total_pressure_dflow(
            self.rpa_flow,
            self.log_area_rpa,
            self.density,
        ) - signed_minor_loss_dflow(
            self.rpa_flow,
            self.log_area_rpa,
            self.density,
            self.loss_coefficient,
            INTO_BRANCH_SIGN,
        ) - self._characteristic_delta_dflow(self._z_rpa(), LEFT_BOUNDARY_SIGN)

    @lpa_total_pressure_residual.partial_derivative(PRESSURE_LPA_ID)
    def lpa_total_pressure_residual_dpressure_lpa(self) -> float:
        return 0.5 * (1.0 - self.wall_pressure_weight.current)

    @lpa_total_pressure_residual.partial_derivative(PRESSURE_RPA_ID)
    def lpa_total_pressure_residual_dpressure_rpa(self) -> float:
        return -0.5 * (1.0 - self.wall_pressure_weight.current)

    @lpa_total_pressure_residual.partial_derivative(LOG_AREA_LPA_ID)
    def lpa_total_pressure_residual_dlog_area_lpa(self) -> Any:
        return blended_total_pressure_dlog_area(
            self.lpa_flow,
            self.log_area_lpa,
            self.wall_stiffness_lpa,
            self.density,
            self.wall_pressure_weight,
        ) + signed_minor_loss_dlog_area(
            self.lpa_flow,
            self.log_area_lpa,
            self.density,
            self.loss_coefficient,
            INTO_BRANCH_SIGN,
        )

    @lpa_total_pressure_residual.partial_derivative(LOG_AREA_RPA_ID)
    def lpa_total_pressure_residual_dlog_area_rpa(self) -> Any:
        return -blended_total_pressure_dlog_area(
            self.rpa_flow,
            self.log_area_rpa,
            self.wall_stiffness_rpa,
            self.density,
            self.wall_pressure_weight,
        ) - signed_minor_loss_dlog_area(
            self.rpa_flow,
            self.log_area_rpa,
            self.density,
            self.loss_coefficient,
            INTO_BRANCH_SIGN,
        )

    @declares_flux(1, PRESSURE_SVC_ID)
    def flux_svc(self) -> Any:
        return -mid_point(self.svc_flow)

    @flux_svc.partial_derivative(SVC_FLOW_ID)
    def flux_svc_dsvc_flow(self) -> float:
        return -0.5

    @declares_flux(2, PRESSURE_IVC_ID)
    def flux_ivc(self) -> Any:
        return -mid_point(self.ivc_flow)

    @flux_ivc.partial_derivative(IVC_FLOW_ID)
    def flux_ivc_divc_flow(self) -> float:
        return -0.5

    @declares_flux(3, PRESSURE_RPA_ID)
    def flux_rpa(self) -> Any:
        return mid_point(self.rpa_flow)

    @flux_rpa.partial_derivative(RPA_FLOW_ID)
    def flux_rpa_drpa_flow(self) -> float:
        return 0.5

    @declares_flux(4, PRESSURE_LPA_ID)
    def flux_lpa(self) -> Any:
        return mid_point(self.lpa_flow)

    @flux_lpa.partial_derivative(LPA_FLOW_ID)
    def flux_lpa_dlpa_flow(self) -> float:
        return 0.5

    @declares_saved_quantity(MASS_BALANCE_ID)
    def mass_balance(self) -> float:
        return float(
            mid_point(self.svc_flow)
            + mid_point(self.ivc_flow)
            - mid_point(self.rpa_flow)
            - mid_point(self.lpa_flow)
        )

    @declares_saved_quantity("svc_total_pressure")
    def svc_total_pressure(self) -> float:
        return float(self._h_svc())

    @declares_saved_quantity("ivc_total_pressure")
    def ivc_total_pressure(self) -> float:
        return float(self._h_ivc())

    @declares_saved_quantity("rpa_total_pressure")
    def rpa_total_pressure(self) -> float:
        return float(self._h_rpa())

    @declares_saved_quantity("lpa_total_pressure")
    def lpa_total_pressure(self) -> float:
        return float(self._h_lpa())

    @declares_saved_quantity("svc_loss_pressure")
    def svc_loss_pressure(self) -> float:
        return float(self._loss_svc())

    @declares_saved_quantity("ivc_loss_pressure")
    def ivc_loss_pressure(self) -> float:
        return float(self._loss_ivc())

    @declares_saved_quantity("rpa_loss_pressure")
    def rpa_loss_pressure(self) -> float:
        return float(self._loss_rpa())

    @declares_saved_quantity("lpa_loss_pressure")
    def lpa_loss_pressure(self) -> float:
        return float(self._loss_lpa())

    @declares_saved_quantity("svc_effective_total_pressure")
    def svc_effective_total_pressure(self) -> float:
        return float(self._effective_h_svc())

    @declares_saved_quantity("ivc_effective_total_pressure")
    def ivc_effective_total_pressure(self) -> float:
        return float(self._effective_h_ivc())

    @declares_saved_quantity("rpa_effective_total_pressure")
    def rpa_effective_total_pressure(self) -> float:
        return float(self._effective_h_rpa())

    @declares_saved_quantity("lpa_effective_total_pressure")
    def lpa_effective_total_pressure(self) -> float:
        return float(self._effective_h_lpa())

    @declares_saved_quantity("svc_wall_pressure")
    def svc_wall_pressure(self) -> float:
        return float(
            wall_pressure(
                self.log_area_svc,
                self.reference_area_svc,
                self.wall_stiffness_svc,
                self.external_pressure_svc,
            )
        )

    @declares_saved_quantity("ivc_wall_pressure")
    def ivc_wall_pressure(self) -> float:
        return float(
            wall_pressure(
                self.log_area_ivc,
                self.reference_area_ivc,
                self.wall_stiffness_ivc,
                self.external_pressure_ivc,
            )
        )

    @declares_saved_quantity("rpa_wall_pressure")
    def rpa_wall_pressure(self) -> float:
        return float(
            wall_pressure(
                self.log_area_rpa,
                self.reference_area_rpa,
                self.wall_stiffness_rpa,
                self.external_pressure_rpa,
            )
        )

    @declares_saved_quantity("lpa_wall_pressure")
    def lpa_wall_pressure(self) -> float:
        return float(
            wall_pressure(
                self.log_area_lpa,
                self.reference_area_lpa,
                self.wall_stiffness_lpa,
                self.external_pressure_lpa,
            )
        )

    @declares_saved_quantity(TOTAL_PRESSURE_SPREAD_ID)
    def total_pressure_spread(self) -> float:
        return spread(
            [
                self._effective_h_svc(),
                self._effective_h_ivc(),
                self._effective_h_rpa(),
                self._effective_h_lpa(),
            ]
        )

    @declares_saved_quantity("svc_characteristic_impedance")
    def svc_characteristic_impedance(self) -> float:
        return float(self._z_svc())

    @declares_saved_quantity("ivc_characteristic_impedance")
    def ivc_characteristic_impedance(self) -> float:
        return float(self._z_ivc())

    @declares_saved_quantity("rpa_characteristic_impedance")
    def rpa_characteristic_impedance(self) -> float:
        return float(self._z_rpa())

    @declares_saved_quantity("lpa_characteristic_impedance")
    def lpa_characteristic_impedance(self) -> float:
        return float(self._z_lpa())

    @declares_saved_quantity("svc_velocity")
    def svc_velocity(self) -> float:
        return float(velocity(self.svc_flow, self.log_area_svc))

    @declares_saved_quantity("ivc_velocity")
    def ivc_velocity(self) -> float:
        return float(velocity(self.ivc_flow, self.log_area_ivc))

    @declares_saved_quantity("rpa_velocity")
    def rpa_velocity(self) -> float:
        return float(velocity(self.rpa_flow, self.log_area_rpa))

    @declares_saved_quantity("lpa_velocity")
    def lpa_velocity(self) -> float:
        return float(velocity(self.lpa_flow, self.log_area_lpa))
