# Repository Instructions

This repository develops closed-loop Fontan circulation models and calibration/reference data derived from Aramburu et al. 2024.

## Model Families

- `models/full_0d`: current full 0-D PhysioBlocks closed-loop model.
- `models/quasi_0d_1d`: future PhysioBlocks-only quasi 0-D/1-D model.
- `models/coupled_0d_1d`: future coupled 0-D/1-D model with 1-D aorta and TCPC components.

## Required Model Documentation

Every model family must have:

- a model-local `README.md` describing model scope, topology, parameters, run commands, and current limitations;
- a model-local schematic under `docs/`;
- enough notes to explain parameter naming, units, block conventions, and calibration targets.

Every change that modifies a model topology, parameterization, interface, or behavior must update that model's README and schematic in the same change. Do not leave diagrams or prose stale.

Schematics must follow the visual style of the current full 0-D schematic: clear labels, visible topology, consistent block/edge styling, and no overlapping text or components. Prefer editing the SVG source first, then exporting a PNG when a PNG is present for that model.

## Data Policy

- Raw Aramburu archives and extracted raw binaries live under `data/raw/` and are ignored by Git.
- Standardized, documented, reproducible processed outputs live under `data/processed/` and are tracked.
- Do not commit raw `.zip`, raw `.mat`, or unreviewed large generated files without an explicit data/versioning decision.
- If processed data is regenerated, verify the manifest/checksums and include any script changes needed to reproduce it.

## Code and Tests

- Keep changes scoped to the relevant model, data-prep, or utility area.
- Use existing PhysioBlocks conventions and local helper scripts before adding new abstractions.
- Run `pytest -q` for normal changes.
- Run the relevant smoke simulation when changing model configs, topology, blocks, or runner behavior.
- Explicit mypy usage is not required for this repository.

## Clinical/Scientific Caveat

The model parameters and standardized data are for computational development and calibration workflows. Do not present simulation outputs as clinically validated without separate validation and documentation.
