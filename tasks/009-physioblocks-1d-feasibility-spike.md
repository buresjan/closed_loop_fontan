# 009 - PhysioBlocks 1-D Feasibility Spike

Status: completed

Depends on: Task 008

## Goal

Determine whether true nonlinear 1-D vessel modeling can be implemented locally in this repository or whether PhysioBlocks internals must be changed.

## Assessment To Validate

Local custom blocks are enough for scalar lumped blocks and quasi chains. The risk begins with configurable true 1-D vessels because PhysioBlocks builds state variables from class-level `internal_variables`; those sizes are declared by decorators on the block class, not by config-time parameters such as `number_of_cells`.

## Implementation

- Prototype a minimal vector internal equation using a fixed-size local block.
- Test whether a local block can expose enough internal variables and fluxes for one 1-D vessel with a fixed cell count.
- Test whether multiple fixed-size classes or generated classes are practical.
- Evaluate a generated-scalar-network option where each cell/face is represented as normal PhysioBlocks blocks and config generation handles size.
- Document solver scaling, Jacobian size, convergence, and saved-output behavior.
- Write a decision memo in `models/coupled_0d_1d/docs/physioblocks_feasibility.md`.

## Decision Criteria

- Continue locally if fixed-size/generated local blocks can support the planned aorta and TCPC submodels with acceptable maintainability and runtime.
- Plan a PhysioBlocks fork/upstream contribution if configurable cell counts, sparse solver performance, positivity safeguards, or boundary-coupling controls are blocked by current internals.

## Acceptance

- Decision memo states the chosen path and rejected alternatives.
- A minimal prototype has tests proving state sizing, residual assembly, and flux coupling.
- Any required PhysioBlocks internal changes are listed as concrete API changes, not vague concerns.

## PhysioBlocks Impact

No immediate PhysioBlocks fork/upstream work is required. Task 010 should start
with local generated scalar/fixed-size 1-D components. A PhysioBlocks internal
change should be reconsidered only if later prototypes show concrete blockers
around config-dependent state sizing, dense Jacobian scaling, area positivity,
or boundary-coupling controls.

## Completion Notes

Completed on 2026-05-17.

- Added a feasibility-only fixed-size 1-D probe block in
  `fontan_blocks/one_d_feasibility.py`.
- Verified local PhysioBlocks extensions can assemble fixed scalar state terms,
  vector residuals, analytic gradients, inlet/outlet flux coupling, and vector
  saved quantities without modifying installed PhysioBlocks.
- Confirmed `number_of_cells` can be a parameter but cannot resize internal
  state because state sizing is class/decorator driven.
- Wrote the decision memo in
  `models/coupled_0d_1d/docs/physioblocks_feasibility.md`.
- Selected the clean next path: local generated scalar/fixed-size 1-D
  components for Task 010, no immediate PhysioBlocks fork.

Validation:

- `python3 -m py_compile fontan_blocks/one_d_feasibility.py scripts/docs/build_model_reference_pdfs.py`
- `python3 -m pytest tests/test_physioblocks_1d_feasibility.py -q`
- `python3 scripts/docs/build_model_reference_pdfs.py --check`
- `python3 -m pytest -q`
