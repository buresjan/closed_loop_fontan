# 011 - Build 1-D Open-Loop Submodels

Status: completed

Depends on: Task 010

## Goal

Validate aorta, TCPC, and combined aorta-TCPC 1-D submodels before attempting a closed-loop coupled model.

## Implementation

- Start from the Task 010 local true 1-D kernel:
  - `fontan_blocks/one_d.py`
  - `fontan_blocks/one_d_geometry.py`
  - `fontan_blocks/one_d_wall_laws.py`
  - `fontan_blocks/one_d_junctions.py`
- Generate scalar/fixed-size vessel components or configs from geometry rather
  than adding a monolithic config-sized block.
- Add configs:
  - `models/coupled_0d_1d/configs/submodel_aorta_1d_openloop.jsonc`
  - `models/coupled_0d_1d/configs/submodel_tcpc_1d_openloop.jsonc`
  - `models/coupled_0d_1d/configs/submodel_aorta_tcpc_1d_openloop.jsonc`
- Add `scripts/modeling/derive_1d_geometry.py`.
- Add `scripts/calibration/validate_1d_submodels.py`.
- Use `aorta_geometry.csv`, `aorta_waves_clinical.csv`, `fontan_cross_geometry.csv`, `fontan_cross_inflows_clinical.csv`, and Nektar converted outputs.
- Do not force a normal LSA branch into the patient-specific coupled aorta unless creating a separate idealized variant.
- Validate submodels in this order:
  - aorta with measured ascending aorta inflow;
  - TCPC with measured SVC/IVC inflows;
  - combined aorta-TCPC open-loop with coupling beds.

## Acceptance

- Open-loop submodels run reproducibly.
- Aorta submodel matches AAo, arch, DAo pressure and DAo flow targets within documented tolerance.
- TCPC submodel matches SVC, IVC, RPA, LPA pressure/flow and split targets within documented tolerance.
- Combined submodel preserves mass balance and has stable boundary signs.

## PhysioBlocks Impact

No immediate fork. Tasks 009 and 010 showed that local fixed-size true 1-D
components can assemble residuals, gradients, flux coupling, and saved
distributed quantities. Revisit PhysioBlocks internals only if Task 011 exposes
specific blockers in mesh scaling, sparse Jacobian performance, area
positivity, or boundary-condition control.

## Completion Notes

Completed on 2026-05-17.

Implemented the open-loop reference layer needed before closed-loop coupling:

- added generated strict-JSON reference specs for aorta, TCPC, and combined
  aorta-TCPC open-loop 1-D submodels under `models/coupled_0d_1d/configs/`;
- added `scripts/modeling/derive_1d_geometry.py` to derive patient-specific
  segment specs from tracked Aramburu geometry and Nektar domain manifests;
- added `scripts/calibration/validate_1d_submodels.py` to validate geometry,
  Nektar domain samples, clinical/paper waveform agreement, flow fraction,
  mass balance, and boundary signs;
- added `models/coupled_0d_1d/calibration/one_d_openloop_geometry.json`;
- added `models/coupled_0d_1d/reference_outputs/openloop_1d_validation.json`;
- added `docs/openloop_1d_submodels.md` and updated README, implementation
  notes, schematic SVG/PNG, and technical reference source/PDF.

All three open-loop specs pass the current reference screen. DAo flow keeps a
broad waveform RMSE tolerance with a tighter mean-flow tolerance because the
accepted aortic signal policy treats downstream DAo/bed-entry flow as sensitive
to terminal-load dynamics.

This task does not promote a closed-loop coupled model and does not yet run a
generated multi-segment local PhysioBlocks network. Task 012 must use these
reference specs and preserve the no-fake-boundary policy: do not prescribe both
pressure and flow at a 0-D/1-D port to manufacture agreement.

Validation:

```bash
python3 scripts/modeling/derive_1d_geometry.py
python3 scripts/modeling/derive_1d_geometry.py --check
python3 scripts/calibration/validate_1d_submodels.py
# all three submodels passed
python3 scripts/calibration/validate_1d_submodels.py --check
python3 -m pytest tests/test_one_d_openloop_submodels.py -q
# 5 passed
python3 scripts/docs/build_model_reference_pdfs.py --model coupled_0d_1d
```
