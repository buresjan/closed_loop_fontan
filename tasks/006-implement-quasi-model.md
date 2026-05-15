# 006 - Implement Quasi 0-D/1-D Model

Status: completed

Depends on: Tasks 002 and 005

## Goal

Build `models/quasi_0d_1d` as a PhysioBlocks-only model using distributed R-L-C chains for selected aortic and Fontan vessels.

## Implementation

- Add model configs:
  - `fontan_quasi_smoke.jsonc`
  - `fontan_quasi_baseline.jsonc`
  - `fontan_quasi_vasodilation.jsonc`
  - `fontan_quasi_fenestration.jsonc`
  - `fontan_quasi_lpa_obstruction.jsonc`
- Keep heart, active atrium, valves, systemic beds, pulmonary RCR beds, and fenestration from the calibrated full 0-D model.
- Replace full 0-D vessel/conduit shortcuts with quasi chains:
  - AAo/arch;
  - DAo;
  - SVC;
  - IVC;
  - RPA;
  - LPA.
- Keep BCA/LCCA/LSA as resistive branches for the first quasi release.
- Add `models/quasi_0d_1d/docs/implementation_notes.md`.
- Update `models/quasi_0d_1d/README.md` and schematic in the same change.

## Acceptance

- Quasi smoke case runs.
- No `valve_rl_block` is used as a conduit in quasi configs.
- Chain topology and total R/L/C are covered by tests.
- README and schematic match the implemented topology.

## PhysioBlocks Impact

No PhysioBlocks internal changes.

## Completion Notes

Completed on 2026-05-15.

- Added `scripts/modeling/build_quasi_configs.py` to assemble executable quasi
  configs from the calibrated full 0-D scenarios and the Task 005 R-L-C chain
  fragment.
- Generated:
  - `models/quasi_0d_1d/configs/fontan_quasi_smoke.jsonc`
  - `models/quasi_0d_1d/configs/fontan_quasi_baseline.jsonc`
  - `models/quasi_0d_1d/configs/fontan_quasi_vasodilation.jsonc`
  - `models/quasi_0d_1d/configs/fontan_quasi_fenestration.jsonc`
  - `models/quasi_0d_1d/configs/fontan_quasi_lpa_obstruction.jsonc`
- Removed the old full 0-D aortic shortcut blocks and Fontan conduit shortcut
  nodes/blocks from the quasi configs.
- Kept `valve_rl_block` only for the atrioventricular and aortic valves.
- Preserved the Task 005 chain totals in the baseline quasi config:
  AAo/arch x4, DAo x6, SVC x3, IVC x5, RPA x3, and LPA x4.
- Carried scenario changes into the quasi family; LPA obstruction doubles the
  total LPA quasi-chain resistance through
  `quasi_lpa.narrowing_resistance_scale = 2.0`.
- Updated `models/quasi_0d_1d/README.md`,
  `models/quasi_0d_1d/docs/implementation_notes.md`,
  `models/quasi_0d_1d/docs/schematic.svg`, and
  `models/quasi_0d_1d/docs/schematic.png`.
- Updated the root `README.md` to mark the quasi model family active.
- Added `tests/test_quasi_configs.py`.

Validation:

- `.venv/bin/python scripts/modeling/build_quasi_configs.py --check`
- `.venv/bin/python scripts/run_one.py models/quasi_0d_1d/configs/fontan_quasi_smoke.jsonc --series QuasiSmokeTask006`
- `.venv/bin/pytest tests/test_quasi_configs.py -q`
- `.venv/bin/pytest -q`
