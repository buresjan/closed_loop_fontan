# 001 - Freeze Full 0-D Reference

Status: completed

Depends on: none

## Goal

Make `models/full_0d` an explicit reference model before adding quasi or coupled variants. This protects the current accepted topology, scenarios, schematics, and metrics from accidental drift.

## Implementation

- Add a short reference-policy section to `models/full_0d/README.md`.
- Add `models/full_0d/calibration/` with placeholder `parameter_priors.yaml`, `parameter_bounds.yaml`, and `target_weights.yaml`.
- Add a static test that verifies the full 0-D config set remains present and that the README references the schematic and implementation notes.
- Decide that any cleanup of resistor/RL workarounds must either preserve reference metrics or create a deliberately named new reference output.

## Acceptance

- `pytest -q` passes.
- Full 0-D smoke simulation still runs.
- `models/full_0d` README and schematic remain synchronized with the existing topology.
- Reference output policy is documented.

## Completion note

Completed on 2026-05-15.

Implemented:

- documented the full 0-D reference policy in `models/full_0d/README.md`;
- added placeholder calibration files under `models/full_0d/calibration/`;
- added static tests that enforce the full 0-D config set, schematic files, implementation notes, calibration placeholders, and README references;
- updated `AGENTS.md` to require `ROADMAP.md` and task status updates as roadmap-scoped work starts or completes.

Validation:

- `.venv/bin/pytest -q` -> `18 passed`
- `.venv/bin/python scripts/run_one.py models/full_0d/configs/fontan_0d_smoke.jsonc --series Smoke` -> completed

## PhysioBlocks Impact

No PhysioBlocks internal changes.
