# 007 - Add Quasi Metrics And Scenarios

Status: completed

Depends on: Task 006

## Goal

Make metrics and scenario comparison work for both the full 0-D and quasi model families.

## Implementation

- Update `scripts/metrics.py` or add a model-family-aware replacement.
- Support:
  - full 0-D conduit flow names;
  - quasi vessel inlet/outlet flows;
  - quasi internal segment flows.
- Add standardized outputs:
  - `mean_<vessel>_inlet_flow_ml_s`
  - `mean_<vessel>_outlet_flow_ml_s`
  - `integral_<vessel>_inlet_flow_ml`
  - `integral_<vessel>_outlet_flow_ml`
  - `<vessel>_cycle_storage_ml`
  - `<vessel>_mass_balance_rel`
- Keep shared clinical metrics: EDV, ESV, SV, CO, pressures, RPA/LPA split, fenestration flow, cycle balance, and periodicity.
- Add quasi scenario comparison and reference-output workflow.

## Acceptance

- `tests/test_quasi_metrics.py` covers inlet/outlet/storage balance.
- Metrics for full 0-D remain unchanged.
- Quasi baseline and intervention scenarios produce comparison-ready JSON outputs.

## PhysioBlocks Impact

No PhysioBlocks internal changes.

## Completion Notes

Completed on 2026-05-15.

- Updated `scripts/metrics.py` to support both full 0-D conduit flow names and
  quasi R-L-C chain inlet/outlet/internal segment flows.
- Added standardized vessel metrics for `aao_arch`, `dao`, `svc`, `ivc`,
  `rpa`, and `lpa`:
  - `mean_<vessel>_inlet_flow_ml_s`
  - `mean_<vessel>_outlet_flow_ml_s`
  - `integral_<vessel>_inlet_flow_ml`
  - `integral_<vessel>_outlet_flow_ml`
  - `<vessel>_cycle_storage_ml`
  - `<vessel>_mass_balance_rel`
- Kept the legacy full 0-D metric keys and existing full 0-D reference outputs
  unchanged.
- Updated `scripts/compare_scenarios.py` to include standardized chain-flow,
  storage, mass-balance, and loop-balance metrics.
- Generated quasi reference outputs:
  - `models/quasi_0d_1d/reference_outputs/baseline_metrics.json`
  - `models/quasi_0d_1d/reference_outputs/vasodilation_metrics.json`
  - `models/quasi_0d_1d/reference_outputs/fenestration_metrics.json`
  - `models/quasi_0d_1d/reference_outputs/lpa_obstruction_metrics.json`
  - `models/quasi_0d_1d/reference_outputs/scenario_comparison.txt`
- Updated the quasi README and implementation notes with the metrics workflow.
- Added `tests/test_quasi_metrics.py`.

Validation:

- `.venv/bin/python scripts/run_one.py models/quasi_0d_1d/configs/fontan_quasi_baseline.jsonc --series QuasiBaselineTask007`
- `.venv/bin/python scripts/run_one.py models/quasi_0d_1d/configs/fontan_quasi_vasodilation.jsonc --series QuasiVasodilationTask007`
- `.venv/bin/python scripts/run_one.py models/quasi_0d_1d/configs/fontan_quasi_fenestration.jsonc --series QuasiFenestrationTask007`
- `.venv/bin/python scripts/run_one.py models/quasi_0d_1d/configs/fontan_quasi_lpa_obstruction.jsonc --series QuasiLPAObstructionTask007`
- `.venv/bin/python scripts/compare_scenarios.py models/quasi_0d_1d/reference_outputs/baseline_metrics.json models/quasi_0d_1d/reference_outputs/vasodilation_metrics.json models/quasi_0d_1d/reference_outputs/fenestration_metrics.json models/quasi_0d_1d/reference_outputs/lpa_obstruction_metrics.json`
- `.venv/bin/pytest -q`
