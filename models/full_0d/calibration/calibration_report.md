# Full 0-D Baseline Calibration Report

Completed on 2026-05-15 for Task 004.

## Scope

The baseline configuration was calibrated against
`data/processed/aramburu_2024/targets` using scale factors rather than raw
per-parameter optimization. The vasodilation, fenestration, and LPA obstruction
configs inherit the calibrated baseline and remain validation scenarios.

No PhysioBlocks internals were changed.

## Selected Scale Factors

| Scale | Value |
|---|---:|
| Heart rate | 69.93006993006986 bpm |
| Heart radius/thickness | 0.715 |
| Heart contractility | 0.42 |
| Aortic trunk resistance | 0.40 |
| Upper systemic resistance | 0.50 |
| Lower systemic resistance | 0.90 |
| Right pulmonary resistance | 0.45 |
| Left pulmonary resistance | 0.65 |
| TCPC entry resistance | 0.55 |
| Pressure-state initialization shift | 5.5 mmHg lower |
| Active atrium unstressed volume | 40 ml |
| Final scenario settling duration | 20 s |

The right/left pulmonary scale split intentionally favors RPA flow and matches
the measured RPA flow fraction.

## Baseline Fit

Primary comparison source: `direct_measurement`.

| Quantity | Model | Target | Error |
|---|---:|---:|---:|
| EDV | 71.65 ml | 74.40 ml | -3.7% |
| ESV | 35.77 ml | 37.60 ml | -4.9% |
| SV | 35.87 ml | 36.80 ml | -2.5% |
| CO | 2.51 L/min | 2.57 L/min | -2.3% |
| Mean AAo pressure | 47.79 mmHg | 50.40 mmHg | -5.2% |
| Mean aortic arch pressure | 47.12 mmHg | 51.73 mmHg | -8.9% |
| Mean DAo pressure | 44.00 mmHg | 53.15 mmHg | -17.2% |
| Mean SVC pressure | 9.11 mmHg | 8.87 mmHg | +2.7% |
| Mean IVC pressure | 8.93 mmHg | 8.54 mmHg | +4.6% |
| Mean RPA pressure | 7.78 mmHg | 8.48 mmHg | -8.3% |
| Mean LPA pressure | 7.78 mmHg | 8.46 mmHg | -8.0% |
| SVC flow | 20.23 ml/s | 20.59 ml/s | -1.7% |
| IVC flow | 21.57 ml/s | 18.84 ml/s | +14.5% |
| RPA flow | 24.70 ml/s | 24.43 ml/s | +1.1% |
| LPA flow | 17.10 ml/s | 16.88 ml/s | +1.3% |
| RPA flow fraction | 0.5909 | 0.5914 | -0.1% |

Weighted RMS relative error: `0.0614` against direct measurements and `0.0793`
against the paper/Nektar closed-loop outputs.

## Numerical Checks

| Check | Value | Threshold |
|---|---:|---:|
| Cavity-volume periodicity | 0.00627 | 0.02 |
| Aortic-valve flux periodicity | 0.00410 | 0.02 |
| Atrioventricular-valve flux periodicity | 0.00110 | 0.02 |
| TCPC cycle balance | 2.35e-05 | 1e-2 |
| Atrial cycle balance | 1.74e-04 | 1e-2 |
| Ventricle cycle balance | 9.01e-05 | 1e-2 |

## Validation Scenarios

Scenario metrics were regenerated without retuning:

- Pulmonary vasodilation: CO increases by 1.39%, TCPC pressure decreases by
  1.78%, and pulmonary flows increase.
- Fenestration: fenestration flow increases from near-zero baseline to
  0.75 ml/s while global CO changes minimally.
- LPA obstruction: RPA flow fraction increases from 0.591 to 0.743, left lung
  flow falls by 38.4%, and right lung flow rises by 23.2%.

The validation summaries are tracked in `scenario_validation_summary.txt`.

## Residual Gaps

- Descending-aorta mean pressure remains low relative to the direct measurement
  table. Matching it more closely caused worse SVC/IVC and pulmonary pressures
  in the tested parameter sets.
- IVC flow remains higher than the direct measurement target. The direct
  measurement flow totals are not perfectly mass-balanced against the volume-
  derived CO, so this was treated as a lower-weight target than SV, CO, and
  pulmonary split.
- Waveform-shape fitting is not active yet. This should wait for the
  model-family-aware metrics planned in later tasks.

## Reproduction

```bash
python scripts/calibration/run_calibration.py --write-configs
python scripts/calibration/run_calibration.py --run-reference-scenarios
python scripts/calibration/objective.py models/full_0d/reference_outputs/baseline_metrics.json --out models/full_0d/calibration/baseline_objective.json
python scripts/calibration/compare_to_paper.py models/full_0d/reference_outputs/baseline_metrics.json --source-id paper_model --out models/full_0d/calibration/baseline_vs_paper.json
python scripts/calibration/plot_calibration.py models/full_0d/reference_outputs/baseline_metrics.json --out models/full_0d/calibration/baseline_target_errors.svg
```
