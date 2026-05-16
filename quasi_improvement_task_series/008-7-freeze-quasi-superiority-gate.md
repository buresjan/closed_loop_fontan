# Task 008.7 — Freeze Quasi Superiority Gate and Reference Metrics

Status: completed

## Goal

Define exactly what it means for the quasi 0-D/1-D loop to be **better than the full 0-D loop**. The current aggregate direct score is misleading because soft/problematic targets improved while hard pump and waveform targets regressed.

This task must produce a fixed, machine-readable promotion gate that all later quasi candidates must pass.

## Inputs

Use existing artifacts:

```text
models/full_0d/calibration/
models/full_0d/reference_outputs/
models/quasi_0d_1d/calibration/baseline_objective.json
models/quasi_0d_1d/calibration/baseline_vs_paper.json
models/quasi_0d_1d/calibration/baseline_waveforms_direct.json
models/quasi_0d_1d/calibration/non_regression_gate.json
models/quasi_0d_1d/calibration/quasi_final_decision.json
models/quasi_0d_1d/calibration/quasi_final_decision.md
```

Use the reported reference values:

```text
full_0d_direct_score = 0.0614
full_0d_hard_score   = 0.0433
full_0d_paper_score  = 0.0793
full_0d_AAo_flow_nRMSE = 0.499
full_0d_DAo_flow_nRMSE = 0.434
```

## Required implementation

Create:

```text
scripts/calibration/compare_quasi_to_full0d.py
models/quasi_0d_1d/calibration/quasi_superiority_gate.json
models/quasi_0d_1d/calibration/full0d_reference_scores.json
models/quasi_0d_1d/calibration/current_quasi_gate_status.json
models/quasi_0d_1d/calibration/current_quasi_gate_status.md
```

The script should compare a quasi baseline run against the frozen full 0-D reference.

## Required gate definition

A quasi candidate is superior only if all of these are true:

```text
1. Stability / numerical gates pass:
   - no NaN/Inf
   - periodicity gates pass
   - TCPC, atrial, and ventricle balance gates pass

2. Hard clinical summary score is not worse than full 0-D:
   quasi_hard_score <= full_0d_hard_score

3. Aggregate direct score is not worse than full 0-D:
   quasi_direct_score <= full_0d_direct_score

4. Paper-model score is not worse than full 0-D:
   quasi_paper_score <= full_0d_paper_score

5. Pump non-regression:
   EDV, ESV, SV, and CO errors must each be <= the full 0-D error + 0.5 percentage points.

6. Fontan/pulmonary non-regression:
   RPA pressure, LPA pressure, SVC flow, RPA flow, LPA flow, and RPA/LPA split must not be worse than full 0-D by more than 0.5 percentage points.

7. Aortic waveform no-regression:
   AAo flow nRMSE <= full_0d_AAo_flow_nRMSE
   DAo flow nRMSE <= full_0d_DAo_flow_nRMSE

8. At least one quasi-specific vascular target must improve:
   accepted examples:
   - DAo pressure profile improves versus full 0-D using the approved DAo target policy;
   - SVC/IVC/RPA/LPA waveform score improves;
   - aortic open-loop profile improves.
```

## Notes

Direct DAo pressure and raw direct IVC flow remain soft/problematic targets. They must not compensate for failed pump or waveform gates.

## Control

This task is complete only if:

```text
1. compare_quasi_to_full0d.py reproduces the known full 0-D and current quasi scores.
2. current_quasi_gate_status.md explicitly reports the current quasi model as not superior.
3. quasi_superiority_gate.json contains the final frozen promotion criteria.
4. Later tasks can call the same script without changing the gate definition.
```

## Completion Notes

Completed on 2026-05-15.

Created:

```text
scripts/calibration/compare_quasi_to_full0d.py
models/quasi_0d_1d/calibration/quasi_superiority_gate.json
models/quasi_0d_1d/calibration/full0d_reference_scores.json
models/quasi_0d_1d/calibration/current_quasi_gate_status.json
models/quasi_0d_1d/calibration/current_quasi_gate_status.md
```

The frozen gate requires all of these groups to pass:

```text
stability
score_non_regression
pump_non_regression
fontan_pulmonary_non_regression
aortic_waveform_no_regression
quasi_specific_vascular_improvement
```

The current quasi model is explicitly not superior:

```text
status = not_superior_to_full_0d
accepted_as_superior = false
failed_groups = score_non_regression, pump_non_regression,
                fontan_pulmonary_non_regression,
                aortic_waveform_no_regression
```

The current quasi model still passes stability and has at least one
quasi-specific vascular improvement, but this cannot compensate for failed
hard, paper, pump, Fontan/pulmonary, or AAo/DAo waveform gates.

Validation:

```bash
.venv/bin/python scripts/calibration/compare_quasi_to_full0d.py
.venv/bin/python -m pytest tests/test_quasi_superiority_gate.py -q
.venv/bin/python -m pytest -q
```

Results: focused gate tests `4 passed`; full suite `67 passed`.
