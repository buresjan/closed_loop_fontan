# 018 - Validate Open-Loop Nektar Equivalence

Status: planned

Depends on: Task 017

## Goal

Validate the Nektar-complex 1-D subsystem against processed Nektar open-loop
outputs before any closed-loop coupling.

## Implementation

- Reproduce tracked open-loop reference cases:
  - aorta-only;
  - TCPC-only;
  - combined aorta-TCPC network.
- Compare pressure, flow, and area waveforms at all available processed Nektar
  domains and sample points.
- Report:
  - waveform mean, amplitude, phase, and normalized error;
  - branch flow fractions;
  - per-domain and network mass balance;
  - area minima and positivity;
  - boundary and junction residuals.
- Do not proceed to closed-loop integration if open-loop equivalence fails
  without an explicit scientific exception.

## Acceptance

- All open-loop cases run reproducibly.
- No negative area, NaN, or Inf occurs.
- Domain and network mass-balance gates pass.
- Waveform agreement meets the frozen Task 014 gates.
- Reference outputs are tracked and reproducible from tracked scripts and
  processed data.

## PhysioBlocks Impact

Maybe. If open-loop equivalence is blocked by solver integration limits rather
than model physics, document the exact PhysioBlocks or local-solver limitation
before continuing.
