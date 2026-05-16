# Task 008.10 — Correct Quasi Aortic Chain Design

Status: blocked_not_promoted

## Goal

Modify the quasi aortic chain so that it has realistic resistance, inertance, compliance, and branch loading. The current quasi model improves some pressures but strongly regresses AAo and DAo flow waveforms.

This task should produce a corrected aortic quasi design before closed-loop recalibration.

## Inputs

Use:

```text
models/quasi_0d_1d/config_fragments/quasi_vessel_chains.json
models/quasi_0d_1d/calibration/aorta_quasi_openloop_metrics.json
models/quasi_0d_1d/calibration/aortic_signal_policy.json
models/quasi_0d_1d/calibration/characteristic_impedance_report.csv
models/quasi_0d_1d/calibration/compliance_budget.csv
data/processed/aramburu_2024/model_inputs/aorta_geometry.csv
```

## Required implementation

Create or update:

```text
models/quasi_0d_1d/config_fragments/quasi_vessel_chains_corrected.json
models/quasi_0d_1d/calibration/aortic_chain_design_report.md
models/quasi_0d_1d/calibration/aortic_chain_design_candidates.csv
```

Test a small design matrix around:

```text
aortic_R_scale
aortic_L_scale
aortic_C_scale
AAo/arch/DAo endpoint-compliance redistribution
branch-loading placement
terminal RCR-style matching
```

## Design requirements

### 1. Do not put large mean pressure loss inside the aortic trunk

The paper/Nektar aortic profile has only a small mean pressure drop:

```text
AAo ≈ 50.66 mmHg
Arch ≈ 50.33 mmHg
DAo ≈ 50.06 mmHg
AAo→DAo drop ≈ 0.60 mmHg
```

The quasi design should avoid a large aortic-trunk drop. Most systemic pressure loss should be in systemic beds, not AAo→Arch→DAo.

### 2. Redistribute compliance rather than only adding it

If chain capacitances are added, reduce retained endpoint compliances where appropriate:

```text
total local aortic compliance = endpoint compliance + internal chain compliance
```

Track this explicitly.

### 3. Match impedance at branch/load interfaces

Use the characteristic impedance report to reduce artificial reflections. Large mismatch ratios should guide load changes.

### 4. Avoid the currently failed distributed-branch topology unless debugged separately

The previous distributed-branch ablations produced severe CO/SVC-flow collapse. Do not promote that topology in this task unless the topology error is identified and corrected.

## Candidate testing

For each candidate, run:

```text
1. open-loop aortic test;
2. short closed-loop smoke;
3. full baseline if smoke passes.
```

## Control

This task is complete only if one corrected aortic-chain candidate passes:

```text
1. Open-loop aortic mass-balance error passes.
2. AAo→DAo mean pressure drop is close to paper/Nektar profile or explicitly justified.
3. Q_AAo nRMSE is not worse than full 0-D.
4. Q_DAo clinical nRMSE is not worse than full 0-D.
5. Q_DAo chain health nRMSE is no longer a severe regression.
6. The corrected candidate does not collapse CO or SVC flow in closed-loop smoke.
```

## Task 008.10 Result

Task 008.10 was attempted on 2026-05-15 and is not complete under its own
control criteria.

Created artifacts:

```text
models/quasi_0d_1d/config_fragments/quasi_vessel_chains_corrected.json
models/quasi_0d_1d/calibration/aortic_chain_design_report.md
models/quasi_0d_1d/calibration/aortic_chain_design_candidates.csv
```

Best defensible partial candidate:

```text
candidate: ep02_r7_art05_frac95
aortic_R_scale: 7.0
aortic_L_scale: 1.0
aortic_C_scale: 1.0
endpoint_compliance_scale: 0.02
terminal_arterial_compliance_scale: 0.5
lower_systemic_proximal_fraction: 0.95
```

It passed open-loop mass/drop, closed-loop stability, Q_AAo no-regression, and
Q_DAo chain-health no-regression. It failed the required clinical Q_DAo
criterion:

```text
candidate Q_DAo clinical nRMSE: 0.352
full 0-D Q_DAo clinical nRMSE: 0.331
```

Do not promote the corrected fragment into default quasi configs until the
clinical DAo outlet issue is resolved or the Task 008.10 control is explicitly
changed.
