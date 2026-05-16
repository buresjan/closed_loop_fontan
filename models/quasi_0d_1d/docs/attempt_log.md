# Quasi 0-D/1-D Attempt Log

Last updated: 2026-05-16

This file is the consolidated record of the quasi 0-D/1-D Fontan work tried so
far. The detailed artifacts remain in task files, calibration reports, JSON
gates, CSV candidate tables, generated configs, and tests. This log records the
decision path so later work does not mistake a lower aggregate objective for an
accepted quasi model.

## Current Decision

The quasi 0-D/1-D family is executable and stable enough for development, but
it is not accepted as superior to the calibrated full 0-D reference.

The accepted reference for downstream work remains the full 0-D model. The
quasi model should be treated as a stable development scaffold until a later
candidate passes the frozen superiority gate in
[`../calibration/quasi_superiority_gate.json`](../calibration/quasi_superiority_gate.json).

Current gate status:

| Gate group | Status |
|---|---|
| Stability and balance | pass |
| Aggregate direct score | pass |
| Hard clinical score | fail |
| Pump target non-regression | fail |
| Fontan/pulmonary target non-regression | fail |
| Paper-model score | fail |
| Aortic flow waveform no-regression | fail |
| Quasi-specific vascular improvement | pass |

Key comparison scores:

| Score | Full 0-D | Current quasi | Status |
|---|---:|---:|---|
| Hard clinical summary | 0.0433 | 0.0561 | fail |
| Aggregate direct | 0.0614 | 0.0592 | pass |
| Paper-model | 0.0793 | 0.0805 | fail |
| AAo flow nRMSE | 0.5718 | 0.5602 | pass |
| DAo chain-health flow nRMSE | 0.4337 | 0.9520 | fail |

## Attempt Timeline

| Task | What was tried | Result |
|---|---|---|
| Task 005 | Derived first-pass quasi R-L-C vessel parameters from geometry, calibrated full 0-D priors, density/viscosity constants, and wave-speed priors. | Completed. Produced chain priors and the first `quasi_vessel_chains.json` fragment. |
| Task 006 | Built executable PhysioBlocks-only quasi configs from the calibrated full 0-D scenarios by replacing selected aortic and Fontan shortcuts with R-L-C chains. | Completed. Smoke case and topology tests passed. |
| Task 007 | Added quasi-aware metrics, chain inlet/outlet/storage/mass-balance metrics, reference outputs, and scenario comparisons. | Completed. Baseline and intervention metrics were generated. |
| Task 008 | Ran first quasi calibration with small global heart, systemic, and pulmonary resistance scales while preserving chain totals. | Completed but superseded. Aggregate direct score improved, but hard non-regression gates were not yet explicit. |
| Task 008.5 | Added corrective calibration, hard non-regression gates, separated hard/soft/paper/waveform scores, pulmonary split knobs, and chain R/L/C scale knobs. | Completed. Stable scaffold; not superior. Pump, paper, and AAo/DAo waveform gates still failed. |
| Task 008.6 | Audited flow signal selection, compliance/storage, characteristic impedance, and ran a 23-candidate ablation/design matrix. | Completed. No candidate passed all closure gates. Task 008.5 configs remained canonical. |
| Task 008.7 | Froze the superiority gate against full 0-D reference scores. | Completed. Current quasi recorded as `not_superior_to_full_0d`. |
| Task 008.8 | Built an open-loop aortic quasi diagnostic harness with prescribed AAo inflow and terminal pressure/load behavior. | Completed. The current aortic chain failed pressure profile and pulse-pressure checks. |
| Task 008.9 | Resolved aortic signal policy for AAo and DAo pressure/flow comparisons. | Completed. Clinical DAo flow maps to `lower_ra4.flow`; DAo chain health remains `quasi_dao_rl_06.flux`. |
| Task 008.10 | Tested corrected aortic-chain candidates around trunk R/L/C, endpoint compliance redistribution, terminal arterial compliance, and lower-body proximal load placement. | Blocked, not promoted. Best candidate fixed several aortic-chain checks but still failed strict clinical DAo no-regression. |

## Details By Attempt

### Task 005 - Parameter Derivation

The first quasi step derived geometry-based R-L-C chain priors from:

- `data/processed/aramburu_2024/model_inputs/aorta_geometry.csv`;
- `data/processed/aramburu_2024/model_inputs/fontan_cross_geometry.csv`;
- `data/processed/aramburu_2024/targets/target_policy.csv`;
- `models/full_0d/configs/fontan_0d_baseline.jsonc`.

The selected first-pass chains were:

| Chain | Cells | Policy |
|---|---:|---|
| AAo/arch | 4 | geometry/friction resistance, aortic wave speed prior |
| DAo | 6 | geometry/friction resistance, aortic wave speed prior |
| SVC | 3 | calibrated full 0-D pathway resistance prior |
| IVC | 5 | calibrated full 0-D pathway resistance prior |
| RPA | 3 | calibrated full 0-D pathway resistance prior |
| LPA | 4 | calibrated full 0-D pathway resistance prior with explicit narrowed segment |

Important decisions:

- The aortic chain did not preserve the excessive full 0-D AAo-to-DAo pressure
  drop; most systemic pressure loss was kept in systemic beds.
- Direct DAo pressure was treated as diagnostic/low-weight because the target
  set did not preserve passive aortic pressure ordering.
- Raw direct IVC flow was treated as mass-closure dependent and was not forced
  at the expense of CO, SVC flow, RPA/LPA flow, or flow split.

Evidence:

- [`../../quasi_0d_1d/calibration/parameter_priors.yaml`](../calibration/parameter_priors.yaml)
- [`../../quasi_0d_1d/config_fragments/quasi_vessel_chains.json`](../config_fragments/quasi_vessel_chains.json)
- [`../../../tasks/005-derive-quasi-vessel-parameters.md`](../../../tasks/005-derive-quasi-vessel-parameters.md)

### Task 006 - Executable Quasi Model

The executable model kept the calibrated full 0-D heart, active atrium, valves,
systemic beds, pulmonary RCR beds, and fenestration. It replaced the AAo/arch,
DAo, SVC, IVC, RPA, and LPA shortcuts with repeated `hydraulic_rl_block` and
`c_block` cells.

What was tried:

- Generated smoke, baseline, vasodilation, fenestration, and LPA obstruction
  configs from the matching full 0-D scenarios.
- Removed the old full 0-D Fontan conduit nodes and conduit workaround blocks.
- Kept `valve_rl_block` only for the atrioventricular and aortic valves.
- Doubled total LPA quasi-chain resistance in the LPA obstruction scenario.

Result:

- The quasi smoke case ran.
- Topology and chain-total checks passed.
- The model-local README, schematic, PNG export, and implementation notes were
  updated to match the executable topology.

Evidence:

- [`../implementation_notes.md`](implementation_notes.md)
- [`../schematic.svg`](schematic.svg)
- [`../../README.md`](../README.md)
- [`../../../tasks/006-implement-quasi-model.md`](../../../tasks/006-implement-quasi-model.md)

### Task 007 - Metrics And Scenarios

What was tried:

- Made `scripts/metrics.py` model-family-aware.
- Added standardized quasi vessel metrics:
  `mean_<vessel>_inlet_flow_ml_s`, `mean_<vessel>_outlet_flow_ml_s`,
  `integral_<vessel>_inlet_flow_ml`, `integral_<vessel>_outlet_flow_ml`,
  `<vessel>_cycle_storage_ml`, and `<vessel>_mass_balance_rel`.
- Regenerated baseline, vasodilation, fenestration, and LPA obstruction
  reference metrics.

Result:

- Quasi metrics and scenario comparisons are available.
- Full 0-D metrics remained compatible.

Evidence:

- [`../reference_outputs/baseline_metrics.json`](../reference_outputs/baseline_metrics.json)
- [`../reference_outputs/scenario_comparison.txt`](../reference_outputs/scenario_comparison.txt)
- [`../../../tasks/007-quasi-metrics-and-scenarios.md`](../../../tasks/007-quasi-metrics-and-scenarios.md)

### Task 008 - First Calibration

What was tried:

- Small global retuning around:
  - `heart_contractility_scale = 0.96`;
  - `upper_systemic_resistance_scale = 1.04`;
  - `lower_systemic_resistance_scale = 1.12`;
  - `pulmonary_bed_resistance_scale = 1.10`.
- Preserved every quasi chain's total resistance, inertance, and compliance.
- Regenerated baseline and intervention reference outputs.
- Added first objective and waveform comparison reports.

Result:

- Aggregate direct-measurement weighted RMS error improved:
  - before Task 008: `0.0817`;
  - after Task 008: `0.0610`;
  - full 0-D reference: `0.0614`.
- This was later judged scientifically provisional because a lower aggregate
  score hid hard pump and waveform regressions.

Evidence:

- [`../../../tasks/008-calibrate-quasi-model.md`](../../../tasks/008-calibrate-quasi-model.md)
- [`../calibration/baseline_objective.json`](../calibration/baseline_objective.json)
- [`../calibration/baseline_waveforms_direct.json`](../calibration/baseline_waveforms_direct.json)

### Task 008.5 - Corrective Calibration And Non-Regression Gate

What was tried:

- Added `scripts/calibration/quasi_non_regression.py`.
- Extended waveform reports to record selected model and reference columns.
- Split scoring into hard clinical targets, soft/problematic targets,
  paper-model comparison, waveform no-strong-regression, and stability.
- Added separate right/left pulmonary total resistance scales, pulmonary
  proximal fractions, and chain-specific R/L/C scale factors.
- Screened heart-frozen variants before accepting the previous heart scale as a
  documented limitation.

Selected corrective factors:

| Factor | Value |
|---|---:|
| Heart contractility scale | 0.96 |
| Upper systemic resistance scale | 1.00 |
| Lower systemic resistance scale | 1.12 |
| Right pulmonary total resistance scale | 1.15 |
| Left pulmonary total resistance scale | 1.15 |
| Right pulmonary proximal fraction | 0.50 |
| Left pulmonary proximal fraction | 0.50 |
| All quasi chain R/L/C scales | 1.00 |

Result:

- Stability and loop-balance gates passed.
- RPA pressure, LPA pressure, SVC flow, and RPA/LPA flow fraction passed
  full-0D non-regression.
- EDV, ESV, SV, and CO still failed pump non-regression.
- Paper-model score remained slightly worse than full 0-D.
- AAo and DAo flow waveform behavior still failed.
- The model was marked as a stable corrective prototype, not a superior quasi
  model.

Evidence:

- [`../calibration/calibration_report.md`](../calibration/calibration_report.md)
- [`../calibration/non_regression_gate.json`](../calibration/non_regression_gate.json)
- [`../../../tasks/008-5-corrective-quasi-calibration.md`](../../../tasks/008-5-corrective-quasi-calibration.md)

### Task 008.6 - Design Audit And Closure Matrix

What was tried:

- Audited AAo and DAo flow signal selection across candidate model columns,
  sign convention, anatomical location, and phase sensitivity.
- Quantified compliance/storage and characteristic impedance.
- Ran a 23-candidate design/ablation matrix:
  - current topology with frozen full 0-D heart;
  - small heart adjustments;
  - aortic R/L/C perturbations;
  - caval R/L/C perturbations;
  - pulmonary R/L/C perturbations;
  - pulmonary proximal/distal split changes;
  - pulmonary total resistance changes;
  - distributed aortic branch takeoff topologies;
  - four-port TCPC separation;
  - combined distributed-aorta plus four-port TCPC topology.

Key candidate observations:

- `current_heart_099` was the best hard/direct candidate, but still failed EDV,
  ESV, RPA pressure, LPA pressure, and AAo/DAo flow waveform gates.
- `aortic_L0_5` was the best waveform candidate, but still failed hard and
  waveform gates.
- Distributed aortic branch topologies severely worsened the loop, including
  CO near `1.72 L/min` and SVC flow near `2 ml/s`.
- Four-port TCPC separation did not materially improve closure gates.

Result:

- No Task 008.6 candidate passed all hard, paper-comparison, waveform,
  stability, and mass-balance gates.
- No tracked quasi config, schematic, or implementation topology was promoted.
- Status:
  `stable_quasi_development_scaffold_not_scientifically_superior`.

Evidence:

- [`../calibration/design_audit_report.md`](../calibration/design_audit_report.md)
- [`../calibration/dao_aao_flow_signal_audit.csv`](../calibration/dao_aao_flow_signal_audit.csv)
- [`../calibration/compliance_budget.csv`](../calibration/compliance_budget.csv)
- [`../calibration/characteristic_impedance_report.csv`](../calibration/characteristic_impedance_report.csv)
- [`../calibration/quasi_ablation_summary.csv`](../calibration/quasi_ablation_summary.csv)
- [`../calibration/quasi_final_decision.md`](../calibration/quasi_final_decision.md)
- [`../../../tasks/008-6-quasi-design-audit-and-calibration-closure.md`](../../../tasks/008-6-quasi-design-audit-and-calibration-closure.md)

### Task 008.7 - Frozen Superiority Gate

What was tried:

- Added `scripts/calibration/compare_quasi_to_full0d.py`.
- Froze full 0-D reference scores.
- Wrote machine-readable promotion criteria.
- Recomputed the current quasi status against the frozen gate.

Promotion requires all of:

- stability and balance;
- hard clinical score not worse than full 0-D;
- aggregate direct score not worse than full 0-D;
- paper-model score not worse than full 0-D;
- pump non-regression;
- Fontan/pulmonary non-regression;
- AAo and DAo waveform no-regression;
- at least one quasi-specific vascular improvement.

Result:

- Current quasi status is `not_superior_to_full_0d`.
- Later quasi candidates must pass the same gate before promotion.

Evidence:

- [`../calibration/quasi_superiority_gate.json`](../calibration/quasi_superiority_gate.json)
- [`../calibration/full0d_reference_scores.json`](../calibration/full0d_reference_scores.json)
- [`../calibration/current_quasi_gate_status.md`](../calibration/current_quasi_gate_status.md)
- [`../../../quasi_improvement_task_series/008-7-freeze-quasi-superiority-gate.md`](../../../quasi_improvement_task_series/008-7-freeze-quasi-superiority-gate.md)

### Task 008.8 - Open-Loop Aortic Diagnostic

What was tried:

- Added `models/quasi_0d_1d/configs/submodel_aorta_quasi_openloop.jsonc`.
- Added scripts to run and evaluate the aortic-only diagnostic.
- Prescribed AAo inflow, retained the quasi AAo/arch/DAo chain and systemic
  branch/load blocks, and terminated SVC/IVC with pressure boundaries.
- Reported DAo chain outlet flow and lower-body outflow separately.

Result:

- Status: `fail_open_loop_aortic_diagnostic`.
- Prescribed AAo inflow nRMSE was `0.004`.
- DAo chain outlet flow nRMSE was `0.424`.
- Lower-body `lower_ra4.flow` nRMSE was `0.332`.
- Aortic chain mass-balance error was `4.714e-03`.
- AAo, arch, and DAo mean-pressure errors were approximately `-5.04`,
  `-4.71`, and `-4.52` mmHg.
- Pulse-pressure relative errors were approximately `-0.695`, `-0.728`, and
  `-0.510`.

Interpretation:

- The issue was not just a closed-loop calibration artifact.
- Likely causes were aortic-chain or terminal-load impedance mismatch,
  branch/load topology, or resistance placement.
- The diagnostic did not promote a new closed-loop topology.

Evidence:

- [`../configs/submodel_aorta_quasi_openloop.jsonc`](../configs/submodel_aorta_quasi_openloop.jsonc)
- [`../calibration/aorta_quasi_openloop_report.md`](../calibration/aorta_quasi_openloop_report.md)
- [`../calibration/aorta_quasi_openloop_metrics.json`](../calibration/aorta_quasi_openloop_metrics.json)
- [`../../../quasi_improvement_task_series/008-8-openloop-aortic-quasi-diagnostic.md`](../../../quasi_improvement_task_series/008-8-openloop-aortic-quasi-diagnostic.md)

### Task 008.9 - Aortic Signal Policy

What was tried:

- Added a machine-readable aortic signal policy and helper script.
- Updated waveform and superiority-gate scripts to use policy-defined aortic
  signal mappings.
- Separated clinical DAo flow from DAo trunk-chain health.

Policy decisions:

| Signal | Quasi column | Full 0-D column | Role |
|---|---|---|---|
| `P_AAo` | `aao.blood_pressure` | `aao.blood_pressure` | soft target |
| `P_arch` | `aortic_arch.blood_pressure` | `aortic_arch.blood_pressure` | soft target |
| `P_DAo` | `dao.blood_pressure` | `dao.blood_pressure` | diagnostic |
| `Q_AAo` | `valve_arterial.flux` | `valve_arterial.flux` | hard gate |
| `Q_DAo` clinical | `lower_ra4.flow` | `lower_ra4.flow` | soft target |
| `Q_DAo_chain_health` | `quasi_dao_rl_06.flux` | `arch_dao.flow` | diagnostic gate |

Result:

- AAo flow no-regression passed under the new policy:
  `0.560` quasi versus `0.572` full 0-D.
- DAo chain-health no-regression still failed:
  `0.952` quasi versus `0.434` full 0-D.
- Phase-shifted nRMSE remains diagnostic only; acceptance uses unshifted nRMSE.
- The current quasi model remained not superior.

Evidence:

- [`../calibration/aortic_signal_policy.md`](../calibration/aortic_signal_policy.md)
- [`../calibration/aortic_signal_policy.json`](../calibration/aortic_signal_policy.json)
- [`../../../quasi_improvement_task_series/008-9-resolve-aortic-flow-signal-policy.md`](../../../quasi_improvement_task_series/008-9-resolve-aortic-flow-signal-policy.md)

### Task 008.10 - Corrected Aortic Chain Design

What was tried:

- Created a corrected aortic-chain fragment for candidate testing.
- Tested a small matrix around:
  - aortic resistance scale;
  - aortic inertance scale;
  - aortic capacitance scale;
  - endpoint aortic compliance redistribution;
  - terminal arterial compliance;
  - lower-body proximal load placement;
  - systemic resistance smoke scaling.
- Avoided promoting the previous distributed-branch topology because it caused
  severe CO/SVC-flow collapse in Task 008.6.

Best open-loop corrected-chain setting:

```text
candidate: ep0.02_art0.5
aortic_R_scale: 7.0
aortic_L_scale: 1.0
aortic_C_scale: 1.0
endpoint_compliance_scale: 0.02
terminal_arterial_compliance_scale: 0.5
```

Open-loop result:

| Metric | Value |
|---|---:|
| Mass-balance error | 5.45e-04 |
| AAo to DAo mean drop | 0.622 mmHg |
| Target AAo to DAo mean drop | about 0.604 mmHg |
| DAo chain nRMSE | 0.227 |
| Lower-body DAo nRMSE | 0.239 |

Best defensible closed-loop partial candidate:

```text
candidate: ep02_r7_art05_frac95
aortic_R_scale: 7.0
aortic_L_scale: 1.0
aortic_C_scale: 1.0
endpoint_compliance_scale: 0.02
terminal_arterial_compliance_scale: 0.5
lower_systemic_proximal_fraction: 0.95
```

Closed-loop result:

| Check | Candidate | Comparator | Status |
|---|---:|---:|---|
| CO | 2.353 L/min | n/a | stable |
| SVC flow | 19.310 ml/s | n/a | stable |
| Q_AAo nRMSE | 0.551 | 0.572 | pass |
| Q_DAo clinical nRMSE | 0.352 | 0.331 | fail |
| Q_DAo chain-health nRMSE | 0.361 | 0.434 | pass |
| TCPC cycle balance | 3.13e-06 | n/a | pass |

Result:

- Corrected-chain candidates restored realistic passive AAo-to-DAo drop and
  removed the severe DAo chain-health waveform regression.
- No tested candidate passed the strict clinical DAo no-regression control.
- Task 008.10 is `blocked_not_promoted`.
- `quasi_vessel_chains_corrected.json` is an evidence artifact, not the default
  quasi fragment.

Evidence:

- [`../config_fragments/quasi_vessel_chains_corrected.json`](../config_fragments/quasi_vessel_chains_corrected.json)
- [`../calibration/aortic_chain_design_report.md`](../calibration/aortic_chain_design_report.md)
- [`../calibration/aortic_chain_design_candidates.csv`](../calibration/aortic_chain_design_candidates.csv)
- [`../../../quasi_improvement_task_series/008-10-correct-quasi-aortic-chain-design.md`](../../../quasi_improvement_task_series/008-10-correct-quasi-aortic-chain-design.md)

## Not Yet Tried

The remaining quasi closure sequence is planned but has not been completed.
These tasks should stay blocked behind the Task 008.10 clinical DAo issue
unless the acceptance policy is explicitly changed.

| Task | Status | Purpose |
|---|---|---|
| 008.11 | planned | Correct Fontan/pulmonary quasi impedance design. |
| 008.12 | planned | Restore pump/preload and compliance budget. |
| 008.13 | planned | Run constrained quasi closed-loop calibration after design corrections. |
| 008.14 | planned | Validate scenarios and promote only if the frozen superiority gate passes. |

## Artifacts To Trust

Use these files as the current acceptance record:

- [`../calibration/calibration_report.md`](../calibration/calibration_report.md)
- [`../calibration/non_regression_gate.json`](../calibration/non_regression_gate.json)
- [`../calibration/quasi_final_decision.md`](../calibration/quasi_final_decision.md)
- [`../calibration/quasi_superiority_gate.json`](../calibration/quasi_superiority_gate.json)
- [`../calibration/current_quasi_gate_status.md`](../calibration/current_quasi_gate_status.md)
- [`../calibration/aortic_signal_policy.md`](../calibration/aortic_signal_policy.md)
- [`../calibration/aortic_chain_design_report.md`](../calibration/aortic_chain_design_report.md)

Use these files as design evidence, not promotion artifacts:

- [`../config_fragments/quasi_vessel_chains_corrected.json`](../config_fragments/quasi_vessel_chains_corrected.json)
- [`../calibration/aortic_chain_design_candidates.csv`](../calibration/aortic_chain_design_candidates.csv)
- [`../calibration/quasi_ablation_summary.csv`](../calibration/quasi_ablation_summary.csv)
- [`../calibration/aorta_quasi_openloop_report.md`](../calibration/aorta_quasi_openloop_report.md)

## Reproduction Commands

The main commands used across the quasi closure work were:

```bash
.venv/bin/python scripts/modeling/derive_quasi_vessel_parameters.py
.venv/bin/python scripts/modeling/build_quasi_configs.py
.venv/bin/python scripts/modeling/build_quasi_configs.py --check
.venv/bin/python scripts/run_one.py models/quasi_0d_1d/configs/fontan_quasi_smoke.jsonc --series QuasiSmoke
.venv/bin/python scripts/calibration/run_quasi_calibration.py --run-reference-scenarios --write-objective-reports
.venv/bin/python scripts/calibration/quasi_non_regression.py --out models/quasi_0d_1d/calibration/non_regression_gate.json
.venv/bin/python scripts/calibration/audit_quasi_design.py
.venv/bin/python scripts/calibration/run_quasi_ablation_grid.py
.venv/bin/python scripts/calibration/run_quasi_closure_calibration.py
.venv/bin/python scripts/calibration/map_aortic_signals.py
.venv/bin/python scripts/calibration/compare_quasi_to_full0d.py
.venv/bin/python scripts/quasi/run_aorta_quasi_openloop.py
.venv/bin/python scripts/quasi/evaluate_aorta_quasi_openloop.py
.venv/bin/python -m pytest -q
```

The latest recorded full-suite validation before this log was added is:
`67 passed` for Task 008.7, with focused gate tests passing. Earlier Task
008.6 closure validation recorded `63 passed in 1.01s`. Re-run the full suite
after any further code or config change.

## Guardrails For Later Work

- Do not promote a quasi config because only the aggregate direct score
  improves.
- Do not let direct DAo pressure or raw direct IVC flow compensate for failed
  hard pump, paper-model, waveform, stability, or mass-balance gates.
- Do not silently replace DAo chain-health flow with `lower_ra4.flow`; report
  both signals and keep their roles separate.
- Do not promote `quasi_vessel_chains_corrected.json` into the default configs
  until the clinical DAo no-regression failure is resolved or the Task 008.10
  control is explicitly changed.
- Keep full 0-D as the calibrated reference until a later quasi candidate
  passes the frozen Task 008.7 gate.
- Simulation outputs remain computational development artifacts, not clinically
  validated results.
