# 003 - Build Calibration Targets

Status: completed

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

## Completion Note

Completed on 2026-05-15.

- Added `scripts/calibration/extract_targets.py` to build a reproducible target
  package from the processed Aramburu data.
- Added tracked target outputs under `data/processed/aramburu_2024/targets/`:
  `summary_targets.csv`, `waveform_targets.csv`, `waveform_metadata.csv`,
  `metadata.yaml`, and `README.md`.
- Included summary targets for cycle length, heart rate, EDV, ESV, stroke
  volume, cardiac output, mean pressures, beat-integrated flows, and RPA/LPA
  flow split.
- Included waveform targets with canonical names, source types, units,
  phase-alignment assumptions, and normalization scales.
- Added tests for unit conversions, cycle length, periodic beat integrals,
  expected target schemas, and reproducibility from processed data.

Validation:

- `.venv/bin/python scripts/calibration/extract_targets.py` -> completed
- `.venv/bin/pytest -q` -> `29 passed`
