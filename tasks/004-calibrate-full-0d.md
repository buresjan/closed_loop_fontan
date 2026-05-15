# 004 - Calibrate Full 0-D Baseline

Status: completed

Depends on: Tasks 001 and 003

## Goal

Tune the current full 0-D model to patient-level means, flows, and volumes before using it as the physiological base for quasi and coupled models.

## Implementation

- Add shared calibration scripts:
  - `scripts/calibration/objective.py`
  - `scripts/calibration/run_calibration.py`
  - `scripts/calibration/plot_calibration.py`
  - `scripts/calibration/compare_to_paper.py`
- Use scale factors instead of hundreds of raw parameters.
- Tune baseline only; keep vasodilation, fenestration, and LPA obstruction as validation scenarios.
- Calibrate in this order:
  - heart rate from measured cycle length;
  - heart/valves for EDV, ESV, SV, CO, and ventricle pressure;
  - systemic afterload for AAo/arch/DAo pressures and CO;
  - upper/lower vascular beds for SVC/IVC flows and pressures;
  - TCPC/pulmonary side for RPA/LPA pressures and split;
  - active atrium and pulmonary Windkessels for wedge/atrial pressure proxy.
- Write `models/full_0d/calibration/calibration_report.md`.

## Acceptance

- Baseline SV/CO errors below 5%.
- Main pressure/flow mean errors below 5-10%.
- Periodicity below 1-2%.
- Mass-balance errors below `1e-2`, with `1e-3` as the preferred target.
- Validation scenarios run without retuning and have plausible directional responses.

## PhysioBlocks Impact

No PhysioBlocks internal changes.

## Completion Notes

Completed on 2026-05-15.

- Added Task 004 calibration scripts under `scripts/calibration/`.
- Calibrated the full 0-D baseline using scale factors against
  `data/processed/aramburu_2024/targets`.
- Regenerated calibrated full 0-D configs, reference metrics, calibration
  comparisons, and the target-error plot.
- Kept vasodilation, fenestration, and LPA obstruction as validation scenarios
  with no scenario-specific retuning.
- Updated `models/full_0d/README.md`,
  `models/full_0d/docs/implementation_notes.md`, and the full 0-D schematic to
  reflect the calibrated model state.
- Added a calibration write guard so `run_calibration.py --write-configs` does
  not scale already calibrated configs a second time.

Validation:

- `.venv/bin/python scripts/calibration/run_calibration.py --write-configs`
- `.venv/bin/python scripts/calibration/run_calibration.py --run-reference-scenarios`
- `.venv/bin/python scripts/run_one.py models/full_0d/configs/fontan_0d_smoke.jsonc --series Smoke`
- `.venv/bin/python scripts/metrics.py runs/simulations/Smoke/.../main.csv models/full_0d/configs/fontan_0d_smoke.jsonc --out models/full_0d/reference_outputs/smoke_metrics.json`
- `.venv/bin/pytest -q`
