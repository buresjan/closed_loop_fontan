# Full 0-D closed-loop Fontan model

This is a concrete starter implementation of a 0-D closed-loop Fontan circulation.
It uses PhysioBlocks' existing block library as much as possible:

- `spherical_cavity_block` with `spherical_dynamics`, `velocity_law_hht`,
  `rheology_fiber_additive`, and `active_law_macro_huxley_two_moments` for the
  single ventricle.
- `valve_rl_block` for the atrioventricular and aortic valves.
- `c_block` for compliant blood-volume compartments.
- `rc_block` with `zero_capacitance = 0.0` as the pure hydraulic resistor used
  for systemic beds, TCPC connectors, and fenestration.
- `rcr_block` for the right and left pulmonary Windkessel beds.
- A local `time_varying_elastance_atrium_block` for active atrial filling and
  atrial kick.

## Model topology

```text
active atrium -> valve_atrium -> cavity -> valve_arterial -> AAo -> aortic arch
                                                                  |-> BCA  \
                                                                  |-> LCCA -> Ca1 -> Rc1 -> Cv1 -> Rv1 -> SVC
                                                                  |-> LSA  /
                                                                  \\-> DAo -> Ra4 -> Ca2 -> Rc2 -> Cv2 -> Rv2 -> IVC

SVC -> SVC conduit R-L-C -> TCPC junction -> RPA conduit R-L-C -> RPA -> Rr1 -> Cr lung -> Rr2 -> active atrium
IVC -> IVC conduit R-L-C -> TCPC junction -> LPA conduit R-L-C -> LPA -> Rl1 -> Cl lung -> Rl2 -> active atrium
optional: ivc -> fenestration -> active atrium
```

The model is closed-loop: no atrial, venous, aortic, or inflow boundary condition
is prescribed in the baseline or scenario configurations.

The aortic outlet is represented as a small tree rather than a single lumped
aorta: ascending aorta (`AAo`), aortic arch, brachiocephalic artery (`BCA`),
left common carotid artery (`LCCA`), left subclavian artery (`LSA`), and
descending aorta (`DAo`). The three upper arch vessels now feed a shared upper
vascular bed: arterial compliance `Ca1`, capillary resistance `Rc1`, venous
compliance `Cv1`, and venous resistance `Rv1` before SVC. The DAo path feeds a
lower vascular bed with arterial resistance `Ra4`, arterial compliance `Ca2`,
capillary resistance `Rc2`, venous compliance `Cv2`, and venous resistance
`Rv2` before IVC.

The Fontan pathway is also no longer a direct four-resistor connection to a
single TCPC node. The SVC, IVC, RPA, and LPA limbs each pass through a short
conduit state with symmetric R-L series behavior and local compliance before
connecting to the TCPC junction or pulmonary artery node. The implementation
uses `valve_rl_block` with equal forward and backward conductance as a
bidirectional inertial conduit element.

Each lung is represented by a small Windkessel bed instead of one direct
resistance. The RPA and LPA feed proximal resistances into pulmonary
microvascular/venous pressure states, which drain through distal resistances to
the atrium. The total right and left pulmonary resistances are preserved from
the previous scenarios and split 40% proximal / 60% distal.

The atrial compartment is active rather than a passive `c_block`. The local
atrium block stores blood with a time-varying elastance, using the old passive
atrial compliance as the minimum elastance state and a late-diastolic activation
pulse to generate atrial kick before ventricular activation.

## Reference policy

This model family is the repository's current full 0-D reference variant. Keep
its accepted topology, scenario set, schematic, and reference metrics stable
while quasi 0-D/1-D and coupled 0-D/1-D variants are developed separately.

Changes that alter full 0-D topology, parameterization, block conventions,
scenario behavior, or accepted metrics must update this README, the schematic,
and the relevant reference outputs in the same change. Cleanup of the current
`rc_block` pure-resistor workaround or `valve_rl_block` bidirectional-conduit
workaround is allowed only if it preserves the accepted reference behavior or
creates a deliberately named new reference output set.

Until the calibration tasks are completed, the included parameters remain
plausible development values rather than patient-calibrated values.

## Files

```text
models/full_0d/configs/fontan_0d_smoke.jsonc
models/full_0d/configs/fontan_0d_baseline.jsonc
models/full_0d/configs/fontan_0d_vasodilation.jsonc
models/full_0d/configs/fontan_0d_fenestration.jsonc
models/full_0d/configs/fontan_0d_lpa_obstruction.jsonc
models/full_0d/docs/fontan_closed_loop_schematic.svg
models/full_0d/docs/fontan_closed_loop_schematic.png
models/full_0d/docs/implementation_notes.md
models/full_0d/reference_outputs/*.json
```

## Run a smoke simulation

```bash
python scripts/run_one.py models/full_0d/configs/fontan_0d_smoke.jsonc --series Smoke
```

Then compute metrics from the generated `main.csv`:

```bash
python scripts/metrics.py runs/simulations/Smoke/*/main.csv models/full_0d/configs/fontan_0d_smoke.jsonc --out models/full_0d/reference_outputs/smoke_metrics.json
```

## Run final scenarios

The final scenario configs run for 8 seconds so the additional systemic and
pulmonary compliances settle before the last-cycle metrics are computed.

```bash
python scripts/run_one.py models/full_0d/configs/fontan_0d_baseline.jsonc --series Baseline
python scripts/run_one.py models/full_0d/configs/fontan_0d_vasodilation.jsonc --series Vasodilation
python scripts/run_one.py models/full_0d/configs/fontan_0d_fenestration.jsonc --series Fenestration
python scripts/run_one.py models/full_0d/configs/fontan_0d_lpa_obstruction.jsonc --series LPAObstruction
```

After computing metrics for each case, compare them:

```bash
python scripts/compare_scenarios.py \
  models/full_0d/reference_outputs/baseline_metrics.json \
  models/full_0d/reference_outputs/vasodilation_metrics.json \
  models/full_0d/reference_outputs/fenestration_metrics.json \
  models/full_0d/reference_outputs/lpa_obstruction_metrics.json
```

## Acceptance checks

Use `scripts/metrics.py` to inspect:

- TCPC cycle balance: SVC + IVC ~= RPA + LPA.
- Atrial cycle balance: right lung distal flow + left lung distal flow +
  fenestration ~= AV valve flow.
- Ventricular cycle balance: AV valve flow ~= aortic valve flow.
- Ventricular EDV, ESV, stroke volume, cardiac output, and pressure range.
- Directional intervention responses for pulmonary vasodilation, fenestration,
  and LPA obstruction.

## Caveat

The included parameters are plausible starting values, not patient-calibrated
values. The scaffold is intended to run, expose the right topology, and support
calibration/testing. Do not interpret the included numerical outputs clinically
without calibration and validation.
