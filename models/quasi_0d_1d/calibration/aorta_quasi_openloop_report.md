# Aorta Quasi Open-Loop Report

Task 008.8 status: `fail_open_loop_aortic_diagnostic`

Source: `Paper/Nektar closed-loop 1-D` (`data/processed/aramburu_2024/comparison/04_aorta_tcpc_closedloop_1d_last_cycle_clinical.csv`)

## Pressure Diagnostics

| Signal | Mean error (mmHg) | Pulse-pressure relative error |
|---|---:|---:|
| ascending_aorta_pressure | -5.038 | -0.695 |
| aortic_arch_pressure | -4.710 | -0.728 |
| descending_aorta_pressure | -4.519 | -0.510 |

## Flow Diagnostics

| Signal | Model signal | nRMSE | Sign-flipped nRMSE | Best phase-shift nRMSE | Amplitude rel. error |
|---|---|---:|---:|---:|---:|
| ascending_aorta_flow | `aao_inflow.blood_flow` | 0.004 | 0.751 | 0.004 | -0.000 |
| descending_aorta_flow | `quasi_dao_rl_06.flux` | 0.424 | 0.858 | 0.368 | 0.934 |
| lower_ra4_flow | `lower_ra4.flow` | 0.332 | 0.459 | 0.231 | -0.684 |

## Pressure Drop And Balance

- Target AAo->DAo mean pressure drop: `0.604` mmHg.
- Model AAo->DAo mean pressure drop: `0.085` mmHg.
- Aortic chain mass-balance error: `4.714e-03`.
- Aortic tree terminal mass-balance error: `7.550e-02`.

## Failure Diagnosis

- amplitude mismatch suggests R/L/C or terminal-load impedance problem.
- branch/load topology or resistance placement distorts the pressure profile.

## Interpretation

The open-loop harness reports DAo chain outlet flow and lower-body outflow separately.
Do not substitute `lower_ra4.flow` for the DAo chain outlet unless a later signal-policy task explicitly approves that target location.
