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
the technical reference PDF/source, and the relevant reference outputs in the
same change. Cleanup of the current `rc_block` pure-resistor workaround or
`valve_rl_block` bidirectional-conduit workaround is allowed only if it
preserves the accepted reference behavior or creates a deliberately named new
reference output set.

Task 004 calibrated the baseline to the Aramburu 2024 direct-measurement
targets with scale factors recorded in `calibration/parameter_priors.yaml`.
Intervention scenarios inherit the calibrated baseline and are validation cases,
not separately retuned cases.

## Files

```text
models/full_0d/configs/fontan_0d_smoke.jsonc
models/full_0d/configs/fontan_0d_baseline.jsonc
models/full_0d/configs/fontan_0d_vasodilation.jsonc
models/full_0d/configs/fontan_0d_fenestration.jsonc
models/full_0d/configs/fontan_0d_lpa_obstruction.jsonc
models/full_0d/docs/full_0d_schematic.svg
models/full_0d/docs/full_0d_schematic.png
models/full_0d/docs/implementation_notes.md
models/full_0d/docs/full_0d_technical_reference.md
models/full_0d/docs/full_0d_technical_reference.pdf
models/full_0d/calibration/calibration_report.md
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

The final scenario configs run for 20 seconds so the calibrated systemic and
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

## Calibration status

The calibrated baseline uses the measured cycle length from
`data/processed/aramburu_2024/targets`, reduced ventricular geometry and
contractility, separated upper/lower systemic resistance scales, an RPA-favoring
pulmonary resistance split, lower TCPC entry resistance, and a lower initialized
pressure pedestal.

Current baseline highlights from `reference_outputs/baseline_metrics.json`:

- SV 35.87 ml versus 36.80 ml target.
- CO 2.51 L/min versus 2.57 L/min target.
- Mean AAo pressure 47.79 mmHg versus 50.40 mmHg target.
- Mean SVC/IVC pressures 9.11/8.93 mmHg versus 8.87/8.54 mmHg targets.
- RPA flow fraction 0.591 versus 0.591 target.

The main residual gap is low descending-aorta pressure relative to the direct
measurement table. See `calibration/calibration_report.md` for the full target
comparison and validation scenario summary.

## Caveat

The included parameters are calibrated for computational development against the
processed Aramburu 2024 targets, but they are not clinically validated. Do not
interpret the numerical outputs clinically without separate validation.
