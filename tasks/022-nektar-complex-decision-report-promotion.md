# 022 - Nektar-Complex Decision Report And Promotion

Status: planned

Depends on: Task 021

## Goal

Decide whether the Nektar-complex coupled model is accepted, experimental, or
blocked, and update repository documentation accordingly.

## Implementation

- Write a decision report summarizing:
  - numerical formulation;
  - open-loop Nektar equivalence;
  - closed-loop stability and periodicity;
  - calibration results;
  - scenario validation;
  - comparison against full 0-D, quasi 0-D/1-D, simplified coupled 0-D/1-D,
    paper outputs, and processed Nektar outputs.
- If accepted, update:
  - `ROADMAP.md`;
  - task files;
  - model README;
  - implementation notes;
  - schematic SVG/PNG;
  - technical reference source/PDF;
  - calibration reports;
  - reference outputs.
- If not accepted, leave the model as experimental with explicit blockers and
  do not replace any accepted reference model.

## Acceptance

- The acceptance status is explicit.
- Promotion is based on frozen gates, not aggregate score alone.
- Any failure mode is documented with concrete evidence and next steps.
- The current accepted reference model remains unambiguous.

## PhysioBlocks Impact

Document any PhysioBlocks or local-solver limitations found during Tasks
014-021. Do not claim model acceptance if infrastructure limitations invalidate
the scientific gates.
