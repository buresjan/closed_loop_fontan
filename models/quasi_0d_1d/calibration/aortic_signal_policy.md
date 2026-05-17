# Aortic Signal Policy

Status: `active`

This policy defines the accepted aortic waveform mapping used by the quasi
0-D/1-D comparison gate.

## Signals

| Signal | Canonical waveform | Full 0-D signal | Quasi signal | Gate role |
|---|---|---|---|---|
| Q_AAo | `ascending_aorta_flow` | `valve_arterial.flux` | `valve_arterial.flux` | hard |
| Q_DAo | `descending_aorta_flow` | `lower_ra4.flow` | `lower_ra4.flow` | soft diagnostic |
| Q_DAo_chain_health | `descending_aorta_chain_health_flow` | `arch_dao.flow` | `quasi_dao_rl_06.flux` | hard |

Clinical DAo bed-entry flow is reported, but it is not the aortic trunk
fidelity gate because it reflects both the DAo pressure node and downstream
systemic-bed/terminal-load dynamics. DAo chain-health flow remains the hard
aortic trunk waveform control.

Phase-shifted nRMSE remains diagnostic only. Accepted waveform comparisons use
unshifted nRMSE under the processed comparison-cycle phase convention.
