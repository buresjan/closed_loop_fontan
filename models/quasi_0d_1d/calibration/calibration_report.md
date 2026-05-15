# Quasi 0-D/1-D Calibration Report

Completed on 2026-05-15 for Task 008.

## Scope

The Task 008 calibration starts from the Task 006/007 executable quasi model and
retunes only small global physiology scales. The quasi R-L-C chain segment
counts and total chain resistance, inertance, and compliance are preserved from
the Task 005 priors.

Intervention scenarios inherit the calibrated baseline and remain validation
cases; they are not retuned.

No PhysioBlocks internals were changed.

## Selected Scale Factors

| Scale | Value |
|---|---:|
| Heart contractility | 0.96 |
| Upper systemic resistance | 1.04 |
| Lower systemic resistance | 1.12 |
| Pulmonary bed resistance | 1.10 |
| Quasi chain R/L/C totals | preserved |

The factors are tracked in `calibration_factors.json` and applied by
`scripts/calibration/quasi.py`.

## Baseline Fit

Primary comparison source: `direct_measurement`.

| Quantity | Model | Target | Error |
|---|---:|---:|---:|
| EDV | 70.44 ml | 74.40 ml | -5.3% |
| ESV | 35.38 ml | 37.60 ml | -5.9% |
| SV | 35.06 ml | 36.80 ml | -4.7% |
| CO | 2.46 L/min | 2.57 L/min | -4.4% |
| Mean AAo pressure | 47.39 mmHg | 50.40 mmHg | -6.0% |
| Mean aortic arch pressure | 47.38 mmHg | 51.73 mmHg | -8.4% |
| Mean DAo pressure | 47.29 mmHg | 53.15 mmHg | -11.0% |
| Mean SVC pressure | 8.92 mmHg | 8.87 mmHg | +0.5% |
| Mean IVC pressure | 8.75 mmHg | 8.54 mmHg | +2.5% |
| Mean RPA pressure | 7.62 mmHg | 8.48 mmHg | -10.2% |
| Mean LPA pressure | 7.62 mmHg | 8.46 mmHg | -9.9% |
| SVC flow | 19.69 ml/s | 20.59 ml/s | -4.4% |
| IVC flow | 21.16 ml/s | 18.84 ml/s | +12.3% |
| RPA flow | 24.14 ml/s | 24.43 ml/s | -1.2% |
| LPA flow | 16.71 ml/s | 16.88 ml/s | -1.0% |
| RPA flow fraction | 0.5909 | 0.5914 | -0.1% |

Weighted RMS relative error improved from `0.0817` before Task 008 to `0.0610`.
The calibrated full 0-D reference is `0.0614` with the same direct-measurement
target set, so the quasi summary fit is comparable to the full 0-D reference.

The paper-model comparison error is `0.0831`; this remains slightly above the
full 0-D paper comparison and is dominated by waveform and aortic-pressure
profile differences that require later calibration or true 1-D coupling.

## Waveform Check

`baseline_waveforms_direct.json` compares the calibrated quasi baseline against
direct-measurement waveforms and includes the calibrated full 0-D baseline as a
reference. Selected normalized RMSE values:

| Waveform | Full 0-D | Calibrated quasi | Direction |
|---|---:|---:|---|
| Descending aorta pressure | 0.466 | 0.422 | improved |
| Ventricle volume | 0.584 | 0.568 | improved |
| IVC flow | 0.265 | 0.254 | improved |
| Ascending aorta pressure | 0.351 | 0.344 | improved |
| Aortic arch pressure | 0.354 | 0.352 | improved |

The DAo pressure amplitude remains below the clinical waveform target, but the
quasi aortic chain improves DAo pressure amplitude and normalized waveform error
over the full 0-D reference without producing visible inertance ringing in the
last-cycle metrics.

## Numerical Checks

| Check | Value | Threshold |
|---|---:|---:|
| Cavity-volume periodicity | 0.00701 | 0.02 |
| Aortic-valve flux periodicity | 0.00670 | 0.02 |
| Atrioventricular-valve flux periodicity | 0.00114 | 0.02 |
| TCPC cycle balance | 2.36e-05 | 1e-2 |
| Atrial cycle balance | 1.54e-04 | 1e-2 |
| Ventricle cycle balance | 9.63e-05 | 1e-2 |

All standardized quasi chain mass-balance values are small in the calibrated
baseline. The largest vessel storage residuals are in the IVC chain and remain
well below the loop-balance thresholds.

## Validation Scenarios

Scenario metrics were regenerated without retuning:

- Pulmonary vasodilation: CO increases by 1.64%, TCPC pressure decreases by
  2.09%, and pulmonary flows increase.
- Fenestration: fenestration flow increases from near-zero baseline to
  0.78 ml/s while global CO changes minimally.
- LPA obstruction: RPA flow fraction increases from 0.591 to 0.743, left lung
  flow falls by 38.6%, and right lung flow rises by 22.9%.

The validation summaries are tracked in
`models/quasi_0d_1d/reference_outputs/scenario_comparison.txt`.

## Residual Gaps

- Aortic, RPA, and LPA mean pressures remain low relative to direct
  measurements. The DAo pressure profile is better than full 0-D but still not
  target-level.
- IVC flow remains higher than the direct target, consistent with the target
  closure issue documented before Task 005.
- Aortic and pulmonary flow waveform amplitudes are still imperfect; this is a
  key reason to continue toward Task 009 and the true 1-D feasibility work.

## Reproduction

```bash
.venv/bin/python scripts/calibration/run_quasi_calibration.py --write-configs
.venv/bin/python scripts/calibration/run_quasi_calibration.py --run-reference-scenarios
.venv/bin/python scripts/calibration/run_quasi_calibration.py --write-objective-reports
.venv/bin/python scripts/calibration/compare_waveforms.py \
  runs/simulations/QuasiBaseline/.../main.csv \
  models/quasi_0d_1d/configs/fontan_quasi_baseline.jsonc \
  --source-id direct_measurement \
  --reference-csv runs/simulations/Baseline/.../main.csv \
  --reference-config models/full_0d/configs/fontan_0d_baseline.jsonc \
  --out models/quasi_0d_1d/calibration/baseline_waveforms_direct.json
```
