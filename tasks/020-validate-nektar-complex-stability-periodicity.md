# 020 - Validate Nektar-Complex Stability And Periodicity

Status: planned

Depends on: Task 019

## Goal

Prove that the Nektar-complex closed-loop model is numerically stable and
physiologically plausible before calibration.

## Implementation

- Run progressively longer closed-loop simulations:
  - smoke;
  - short baseline;
  - full baseline;
  - extended periodicity run as needed.
- Inspect pressure, flow, area, volume, residual, and junction traces.
- Report:
  - global mass balance;
  - per-network mass balance;
  - TCPC and aortic junction residuals;
  - cardiac-cycle periodicity;
  - cavity volume closure;
  - vessel area minima/maxima;
  - pressure and flow bounds.
- Do not tune clinical targets in this task except for bounded numerical
  stabilization parameters explicitly allowed by Task 014.

## Acceptance

- No numerical blow-up, NaN, Inf, or negative area.
- Stable cardiac-cycle periodicity is demonstrated.
- Global, aortic, TCPC, atrium, and ventricle mass-balance gates pass.
- Fontan, pulmonary, aortic, venous, and ventricular pressures are
  physiologically plausible.
- No junction ringing or artificial damping dominates the result.

## PhysioBlocks Impact

Maybe. If stability requires solver infrastructure changes rather than
physical parameter changes, update the roadmap and task file before
calibration.
