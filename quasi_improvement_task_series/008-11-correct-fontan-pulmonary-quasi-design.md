# Task 008.11 — Correct Fontan/Pulmonary Quasi Impedance Design

## Goal

Fix the pulmonary pressure partition and TCPC limb impedance after the aortic chain has been corrected. The current quasi model has good RPA/LPA flows and split, but RPA/LPA pressures remain low.

Current issue:

```text
RPA pressure target ≈ 8.48 mmHg
current quasi RPA ≈ 7.72 mmHg

LPA pressure target ≈ 8.46 mmHg
current quasi LPA ≈ 7.72 mmHg
```

At the same time, wedge/mid-lung pressure is not obviously too low. Therefore, the fix is probably not simply increasing total pulmonary resistance.

## Inputs

Use:

```text
models/quasi_0d_1d/config_fragments/quasi_vessel_chains_corrected.json
models/quasi_0d_1d/calibration/characteristic_impedance_report.csv
models/quasi_0d_1d/calibration/compliance_budget.csv
data/processed/aramburu_2024/model_inputs/fontan_cross_geometry.csv
models/quasi_0d_1d/calibration/baseline_objective.json
```

## Required implementation

Create or update:

```text
models/quasi_0d_1d/calibration/fontan_pulmonary_design_report.md
models/quasi_0d_1d/calibration/fontan_pulmonary_design_candidates.csv
models/quasi_0d_1d/config_fragments/quasi_fontan_pulmonary_corrected.json
```

Test a small grid around:

```text
SVC limb R/L/C scale
IVC limb R/L/C scale
RPA limb R/L/C scale
LPA limb R/L/C scale
RPA/LPA branch resistance scale
right_lung_Rprox_fraction
left_lung_Rprox_fraction
right_lung_C scale
left_lung_C scale
```

## Main design logic

To raise RPA/LPA pressures without over-raising wedge/mid-lung pressure:

```text
increase pulmonary proximal resistance fraction
preserve total pulmonary resistance initially
reduce distal resistance accordingly
```

That means:

```text
Rprox increases
Rdist decreases
Rtotal = Rprox + Rdist remains near calibrated value
```

## TCPC limb design logic

Use the quasi limbs to represent conduit inertia and distributed storage, not artificial large pressure losses. If SVC/IVC pressures are close but TCPC/RPA/LPA are too low, inspect whether the pressure drops across:

```text
SVC→TCPC
IVC→TCPC
TCPC→RPA
TCPC→LPA
```

are too large or incorrectly distributed.

## Control

This task is complete only if the corrected Fontan/pulmonary design passes:

```text
1. RPA pressure error is not worse than full 0-D.
2. LPA pressure error is not worse than full 0-D.
3. RPA and LPA flow errors remain close to target and do not regress versus full 0-D.
4. RPA/LPA flow fraction passes the gate.
5. SVC flow and IVC flow remain mass-consistent.
6. TCPC, atrial, and ventricle mass-balance gates pass.
7. No obvious high-frequency inertial ringing is introduced in SVC/IVC/RPA/LPA flows.
```
