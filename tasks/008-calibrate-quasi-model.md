# 008 - Calibrate Quasi 0-D/1-D Model

Status: completed

Depends on: Tasks 004, 006, and 007

## Goal

Tune the quasi model from the calibrated full 0-D physiology while improving impedance, inertance, distributed compliance, and waveform timing.

## Implementation

- Start from calibrated full 0-D parameters.
- Preserve total vessel resistance, total vessel compliance, and geometry-derived inertance.
- Calibrate quasi aortic chain scales:
  - AAo/arch R, C, and L or wave-speed scale;
  - DAo R, C, and L or wave-speed scale.
- Calibrate quasi TCPC/caval/pulmonary limb scales:
  - SVC, IVC, RPA, and LPA R/L/C scales;
  - LPA narrowed-segment scale;
  - TCPC junction compliance/loss scale.
- Allow only small global retuning of heart contractility, systemic resistance, pulmonary resistance, and active atrium pressure level.
- Validate intervention scenarios without retuning.

## Acceptance

- Summary accuracy is comparable to full 0-D or only modestly worse.
- Waveform amplitude/timing improves over full 0-D for selected targets.
- No artificial ringing from excessive inertance.
- Periodicity and mass-balance thresholds remain acceptable.

## PhysioBlocks Impact

No PhysioBlocks internal changes.

## Completion Notes

Completed on 2026-05-15.

Task 008 now records the accepted canonical quasi 0-D/1-D model.

- Added quasi calibration helpers:
  - `scripts/calibration/quasi.py`
  - `scripts/calibration/run_quasi_calibration.py`
  - `scripts/calibration/compare_waveforms.py`
- Updated `scripts/modeling/build_quasi_configs.py` so the default tracked
  configs include the accepted calibration factors; `--uncalibrated` remains
  available for raw assembly checks.
- Selected accepted physiology/design scales:
  - heart contractility: `1.05`
  - lower systemic resistance: `1.12`
  - pulmonary bed resistance: `1.15`
  - pulmonary proximal resistance fraction: `0.65`
  - endpoint aortic compliance scale: `0.02`
  - lower systemic proximal resistance fraction: `0.95`
- Preserved all quasi chain segment counts and total chain inertance and
  compliance from the accepted fragment.
- Regenerated calibrated quasi configs, baseline/intervention reference
  outputs, baseline objective reports, waveform comparison, and scenario
  comparison.
- Added `models/quasi_0d_1d/calibration/calibration_report.md`,
  `calibration_factors.json`, `baseline_objective.json`,
  `baseline_vs_paper.json`, and `baseline_waveforms_direct.json`.
- Updated the quasi README, implementation notes, SVG schematic, PNG schematic
  export, and standardized technical reference source/PDF.
- Added `tests/test_quasi_calibration.py`.

Accepted comparison scores:

- full 0-D hard score: `0.0433`
- quasi hard score: `0.0244`
- full 0-D direct score: `0.0614`
- quasi direct score: `0.0470`
- full 0-D paper score: `0.0793`
- quasi paper score: `0.0714`

Validation:

- `.venv/bin/python scripts/modeling/build_quasi_configs.py --check`
- `.venv/bin/python scripts/run_one.py models/quasi_0d_1d/configs/fontan_quasi_smoke.jsonc --series QuasiSmokeTask008`
- `.venv/bin/python scripts/run_one.py models/quasi_0d_1d/configs/fontan_quasi_baseline.jsonc --series QuasiBaseline`
- `.venv/bin/python scripts/run_one.py models/quasi_0d_1d/configs/fontan_quasi_vasodilation.jsonc --series QuasiVasodilation`
- `.venv/bin/python scripts/run_one.py models/quasi_0d_1d/configs/fontan_quasi_fenestration.jsonc --series QuasiFenestration`
- `.venv/bin/python scripts/run_one.py models/quasi_0d_1d/configs/fontan_quasi_lpa_obstruction.jsonc --series QuasiLPAObstruction`
- `.venv/bin/python scripts/calibration/objective.py models/quasi_0d_1d/reference_outputs/baseline_metrics.json --out models/quasi_0d_1d/calibration/baseline_objective.json`
- `.venv/bin/python scripts/calibration/compare_to_paper.py models/quasi_0d_1d/reference_outputs/baseline_metrics.json --source-id paper_model --out models/quasi_0d_1d/calibration/baseline_vs_paper.json`
- `.venv/bin/python scripts/calibration/compare_waveforms.py ... --out models/quasi_0d_1d/calibration/baseline_waveforms_direct.json`
- `.venv/bin/pytest -q`
