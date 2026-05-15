# 008 - Calibrate Quasi 0-D/1-D Model

Status: planned

Depends on: Tasks 004, 006, and 007

## Goal

Tune the quasi model from the calibrated full 0-D physiology while improving impedance, inertance, distributed compliance, and waveform timing.

## Implementation

- Start from calibrated full 0-D parameters.
- Preserve total vessel resistance, total vessel compliance, and geometry-derived inertance.
- Calibrate quasi aortic chain scales:
  - AAo/arch R, C, and L or wave-speed scale;
  - DAo R, C, and L or wave-speed scale.
- Calibrate quasi TCPC/caval/pulmonary limb scales:
  - SVC, IVC, RPA, and LPA R/L/C scales;
  - LPA narrowed-segment scale;
  - TCPC junction compliance/loss scale.
- Allow only small global retuning of heart contractility, systemic resistance, pulmonary resistance, and active atrium pressure level.
- Validate intervention scenarios without retuning.

## Acceptance

- Summary accuracy is comparable to full 0-D or only modestly worse.
- Waveform amplitude/timing improves over full 0-D for selected targets.
- No artificial ringing from excessive inertance.
- Periodicity and mass-balance thresholds remain acceptable.

## PhysioBlocks Impact

No PhysioBlocks internal changes.
