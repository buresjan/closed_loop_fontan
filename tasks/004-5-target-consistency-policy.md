# 004.5 - Target Consistency and Target Policy Check

Status: completed

Depends on: Tasks 003 and 004

## Goal

Document target conflicts before quasi 0-D/1-D parameter derivation so Task 005
does not overfit raw IVC flow or direct DAo pressure.

## Implementation

- Add `scripts/calibration/check_target_consistency.py`.
- Generate:
  - `models/full_0d/calibration/target_consistency_report.md`
  - `models/full_0d/calibration/target_consistency.json`
  - `data/processed/aramburu_2024/targets/target_policy.csv`
- Compute flow-closure checks for `direct_measurement`, `paper_model`, and
  `nektar_closed_loop_1d`.
- Compute direct-measurement implied IVC flow from pulmonary closure and CO
  closure.
- Check passive aortic pressure ordering with `AAo >= Arch >= DAo`.
- Define which targets are hard, medium, soft, or diagnostic.
- Update the Task 004 calibration report and Task 005 instructions with the
  target policy.

## Acceptance

- Direct target flow closure mismatch is reported explicitly.
- Direct IVC flow is classified as soft and mass-closure dependent.
- Direct DAo pressure is classified as diagnostic/low-weight for passive full
  0-D calibration.
- Paper/Nektar aortic pressure profile is marked as the preferred quasi/1-D
  aortic-profile guide.
- No model configs or reference simulation outputs are changed.

## PhysioBlocks Impact

No PhysioBlocks internal changes.

## Completion Notes

Completed on 2026-05-15.

- Added `scripts/calibration/check_target_consistency.py`.
- Generated `models/full_0d/calibration/target_consistency_report.md`.
- Generated `models/full_0d/calibration/target_consistency.json`.
- Generated `data/processed/aramburu_2024/targets/target_policy.csv`.
- Updated Task 005 so quasi-vessel derivation uses the target policy.
- Updated the full 0-D calibration report with a target consistency note.

Validation:

- `.venv/bin/python scripts/calibration/check_target_consistency.py`
- `.venv/bin/pytest -q`
