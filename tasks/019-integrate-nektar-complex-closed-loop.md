# 019 - Integrate Nektar-Complex Closed-Loop Model

Status: planned

Depends on: Task 018

## Goal

Couple the validated Nektar-complex 1-D network to the accepted 0-D heart and
Fontan foundation.

## Implementation

- Reuse the accepted coupled-model foundation:
  - active atrium and ventricle behavior;
  - valves;
  - systemic and pulmonary retained beds;
  - fenestration handling;
  - intervention scenario conventions;
  - runner and metrics conventions.
- Replace only the simplified 1-D vessel subsystem with the Nektar-complex
  network.
- Add closed-loop configs:
  - `fontan_coupled_nektar_smoke.jsonc`;
  - `fontan_coupled_nektar_baseline.jsonc`;
  - `fontan_coupled_nektar_vasodilation.jsonc`;
  - `fontan_coupled_nektar_fenestration.jsonc`;
  - `fontan_coupled_nektar_lpa_obstruction.jsonc`.
- Add metrics for Nektar-complex vessel state, residuals, mass balance, and
  waveform comparison.
- Update README, schematic SVG/PNG, implementation notes, and technical
  reference in the same change.

## Acceptance

- The closed-loop smoke config launches.
- The model uses the current accepted 0-D foundation and the new
  Nektar-complex 1-D subsystem.
- No scenario-specific retuning is introduced.
- Documentation and schematic match the implemented topology.

## PhysioBlocks Impact

Maybe. Closed-loop coupling may expose scaling or solver limitations; record
any such limitation before changing model physics to compensate.
