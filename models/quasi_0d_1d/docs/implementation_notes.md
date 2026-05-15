# Implementation notes

## Current state

The quasi 0-D/1-D model family is not executable yet. Task 005 defines the
first parameter layer for the future PhysioBlocks-only quasi model:

```text
models/quasi_0d_1d/calibration/parameter_priors.yaml
models/quasi_0d_1d/config_fragments/quasi_vessel_chains.json
```

The generated priors are inputs for Task 006, where runnable quasi configs will
be assembled from the calibrated full 0-D model plus the derived R-L-C vessel
chains.

## Intended topology

The quasi model keeps the full 0-D pump, valve, bed, pulmonary, and
fenestration components:

```text
active atrium E(t)
  -> AV valve R-L -> active spherical ventricle
  -> aortic valve R-L -> aortic quasi chain
  -> systemic beds -> caval quasi chains
  -> TCPC node -> pulmonary quasi chains
  -> pulmonary RCR beds -> active atrium E(t)
```

The first quasi release replaces these full 0-D pathways with repeated
`hydraulic_rl_block` plus `c_block` cells:

```text
AAo -> AAo/arch R-L-C chain -> aortic_arch
aortic_arch -> DAo R-L-C chain -> dao
SVC -> SVC R-L-C chain -> TCPC
IVC -> IVC R-L-C chain -> TCPC
TCPC -> RPA R-L-C chain -> RPA
TCPC -> LPA R-L-C chain -> LPA
```

The BCA, LCCA, and LSA upper-body branches remain 0-D resistive branches for
the first quasi release.

## Chain parameter derivation

`scripts/modeling/derive_quasi_vessel_parameters.py` reads:

```text
data/processed/aramburu_2024/model_inputs/aorta_geometry.csv
data/processed/aramburu_2024/model_inputs/fontan_cross_geometry.csv
data/processed/aramburu_2024/targets/target_policy.csv
models/full_0d/configs/fontan_0d_baseline.jsonc
```

For each geometry cell it computes:

```text
Abar = 0.5 * (pi * r_in^2 + pi * r_out^2)
Lhyd = rho * length / Abar
Ctot = Abar * length / (rho * c^2)
Rgeom = tapered Poiseuille resistance
```

with:

```text
rho = 1060 kg/m^3
mu = 0.0035 Pa*s
aortic wave speed prior = 5.35 m/s
Fontan/TCPC wave speed prior = 2.81 m/s
```

The first-pass segment counts are:

```text
AAo/arch: 4 cells
DAo:      6 cells
SVC:      3 cells
IVC:      5 cells
RPA:      3 cells
LPA:      4 cells
```

## Resistance policy

The Task 004.5 target policy is applied directly.

The aortic quasi chains use geometry/friction resistance. They do not preserve
the excessive full 0-D AAo-to-DAo pressure drop. Later quasi calibration should
keep most systemic pressure loss in the systemic beds unless data justify a
larger aortic trunk loss.

The SVC, IVC, RPA, and LPA quasi chains start from the calibrated full 0-D
pathway resistances. The current full 0-D Fontan pressures and RPA/LPA flow
split are accepted baseline physiology, so these values are useful priors.

Direct DAo pressure remains diagnostic/low-weight. IVC flow remains
mass-closure dependent and should be compared against raw direct,
implied-from-CO, and implied-from-pulmonary-closure targets.

## LPA narrowing

The LPA narrowing is explicit in the generated priors:

```text
quasi_lpa.narrowing_radius_m = 0.003
quasi_lpa.narrowing_resistance_scale = 1.0
```

The narrowing comes from the shared LPA I outlet / LPA II inlet radius in the
processed Fontan cross geometry. Later LPA obstruction scenarios should adjust
the LPA quasi-chain resistance and/or compliance through this explicit
narrowing metadata rather than hiding the change in unrelated parameters.

## Config fragment convention

`config_fragments/quasi_vessel_chains.json` is not a runnable PhysioBlocks
configuration. It contains reusable chain pieces for Task 006:

```text
nodes
blocks
parameters
variables_initialization
variables_magnitudes
```

Each R-L-C chain cell is represented by:

```text
hydraulic_rl_block: source pressure node -> downstream pressure node
c_block: downstream pressure node compliance
```

The orientation follows the local hydraulic block convention:

```text
node 1 -> node 2 is positive physical flow
```

## Schematic convention

`docs/schematic.svg` follows the full 0-D schematic style and component set.
The quasi-specific labels mark the derived R-L-C chain counts and the narrowed
LPA pressure node. Update both the SVG and PNG whenever the quasi topology or
chain counts change.
