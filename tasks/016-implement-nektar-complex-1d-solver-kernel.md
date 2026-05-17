# 016 - Implement Nektar-Complex 1-D Solver Kernel

Status: planned

Depends on: Task 015

## Goal

Implement the local high-order 1-D vessel kernel needed by the separate
Nektar-complex coupled model.

## Implementation

- Implement a repo-owned local solver path rather than an external Nektar
  co-simulation bridge.
- Represent each 1-D vessel with:
  - domains and elements;
  - high-order interpolation/quadrature data;
  - pressure, flow, area, and geometry state;
  - wall-law and friction/viscosity parameters;
  - saved internal sample outputs.
- Preserve the Task 014 formulation for fluxes, wall laws, units, and state
  variables.
- Generate deterministic fixed-size components when needed to stay compatible
  with PhysioBlocks-style model construction.
- Add diagnostics for:
  - element residuals;
  - area positivity;
  - stored volume;
  - inlet/outlet flow balance;
  - pressure-area consistency.

## Acceptance

- Unit tests cover geometry parsing, unit conversion, wall-law behavior, flux
  sign convention, state dimensions, and single-vessel mass conservation.
- The solver can run isolated single-vessel checks without negative area or
  non-finite state values.
- The implementation remains separate from the existing simplified coupled
  vessel blocks.

## PhysioBlocks Impact

Use local generated/fixed-size components first. Revisit PhysioBlocks internals
only if Task 016 records a concrete blocker such as state-size construction,
sparse Jacobian scaling, or boundary-condition control.
