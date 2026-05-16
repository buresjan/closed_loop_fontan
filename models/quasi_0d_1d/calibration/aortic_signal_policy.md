# Aortic Signal Policy

Task 008.9 status: `active`

This policy is the single source for aortic pressure/flow model columns used by later waveform and gate scripts.

## Decisions

### q_dao_target_location

- Decision: Use lower-body DAo outflow as the clinical waveform match in the current lumped/quasi models.
- Reason: The tracked descending-aorta flow target is a lower-body aortic measurement after arch branches. In the quasi topology, lower_ra4.flow is the flow from the DAo pressure node into the lower systemic artery and is the best anatomical clinical match. The DAo chain outlet remains a separate trunk-chain health signal.

### dao_chain_health

- Decision: Keep DAo chain outlet flow as a separate no-strong-regression diagnostic.
- Reason: Switching only to lower_ra4.flow would hide waveform behavior inside the quasi DAo trunk.

### phase_shifted_nrmse

- Decision: Use phase-shifted nRMSE only diagnostically.
- Reason: The accepted waveform metric remains unshifted nRMSE under the shared target phase convention.

### phase_convention_consistency

- Decision: Treat AAo and DAo target waveforms and model last-cycle outputs as using the same cardiac-cycle phase convention.
- Reason: The target metadata records processed comparison-cycle phase for all waveform targets, and no later script applies a phase shift for acceptance.

## Phase Policy

- Convention: All waveform targets use the processed Aramburu comparison-cycle phase from phase 0 to 1. No valve-event alignment or cross-correlation phase shift is applied before acceptance scoring.
- Acceptance metric: `unshifted_normalized_rmse`.
- Phase-shifted nRMSE: `diagnostic_only`.

## Signals

| ID | Canonical output | Target | Quasi model column | Full 0-D column | Role | Gate | Reason |
|---|---|---|---|---|---|---|---|
| P_AAo | `ascending_aorta_pressure` | `ascending_aorta_pressure_mmHg` | `aao.blood_pressure` | `aao.blood_pressure` | soft_target | no | Paper/Nektar aortic pressure profile is preferred for passive aortic-profile checks; direct pressure remains useful context. |
| P_arch | `aortic_arch_pressure` | `aortic_arch_pressure_mmHg` | `aortic_arch.blood_pressure` | `aortic_arch.blood_pressure` | soft_target | no | Used for passive aortic pressure-profile consistency. |
| P_DAo | `descending_aorta_pressure` | `descending_aorta_pressure_mmHg` | `dao.blood_pressure` | `dao.blood_pressure` | diagnostic | no | Direct DAo pressure violates passive pressure ordering in the current target set, so it remains diagnostic/soft. |
| Q_AAo | `ascending_aorta_flow` | `ascending_aorta_flow_ml_s` | `valve_arterial.flux` | `valve_arterial.flux` | hard_gate | yes | Q_ascAo is a root/ascending-aorta flow target. The aortic-valve outlet is the shared full 0-D/quasi signal closest to that root inflow location. |
| Q_DAo | `descending_aorta_flow` | `descending_aorta_flow_ml_s` | `lower_ra4.flow` | `lower_ra4.flow` | soft_target | no | This is the best clinical DAo waveform match in the current lumped/quasi topology, but the measurement-location ambiguity keeps it soft until later validation. |
| Q_DAo_chain_health | `descending_aorta_chain_health_flow` | `descending_aorta_flow_ml_s` | `quasi_dao_rl_06.flux` | `arch_dao.flow` | diagnostic | yes | This is not the clinical DAo target, but it remains the health check for the quasi aortic trunk. It prevents lower_ra4.flow from hiding a broken DAo chain. |

## DAo Policy

`Q_DAo` is the clinical descending-aorta flow target and maps to `lower_ra4.flow` in the current full 0-D and quasi models.
`Q_DAo_chain_health` is the DAo trunk/chain diagnostic and maps to `quasi_dao_rl_06.flux` in the quasi model and `arch_dao.flow` in the full 0-D reference.
Both are reported; only the chain-health signal remains in the aortic waveform no-regression gate.
