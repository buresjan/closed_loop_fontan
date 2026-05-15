# Implementation notes

## Constructed closed loop

The complete topology is defined by the scenario configurations, with
`models/full_0d/configs/fontan_0d_baseline.jsonc` as the reference. The baseline and final
scenario files share the same closed-loop network: `boundaries_conditions` is
empty, so no inlet pressure, outlet pressure, or prescribed flow boundary is
used to drive the circulation.

The loop contains 21 pressure nodes:

```text
atrial, cavity,
aao, aortic_arch, bca, lcca, lsa, upper_art, upper_ven,
dao, lower_art, lower_ven,
svc, svc_conduit, ivc, ivc_conduit, tcpc,
rpa_conduit, lpa_conduit, rpa, lpa
```

At a circuit level, blood moves around the loop as:

```text
active atrium E(t) at atrial node
  -> AV valve R-L -> active spherical ventricle / cavity
  -> aortic valve R-L -> AAo C -> aortic arch C

aortic arch C
  -> BCA C  -> upper arterial C / Ca1
  -> LCCA C -> upper arterial C / Ca1
  -> LSA C  -> upper arterial C / Ca1
upper arterial C / Ca1 -> Rc1 -> upper venous C / Cv1 -> Rv1 -> SVC C

aortic arch C -> DAo C -> Ra4 -> lower arterial C / Ca2
lower arterial C / Ca2 -> Rc2 -> lower venous C / Cv2 -> Rv2 -> IVC C

SVC C -> SVC conduit R-L -> SVC conduit C -> connector R -> TCPC C
IVC C -> IVC conduit R-L -> IVC conduit C -> connector R -> TCPC C

TCPC C -> RPA conduit R-L -> RPA conduit C -> connector R -> RPA C
RPA C -> right pulmonary RCR bed -> active atrium E(t)

TCPC C -> LPA conduit R-L -> LPA conduit C -> connector R -> LPA C
LPA C -> left pulmonary RCR bed -> active atrium E(t)

optional high-resistance baseline path: IVC -> fenestration R -> atrial node
```

## Block inventory

The model uses these block classes:

- `spherical_cavity_block`: `cavity`, the active single ventricle.
- `time_varying_elastance_atrium_block`: `active_atrium`, the active atrial
  chamber attached to the `atrial` node.
- `valve_rl_block`: `valve_atrium`, `valve_arterial`, and the four bidirectional
  conduit R-L elements `svc_conduit_rl`, `ivc_conduit_rl`,
  `rpa_conduit_rl`, `lpa_conduit_rl`.
- `c_block`: passive compliances at `cavity`, `aao`, `aortic_arch`, `bca`,
  `lcca`, `lsa`, `upper_art`, `upper_ven`, `dao`, `lower_art`, `lower_ven`,
  `svc`, `ivc`, `tcpc`, `svc_conduit`, `ivc_conduit`, `rpa_conduit`,
  `lpa_conduit`, `rpa`, and `lpa`.
- `rc_block` with `zero_capacitance = 0.0`: pure resistive links in the aortic
  tree, systemic beds, TCPC connectors, and fenestration.
- `rcr_block`: `right_lung` and `left_lung`, each with a proximal resistance,
  middle compliant pressure state, and distal resistance.

The exact passive-compliance block-to-node map is:

```text
capacitance_valve       -> cavity
aao_compliance          -> aao
aortic_arch_compliance  -> aortic_arch
bca_compliance          -> bca
lcca_compliance         -> lcca
lsa_compliance          -> lsa
upper_ca1               -> upper_art
upper_cv1               -> upper_ven
dao_compliance          -> dao
lower_ca2               -> lower_art
lower_cv2               -> lower_ven
svc_compliance          -> svc
ivc_compliance          -> ivc
tcpc_compliance         -> tcpc
svc_conduit_compliance  -> svc_conduit
ivc_conduit_compliance  -> ivc_conduit
rpa_conduit_compliance  -> rpa_conduit
lpa_conduit_compliance  -> lpa_conduit
rpa_compliance          -> rpa
lpa_compliance          -> lpa
```

The exact pure-resistor `rc_block` connections are:

```text
aao_arch             : aao -> aortic_arch
arch_bca             : aortic_arch -> bca
upper_bca_to_ca1     : bca -> upper_art
arch_lcca            : aortic_arch -> lcca
upper_lcca_to_ca1    : lcca -> upper_art
arch_lsa             : aortic_arch -> lsa
upper_lsa_to_ca1     : lsa -> upper_art
upper_rc1            : upper_art -> upper_ven
upper_rv1            : upper_ven -> svc
arch_dao             : aortic_arch -> dao
lower_ra4            : dao -> lower_art
lower_rc2            : lower_art -> lower_ven
lower_rv2            : lower_ven -> ivc
svc_conduit_junction : svc_conduit -> tcpc
ivc_conduit_junction : ivc_conduit -> tcpc
rpa_conduit_out      : rpa_conduit -> rpa
lpa_conduit_out      : lpa_conduit -> lpa
fenestration         : ivc -> atrial
```

## Heart and valve convention

The ventricle remains the PhysioBlocks active spherical cavity. The `cavity`
block uses `spherical_dynamics`, `velocity_law_hht`,
`rheology_fiber_additive`, and `active_law_macro_huxley_two_moments`, with
`pleural.pressure` as the external pressure. The small `capacitance_valve`
`c_block` is also attached to the `cavity` node and provides the small cavity
compliance shown in the schematic.

The atrioventricular and aortic valves use `valve_rl_block` with inertance,
large forward conductance, and small reverse conductance. The AV valve connects
`atrial -> cavity`; the aortic valve connects `cavity -> aao`.

## RC-block resistor convention

For an `rc_block`, PhysioBlocks defines local-node fluxes as:

```text
Q1 = (P2 - P1) / R
Q2 = (P1 - P2) / R - C dP2/dt
```

Therefore this scaffold represents a source-to-target resistor by assigning:

```text
node 2 = source / upstream
node 1 = target / downstream
```

With `zero_capacitance = 0.0`, the block acts as a pure resistor while the
separate `c_block`s provide compartmental storage.

## Aortic-tree convention

The systemic arterial outlet is no longer a single `aorta` node. The arterial
tree is represented as:

```text
cavity -> valve_arterial -> aao -> aortic_arch
                              -> bca  \
                              -> lcca -> upper_art(Ca1) -> Rc1 -> upper_ven(Cv1) -> Rv1 -> svc
                              -> lsa  /
                              -> dao -> Ra4 -> lower_art(Ca2) -> Rc2 -> lower_ven(Cv2) -> Rv2 -> ivc
```

The same resistor node convention applies: for example, `arch_bca` has node 2
at `aortic_arch` and node 1 at `bca`, while `upper_rc1` has node 2 at
`upper_art` and node 1 at `upper_ven`.

The systemic bed parameterization keeps the previous aggregate systemic loads
approximately unchanged. The shared `aao_arch` resistance is common to upper and
lower systemic outflow. The BCA/LCCA/LSA paths remain parallel up to `Ca1`; their
parallel equivalent plus `Rc1` and `Rv1`, plus `aao_arch`, matches the prior
`aorta_upper + upper_body` load. The DAo path plus `Ra4`, `Rc2`, `Rv2`, and
`aao_arch` matches the prior `aorta_lower + lower_body` load.

The aortic tree also has passive compliances at `aao`, `aortic_arch`, `bca`,
`lcca`, `lsa`, and `dao`, in addition to the shared upper and lower vascular-bed
compliances.

The upper and lower vascular beds add compliant arterial and venous states:

```text
BCA/LCCA/LSA -> upper_art / Ca1 -> upper_rc1 / Rc1 -> upper_ven / Cv1 -> upper_rv1 / Rv1 -> SVC
DAo -> lower_ra4 / Ra4 -> lower_art / Ca2 -> lower_rc2 / Rc2 -> lower_ven / Cv2 -> lower_rv2 / Rv2 -> IVC
```

Because these added states introduce slower storage dynamics, the calibrated
final scenario configurations run for 20 seconds before metrics are derived
from the last cycle. The smoke case remains intentionally short and only checks
that the network executes without numerical failure.

## TCPC-conduit convention

PhysioBlocks 1.2.0 does not provide a generic `rlc_block`. The Fontan conduits
therefore use the existing `valve_rl_block` as a symmetric bidirectional RL
element by assigning equal `conductance` and `backward_conductance`. This removes
the diode behavior while retaining the block's inertance state:

```text
L dQ/dt + R Q + P_target - P_source = 0
```

Each Fontan limb is represented by an RL element, a local conduit compliance,
and a short connector resistance:

```text
SVC -> svc_conduit_rl -> svc_conduit(C) -> svc_conduit_junction -> TCPC
IVC -> ivc_conduit_rl -> ivc_conduit(C) -> ivc_conduit_junction -> TCPC
TCPC -> rpa_conduit_rl -> rpa_conduit(C) -> rpa_conduit_out -> RPA
TCPC -> lpa_conduit_rl -> lpa_conduit(C) -> lpa_conduit_out -> LPA
```

The connector resistance is 5% of the previous direct pathway resistance, and
the RL element carries the remaining 95%. This keeps the previous aggregate
Fontan pathway load while adding conduit pressure and inertial flow states. The
old `tcpc_compliance` is split across the central junction and the four conduit
compliances.

## Pulmonary Windkessel convention

The right and left pulmonary beds use PhysioBlocks' `rcr_block` instead of a
single pure resistor:

```text
RPA -> right_lung.resistance_1 -> right_lung.pressure_mid(C) -> right_lung.resistance_2 -> atrial
LPA -> left_lung.resistance_1  -> left_lung.pressure_mid(C)  -> left_lung.resistance_2  -> atrial
```

For `rcr_block`, local node 1 is the upstream pulmonary artery and local node 2
is the downstream atrium. The internal `pressure_mid` state is interpreted as a
pulmonary microvascular / pulmonary venous pressure, not as an explicitly
resolved anatomic pulmonary vein.

The previous aggregate lung resistances are preserved by splitting each lung
load into 40% proximal resistance and 60% distal resistance. The vasodilation
and LPA obstruction scenarios change both proximal and distal components
proportionally, so the intervention still acts on total pulmonary vascular
load.

Derived metrics report both proximal and distal pulmonary flows. The legacy
`right_lung.flow` and `left_lung.flow` aliases are retained as distal flow to
keep scenario comparisons and atrial mass-balance checks stable.

## Active-atrium convention

The old passive atrial `c_block` is replaced by the local
`time_varying_elastance_atrium_block` registered in `fontan_blocks/active_atrium.py`.
The active block remains attached to the same `atrial` pressure node, so the
pulmonary returns, fenestration, and AV valve still connect to one common atrial
pressure.

The chamber relation is:

```text
V_atrium = V0 + (P_atrium - P_external) / E_atrium(t)
```

and the nodal flux is the negative time derivative of that volume. When
`E_atrium(t)` rises in late diastole, the chamber becomes less compliant and
pushes blood toward the AV valve. This introduces an atrial kick while leaving
the existing active spherical ventricle unchanged.

The minimum elastance is the reciprocal of the previous passive atrial
compliance, so the low-activation filling behavior starts from the earlier
model. The activation pulse is parameterized as fractions of the cardiac period:

```text
active_atrium.activation_start = 0.78
active_atrium.activation_peak  = 0.90
active_atrium.activation_end   = 0.98
```

`scripts/run_one.py` adds the repo-local `fontan_blocks` package to the
PhysioBlocks launcher configuration and to `PYTHONPATH` before starting a
simulation. This keeps the block definition versioned with the model instead of
patching the installed PhysioBlocks package.

## Why the fenestration block is present in baseline

The baseline includes a fenestration path with extremely high resistance. This
keeps the set of block names stable across configurations. The fenestration
scenario lowers `fenestration.resistance` to open the shunt.

## Scenario variants

All final scenario files keep the same topology and change only parameters:

- `fontan_0d_baseline.jsonc`: reference closed-loop circuit.
- `fontan_0d_vasodilation.jsonc`: lowers both right and left pulmonary
  proximal/distal resistances.
- `fontan_0d_fenestration.jsonc`: lowers `fenestration.resistance`, opening the
  IVC-to-atrium shunt.
- `fontan_0d_lpa_obstruction.jsonc`: increases left pulmonary proximal/distal
  resistance and increases the LPA conduit pathway load.
- `fontan_0d_smoke.jsonc`: same topology as baseline, with a shorter run used
  only as a numerical smoke check.

## Task 004 calibration state

The accepted Task 004 baseline is a scale-factor calibration against
`data/processed/aramburu_2024/targets`. It changes heart rate, ventricular
geometry and contractility, active-atrium unstressed volume, systemic
resistance groups, pulmonary resistance groups, TCPC entry resistances, and
initial pressure states. It does not change the topology described above.

The calibration scripts are under `scripts/calibration/`. The selected factors,
baseline target comparison, numerical periodicity checks, and validation
scenario responses are documented in
`models/full_0d/calibration/calibration_report.md`.
