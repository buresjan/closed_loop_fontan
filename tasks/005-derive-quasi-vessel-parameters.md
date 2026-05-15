# 005 - Derive Quasi Vessel Parameters

Status: completed

Depends on: Tasks 002, 003, 004, and 004.5

## Goal

Derive first-pass R-L-C chain parameters for the quasi 0-D/1-D model from geometry and calibrated full 0-D totals.

## Implementation

- Add `scripts/modeling/derive_quasi_vessel_parameters.py`.
- Read:
  - `data/processed/aramburu_2024/model_inputs/aorta_geometry.csv`
  - `data/processed/aramburu_2024/model_inputs/fontan_cross_geometry.csv`
  - `data/processed/aramburu_2024/targets/target_policy.csv`
  - calibrated full 0-D baseline parameters.
- Use constants:
  - `rho = 1060 kg/m^3`
  - `mu = 0.0035 Pa*s`
  - aortic wave speed prior near `5.35 m/s`
  - Fontan/TCPC wave speed prior near `2.81 m/s`
- Derive `Abar`, total inertance, total compliance, and first-pass resistance for each chain.
- Emit `models/quasi_0d_1d/calibration/parameter_priors.yaml` and derived config fragments.
- Use calibrated full 0-D parameters as priors, not immutable constraints.
- Derive aortic R/L/C from geometry and wave-speed priors instead of preserving
  the current full 0-D AAo-to-DAo pressure drop.
- Place most systemic pressure loss in the systemic beds, not inside the
  aortic trunk.
- Use the paper/Nektar aortic pressure profile as the preferred quasi/1-D
  aortic-profile guide.
- Treat direct DAo mean pressure as diagnostic/low-weight unless source
  labeling or extraction is verified.
- Treat IVC flow as mass-closure dependent. Compare it against raw direct,
  implied-from-CO, and implied-from-pulmonary-closure targets; do not force raw
  direct IVC flow if doing so breaks CO, SVC, RPA, LPA, or RPA/LPA split.
- Use initial segment counts:
  - AAo/arch: 3-5;
  - DAo: 5-8;
  - SVC: 2-3;
  - IVC: 4-6;
  - RPA: 2-3;
  - LPA: 3-5 including a narrowed segment.

## Acceptance

- Tests verify total R/L/C preservation across chain discretization.
- Derived parameters are positive and unit-documented.
- LPA narrowing has an explicit parameter and metadata entry.

## PhysioBlocks Impact

No PhysioBlocks internal changes.

## Completion Notes

Completed on 2026-05-15.

- Added `scripts/modeling/derive_quasi_vessel_parameters.py`.
- Generated `models/quasi_0d_1d/calibration/parameter_priors.yaml`.
- Generated `models/quasi_0d_1d/config_fragments/quasi_vessel_chains.json`.
- Updated `models/quasi_0d_1d/README.md` and
  `models/quasi_0d_1d/docs/schematic.svg`.
- Added `tests/test_quasi_parameter_derivation.py`.

Selected first-pass chain counts:

- AAo/arch: 4 R-L-C cells.
- DAo: 6 R-L-C cells.
- SVC: 3 R-L-C cells.
- IVC: 5 R-L-C cells.
- RPA: 3 R-L-C cells.
- LPA: 4 R-L-C cells with explicit `quasi_lpa.narrowing_radius_m`.

Policy decisions:

- Aortic chain resistance is geometry/friction based and does not preserve the
  excessive full 0-D AAo-to-DAo pressure drop.
- Fontan-limb chain resistance starts from the calibrated full 0-D pathway
  resistance because the full 0-D Fontan pressures and pulmonary split are
  accepted baseline physiology.
- Direct DAo pressure remains diagnostic/low-weight.
- IVC flow remains mass-closure dependent.

Validation:

- `.venv/bin/python scripts/modeling/derive_quasi_vessel_parameters.py`
- `.venv/bin/pytest tests/test_quasi_parameter_derivation.py -q`
- `.venv/bin/pytest -q`
