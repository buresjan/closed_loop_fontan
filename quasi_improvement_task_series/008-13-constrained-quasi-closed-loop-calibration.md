# Task 008.13 — Constrained Quasi Closed-Loop Calibration

## Goal

Run the final quasi calibration using the corrected aortic design, corrected Fontan/pulmonary design, and restored preload/compliance budget.

Unlike Tasks 008 and 008.5, this calibration must not let soft targets hide hard-target regressions.

## Inputs

Use:

```text
models/quasi_0d_1d/config_fragments/quasi_vessel_chains_corrected.json
models/quasi_0d_1d/config_fragments/quasi_fontan_pulmonary_corrected.json
models/quasi_0d_1d/config_fragments/quasi_preload_corrected.json
models/quasi_0d_1d/calibration/quasi_superiority_gate.json
models/quasi_0d_1d/calibration/aortic_signal_policy.json
models/full_0d/calibration/full0d_reference_scores.json
```

## Required implementation

Create:

```text
models/quasi_0d_1d/configs/fontan_quasi_baseline_candidate.jsonc
models/quasi_0d_1d/calibration/final_quasi_calibration_report.md
models/quasi_0d_1d/calibration/final_quasi_calibration_factors.json
models/quasi_0d_1d/calibration/final_quasi_gate_status.json
models/quasi_0d_1d/calibration/final_quasi_gate_status.md
```

Update calibration scripts so that the objective is layered:

```text
1. Hard pump and clinical targets
2. Fontan/pulmonary targets
3. Paper-model comparison
4. Aortic and vascular waveform targets
5. Soft/problematic targets
```

The optimizer must treat the hard gates as constraints, not just terms in the weighted aggregate objective.

## Recommended tunable parameters

Use limited, interpretable scale factors:

```text
heart_radius_scale                    small range only
heart_contractility_scale             small range only
active_atrium_unstressed_volume_scale
active_atrium_elastance_scale
upper_systemic_resistance_scale
lower_systemic_resistance_scale
upper_venous_compliance_scale
lower_venous_compliance_scale
aortic_R_scale
aortic_L_scale
aortic_C_scale
SVC_limb_RLC_scales
IVC_limb_RLC_scales
RPA_limb_RLC_scales
LPA_limb_RLC_scales
pulmonary_Rprox_fraction_right
pulmonary_Rprox_fraction_left
pulmonary_total_resistance_right_scale
pulmonary_total_resistance_left_scale
```

Do not allow dozens of independent R/C/L values to vary freely.

## Do not overfit

Keep regularization against:

```text
paper priors
geometry-derived R/L/C values
full 0-D calibrated physiological values
previous accepted corrected designs
```

## Control

This task is complete only if the final quasi candidate passes:

```text
1. Stability and mass-balance gates.
2. Hard clinical score <= full 0-D hard clinical score.
3. Direct aggregate score <= full 0-D direct aggregate score.
4. Paper-model score <= full 0-D paper-model score.
5. EDV, ESV, SV, CO non-regression gates.
6. RPA/LPA pressure and flow non-regression gates.
7. SVC flow non-regression gate.
8. AAo and DAo flow waveform no-regression gates according to aortic_signal_policy.json.
9. At least one quasi-specific vascular metric improves over full 0-D.
```

If any of these fail, do not promote the quasi baseline. Return to Tasks
008.10-008.12 depending on the failure source.
