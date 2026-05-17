---
title: Full 0-D Closed-Loop Fontan Model Technical Reference
subtitle: Standardized model definition, equations, segments, and free parameters
---

# Full 0-D Closed-Loop Fontan Model Technical Reference

This document is generated from repository sources by `scripts/docs/build_model_reference_pdfs.py`. Edit the model config, implementation notes, schematic, or this generator, then regenerate the markdown and PDF together.

## Model Construction

### Scope and Status

Accepted full 0-D reference model.

This model is the accepted closed-loop 0-D reference circulation.

It uses a PhysioBlocks active spherical single ventricle, an active time-varying-elastance atrium, R-L valves, lumped vascular compliances, systemic resistive beds, Fontan conduit elements, pulmonary RCR beds, and an optional fenestration shunt.

No inlet pressure, outlet pressure, or prescribed inflow boundary condition drives the baseline circulation.

### Schematic

![full_0d schematic](full_0d_schematic.png){ width=100% }

### Accepted Components

- active atrium and active spherical ventricle
- atrioventricular and aortic valve R-L blocks
- ascending aorta, aortic arch, BCA, LCCA, LSA, and DAo tree
- upper and lower systemic vascular beds
- SVC, IVC, RPA, and LPA Fontan conduit states
- right and left pulmonary RCR Windkessel beds
- high-resistance baseline fenestration path

### Authoritative Baseline Config

The executable topology and free-parameter values are taken from `models/full_0d/configs/fontan_0d_baseline.jsonc`.

- pressure nodes: 21
- blocks/segments: 48
- free parameter entries: 91
- boundary conditions: 0

### Scenario Configs

- `models/full_0d/configs/fontan_0d_baseline.jsonc`
- `models/full_0d/configs/fontan_0d_fenestration.jsonc`
- `models/full_0d/configs/fontan_0d_lpa_obstruction.jsonc`
- `models/full_0d/configs/fontan_0d_smoke.jsonc`
- `models/full_0d/configs/fontan_0d_vasodilation.jsonc`

### Pressure Nodes

- `atrial`
- `cavity`
- `aao`
- `aortic_arch`
- `bca`
- `lcca`
- `lsa`
- `upper_art`
- `upper_ven`
- `dao`
- `lower_art`
- `lower_ven`
- `svc`
- `svc_conduit`
- `ivc`
- `ivc_conduit`
- `tcpc`
- `rpa_conduit`
- `lpa_conduit`
- `rpa`
- `lpa`

### Block Type Counts

| Block type | Count |
|---|---:|
| `c_block` | 20 |
| `rc_block` | 18 |
| `rcr_block` | 2 |
| `spherical_cavity_block` | 1 |
| `time_varying_elastance_atrium_block` | 1 |
| `valve_rl_block` | 6 |

## Governing Equations

The sign convention follows PhysioBlocks local block fluxes. For a two-node flow element, local node 1 is the first node listed in the config and local node 2 is the second node listed in the config.

### Nodal Conservation

At every pressure node, the algebraic/differential network residual is the sum of all block flux contributions attached to that node:

$$\sum_{b \in \mathcal{B}(i)} Q_{b,i} = 0.$$

Storage blocks contribute pressure derivatives to this same residual, so closed-loop volume conservation is enforced through the connected block equations rather than through prescribed boundary flow.

### Passive Compliance Block

For a `c_block` at pressure node `P` with capacitance `C`:

$$Q = -C \frac{dP}{dt}.$$

The saved stored volume is proportional to pressure in the local linear compliance approximation:

$$V = C P.$$

### Pure RC Resistor Convention

This repository uses `rc_block` with zero capacitance as a pure resistive link. PhysioBlocks defines the local fluxes as:

$$Q_1 = \frac{P_2 - P_1}{R},$$

$$Q_2 = \frac{P_1 - P_2}{R} - C \frac{dP_2}{dt}.$$

When `C = 0`, the block is used as a pure resistor. To represent an upstream-to-downstream path with positive physical flow from upstream to downstream, the configs assign local node 2 to the upstream pressure and local node 1 to the downstream pressure.

### Hydraulic R-L Link

The local quasi-vessel R-L element uses positive internal flow from local node 1 to local node 2:

$$L \frac{dQ}{dt} + RQ = P_1 - P_2,$$

$$Q_1 = -Q,\qquad Q_2 = Q.$$

This is the repeated segment equation used by the quasi 0-D/1-D chains.

### Valve R-L Block

The R-L valve block has local positive flow from node 1 to node 2 and switches conductance according to flow direction:

$$L \frac{dQ}{dt} + P_2 - P_1 + R(Q)Q = 0,$$

$$R(Q) = \begin{cases}1/G_f,& Q>0,\\ 1/G_b,& Q<0,\end{cases}$$

$$Q_1=-Q,\qquad Q_2=Q.$$

`G_f` is the forward conductance and `G_b` is the backward conductance.

### Pulmonary RCR Windkessel

For an `rcr_block` with inlet pressure `P_1`, outlet pressure `P_2`, middle pressure `P_m`, proximal resistance `R_1`, distal resistance `R_2`, and compliance `C`:

$$Q_1 = \frac{P_m - P_1}{R_1},$$

$$Q_2 = \frac{P_m - P_2}{R_2},$$

$$\frac{P_1 - P_m}{R_1} + \frac{P_2 - P_m}{R_2} - C\frac{dP_m}{dt}=0.$$

### Active Atrium

The active atrium is a one-node time-varying elastance chamber:

$$E(t) = E_{min} + (E_{max}-E_{min})a(t),$$

$$V_a(t) = V_{0,a} + \frac{P_a(t)-P_{ext}}{E(t)},$$

$$Q_a = -\frac{dV_a}{dt}.$$

The activation `a(t)` is a raised-cosine pulse over the configured start, peak, and end phase of the cardiac cycle.

### Spherical Ventricular Cavity

The active ventricular cavity stores volume through the spherical cavity displacement `y`, reference radius `R_0`, and wall thickness `d_0`:

$$V(y)=\frac{4\pi}{3}\left[R_0\left(1+\frac{y}{R_0}\right)-\frac{d_0}{2\left(1+\frac{y}{R_0}\right)^2}\right]^3,$$

$$Q_v = -\frac{dV(y)}{dt}.$$

The pressure-displacement relation comes from the configured PhysioBlocks spherical dynamics, velocity law, passive rheology, and active macro-Huxley submodels. The corresponding free parameters are listed in the parameter inventory below with the `cavity.*` prefix.

## Segment Inventory

Each row is a block or segment in the accepted baseline config. The parameter column lists explicit block fields and all config parameters sharing the block-name prefix.

| Segment/block | Type | Local nodes | Free-parameter fields |
|---|---|---|---|
| `cavity` | `spherical_cavity_block` | 1: cavity | disp = cavity.dynamics.disp; radius -> heart_radius; thickness -> heart_thickness; cavity.dynamics.damping_coef; cavity.dynamics.hyperelastic_cst; cavity.dynamics.vol_mass; cavity.rheology.active_law.activation; cavity.rheology.active_law.crossbridge_stiffness; cavity.rheology.active_law.destruction_rate; cavity.rheology.active_law.starling_abscissas; cavity.rheology.active_law.starling_ordinates; cavity.rheology.damping_parallel; cavity.rheology.series_stiffness; cavity.velocity_law.scheme_ts_hht |
| `valve_atrium` | `valve_rl_block` | 1: atrial; 2: cavity | backward_conductance -> valves.backward_conductance; valve_atrium.conductance; valve_atrium.inductance; valve_atrium.scheme_ts_flux |
| `valve_arterial` | `valve_rl_block` | 1: cavity; 2: aao | backward_conductance -> valves.backward_conductance; valve_arterial.conductance; valve_arterial.inductance; valve_arterial.scheme_ts_flux |
| `capacitance_valve` | `c_block` | 1: cavity | capacitance_valve.capacitance |
| `active_atrium` | `time_varying_elastance_atrium_block` | 1: atrial | pressure_external -> pleural.pressure; elastance_min -> active_atrium.elastance_min; elastance_max -> active_atrium.elastance_max; unstressed_volume -> active_atrium.unstressed_volume; activation_start -> active_atrium.activation_start; activation_peak -> active_atrium.activation_peak; activation_end -> active_atrium.activation_end; heartbeat_duration -> heartbeat_duration |
| `aao_compliance` | `c_block` | 1: aao | aao_compliance.capacitance |
| `aortic_arch_compliance` | `c_block` | 1: aortic_arch | aortic_arch_compliance.capacitance |
| `bca_compliance` | `c_block` | 1: bca | bca_compliance.capacitance |
| `lcca_compliance` | `c_block` | 1: lcca | lcca_compliance.capacitance |
| `lsa_compliance` | `c_block` | 1: lsa | lsa_compliance.capacitance |
| `upper_ca1` | `c_block` | 1: upper_art | upper_ca1.capacitance |
| `upper_cv1` | `c_block` | 1: upper_ven | upper_cv1.capacitance |
| `dao_compliance` | `c_block` | 1: dao | dao_compliance.capacitance |
| `lower_ca2` | `c_block` | 1: lower_art | lower_ca2.capacitance |
| `lower_cv2` | `c_block` | 1: lower_ven | lower_cv2.capacitance |
| `svc_compliance` | `c_block` | 1: svc | svc_compliance.capacitance |
| `ivc_compliance` | `c_block` | 1: ivc | ivc_compliance.capacitance |
| `tcpc_compliance` | `c_block` | 1: tcpc | tcpc_compliance.capacitance |
| `svc_conduit_compliance` | `c_block` | 1: svc_conduit | svc_conduit_compliance.capacitance |
| `ivc_conduit_compliance` | `c_block` | 1: ivc_conduit | ivc_conduit_compliance.capacitance |
| `rpa_conduit_compliance` | `c_block` | 1: rpa_conduit | rpa_conduit_compliance.capacitance |
| `lpa_conduit_compliance` | `c_block` | 1: lpa_conduit | lpa_conduit_compliance.capacitance |
| `rpa_compliance` | `c_block` | 1: rpa | rpa_compliance.capacitance |
| `lpa_compliance` | `c_block` | 1: lpa | lpa_compliance.capacitance |
| `svc_conduit_rl` | `valve_rl_block` | 1: svc; 2: svc_conduit | conductance -> svc_conduit_rl.conductance; backward_conductance -> svc_conduit_rl.backward_conductance; scheme_ts_flux -> conduit.scheme_ts_flux; svc_conduit_rl.inductance |
| `svc_conduit_junction` | `rc_block` | 1: tcpc; 2: svc_conduit | capacitance -> zero_capacitance; svc_conduit_junction.resistance |
| `aao_arch` | `rc_block` | 1: aortic_arch; 2: aao | capacitance -> zero_capacitance; aao_arch.resistance |
| `arch_bca` | `rc_block` | 1: bca; 2: aortic_arch | capacitance -> zero_capacitance; arch_bca.resistance |
| `upper_bca_to_ca1` | `rc_block` | 1: upper_art; 2: bca | capacitance -> zero_capacitance; upper_bca_to_ca1.resistance |
| `arch_lcca` | `rc_block` | 1: lcca; 2: aortic_arch | capacitance -> zero_capacitance; arch_lcca.resistance |
| `upper_lcca_to_ca1` | `rc_block` | 1: upper_art; 2: lcca | capacitance -> zero_capacitance; upper_lcca_to_ca1.resistance |
| `arch_lsa` | `rc_block` | 1: lsa; 2: aortic_arch | capacitance -> zero_capacitance; arch_lsa.resistance |
| `upper_lsa_to_ca1` | `rc_block` | 1: upper_art; 2: lsa | capacitance -> zero_capacitance; upper_lsa_to_ca1.resistance |
| `upper_rc1` | `rc_block` | 1: upper_ven; 2: upper_art | capacitance -> zero_capacitance; upper_rc1.resistance |
| `upper_rv1` | `rc_block` | 1: svc; 2: upper_ven | capacitance -> zero_capacitance; upper_rv1.resistance |
| `arch_dao` | `rc_block` | 1: dao; 2: aortic_arch | capacitance -> zero_capacitance; arch_dao.resistance |
| `lower_ra4` | `rc_block` | 1: lower_art; 2: dao | capacitance -> zero_capacitance; lower_ra4.resistance |
| `lower_rc2` | `rc_block` | 1: lower_ven; 2: lower_art | capacitance -> zero_capacitance; lower_rc2.resistance |
| `lower_rv2` | `rc_block` | 1: ivc; 2: lower_ven | capacitance -> zero_capacitance; lower_rv2.resistance |
| `ivc_conduit_rl` | `valve_rl_block` | 1: ivc; 2: ivc_conduit | conductance -> ivc_conduit_rl.conductance; backward_conductance -> ivc_conduit_rl.backward_conductance; scheme_ts_flux -> conduit.scheme_ts_flux; ivc_conduit_rl.inductance |
| `ivc_conduit_junction` | `rc_block` | 1: tcpc; 2: ivc_conduit | capacitance -> zero_capacitance; ivc_conduit_junction.resistance |
| `rpa_conduit_rl` | `valve_rl_block` | 1: tcpc; 2: rpa_conduit | conductance -> rpa_conduit_rl.conductance; backward_conductance -> rpa_conduit_rl.backward_conductance; scheme_ts_flux -> conduit.scheme_ts_flux; rpa_conduit_rl.inductance |
| `rpa_conduit_out` | `rc_block` | 1: rpa; 2: rpa_conduit | capacitance -> zero_capacitance; rpa_conduit_out.resistance |
| `lpa_conduit_rl` | `valve_rl_block` | 1: tcpc; 2: lpa_conduit | conductance -> lpa_conduit_rl.conductance; backward_conductance -> lpa_conduit_rl.backward_conductance; scheme_ts_flux -> conduit.scheme_ts_flux; lpa_conduit_rl.inductance |
| `lpa_conduit_out` | `rc_block` | 1: lpa; 2: lpa_conduit | capacitance -> zero_capacitance; lpa_conduit_out.resistance |
| `right_lung` | `rcr_block` | 1: rpa; 2: atrial | pressure_mid = right_lung.pressure_mid; resistance_1 -> right_lung.resistance_1; resistance_2 -> right_lung.resistance_2; capacitance -> right_lung.capacitance |
| `left_lung` | `rcr_block` | 1: lpa; 2: atrial | pressure_mid = left_lung.pressure_mid; resistance_1 -> left_lung.resistance_1; resistance_2 -> left_lung.resistance_2; capacitance -> left_lung.capacitance |
| `fenestration` | `rc_block` | 1: atrial; 2: ivc | capacitance -> zero_capacitance; fenestration.resistance |

## Free Parameters

Unless a parameter states otherwise in the config, units follow the repository SI convention: pressure in $\mathrm{Pa}$, flow in $\mathrm{m^{3}\,s^{-1}}$, resistance in $\mathrm{Pa\,s\,m^{-3}}$, capacitance in $\mathrm{m^{3}\,Pa^{-1}}$, inertance in $\mathrm{Pa\,s^{2}\,m^{-3}}$, volume in $\mathrm{m^{3}}$, length in $\mathrm{m}$, and time in $\mathrm{s}$.

The entries below are the complete `parameters` dictionary from the authoritative baseline config. Derived-expression entries are shown as compact JSON.

- `aao_arch.resistance` = `2133152`
- `aao_compliance.capacitance` = `4.0003400289e-09`
- `active_atrium.activation_end` = `0.98`
- `active_atrium.activation_peak` = `0.9`
- `active_atrium.activation_start` = `0.78`
- `active_atrium.elastance_max` = `66661000`
- `active_atrium.elastance_min` = `16665250`
- `active_atrium.unstressed_volume` = `4e-05`
- `active_law.activation.max` = `35`
- `active_law.activation.min` = `-20`
- `aortic_arch_compliance.capacitance` = `5.00042503613e-09`
- `arch_bca.resistance` = `5332880`
- `arch_dao.resistance` = `19198368`
- `arch_lcca.resistance` = `7999320`
- `arch_lsa.resistance` = `7999320`
- `bca_compliance.capacitance` = `3.00025502168e-09`
- `capacitance_valve.capacitance` = `5e-12`
- `cavity.dynamics.damping_coef` = `70`
- `cavity.dynamics.hyperelastic_cst` = `[444.0,2.9,69.0,6.5]`
- `cavity.dynamics.vol_mass` = `1000`
- `cavity.rheology.active_law.activation` = `{"alpha":"diastole_scaling_factor","phases":[0,0,1,1,1,0,0],"reference_function":[[0.0,"active_law.activation.min"],[0.027,"active_law.activation.min"],[0.037,0.0],[0.145,"active_law.activation.max"],[0.309,"active_law.activation.max"],[0.417,0.0],[0.427,"active_law.activation.min"],[0.9,"active_law.activation.min"]],"rescaled_period":"heartbeat_duration","type":"rescale_two_phases_function"}`
- `cavity.rheology.active_law.crossbridge_stiffness` = `273000`
- `cavity.rheology.active_law.destruction_rate` = `12`
- `cavity.rheology.active_law.starling_abscissas` = `[-0.1668,-0.0073,0.0534,0.0969,0.1326,0.2016,0.4663,0.9187,1.1762]`
- `cavity.rheology.active_law.starling_ordinates` = `[0.0,0.5614,0.7748,0.8933,0.9618,1.0,1.0,0.1075,0.0]`
- `cavity.rheology.damping_parallel` = `70`
- `cavity.rheology.series_stiffness` = `100000000`
- `cavity.velocity_law.scheme_ts_hht` = `0.4`
- `conduit.scheme_ts_flux` = `0.25`
- `dao_compliance.capacitance` = `9.00076506503e-09`
- `diastole_scaling_factor` = `0.8`
- `fenestration.resistance` = `1.33322e+14`
- `heart_contractility` = `37800`
- `heart_radius` = `0.02431`
- `heart_rate` = `69.9300699301`
- `heart_thickness` = `0.0080795`
- `heartbeat_duration` = `{"factors":[60.0],"inverses":["heart_rate"],"type":"product"}`
- `ivc_compliance.capacitance` = `2.25019126626e-07`
- `ivc_conduit_compliance.capacitance` = `1.20010200867e-09`
- `ivc_conduit_junction.resistance` = `219981.3`
- `ivc_conduit_rl.backward_conductance` = `2.39254786418e-07`
- `ivc_conduit_rl.conductance` = `2.39254786418e-07`
- `ivc_conduit_rl.inductance` = `80000`
- `lcca_compliance.capacitance` = `1.50012751084e-09`
- `left_lung.capacitance` = `3.00025502168e-08`
- `left_lung.resistance_1` = `8319292.8`
- `left_lung.resistance_2` = `12478939.2`
- `lower_ca2.capacitance` = `2.50021251806e-08`
- `lower_cv2.capacitance` = `9.00076506503e-08`
- `lower_ra4.resistance` = `43196328`
- `lower_rc2.resistance` = `140388066`
- `lower_rv2.resistance` = `32397246`
- `lpa_compliance.capacitance` = `1.12509563313e-08`
- `lpa_conduit_compliance.capacitance` = `1.20010200867e-09`
- `lpa_conduit_out.resistance` = `173318.6`
- `lpa_conduit_rl.backward_conductance` = `3.03669536607e-07`
- `lpa_conduit_rl.conductance` = `3.03669536607e-07`
- `lpa_conduit_rl.inductance` = `60000`
- `lsa_compliance.capacitance` = `1.50012751084e-09`
- `pleural.pressure` = `0`
- `right_lung.capacitance` = `3.00025502168e-08`
- `right_lung.resistance_1` = `5759510.4`
- `right_lung.resistance_2` = `8639265.6`
- `rpa_compliance.capacitance` = `1.12509563313e-08`
- `rpa_conduit_compliance.capacitance` = `1.20010200867e-09`
- `rpa_conduit_out.resistance` = `119989.8`
- `rpa_conduit_rl.backward_conductance` = `4.38633775099e-07`
- `rpa_conduit_rl.conductance` = `4.38633775099e-07`
- `rpa_conduit_rl.inductance` = `60000`
- `svc_compliance.capacitance` = `1.50012751084e-07`
- `svc_conduit_compliance.capacitance` = `1.20010200867e-09`
- `svc_conduit_junction.resistance` = `293308.4`
- `svc_conduit_rl.backward_conductance` = `1.79441089813e-07`
- `svc_conduit_rl.conductance` = `1.79441089813e-07`
- `svc_conduit_rl.inductance` = `80000`
- `tcpc_compliance.capacitance` = `1.20010200867e-09`
- `upper_bca_to_ca1.resistance` = `49595784`
- `upper_ca1.capacitance` = `1.50012751084e-08`
- `upper_cv1.capacitance` = `6.00051004335e-08`
- `upper_lcca_to_ca1.resistance` = `99458212`
- `upper_lsa_to_ca1.resistance` = `99458212`
- `upper_rc1.resistance` = `156439020.571`
- `upper_rv1.resistance` = `67045294.5306`
- `valve_arterial.conductance` = `1.3e-05`
- `valve_arterial.inductance` = `30000`
- `valve_arterial.scheme_ts_flux` = `0.25`
- `valve_atrium.conductance` = `9e-06`
- `valve_atrium.inductance` = `1000`
- `valve_atrium.scheme_ts_flux` = `0.25`
- `valves.backward_conductance` = `5e-12`
- `zero_capacitance` = `0`

## Documentation and Regeneration

Model-local documentation artifacts:

- `models/full_0d/README.md`
- `models/full_0d/docs/full_0d_schematic.svg`
- `models/full_0d/docs/full_0d_schematic.png`
- `models/full_0d/docs/implementation_notes.md`
- `models/full_0d/docs/full_0d_technical_reference.md`
- `models/full_0d/docs/full_0d_technical_reference.pdf`

Regenerate the technical reference source and PDF with:

```bash
python3 scripts/docs/build_model_reference_pdfs.py --model full_0d
```

## Current Limitations

- The model is a calibrated computational development artifact, not a clinically validated patient-specific simulator.
- The aortic and Fontan pathways are lumped 0-D approximations rather than true spatially resolved 1-D domains.
- Scenario files inherit the baseline calibration and are validation cases, not independently retuned models.

The model parameters and standardized data are for computational development and calibration workflows. Simulation outputs must not be presented as clinically validated without separate validation and documentation.
