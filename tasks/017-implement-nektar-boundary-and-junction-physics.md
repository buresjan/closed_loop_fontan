# 017 - Implement Nektar-Complex Boundary And Junction Physics

Status: planned

Depends on: Task 016

## Goal

Implement the boundary, branch, junction, and terminal-coupling physics needed
for the Nektar-complex 1-D network.

## Implementation

- Implement characteristic/Riemann-compatible inlet and outlet treatment.
- Implement aortic branch junctions using the Task 014 equations and sign
  conventions.
- Implement TCPC/SVC/IVC/RPA/LPA junction behavior with documented pressure,
  flow, and loss terms.
- Couple terminal 1-D outlets to retained 0-D systemic and pulmonary beds
  without prescribing both pressure and flow at the same boundary.
- Avoid artificial pressure reservoirs or numerically convenient junction
  states unless they are mathematically derived and documented.
- Add boundary and junction residual diagnostics.

## Acceptance

- Isolated boundary tests pass for physiological pressure and flow ranges.
- Junction tests pass for flow sign convention, mass conservation, pressure or
  total-pressure compatibility, and loss behavior.
- No junction creates mass or hidden storage unless explicitly modeled.
- The implementation notes document the equations and free parameters.

## PhysioBlocks Impact

No planned fork. Boundary and junction behavior should remain in local blocks
or generated local components unless a documented Task 017 blocker requires a
different path.
