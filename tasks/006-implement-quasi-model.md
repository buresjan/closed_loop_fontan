# 006 - Implement Quasi 0-D/1-D Model

Status: planned

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
