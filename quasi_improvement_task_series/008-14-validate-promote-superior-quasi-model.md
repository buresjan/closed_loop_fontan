# Task 008.14 — Validate Scenarios and Promote Superior Quasi Model

## Goal

Promote the quasi 0-D/1-D model only if it performs better than the full 0-D model and remains physiologically credible in intervention scenarios.

This is the final task in the quasi closure sequence.

## Inputs

Use:

```text
models/quasi_0d_1d/configs/fontan_quasi_baseline_candidate.jsonc
models/quasi_0d_1d/configs/fontan_quasi_vasodilation.jsonc
models/quasi_0d_1d/configs/fontan_quasi_fenestration.jsonc
models/quasi_0d_1d/configs/fontan_quasi_lpa_obstruction.jsonc
models/quasi_0d_1d/calibration/final_quasi_gate_status.json
models/quasi_0d_1d/calibration/quasi_superiority_gate.json
models/full_0d/reference_outputs/
models/quasi_0d_1d/reference_outputs/
data/processed/aramburu_2024/paper_results/model.csv
```

## Required implementation

Create:

```text
models/quasi_0d_1d/calibration/final_quasi_vs_full0d_report.md
models/quasi_0d_1d/calibration/final_quasi_vs_full0d_summary.csv
models/quasi_0d_1d/reference_outputs/final_baseline_metrics.json
models/quasi_0d_1d/reference_outputs/final_vasodilation_metrics.json
models/quasi_0d_1d/reference_outputs/final_fenestration_metrics.json
models/quasi_0d_1d/reference_outputs/final_lpa_obstruction_metrics.json
models/quasi_0d_1d/reference_outputs/final_scenario_comparison.txt
models/quasi_0d_1d/configs/fontan_quasi_baseline.jsonc
```

Only overwrite/promote `fontan_quasi_baseline.jsonc` if the promotion gate passes.

## Scenario checks

Run without retuning:

```text
baseline
25% pulmonary vasodilation
fenestration
LPA obstruction
```

Expected directions:

```text
vasodilation:
  CO increases
  SV increases
  TCPC pressure decreases
  pulmonary flow increases

fenestration:
  fenestration flow becomes positive
  CO increases or remains physiologically plausible
  pulmonary flow decreases or increases less than systemic CO
  TCPC pressure decreases or remains bounded

LPA obstruction:
  LPA flow decreases
  RPA flow fraction increases
  TCPC pressure increases or remains physiologically plausible
```

## Required final claim

If the gate passes, the report may state:

```text
The quasi 0-D/1-D model is now superior to the full 0-D baseline under the frozen promotion gate.
```

If it fails, the report must state:

```text
The quasi 0-D/1-D model remains a stable development scaffold and is not promoted.
```

## Control

This task is complete only if:

```text
1. final_quasi_gate_status.json reports PASS.
2. final_quasi_vs_full0d_report.md states the quasi model is superior under the frozen gate.
3. Hard clinical score is <= full 0-D.
4. Paper-model score is <= full 0-D.
5. Direct aggregate score is <= full 0-D.
6. Pump non-regression gates pass.
7. RPA/LPA/SVC gates pass.
8. AAo/DAo waveform gates pass.
9. Scenario responses have the expected physiological directions.
10. The promoted quasi config is copied to:
    models/quasi_0d_1d/configs/fontan_quasi_baseline.jsonc
11. The old non-superior quasi config is preserved under an archive name.
```

If all controls pass, the task series ends with a quasi closed loop that performs better than the full 0-D closed loop.
