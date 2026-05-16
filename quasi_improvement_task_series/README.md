# Quasi 0-D/1-D Improvement Task Series

This task series is intended to close the current gap between the stable quasi 0-D/1-D prototype and the calibrated full 0-D reference.

Current status from Task 008.6:

```text
Full 0-D direct score:      0.0614
Current quasi direct score: 0.0592

Full 0-D hard score:        0.0433
Current quasi hard score:   0.0561

Full 0-D paper score:       0.0793
Current quasi paper score:  0.0805

Full 0-D AAo flow nRMSE:    0.499
Current quasi AAo nRMSE:    0.578

Full 0-D DAo flow nRMSE:    0.434
Current quasi DAo nRMSE:    0.952
```

Interpretation:

```text
The current quasi model is stable, but not scientifically superior.
The next work should be design-first, then calibration.
```

The final task in this sequence cannot be marked complete unless the quasi loop is objectively better than the full 0-D reference under the defined promotion gate.

Task 008.10 is currently blocked: a corrected aortic-chain candidate restored
the passive AAo-to-DAo drop and DAo chain-health waveform, but no tested
candidate passed the strict clinical DAo `lower_ra4.flow` no-regression check.
Resolve that blocker before treating the quasi model as promotable.

## Task list

```text
008.7  completed  Freeze superiority gate and reference metrics
008.8  completed  Build open-loop aortic quasi diagnostic harness
008.9  completed  Resolve AAo/DAo flow signal definitions
008.10 blocked    Correct quasi aortic chain design
008.11 planned    Correct Fontan/pulmonary quasi impedance design
008.12 planned    Restore pump/preload and compliance budget
008.13 planned    Run constrained quasi closed-loop calibration
008.14 planned    Validate scenarios and promote quasi model only if superior
```

These task files live in `quasi_improvement_task_series/` and are mirrored in
the root roadmap table.

Recommended implementation outputs:

```text
models/quasi_0d_1d/calibration/
models/quasi_0d_1d/configs/
models/quasi_0d_1d/config_fragments/
models/quasi_0d_1d/reference_outputs/
scripts/calibration/
scripts/quasi/
```
