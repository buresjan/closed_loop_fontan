# Task 008.8 — Build Open-Loop Aortic Quasi Diagnostic Harness

Status: completed

Completion date: 2026-05-15

Outcome: the diagnostic harness was implemented, generated, run, and evaluated.
The current quasi aortic chain fails the open-loop diagnostic because the
pressure profile and pulse pressure are too damped, even though the prescribed
AAo inflow, DAo chain outlet flow, lower-body outflow, and chain mass balance
are reported separately.

## Goal

Diagnose the quasi aortic chain outside the full closed loop. The current closed-loop quasi model strongly regresses AAo and DAo flow waveforms, especially DAo chain flow.

Before further closed-loop calibration, determine whether the aortic quasi chain can reproduce the measured / paper-consistent aortic pressure-flow behavior in an open-loop setting.

## Inputs

Use:

```text
data/processed/aramburu_2024/measurements_clinical.csv
data/processed/aramburu_2024/comparison/measurements_last_cycle_clinical.csv
data/processed/aramburu_2024/comparison/03_aorta_tcpc_1d_last_cycle_clinical.csv
data/processed/aramburu_2024/comparison/04_aorta_tcpc_closedloop_1d_last_cycle_clinical.csv
data/processed/aramburu_2024/model_inputs/aorta_geometry.csv
models/quasi_0d_1d/config_fragments/quasi_vessel_chains.json
models/quasi_0d_1d/configs/fontan_quasi_baseline.jsonc
```

Use the already established DAo target policy:

```text
Direct DAo pressure is soft/diagnostic because it violates passive pressure ordering.
Paper/Nektar aortic pressure profile is preferred for passive aortic-profile checks.
```

## Required implementation

Create:

```text
models/quasi_0d_1d/configs/submodel_aorta_quasi_openloop.jsonc
scripts/quasi/run_aorta_quasi_openloop.py
scripts/quasi/evaluate_aorta_quasi_openloop.py
models/quasi_0d_1d/calibration/aorta_quasi_openloop_report.md
models/quasi_0d_1d/calibration/aorta_quasi_openloop_metrics.json
models/quasi_0d_1d/calibration/aorta_quasi_openloop_waveforms.csv
```

The open-loop submodel should use:

```text
measured AAo inflow or paper/Nektar AAo inflow
→ quasi AAo/arch/DAo chain
→ terminal upper/lower systemic loads
```

It should evaluate:

```text
AAo pressure
arch pressure
DAo pressure
DAo chain flow
lower_ra4 / lower-body outflow
pressure drop AAo→arch→DAo
mass balance across the aortic chain
```

## Required diagnostics

Report at least:

```text
1. mean pressure errors for AAo, arch, DAo;
2. pulse-pressure errors for AAo, arch, DAo;
3. AAo flow waveform nRMSE;
4. DAo chain outlet flow nRMSE;
5. lower_ra4.flow nRMSE;
6. AAo→DAo mean pressure drop;
7. chain mass-balance error;
8. whether failure is caused mostly by amplitude, timing, sign, or topology.
```

## Design rule

Do not attempt to fix the quasi closed loop until the aortic submodel behavior is understood. The closed loop cannot compensate reliably for a broken aortic chain.

## Control

This task is complete only if:

```text
1. aorta_quasi_openloop_report.md clearly states whether the quasi aortic chain passes or fails open-loop.
2. DAo chain flow and lower_ra4.flow are both reported, not substituted silently.
3. Sign-flipped and phase-shifted waveform diagnostics are included.
4. The report identifies the most likely cause of AAo/DAo flow regression:
   - wrong signal;
   - excessive inertance;
   - excessive/insufficient compliance;
   - wrong resistance placement;
   - wrong branch/load topology;
   - target-location mismatch.
```

## Completion Notes

Created:

```text
models/quasi_0d_1d/configs/submodel_aorta_quasi_openloop.jsonc
scripts/quasi/run_aorta_quasi_openloop.py
scripts/quasi/evaluate_aorta_quasi_openloop.py
models/quasi_0d_1d/calibration/aorta_quasi_openloop_report.md
models/quasi_0d_1d/calibration/aorta_quasi_openloop_metrics.json
models/quasi_0d_1d/calibration/aorta_quasi_openloop_waveforms.csv
```

Reproduce the diagnostic:

```bash
.venv/bin/python scripts/quasi/run_aorta_quasi_openloop.py --skip-run
.venv/bin/python scripts/quasi/run_aorta_quasi_openloop.py
.venv/bin/python scripts/quasi/evaluate_aorta_quasi_openloop.py
```

The generated report records
`fail_open_loop_aortic_diagnostic`. The primary issue is insufficient pressure
pulse/profile response across the aortic chain and terminal loads. The likely
causes are an R/L/C or terminal-load impedance mismatch and/or branch/load
topology or resistance placement, not a silent substitution of lower-body flow
for DAo chain flow.
