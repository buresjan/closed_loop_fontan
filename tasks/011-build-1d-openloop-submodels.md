# 011 - Build 1-D Open-Loop Submodels

Status: planned

Depends on: Task 010

## Goal

Validate aorta, TCPC, and combined aorta-TCPC 1-D submodels before attempting a closed-loop coupled model.

## Implementation

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

Maybe, depending on Task 009.
