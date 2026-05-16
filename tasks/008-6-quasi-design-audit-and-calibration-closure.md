# 008.6 - Quasi Design Audit and Calibration Closure

Status: completed

Depends on: Task 008.5

## Goal

Decide whether the Task 008.5 quasi model can be promoted into a scientifically
credible calibrated quasi reference, or whether it must remain a stable
development scaffold before Task 009.

## Implementation

- Preserve the Task 008.5 interpretation: the quasi model is stable and has a
  lower aggregate direct score than Task 008, but it is not superior to full
  0-D because hard pump gates and AAo/DAo flow waveform gates fail.
- Audit AAo and DAo waveform extraction across candidate model signals, sign
  conventions, anatomical locations, and phase-shift sensitivity.
- Produce compliance/storage and characteristic impedance reports for the
  current quasi design.
- Run a small ablation/design matrix covering:
  - current topology with frozen full 0-D heart;
  - small heart adjustment only;
  - aortic R/L/C scale perturbations;
  - caval and pulmonary R/L/C perturbations;
  - pulmonary proximal/distal split perturbations;
  - distributed aortic branch takeoffs;
  - four-port TCPC port separation;
  - combined distributed-aorta plus four-port TCPC topology.
- Keep candidate configs and simulation runs under `runs/`; only promote a
  tracked quasi config if the closure gate accepts the candidate.

## Acceptance

- `models/quasi_0d_1d/calibration/design_audit_report.md` documents whether
  the AAo/DAo waveform failures are likely metric artifacts or real
  design/calibration failures.
- `models/quasi_0d_1d/calibration/quasi_ablation_summary.csv` records all
  candidates and separate hard, direct, paper, and waveform scores.
- `models/quasi_0d_1d/calibration/quasi_final_decision.md` gives one explicit
  closure status:
  - `accepted_superior_to_full_0d`, or
  - `stable_quasi_development_scaffold_not_scientifically_superior`.
- If no candidate clears the closure gate, Task 009 proceeds with full 0-D as
  the calibrated reference and quasi as a stable non-superior scaffold.

## PhysioBlocks Impact

No PhysioBlocks internal changes.

This task may strengthen the motivation for true 1-D work, but all tested
quasi candidates remain repository-local PhysioBlocks configs built from
existing local blocks.

## Completion Notes

Completed on 2026-05-15.

- Added the Task 008.6 design audit:
  - `models/quasi_0d_1d/calibration/design_audit_report.md`;
  - `models/quasi_0d_1d/calibration/design_audit.json`;
  - `models/quasi_0d_1d/calibration/dao_aao_flow_signal_audit.csv`;
  - `models/quasi_0d_1d/calibration/compliance_budget.csv`;
  - `models/quasi_0d_1d/calibration/characteristic_impedance_report.csv`.
- Added and ran a 23-candidate ablation/design matrix. The tracked summary is
  `models/quasi_0d_1d/calibration/quasi_ablation_summary.csv`.
- Added the closure decision in
  `models/quasi_0d_1d/calibration/quasi_final_decision.md` and
  `models/quasi_0d_1d/calibration/quasi_final_decision.json`.
- No candidate passed all hard, paper-comparison, waveform, stability, and
  mass-balance gates. The final status is
  `stable_quasi_development_scaffold_not_scientifically_superior`.
- The Task 008.5 quasi configs remain canonical. No schematic was changed
  because no Task 008.6 topology or parameterization was promoted.
- Task 009 remains justified and should use full 0-D as the calibrated
  reference.

Key findings:

- The best hard/direct candidate was `current_heart_099`, but it still failed
  EDV, ESV, RPA pressure, LPA pressure, and AAo/DAo flow waveform gates.
- The best waveform candidate was `aortic_L0_5`, but it still failed hard and
  waveform gates.
- Distributed aortic branch topology candidates worsened the loop strongly,
  including CO near `1.72 L/min` and SVC flow near `2 ml/s`.
- Four-port TCPC separation did not materially improve the closure gates.

Validation:

```bash
.venv/bin/python scripts/calibration/audit_quasi_design.py
.venv/bin/python scripts/calibration/run_quasi_ablation_grid.py
.venv/bin/python scripts/calibration/run_quasi_closure_calibration.py
.venv/bin/python scripts/modeling/build_quasi_configs.py --check
.venv/bin/python -m pytest -q
```

Result: `63 passed in 1.01s`.
