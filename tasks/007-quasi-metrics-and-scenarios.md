# 007 - Add Quasi Metrics And Scenarios

Status: planned

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
