# 013 - Calibrate And Validate Coupled 0-D/1-D Model

Status: planned

Depends on: Task 012

## Goal

Calibrate the coupled 0-D/1-D baseline with tightly bounded parameters, then validate interventions against measurements, Nektar outputs, paper outputs, and scenario behavior.

## Implementation

- Use:
  - `comparison/04_aorta_tcpc_closedloop_1d_last_cycle_clinical.csv`
  - `paper_results/model.csv`
  - `measurements_last_cycle_clinical.csv`
  - relevant Nektar domain outputs.
- Keep fixed or tightly bounded:
  - vessel lengths and radii;
  - blood density and viscosity;
  - segment connectivity;
  - measured heart rate.
- Optimize:
  - wave-speed/stiffness scales per vessel family;
  - friction scales per vessel family;
  - junction loss coefficient if used;
  - terminal 0-D bed resistance/compliance scales;
  - heart/atrium scales;
  - LPA narrowing scale.
- Do not freely retune 1-D geometry.
- Validate vasodilation, fenestration, and LPA obstruction without retuning.

## Acceptance

- Summary errors comparable to or better than the quasi model.
- Waveform RPPE improves over full 0-D and quasi for selected waveform targets.
- 1-D submodels reproduce Nektar outputs within documented tolerance.
- No negative area and stable boundary coupling.
- Scenario responses are plausible and close to the paper behavior where comparable.

## PhysioBlocks Impact

Maybe, depending on Task 009.
