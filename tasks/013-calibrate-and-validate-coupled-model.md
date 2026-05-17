# 013 - Calibrate And Validate Coupled 0-D/1-D Model

Status: planned

Depends on: Task 012

## Goal

Calibrate the coupled 0-D/1-D baseline with tightly bounded parameters, then validate interventions against measurements, Nektar outputs, paper outputs, and scenario behavior.

## Implementation

Task 013 is unblocked by the completed Task 012 20 s generated baseline. The
current coupled prototype now runs a periodic closed-loop baseline with no
NaNs, no negative saved 1-D areas, near-zero aortic/TCPC junction mass
residuals, passing TCPC balance, and passing atrium/ventricle balance after the
total-pressure junction/tapered-LPA/retained-LSA update. The accepted Task 012
reference metrics are tracked in
`models/coupled_0d_1d/reference_outputs/baseline_20s_metrics.json`.

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
  - tightly bounded total-pressure junction loss or compatibility correction
    only if Task 012 documents a specific scientific reason;
  - terminal 0-D bed resistance/compliance scales;
  - heart/atrium scales;
  - LPA narrowing scale.
- Do not freely retune 1-D geometry.
- Use short smoke and 2 s screens for candidate rejection where useful, but
  final baseline acceptance must use a long periodic run comparable to the
  completed Task 012 20 s baseline.
- Validate vasodilation, fenestration, and LPA obstruction without retuning.
  Final scenario validation should also run long enough to demonstrate stable
  periodic behavior; use the same 20 s duration unless Task 013 documents a
  shorter scientifically justified periodicity gate.

## Acceptance

- Summary errors comparable to or better than the quasi model.
- Waveform RPPE improves over full 0-D and quasi for selected waveform targets.
- 1-D submodels reproduce Nektar outputs within documented tolerance.
- No negative area and stable boundary coupling.
- Scenario responses are plausible and close to the paper behavior where comparable.

## PhysioBlocks Impact

Maybe, depending on Task 009.
