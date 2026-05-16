# Task 008.12 — Restore Pump/Preload and Compliance Budget

## Goal

Recover EDV, ESV, SV, and CO after adding quasi vessel dynamics. The current quasi model has lower pump quantities than the full 0-D baseline and fails the pump non-regression gates.

Current quasi values:

```text
EDV ≈ 70.04 ml, target 74.40 ml
ESV ≈ 34.80 ml, target 37.60 ml
SV  ≈ 35.23 ml, target 36.80 ml
CO  ≈ 2.47 L/min, target 2.57 L/min
```

This is likely related to impedance and volume/storage redistribution, not just contractility.

## Inputs

Use:

```text
models/quasi_0d_1d/calibration/compliance_budget.csv
models/quasi_0d_1d/calibration/aortic_chain_design_report.md
models/quasi_0d_1d/calibration/fontan_pulmonary_design_report.md
models/full_0d/reference_outputs/baseline_metrics.json
models/quasi_0d_1d/reference_outputs/baseline_metrics.json
```

## Required implementation

Create or update:

```text
models/quasi_0d_1d/calibration/preload_compliance_budget_report.md
models/quasi_0d_1d/calibration/preload_restoration_candidates.csv
models/quasi_0d_1d/config_fragments/quasi_preload_corrected.json
```

## Things to inspect

### 1. Added storage

For each quasi chain, compute:

```text
internal chain compliance
retained endpoint compliance
total local compliance
estimated gauge storage over the final cycle
```

Check whether the quasi model effectively added vascular storage without removing storage elsewhere.

### 2. Preload-sensitive parameters

Prioritize physically meaningful preload restoration:

```text
active atrium unstressed volume
active atrium elastance_min/elastance_max
venous compliance distribution
SVC/IVC compliance
initial pressure / stressed-volume proxy if present
heart radius / chamber size small adjustment
```

Do not rely only on:

```text
heart_contractility_scale
```

because contractility changes may fix SV while hiding a preload/volume-distribution problem.

### 3. Endpoint-compliance redistribution

For quasi vessels, test:

```text
additive compliance design
redistributed compliance design
```

The redistributed design is preferred if it restores pump volumes without worsening pressures.

## Calibration rule

First recover pump quantities while holding the corrected aortic and pulmonary designs fixed. Then allow small vascular retuning.

## Control

This task is complete only if one preload-restored candidate passes:

```text
1. EDV error <= full 0-D EDV error + 0.5 percentage points.
2. ESV error <= full 0-D ESV error + 0.5 percentage points.
3. SV error  <= full 0-D SV error  + 0.5 percentage points.
4. CO error  <= full 0-D CO error  + 0.5 percentage points.
5. The candidate does not make RPA/LPA pressure errors worse than full 0-D.
6. The candidate does not reintroduce strong AAo/DAo flow waveform regression.
7. Mass balance and periodicity pass.
```
