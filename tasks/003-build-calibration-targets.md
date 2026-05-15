# 003 - Build Calibration Targets

Status: planned

Depends on: Task 001

## Goal

Create shared calibration target extraction so all model families use the same Aramburu-derived summary and waveform targets.

## Implementation

- Add `scripts/calibration/extract_targets.py`.
- Read:
  - `data/processed/aramburu_2024/measurements_clinical.csv`
  - `data/processed/aramburu_2024/measurements.csv`
  - `data/processed/aramburu_2024/comparison/measurements_last_cycle_clinical.csv`
  - `data/processed/aramburu_2024/paper_results/model.csv`
  - `data/processed/aramburu_2024/comparison/04_aorta_tcpc_closedloop_1d_last_cycle_clinical.csv`
- Write a tracked target package under `data/processed/aramburu_2024/targets/`.
- Include summary targets for heart rate, EDV, ESV, SV, CO, mean pressures, beat-integrated flows, and RPA/LPA split.
- Include waveform targets with canonical names, units, phase alignment assumptions, and normalization scales.

## Acceptance

- Target extraction is reproducible from processed data.
- Tests cover unit conversions, cycle length, beat integrals, and expected column names.
- Target metadata states whether each target is a direct measurement, paper output, or Nektar comparison output.

## PhysioBlocks Impact

No PhysioBlocks internal changes.
