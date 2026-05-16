# 008.5 - Corrective Quasi Calibration and Non-Regression Gate

Status: completed

Depends on: Tasks 004, 006, 007, and 008

## Goal

Correct the Task 008 quasi calibration so that aggregate direct-measurement
improvement cannot hide clinically important regressions.

## Implementation

- Treat Task 008 as a stable first pass, but not as a scientifically accepted
  quasi model.
- Add explicit non-regression gates against the calibrated full 0-D baseline:
  - EDV, ESV, SV, and CO no worse than full 0-D plus 1 percentage point;
  - RPA pressure, LPA pressure, and SVC flow no worse than full 0-D plus
    1 percentage point;
  - RPA/LPA flow fraction no worse than full 0-D plus 0.005 absolute fraction;
  - stability, periodicity, and loop-balance checks must pass.
- Keep direct DAo pressure and raw direct IVC flow out of the hard gate and
  report them as soft/problematic diagnostics.
- Add separate scores for hard clinical targets, soft/problematic targets,
  paper-model comparison, and waveform no-strong-regression.
- Verify DAo flow waveform extraction by recording the selected model and
  reference signal columns in the waveform report.

## Acceptance

- The corrective calibration must report whether the quasi model is accepted as
  superior or remains a stable prototype.
- If all hard, paper, and waveform gates cannot be met without broader topology
  work, document the failed gates and do not proceed as if quasi superiority is
  established.
- Intervention scenarios remain validation cases and are regenerated without
  retuning.

## PhysioBlocks Impact

No PhysioBlocks internal changes.

The corrective work reinforces that near-term quasi calibration can stay inside
this repository. True 1-D needs remain deferred to Task 009.

## Completion Notes

Completed on 2026-05-15.

- Added `scripts/calibration/quasi_non_regression.py`.
- Extended `scripts/calibration/compare_waveforms.py` so waveform diagnostics
  record the selected model/reference signal columns.
- Updated `scripts/calibration/quasi.py` to expose:
  - separate right/left pulmonary total resistance scales;
  - right/left pulmonary proximal resistance fractions;
  - chain-specific R/L/C scale knobs for AAo/arch, DAo, SVC, IVC, RPA, and LPA.
- Selected corrective factors:
  - heart contractility scale: `0.96`;
  - upper systemic resistance scale: `1.00`;
  - lower systemic resistance scale: `1.12`;
  - right/left pulmonary total resistance scale: `1.15`;
  - right/left pulmonary proximal fraction: `0.50`;
  - all quasi chain R/L/C scales: `1.00`.
- The candidate screen tested heart-frozen variants first. None recovered the
  hard pump gates, so the previous heart scale remains a documented residual
  limitation rather than a claim of clean quasi superiority.
- Regenerated quasi configs, baseline/intervention reference outputs,
  direct/paper objective reports, waveform comparison, scenario comparison, and
  the non-regression gate report.

Corrective outcome:

- Stability and loop-balance gates pass.
- RPA pressure, LPA pressure, SVC flow, and RPA/LPA flow fraction now pass the
  full-0D non-regression gates.
- EDV, ESV, SV, and CO still fail the pump non-regression gates.
- Paper-model score improved from Task 008 but remains slightly worse than the
  full 0-D reference.
- Ascending and descending aortic flow waveforms still strongly regress relative
  to full 0-D.

The quasi model is therefore marked as a stable corrective prototype, not yet a
superior calibrated quasi model.

Validation:

- `.venv/bin/python scripts/modeling/build_quasi_configs.py`
- `.venv/bin/python scripts/calibration/run_quasi_calibration.py --run-reference-scenarios --write-objective-reports`
- `.venv/bin/python scripts/calibration/quasi_non_regression.py --out models/quasi_0d_1d/calibration/non_regression_gate.json`
