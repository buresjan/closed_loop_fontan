# Repository Instructions

This repository develops closed-loop Fontan circulation models and calibration/reference data derived from Aramburu et al. 2024.

## Model Families

- `models/full_0d`: current full 0-D PhysioBlocks closed-loop model.
- `models/quasi_0d_1d`: future PhysioBlocks-only quasi 0-D/1-D model.
- `models/coupled_0d_1d`: future coupled 0-D/1-D model with 1-D aorta and TCPC components.

## Required Model Documentation

Every model family must have:

- a model-local `README.md` describing model scope, topology, parameters, run commands, and current limitations;
- a model-local SVG schematic under `docs/`, named `docs/{model}_schematic.svg`;
- a PNG export of that schematic under `docs/`, named `docs/{model}_schematic.png`;
- a model-local `docs/implementation_notes.md` explaining parameter naming, units, block conventions, topology assumptions, calibration targets, and current limitations;
- a model-local technical reference source named `docs/{model}_technical_reference.md`;
- a generated technical reference PDF named `docs/{model}_technical_reference.pdf`.

Every change that modifies a model topology, parameterization, interface, or behavior must update that model's README, SVG schematic, PNG schematic export, implementation notes, technical reference source, and generated technical reference PDF in the same change. Do not leave diagrams, equations, parameter inventories, or prose stale.

Schematics must follow the visual style of the current full 0-D schematic: clear labels, visible topology, consistent block/edge styling, and no overlapping text or components. Edit the SVG source first, then regenerate the PNG export from that SVG.

Technical reference PDFs must be long-form, standardized model-definition
documents. They must explain how the model is built, include the governing
mathematical equations for the block/segment types used, list every segment or
block in the accepted topology, and list the free parameters and accepted values
or state explicitly that the model family is not executable yet. Regenerate the
technical reference markdown/PDF with
`python3 scripts/docs/build_model_reference_pdfs.py` after model changes.

## Roadmap and Task Tracking

- Keep `ROADMAP.md` and the matching `tasks/*.md` file updated whenever roadmap-scoped work starts, changes scope, or completes.
- When starting a task, set its task file status to `in_progress` and update the roadmap task table status.
- When completing a task, set its task file status to `completed`, add a short completion note with the validation commands/results, and update the roadmap task table status.
- If implementation reveals that a task should be split, reordered, or blocked, record that in both the task file and `ROADMAP.md` before continuing.
- Do not let roadmap/task status drift from the actual repository state.
- For calibration tasks, keep model acceptance status explicit. A lower aggregate
  objective is not enough to claim a model is superior if hard-target,
  paper-comparison, waveform, stability, or mass-balance gates fail.
- Before advancing past a calibration closure task, write the decision report
  and update downstream task dependencies so later work uses the accepted
  reference model, not an ambiguous candidate.

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
