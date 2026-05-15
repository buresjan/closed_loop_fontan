# 004 - Calibrate Full 0-D Baseline

Status: planned

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
