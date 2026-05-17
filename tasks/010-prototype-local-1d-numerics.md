# 010 - Prototype Local 1-D Numerics

Status: completed

Depends on: Task 009

## Goal

Implement the smallest validated nonlinear 1-D vessel numerics needed before building patient-specific open-loop networks.

## Implementation

- Add local modules according to the Task 009 decision:
  - `fontan_blocks/one_d.py`
  - `fontan_blocks/one_d_geometry.py`
  - `fontan_blocks/one_d_wall_laws.py`
  - `fontan_blocks/one_d_junctions.py`
- Start from local generated scalar/fixed-size components. Do not implement a
  monolithic block whose state size depends on config-time `number_of_cells`.
- Implement wall law utilities:
  - `P - P_ext = beta * (sqrt(A) - sqrt(A0))` or an equivalent wave-speed form.
- Implement one straight vessel residual with states for area and flow.
- Add boundary coupling tests for pressure-driven and flow-driven cases.
- Add saved quantities for pressure, area, flow, stored volume, and negative-area diagnostics.

## Acceptance

- Same pressure at both ends gives no drift and near-zero flow.
- Steady pressure drop gives plausible steady flow.
- Pulse propagation speed matches the target wave speed within the chosen tolerance.
- No negative area in accepted tests.
- Volume conservation matches inlet minus outlet flow.

## PhysioBlocks Impact

No immediate PhysioBlocks fork. Task 009 selected a local generated
scalar/fixed-size path; revisit PhysioBlocks internals only if dense Jacobian
scaling, area positivity, or boundary-coupling controls become concrete
blockers.

## Completion Notes

Completed on 2026-05-17.

Implemented a local true 1-D numerical prototype without changing
PhysioBlocks internals:

- `fontan_blocks/one_d_wall_laws.py` for square-root pressure-area law,
  inverse wall law, wave-speed targeting, and characteristic impedance.
- `fontan_blocks/one_d_geometry.py` for uniform straight-vessel geometry,
  staggered face interpolation, and stored volume.
- `fontan_blocks/one_d_junctions.py` for boundary pressure gradients, port flux
  orientation, and volume balance.
- `fontan_blocks/one_d.py` for `Fixed3CellOneDVesselBlock`, a fixed three-cell
  true 1-D finite-volume vessel with area states, face-flow states, nonlinear
  momentum, pressure/flow ports, saved distributed quantities, and analytic
  Jacobian entries.

Documentation was updated in `models/coupled_0d_1d/docs/one_d_numerics.md`,
`README.md`, `docs/implementation_notes.md`, and the generated coupled
technical reference source/PDF. The coupled schematic was not changed because
no coupled closed-loop topology or patient-specific 1-D segment has been
inserted yet.

Validation:

```bash
python3 -m py_compile fontan_blocks/one_d.py fontan_blocks/one_d_geometry.py fontan_blocks/one_d_junctions.py fontan_blocks/one_d_wall_laws.py scripts/docs/build_model_reference_pdfs.py tests/test_one_d_numerics.py
python3 -m pytest tests/test_one_d_numerics.py -q
# 11 passed
python3 -m pytest -q
# 82 passed
python3 scripts/docs/build_model_reference_pdfs.py --model coupled_0d_1d
```
