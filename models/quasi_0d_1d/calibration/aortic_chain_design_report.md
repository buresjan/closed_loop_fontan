# Aortic Chain Design Report

Task 008.10 status: `blocked_not_promoted`

## Goal

Correct the quasi aortic chain before closed-loop recalibration by testing a small matrix around aortic resistance, inertance, compliance redistribution, terminal arterial compliance, and terminal lower-body load placement.

## Inputs

- `models/quasi_0d_1d/config_fragments/quasi_vessel_chains.json`
- `models/quasi_0d_1d/calibration/aorta_quasi_openloop_metrics.json`
- `models/quasi_0d_1d/calibration/aortic_signal_policy.json`
- `models/quasi_0d_1d/calibration/characteristic_impedance_report.csv`
- `models/quasi_0d_1d/calibration/compliance_budget.csv`
- `data/processed/aramburu_2024/model_inputs/aorta_geometry.csv`

## Output Artifacts

- `models/quasi_0d_1d/config_fragments/quasi_vessel_chains_corrected.json`
- `models/quasi_0d_1d/calibration/aortic_chain_design_candidates.csv`
- `runs/quasi_0090/openloop_probe2/summary.csv`
- `runs/quasi_0090/closedloop_probe/summary.csv`
- `runs/quasi_0090/closedloop_probe2/summary.csv`
- `runs/quasi_0090/closedloop_probe_final/summary.json`

## Signal Policy

Task 008.9 is used unchanged:

- `Q_AAo`: `valve_arterial.flux`
- `Q_DAo clinical`: `lower_ra4.flow`
- `Q_DAo chain health`: `quasi_dao_rl_06.flux`

The clinical DAo signal remains a soft target in the general waveform policy, but Task 008.10 explicitly required it to be not worse than the full 0-D comparator.

## Candidate Matrix

The tested matrix covered:

- aortic resistance scale: `4.5`, `7.0`
- aortic inertance scale: `0.05`, `0.1`, `0.25`, `1.0`
- aortic chain capacitance scale: retained at `1.0`
- retained endpoint aortic compliance scale: `0.02` to `0.20`
- terminal arterial compliance scale: `0.1`, `0.25`, `0.5`, `1.0`
- lower-body proximal load fraction: `0.45` to `0.95`
- systemic resistance scale smoke: `1.1`

No distributed-branch topology was promoted, because the earlier distributed-branch ablations collapsed CO/SVC flow.

## Open-Loop Result

The clearest open-loop corrected-chain setting was:

```text
candidate: ep0.02_art0.5
aortic_R_scale: 7.0
aortic_L_scale: 1.0
aortic_C_scale: 1.0
endpoint_compliance_scale: 0.02
terminal_arterial_compliance_scale: 0.5
```

Key open-loop metrics:

```text
mass balance error: 5.45e-04
AAo->DAo mean drop: 0.622 mmHg
target AAo->DAo mean drop: about 0.604 mmHg
DAo chain nRMSE: 0.227
lower-body DAo nRMSE: 0.239
```

This fixes the current model's major passive aortic-chain issue: the previous trunk drop was about `0.085 mmHg`, while the paper/Nektar profile expects about `0.60 mmHg`.

## Closed-Loop Result

The best defensible closed-loop partial candidate was:

```text
candidate: ep02_r7_art05_frac95
aortic_R_scale: 7.0
aortic_L_scale: 1.0
aortic_C_scale: 1.0
endpoint_compliance_scale: 0.02
terminal_arterial_compliance_scale: 0.5
lower_systemic_proximal_fraction: 0.95
```

Closed-loop metrics:

| Check | Candidate | Full 0-D comparator | Pass |
|---|---:|---:|---|
| CO stable | 2.353 L/min | n/a | yes |
| SVC flow stable | 19.310 ml/s | n/a | yes |
| Q_AAo nRMSE | 0.551 | 0.572 | yes |
| Q_DAo clinical nRMSE | 0.352 | 0.331 | no |
| Q_DAo chain-health nRMSE | 0.361 | 0.434 | yes |
| TCPC cycle balance | 3.13e-06 | n/a | yes |

This candidate is stable and removes the severe DAo chain-health regression, but it still fails the Task 008.10 clinical DAo control.

## Follow-Up Probes

Lowering aortic inertance improved AAo waveform nRMSE and moved the DAo clinical peak earlier, but it did not reduce clinical DAo nRMSE below the full 0-D comparator:

```text
ep02_r7_L0p05_art05_frac85:
  Q_AAo nRMSE: 0.545 vs full 0-D 0.572
  Q_DAo clinical nRMSE: 0.354 vs full 0-D 0.331
  Q_DAo chain-health nRMSE: 0.362 vs full 0-D 0.434
```

Reducing aortic resistance from `7.0` to `4.5` also did not improve the clinical DAo gate:

```text
ep02_r4p5_L0p05_art05_frac85:
  Q_AAo nRMSE: 0.546 vs full 0-D 0.572
  Q_DAo clinical nRMSE: 0.354 vs full 0-D 0.331
  Q_DAo chain-health nRMSE: 0.362 vs full 0-D 0.434
```

The best clinical DAo score observed was `0.351` for `ep05_r7_art05_frac95`, but the corresponding open-loop family with `endpoint_compliance_scale=0.05` and `terminal_arterial_compliance_scale=0.5` failed the open-loop pressure/pulse diagnostic, so it was not promoted as the corrected candidate.

## Control Assessment

| Task 008.10 control | Result |
|---|---|
| Open-loop aortic mass-balance error passes | pass |
| AAo->DAo mean pressure drop close to paper/Nektar | pass |
| Q_AAo nRMSE not worse than full 0-D | pass |
| Q_DAo clinical nRMSE not worse than full 0-D | fail |
| Q_DAo chain health no longer severe regression | pass |
| No CO/SVC collapse in closed-loop smoke | pass |

Task 008.10 is therefore not complete under its own control criteria.

## Interpretation

The aortic trunk-chain correction is useful: it restores a realistic mean AAo-to-DAo drop and changes the DAo chain-health waveform from a severe regression to better than the full 0-D comparator. The remaining failure is not solved by aortic R/L/C scaling alone.

The likely remaining issue is downstream of the corrected aortic trunk: the current terminal lower-body load and `lower_ra4.flow` clinical signal relationship need either a more defensible terminal RCR-style load redesign or a coordinated recalibration after the broader Fontan/pulmonary and preload/compliance tasks. Promoting the aortic correction alone would create a partially improved but still non-compliant quasi baseline.

## PhysioBlocks Impact

No PhysioBlocks internal changes are needed for Task 008.10. All tested changes were ordinary config parameter changes using existing `hydraulic_rl_block`, `c_block`, and systemic-bed parameters.

## Recommendation

Do not promote `quasi_vessel_chains_corrected.json` into the default quasi configs yet. Keep it as a documented blocked design artifact and resolve the clinical DAo outlet issue before Task 008.14 promotion.
