# 014 - Specify Nektar-Complex Coupled 0-D/1-D Target

Status: planned

Depends on: Task 013

## Goal

Freeze the scientific and numerical target for a new separate Nektar-complex
coupled 0-D/1-D model before implementation begins.

The new model family will build on the accepted coupled 0-D heart, valves,
atrium, Fontan foundation, scenarios, and calibration workflow, but will use a
local repo-owned 1-D vessel implementation with Nektar-level numerical
complexity.

## Implementation

- Use the local Nektar source tree and tracked processed Aramburu/Nektar data
  as reference material.
- Document the target 1-D vessel formulation:
  - vessel/domain list and connectivity;
  - element layout and polynomial/quadrature order;
  - state variables, flux form, wall law, viscosity/friction terms, and units;
  - inlet/outlet characteristic treatment;
  - bifurcation, junction, and 0-D coupling equations;
  - saved pressure, flow, area, and residual outputs.
- Compare the target against the current simplified coupled model:
  - what is reused from the current coupled 0-D foundation;
  - what remains simplified in `models/coupled_0d_1d`;
  - what must be added for `models/coupled_0d_1d_nektar`.
- Freeze validation gates before any tuning:
  - no negative vessel area;
  - no NaN/Inf;
  - per-domain and network mass balance;
  - open-loop waveform agreement against processed Nektar outputs;
  - closed-loop clinical and paper-target non-regression;
  - at least one 1-D waveform/fidelity improvement over the simplified
    coupled model.
- Record whether any PhysioBlocks internals or solver-generation constraints
  are expected to become blockers.

## Acceptance

- A tracked specification document exists for the Nektar-complex model.
- The accepted current coupled model and the new Nektar-complex target are
  clearly distinguished.
- Validation thresholds and comparison priorities are frozen before
  implementation starts.
- The roadmap and this task file state whether Task 015 can begin.

## PhysioBlocks Impact

No implementation in this task. The default path is a local repo-owned solver
integrated with the current 0-D foundation, not an external Nektar bridge.
