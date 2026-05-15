# 002 - Add Hydraulic Lumped Blocks

Status: planned

Depends on: Task 001

## Goal

Add clean local hydraulic blocks so future models do not need to use `rc_block` as a pure resistor or `valve_rl_block` as a bidirectional conduit.

## Implementation

- Add `fontan_blocks/lumped.py`.
- Register `hydraulic_resistor_block` with physical orientation `node 1 -> node 2`:
  - `Q = (P1 - P2) / R`
  - node 1 flux `-Q`
  - node 2 flux `+Q`
- Register `hydraulic_rl_block`:
  - `L dQ/dt + R Q = P1 - P2`
  - node 1 flux `-Q`
  - node 2 flux `+Q`
  - symmetric and bidirectional, with no valve behavior.
- Export the new blocks from `fontan_blocks/__init__.py`.
- Add `tests/test_lumped_blocks.py` with orientation, derivative, registration, and simple bidirectional checks.

## Acceptance

- Unit tests prove the resistor sign convention and RL symmetry.
- Existing full 0-D tests still pass.
- No current full 0-D config is behaviorally changed unless Task 001's reference policy is followed.

## PhysioBlocks Impact

No PhysioBlocks internal changes. The existing local registration pattern is sufficient.
