# 005 - Derive Quasi Vessel Parameters

Status: planned

Depends on: Tasks 002, 003, and 004

## Goal

Derive first-pass R-L-C chain parameters for the quasi 0-D/1-D model from geometry and calibrated full 0-D totals.

## Implementation

- Add `scripts/modeling/derive_quasi_vessel_parameters.py`.
- Read:
  - `data/processed/aramburu_2024/model_inputs/aorta_geometry.csv`
  - `data/processed/aramburu_2024/model_inputs/fontan_cross_geometry.csv`
  - calibrated full 0-D baseline parameters.
- Use constants:
  - `rho = 1060 kg/m^3`
  - `mu = 0.0035 Pa*s`
  - aortic wave speed prior near `5.35 m/s`
  - Fontan/TCPC wave speed prior near `2.81 m/s`
- Derive `Abar`, total inertance, total compliance, and first-pass resistance for each chain.
- Emit `models/quasi_0d_1d/calibration/parameter_priors.yaml` and derived config fragments.
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
