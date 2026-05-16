# Task 008.9 — Resolve AAo/DAo Flow Signal Definitions and Target Policy

Status: completed

Completion date: 2026-05-15

Outcome: the aortic signal policy is now machine-readable, documented, and used
by the waveform and superiority-gate scripts. The policy separates clinical DAo
flow (`lower_ra4.flow`) from DAo chain-health flow (`quasi_dao_rl_06.flux`).

## Goal

Decide exactly which model signal should be compared to each measured/paper aortic flow target. The current reports show a large difference between:

```text
quasi_dao_rl_06.flux  nRMSE ≈ 0.95
lower_ra4.flow        nRMSE ≈ 0.38
```

This task prevents the calibration from either hiding a true trunk-chain failure or unfairly penalizing the wrong anatomical signal.

## Inputs

Use:

```text
models/quasi_0d_1d/calibration/dao_aao_flow_signal_audit.csv
models/quasi_0d_1d/calibration/design_audit_report.md
models/quasi_0d_1d/calibration/aorta_quasi_openloop_report.md
data/processed/aramburu_2024/measurements_clinical.csv
data/processed/aramburu_2024/comparison/measurements_last_cycle_clinical.csv
data/processed/aramburu_2024/model_inputs/aorta_geometry.csv
```

## Required implementation

Create:

```text
models/quasi_0d_1d/calibration/aortic_signal_policy.md
models/quasi_0d_1d/calibration/aortic_signal_policy.json
scripts/calibration/map_aortic_signals.py
```

The policy must define:

```text
P_AAo model signal
P_arch model signal
P_DAo model signal
Q_AAo model signal
Q_DAo model signal
```

For each signal, state:

```text
model column
anatomical interpretation
measurement/paper target column
whether it is a hard gate, soft target, or diagnostic
reason
```

## Required decision points

Explicitly decide:

```text
1. Does measured Q_DAo correspond to flow inside the DAo trunk, or flow entering the lower-body systemic bed?
2. Should DAo chain outlet flow remain a waveform health diagnostic even if lower_ra4.flow is the clinical target?
3. Should phase-shifted nRMSE be used only diagnostically or as an acceptance metric?
4. Are AAo and DAo flow targets coming from the same cardiac-cycle phase convention as model outputs?
```

## Recommended policy

Use two DAo flow quantities:

```text
Q_DAo_clinical:
  best anatomical match to the measurement target;
  likely lower_ra4.flow if measurement is lower-body descending-aorta flow into systemic branch.

Q_DAo_chain_health:
  quasi chain outlet flow;
  remains a diagnostic and no-strong-regression check.
```

Do not remove the DAo chain health check. It is useful for detecting a broken quasi chain.

## Control

This task is complete only if:

```text
1. aortic_signal_policy.json is used by the waveform/objective scripts.
2. The report explicitly justifies the selected Q_DAo clinical signal.
3. The DAo chain health signal remains tracked separately.
4. No later calibration script hard-codes DAo flow columns outside this policy file.
```

## Completion Notes

Created:

```text
models/quasi_0d_1d/calibration/aortic_signal_policy.md
models/quasi_0d_1d/calibration/aortic_signal_policy.json
scripts/calibration/map_aortic_signals.py
tests/test_aortic_signal_policy.py
```

Implemented policy:

```text
P_AAo: aao.blood_pressure
P_arch: aortic_arch.blood_pressure
P_DAo: dao.blood_pressure
Q_AAo: valve_arterial.flux
Q_DAo clinical: lower_ra4.flow
Q_DAo chain health: quasi_dao_rl_06.flux
```

Decision summary:

```text
1. Measured Q_DAo is treated as lower-body DAo outflow for clinical waveform comparison.
2. DAo chain outlet flow remains a separate no-strong-regression diagnostic.
3. Phase-shifted nRMSE is diagnostic only; acceptance uses unshifted nRMSE.
4. AAo and DAo targets are treated as using the processed comparison-cycle phase convention.
```

Regenerated:

```text
models/quasi_0d_1d/calibration/baseline_waveforms_direct.json
models/quasi_0d_1d/calibration/non_regression_gate.json
models/quasi_0d_1d/calibration/quasi_superiority_gate.json
models/quasi_0d_1d/calibration/full0d_reference_scores.json
models/quasi_0d_1d/calibration/current_quasi_gate_status.json
models/quasi_0d_1d/calibration/current_quasi_gate_status.md
```

Task 008.9 does not promote the quasi model. Under the new policy, AAo flow
now passes the full 0-D no-regression comparison, but DAo chain-health flow
still fails (`0.952` quasi nRMSE versus `0.434` full 0-D reference nRMSE).
