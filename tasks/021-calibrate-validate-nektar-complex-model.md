# 021 - Calibrate And Validate Nektar-Complex Coupled Model

Status: planned

Depends on: Task 020

## Goal

Calibrate the Nektar-complex coupled baseline with bounded physical parameters
and validate intervention scenarios without retuning.

## Implementation

- Calibrate baseline only.
- Keep fixed unless Task 014 explicitly allows otherwise:
  - measured geometry;
  - segment connectivity;
  - blood density and viscosity;
  - measured heart rate;
  - intervention definitions.
- Optimize only documented bounded parameters:
  - wall stiffness or compliance scales;
  - friction/loss parameters;
  - terminal bed coupling parameters;
  - limited preload/foundation parameters if scientifically justified.
- Validate without retuning:
  - vasodilation;
  - fenestration;
  - LPA obstruction.
- Compare against:
  - clinical targets;
  - Aramburu paper outputs;
  - processed Nektar closed-loop outputs;
  - full 0-D model;
  - quasi 0-D/1-D model;
  - simplified coupled 0-D/1-D model.

## Acceptance

- Hard clinical targets are not worse than the accepted reference model.
- Paper-model comparison is not worse than the accepted reference model.
- The Nektar-complex model improves at least one 1-D waveform/fidelity metric
  over the simplified coupled model.
- Scenario responses remain physiologically plausible without scenario-specific
  retuning.
- Stability, mass balance, area positivity, and waveform gates pass.

## PhysioBlocks Impact

Maybe. Calibration cannot hide solver or coupling failures. If hard gates fail
because of implementation limits, block promotion and document the limitation.
