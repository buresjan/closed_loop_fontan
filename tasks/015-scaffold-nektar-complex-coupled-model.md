# 015 - Scaffold Nektar-Complex Coupled Model Family

Status: planned

Depends on: Task 014

## Goal

Create the separate model family and documentation structure for the
Nektar-complex coupled 0-D/1-D model without replacing the current simplified
coupled model.

## Implementation

- Add `models/coupled_0d_1d_nektar` as a new model family.
- Standardize the model-local artifacts:
  - `README.md`;
  - `docs/coupled_0d_1d_nektar_schematic.svg`;
  - `docs/coupled_0d_1d_nektar_schematic.png`;
  - `docs/implementation_notes.md`;
  - long technical reference source and PDF.
- Add generator/config support for:
  - smoke;
  - baseline;
  - vasodilation;
  - fenestration;
  - LPA obstruction.
- Reuse the accepted coupled-model 0-D heart/foundation and scenario
  conventions.
- Keep all Nektar-complex geometry, solver, and validation artifacts separate
  from `models/coupled_0d_1d`.

## Acceptance

- The new model family exists with standardized documentation placeholders.
- Config names and output paths are separate from the simplified coupled model.
- The schematic follows the visual style and naming pattern of the other model
  families.
- No accepted reference model is changed or replaced.

## PhysioBlocks Impact

No PhysioBlocks fork by default. This task may add scaffolding for generated
local solver components, but not the solver itself.
