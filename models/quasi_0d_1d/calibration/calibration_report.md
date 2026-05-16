# Quasi 0-D/1-D Calibration Report

Completed on 2026-05-15 for Task 008.5.

## Scope

Task 008.5 corrects the Task 008 quasi calibration review. The model remains
stable and useful for development, but it is not accepted as a superior
calibrated quasi model because several pump and waveform non-regression gates
still fail.

Intervention scenarios inherit the calibrated baseline and remain validation
cases; they are not retuned.

No PhysioBlocks internals were changed.

## Selected Scale Factors

| Scale | Value |
|---|---:|
| Heart contractility | 0.96 |
| Upper systemic resistance | 1.00 |
| Lower systemic resistance | 1.12 |
| Right pulmonary total resistance | 1.15 |
| Left pulmonary total resistance | 1.15 |
| Right pulmonary proximal fraction | 0.50 |
| Left pulmonary proximal fraction | 0.50 |
| Quasi chain R/L/C scales | 1.00 |

Heart-frozen candidates were tested first. They did not recover the hard pump
gates, so the previous heart scale is retained and documented as a residual
limitation rather than a clean quasi-specific win.

## Baseline Fit

Primary comparison source: `direct_measurement`.

| Quantity | Model | Target | Error |
|---|---:|---:|---:|
| EDV | 70.04 ml | 74.40 ml | -5.9% |
| ESV | 34.80 ml | 37.60 ml | -7.4% |
| SV | 35.23 ml | 36.80 ml | -4.3% |
| CO | 2.47 L/min | 2.57 L/min | -3.9% |
| Mean AAo pressure | 46.96 mmHg | 50.40 mmHg | -6.8% |
| Mean aortic arch pressure | 46.95 mmHg | 51.73 mmHg | -9.2% |
| Mean DAo pressure | 46.87 mmHg | 53.15 mmHg | -11.8% |
| Mean SVC pressure | 9.05 mmHg | 8.87 mmHg | +2.0% |
| Mean IVC pressure | 8.85 mmHg | 8.54 mmHg | +3.6% |
| Mean RPA pressure | 7.72 mmHg | 8.48 mmHg | -9.0% |
| Mean LPA pressure | 7.72 mmHg | 8.46 mmHg | -8.7% |
| SVC flow | 20.18 ml/s | 20.59 ml/s | -2.0% |
| IVC flow | 20.87 ml/s | 18.84 ml/s | +10.8% |
| RPA flow | 24.26 ml/s | 24.43 ml/s | -0.7% |
| LPA flow | 16.79 ml/s | 16.88 ml/s | -0.5% |
| RPA flow fraction | 0.5909 | 0.5914 | -0.1% |

Aggregate direct-measurement weighted RMS relative error is `0.0592`, improved
from Task 008 (`0.0610`) and the full 0-D direct score (`0.0614`). This is not
used as the acceptance criterion.

## Non-Regression Gate

The canonical gate report is
`models/quasi_0d_1d/calibration/non_regression_gate.json`.

| Gate Group | Result |
|---|---|
| Stability and loop balance | pass |
| RPA pressure | pass |
| LPA pressure | pass |
| SVC flow | pass |
| RPA/LPA flow fraction | pass |
| EDV | fail |
| ESV | fail |
| SV | fail |
| CO | fail |
| Paper-model score | fail |
| Waveform no-strong-regression | fail |

Direct DAo pressure and raw direct IVC flow are soft/problematic diagnostics and
are not allowed to compensate for hard pump or Fontan regressions.

Grouped scores:

| Score | Full 0-D | Quasi |
|---|---:|---:|
| Hard clinical summary | 0.0433 | 0.0561 |
| Soft/problematic direct targets | 0.1563 | 0.1120 |
| Aggregate direct targets | 0.0614 | 0.0592 |
| Paper-model comparison | 0.0793 | 0.0805 |

## Waveform Check

The waveform report now records selected model and reference signal columns so
flow extraction can be audited. Task 008.9 centralizes the aortic flow policy:
AAo flow uses `valve_arterial.flux`, clinical DAo flow uses `lower_ra4.flow`,
and DAo chain-health flow remains `quasi_dao_rl_06.flux` compared to full 0-D
`arch_dao.flow`.

Selected normalized RMSE values:

| Waveform | Full 0-D | Corrective quasi | Direction |
|---|---:|---:|---|
| Descending aorta pressure | 0.466 | 0.432 | improved |
| Ventricle volume | 0.584 | 0.574 | improved |
| IVC flow | 0.265 | 0.248 | improved |
| SVC pressure | 0.336 | 0.279 | improved |
| Ascending aorta flow | 0.572 | 0.560 | improved |
| Descending aorta clinical flow | 0.331 | 0.381 | soft target |
| Descending aorta chain-health flow | 0.434 | 0.952 | worse |

The large DAo chain-health regression remains a real quasi-chain issue, not a
hidden column-selection bug. Clinical DAo flow is now reported separately and is
not allowed to hide trunk-chain behavior.

## Task 008.6 Design Closure

Task 008.6 audited the AAo/DAo flow signal selection, compliance/storage
budget, and characteristic impedance, then ran 23 quasi design/ablation
candidates. The generated closure artifacts are:

```text
models/quasi_0d_1d/calibration/design_audit_report.md
models/quasi_0d_1d/calibration/dao_aao_flow_signal_audit.csv
models/quasi_0d_1d/calibration/compliance_budget.csv
models/quasi_0d_1d/calibration/characteristic_impedance_report.csv
models/quasi_0d_1d/calibration/quasi_ablation_summary.csv
models/quasi_0d_1d/calibration/quasi_final_decision.md
```

No Task 008.6 candidate passed all closure gates. The best hard/direct
candidate was `current_heart_099` with hard score `0.0632`, still worse than
the Task 008.5 reference hard score `0.0561` and still failing EDV, ESV, RPA
pressure, LPA pressure, and AAo/DAo flow waveform gates. The best waveform
candidate was `aortic_L0_5` with waveform regression RMS `0.0742`, but it also
failed the hard and waveform gates. Distributed aortic branch topologies
substantially worsened the loop, including CO near `1.72 L/min` and SVC flow
near `2 ml/s`.

Task 008.6 therefore closes with
`stable_quasi_development_scaffold_not_scientifically_superior`; no tracked
quasi config or schematic is promoted.

## Task 008.7 Frozen Superiority Gate

Task 008.7 freezes the promotion criteria in:

```text
models/quasi_0d_1d/calibration/quasi_superiority_gate.json
models/quasi_0d_1d/calibration/full0d_reference_scores.json
models/quasi_0d_1d/calibration/current_quasi_gate_status.json
models/quasi_0d_1d/calibration/current_quasi_gate_status.md
```

The current quasi model is `not_superior_to_full_0d`. It passes stability and
has at least one quasi-specific vascular improvement, but it fails:

```text
score_non_regression
pump_non_regression
fontan_pulmonary_non_regression
aortic_waveform_no_regression
```

Later quasi candidates must pass
`scripts/calibration/compare_quasi_to_full0d.py` against the frozen gate before
the repository can claim quasi superiority.

## Task 008.8 Aortic Open-Loop Diagnostic

Task 008.8 isolates the quasi aortic chain outside the closed-loop circulation.
The generated artifacts are:

```text
models/quasi_0d_1d/configs/submodel_aorta_quasi_openloop.jsonc
models/quasi_0d_1d/calibration/aorta_quasi_openloop_report.md
models/quasi_0d_1d/calibration/aorta_quasi_openloop_metrics.json
models/quasi_0d_1d/calibration/aorta_quasi_openloop_waveforms.csv
```

The current status is `fail_open_loop_aortic_diagnostic`. The prescribed AAo
inflow is reproduced with nRMSE `0.004`, DAo chain outlet flow nRMSE is
`0.424`, lower-body `lower_ra4.flow` nRMSE is `0.332`, and aortic chain
mass-balance error is `4.714e-03`. The pressure profile fails: AAo, arch, and
DAo mean errors are approximately `-5.04`, `-4.71`, and `-4.52` mmHg, while
pulse-pressure relative errors are `-0.695`, `-0.728`, and `-0.510`.

The diagnostic identifies the likely causes as an R/L/C or terminal-load
impedance mismatch and/or branch/load topology or resistance-placement problem.
It reports `quasi_dao_rl_06.flux` and `lower_ra4.flow` separately and should
not be used to promote the current closed-loop quasi model.

## Task 008.9 Aortic Signal Policy

Task 008.9 adds:

```text
models/quasi_0d_1d/calibration/aortic_signal_policy.md
models/quasi_0d_1d/calibration/aortic_signal_policy.json
scripts/calibration/map_aortic_signals.py
```

The policy decides that measured/paper `Q_DAo` is treated as lower-body DAo
outflow for clinical waveform comparison in the current lumped/quasi topology.
The selected clinical signal is `lower_ra4.flow`. DAo trunk behavior remains a
separate health check, `descending_aorta_chain_health_flow`, using
`quasi_dao_rl_06.flux` in the quasi model and `arch_dao.flow` in the full 0-D
reference.

Phase-shifted nRMSE remains diagnostic only. Acceptance and promotion gates use
unshifted nRMSE under the processed comparison-cycle phase convention.

After policy application, AAo flow no-regression passes (`0.560` quasi versus
`0.572` full 0-D), but DAo chain-health no-regression fails (`0.952` quasi
versus `0.434` full 0-D). The current quasi model therefore remains
`not_superior_to_full_0d`.

## Numerical Checks

| Check | Value | Threshold |
|---|---:|---:|
| Cavity-volume periodicity | 0.00697 | 0.02 |
| Aortic-valve flux periodicity | 0.00714 | 0.02 |
| Atrioventricular-valve flux periodicity | 0.00108 | 0.02 |
| TCPC cycle balance | 2.28e-05 | 1e-2 |
| Atrial cycle balance | 1.48e-04 | 1e-2 |
| Ventricle cycle balance | 9.58e-05 | 1e-2 |

All standardized quasi chain mass-balance values remain small.

## Validation Scenarios

Scenario metrics were regenerated without retuning:

- Pulmonary vasodilation: CO increases by 1.73%, TCPC pressure decreases by
  2.23%, and pulmonary flows increase.
- Fenestration: fenestration flow increases from near-zero baseline to
  0.81 ml/s while global CO changes minimally.
- LPA obstruction: RPA flow fraction increases from 0.591 to 0.743, left lung
  flow falls, and right lung flow rises.

The validation summaries are tracked in
`models/quasi_0d_1d/reference_outputs/scenario_comparison.txt`.

## Status

The current quasi model is a stable development scaffold, not a superior
closed-loop Fontan model. Task 009 can proceed as a feasibility spike with full
0-D as the calibrated reference. Later quasi or coupled-model work should not
inherit a claim that Task 008.5 or Task 008.6 solved the pump and aortic-flow
regressions.

## Reproduction

```bash
.venv/bin/python scripts/modeling/build_quasi_configs.py
.venv/bin/python scripts/calibration/run_quasi_calibration.py --run-reference-scenarios --write-objective-reports
.venv/bin/python scripts/calibration/quasi_non_regression.py \
  --out models/quasi_0d_1d/calibration/non_regression_gate.json
.venv/bin/python scripts/calibration/audit_quasi_design.py
.venv/bin/python scripts/calibration/run_quasi_ablation_grid.py
.venv/bin/python scripts/calibration/run_quasi_closure_calibration.py
.venv/bin/python scripts/calibration/map_aortic_signals.py
.venv/bin/python scripts/calibration/compare_waveforms.py \
  runs/simulations/QuasiBaseline/eden_QuasiBaseline_2/main.csv \
  models/quasi_0d_1d/configs/fontan_quasi_baseline.jsonc \
  --source-id direct_measurement \
  --reference-csv runs/simulations/Baseline/eden_Baseline_3/main.csv \
  --reference-config models/full_0d/configs/fontan_0d_baseline.jsonc \
  --out models/quasi_0d_1d/calibration/baseline_waveforms_direct.json
.venv/bin/python scripts/calibration/compare_quasi_to_full0d.py
.venv/bin/python scripts/quasi/run_aorta_quasi_openloop.py
.venv/bin/python scripts/quasi/evaluate_aorta_quasi_openloop.py
```
