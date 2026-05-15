# 010 - Prototype Local 1-D Numerics

Status: planned

Depends on: Task 009

## Goal

Implement the smallest validated nonlinear 1-D vessel numerics needed before building patient-specific open-loop networks.

## Implementation

- Add local modules according to the Task 009 decision:
  - `fontan_blocks/one_d.py`
  - `fontan_blocks/one_d_geometry.py`
  - `fontan_blocks/one_d_wall_laws.py`
  - `fontan_blocks/one_d_junctions.py`
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

Maybe. If Task 009 chose a PhysioBlocks internal change path, this task starts from that agreed API. Otherwise it remains local.
