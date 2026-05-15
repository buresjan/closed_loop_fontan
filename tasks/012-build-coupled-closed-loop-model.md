# 012 - Build Coupled Closed-Loop 0-D/1-D Model

Status: planned

Depends on: Task 011

## Goal

Build the true coupled closed-loop model with 1-D aorta and TCPC pathways attached to the 0-D heart, atrium, valves, beds, pulmonary Windkessels, and fenestration.

## Implementation

- Add configs:
  - `fontan_coupled_0d_1d_smoke.jsonc`
  - `fontan_coupled_0d_1d_baseline.jsonc`
  - `fontan_coupled_0d_1d_vasodilation.jsonc`
  - `fontan_coupled_0d_1d_fenestration.jsonc`
  - `fontan_coupled_0d_1d_lpa_obstruction.jsonc`
- Couple 1-D vessel ports to PhysioBlocks pressure nodes without prescribing both pressure and flow.
- Implement the TCPC junction initially with mass conservation and pressure or total-pressure compatibility, with an optional loss coefficient.
- Update `models/coupled_0d_1d/README.md`, schematic, and `docs/implementation_notes.md` in the same change.
- Extend metrics for 1-D vessel stored volume, inlet/outlet flow, negative area, and boundary sign diagnostics.

## Acceptance

- Coupled smoke case runs.
- Baseline can reach a periodic state after sufficient cycles.
- No NaN/Inf and no negative vessel area.
- TCPC, atrium, and ventricle mass-balance checks pass.
- README and schematic match the implemented topology.

## PhysioBlocks Impact

Maybe, depending on Task 009.
