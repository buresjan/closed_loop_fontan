# Implementation and calibration plans for the current Fontan repository

This plan assumes the current repository structure in `current_code.zip`:

```text
fontan_blocks/
  active_atrium.py
models/
  full_0d/
  quasi_0d_1d/
  coupled_0d_1d/
scripts/
  run_one.py
  metrics.py
  compare_scenarios.py
  data/prepare_aramburu_2024.py
data/processed/aramburu_2024/
```

The current `models/full_0d` implementation already has an active atrium, PhysioBlocks spherical ventricle, aortic tree, upper/lower vascular beds, RCR pulmonary beds, TCPC conduit states, fenestration, reference outputs, and static tests. The two future model families should be implemented as separate model variants, not by overwriting `models/full_0d`.

---

## 1. Quasi 0-D/1-D implementation plan

### Purpose

Create a PhysioBlocks-only model that remains lumped/ODE-based, but represents the aorta and Fontan vessels as distributed R-L-C chains. This is not a true 1-D blood-flow PDE model. It is a quasi-1-D / transmission-line surrogate.

### Repository placement

Add:

```text
fontan_blocks/lumped.py
fontan_blocks/quasi_vessels.py          # optional helpers if using composite blocks
models/quasi_0d_1d/configs/
  fontan_quasi_smoke.jsonc
  fontan_quasi_baseline.jsonc
  fontan_quasi_vasodilation.jsonc
  fontan_quasi_fenestration.jsonc
  fontan_quasi_lpa_obstruction.jsonc
models/quasi_0d_1d/docs/
  schematic.svg
  implementation_notes.md
models/quasi_0d_1d/reference_outputs/
models/quasi_0d_1d/calibration/
  parameter_priors.yaml
  parameter_bounds.yaml
  target_weights.yaml
scripts/modeling/derive_quasi_vessel_parameters.py
scripts/modeling/build_quasi_configs.py        # optional but strongly recommended
```

Update:

```text
fontan_blocks/__init__.py
models/quasi_0d_1d/README.md
scripts/metrics.py
scripts/compare_scenarios.py or a model-family-aware replacement
pytest tests
```

### Custom blocks to add

#### `hydraulic_resistor_block`

Purpose: replace `rc_block` with `zero_capacitance = 0`.

Equation for physical orientation node 1 -> node 2:

```text
Q = (P1 - P2) / R
node 1 flux = -Q
node 2 flux = +Q
```

This removes the current resistor workaround.

#### `hydraulic_rl_block`

Purpose: replace `valve_rl_block` used as a bidirectional conduit.

Equation:

```text
L dQ/dt + R Q = P1 - P2
node 1 flux = -Q
node 2 flux = +Q
```

It must be symmetric and bidirectional, with no valve/diode behavior.

#### Optional `linear_rcl_vessel_chain_block`

Two implementation options are acceptable:

Option A, preferred for transparency: build chains directly in JSON using repeated `hydraulic_rl_block` plus `c_block` nodes.

```text
node_in -> RL segment -> internal_C_1 -> RL segment -> internal_C_2 -> ... -> node_out
```

Option B: one composite block with internal pressure/flow states.

For this repo, Option A is easier to inspect, test, and draw in schematics.

### Topology conversion from full 0-D

Start from `models/full_0d/configs/fontan_0d_baseline.jsonc` and keep unchanged:

```text
active_atrium
valve_atrium
spherical_cavity_block
valve_arterial
upper/lower vascular beds
pulmonary RCR beds
fenestration
```

Replace these full-0D pieces:

```text
aao_arch rc_block
arch_dao rc_block
svc_conduit_rl + svc_conduit_junction
ivc_conduit_rl + ivc_conduit_junction
rpa_conduit_rl + rpa_conduit_out
lpa_conduit_rl + lpa_conduit_out
```

with quasi vessel chains:

```text
AAo -> quasi_AAo/arch chain -> aortic_arch
aortic_arch -> quasi_DAo chain -> dao
SVC -> quasi_SVC chain -> TCPC
IVC -> quasi_IVC chain -> TCPC
TCPC -> quasi_RPA chain -> RPA
TCPC -> quasi_LPA chain -> LPA
```

Optionally also represent BCA/LCCA/LSA as short quasi chains; for the first release keep them as resistive branches feeding the upper systemic bed.

### Parameter derivation

Use files already processed by the repo:

```text
data/processed/aramburu_2024/model_inputs/aorta_geometry.csv
data/processed/aramburu_2024/model_inputs/fontan_cross_geometry.csv
```

For each vessel segment derive first guesses:

```text
Abar = average cross-sectional area from inlet/outlet radius
Lhyd = rho * length / Abar
Ctot = Abar * length / (rho * c^2)
Rtot = geometry/friction estimate or inherited/calibrated total vessel resistance
```

Recommended constants:

```text
rho = 1060 kg/m^3
mu  = 0.0035 Pa*s
```

Use paper-informed wave speeds as priors:

```text
aortic wave speed: ~5.35 m/s
Fontan/TCPC wave speed: ~2.81 m/s
```

For a chain with `N` segments:

```text
R_i = Rtot / N
L_i = Lhyd / N
C_i = Ctot / N or Ctot / (N-1), depending on node placement
```

Recommended first segment counts:

```text
AAo/arch: 3-5 segments
DAo: 5-8 segments
SVC: 2-3 segments
IVC: 4-6 segments
RPA: 2-3 segments
LPA: 3-5 segments, including a separate narrowed LPA segment
```

### Scenario configs

Create the same scenarios as full 0-D:

```text
baseline
25% pulmonary vasodilation
fenestration
LPA obstruction
smoke
```

The scenario changes should be applied by modifying the same physiological features:

```text
vasodilation: scale right/left pulmonary RCR resistances by 0.75
fenestration: lower fenestration resistance
LPA obstruction: increase LPA quasi-chain resistance / reduce conductance-equivalent / reduce compliance if modeling narrowing
```

### Metrics updates

`scripts/metrics.py` should become model-family aware. It should support:

```text
full_0d conduit flow names
quasi vessel inlet/outlet flows
quasi internal segment flows
```

Add standardized outputs:

```text
mean_<vessel>_inlet_flow_ml_s
mean_<vessel>_outlet_flow_ml_s
integral_<vessel>_inlet_flow_ml
integral_<vessel>_outlet_flow_ml
<vessel>_cycle_storage_ml
<vessel>_mass_balance_rel
```

Keep the existing clinical metrics:

```text
EDV, ESV, SV, CO
mean AAo/arch/DAo/SVC/IVC/RPA/LPA/atrium/TCPC pressures
RPA/LPA flow split
fenestration flow
cycle balance and periodicity
```

### Tests and acceptance checks

Add tests:

```text
tests/test_lumped_blocks.py
tests/test_quasi_topology.py
tests/test_quasi_parameter_derivation.py
tests/test_quasi_metrics.py
```

Checks:

```text
hydraulic_resistor gives Q = (P1-P2)/R
hydraulic_rl gives stable bidirectional inertial flow
no valve_rl_block is used as a conduit in quasi configs
R-L-C chains preserve intended total R, L, C
smoke case runs
baseline reaches periodic state
TCPC mass balance passes
atrium and ventricle balance pass
scenario directions are correct
```

Recommended acceptance thresholds:

```text
cycle-integrated mass-balance errors < 1e-2 initially, < 1e-3 after tuning
last-cycle ventricular periodicity < 1-2%
no NaN/Inf
no solver overflow warnings in accepted reference runs
```

---

## 2. Fully coupled 0-D/1-D implementation plan

### Purpose

Create the true nonlinear 0-D/1-D model family. Here the aorta and TCPC pathways are modeled by real nonlinear 1-D blood-flow equations, while the heart, atrium, valves, systemic beds, pulmonary Windkessels, and fenestration remain 0-D PhysioBlocks components.

This is the model closest in spirit to the paper. It should not reuse the quasi R-L-C chain as the final 1-D solver.

### Repository placement

Add:

```text
fontan_blocks/one_d.py
fontan_blocks/one_d_geometry.py
fontan_blocks/one_d_wall_laws.py
fontan_blocks/one_d_junctions.py
models/coupled_0d_1d/configs/
  submodel_aorta_1d_openloop.jsonc
  submodel_tcpc_1d_openloop.jsonc
  submodel_aorta_tcpc_1d_openloop.jsonc
  fontan_coupled_0d_1d_smoke.jsonc
  fontan_coupled_0d_1d_baseline.jsonc
  fontan_coupled_0d_1d_vasodilation.jsonc
  fontan_coupled_0d_1d_fenestration.jsonc
  fontan_coupled_0d_1d_lpa_obstruction.jsonc
models/coupled_0d_1d/docs/
  schematic.svg
  implementation_notes.md
models/coupled_0d_1d/reference_outputs/
models/coupled_0d_1d/calibration/
  one_d_geometry.yaml
  parameter_priors.yaml
  parameter_bounds.yaml
  target_weights.yaml
scripts/modeling/derive_1d_geometry.py
scripts/calibration/validate_1d_submodels.py
```

Update:

```text
fontan_blocks/__init__.py
models/coupled_0d_1d/README.md
scripts/metrics.py
pytest tests
```

### Native nonlinear 1-D vessel block

Add `nonlinear_vessel_1d_block`.

Each vessel has internal states such as:

```text
A_i(t): cross-sectional area in each cell
Q_i(t): flow in each cell or face
P_i(t): pressure from wall law
```

Core equations:

```text
dA/dt + dQ/dx = 0

dQ/dt + d(alpha Q^2/A)/dx + A/rho * dP/dx = friction/loss
```

Wall law:

```text
P - P_ext = f(A, A0, beta)
```

A simple first wall law is sufficient initially:

```text
P - P_ext = beta * (sqrt(A) - sqrt(A0))
```

or a wave-speed-equivalent form derived from the paper geometry/wave-speed data.

Each vessel block should support:

```text
length
number_of_cells
rho
mu
alpha
A0(x) from tapered inlet/outlet radii
beta(x) or wave_speed(x)
external_pressure
initial A/Q
```

### Boundary coupling to PhysioBlocks

Externally, each 1-D vessel connects to two PhysioBlocks pressure nodes:

```text
node 1: inlet-side pressure DOF
node 2: outlet-side pressure DOF
```

The block contributes the corresponding port fluxes:

```text
node 1 flux = -Q_in
node 2 flux = +Q_out
```

Boundary conditions must not naively prescribe both pressure and flow. Implement a stable implicit or characteristic-consistent boundary formulation. Initial acceptable approach:

```text
use node pressure to set boundary pressure through the wall law
use one incoming characteristic / ghost state to solve boundary flow
return boundary flow to the 0-D node balance
```

This must be validated on isolated vessels before closed-loop use.

### 1-D aorta network

Use:

```text
data/processed/aramburu_2024/model_inputs/aorta_geometry.csv
```

Segments:

```text
Ascending aorta
Thoracic/descending aorta
Brachiocephalic
Left carotid
```

The processed geometry does not include a normal LSA in the patient-specific table. For paper matching, do not force a normal LSA branch into the coupled 1-D aorta unless creating a separate idealized-anatomy variant.

Network topology:

```text
Ao valve / 0-D heart -> 1-D ascending aorta -> aortic junction
                                          |-> 1-D BCA -> upper bed
                                          |-> 1-D LCCA -> upper bed
                                          |-> 1-D DAo -> lower bed
```

### 1-D TCPC network

Use:

```text
data/processed/aramburu_2024/model_inputs/fontan_cross_geometry.csv
```

Segments:

```text
IVC
SVC
RPA
LPA I
LPA II / narrowed LPA segment
additional outlet segment if present in geometry table
```

Network topology:

```text
upper venous bed -> SVC 1-D vessel -> TCPC junction
lower venous bed -> IVC 1-D vessel -> TCPC junction
TCPC junction -> RPA 1-D vessel -> right pulmonary Windkessel
TCPC junction -> LPA I + LPA II 1-D vessels -> left pulmonary Windkessel
```

Represent the TCPC junction initially as a 1-D network junction enforcing:

```text
mass conservation
pressure/total-pressure compatibility
optional empirical loss coefficient
```

Later, this junction can be replaced by a CFD-derived four-port TCPC surrogate, while keeping the SVC/IVC/RPA/LPA 1-D vessels.

### Development order

Do not implement the full closed loop first.

1. Implement and unit-test wall law and vessel residuals.
2. Implement one straight vessel with fixed pressure/flow test cases.
3. Validate single-vessel mass conservation and wave speed.
4. Build `submodel_aorta_1d_openloop.jsonc`.
5. Build `submodel_tcpc_1d_openloop.jsonc`.
6. Build `submodel_aorta_tcpc_1d_openloop.jsonc`.
7. Only then build the closed-loop config.
8. Add intervention scenario configs.

### Validation data for 1-D implementation

Use the processed Aramburu data:

```text
data/processed/aramburu_2024/comparison/measurements_last_cycle_clinical.csv
data/processed/aramburu_2024/comparison/03_aorta_tcpc_1d_last_cycle_clinical.csv
data/processed/aramburu_2024/comparison/04_aorta_tcpc_closedloop_1d_last_cycle_clinical.csv
data/processed/aramburu_2024/nektar_1d/01_aorta/*.csv.gz
data/processed/aramburu_2024/nektar_1d/02_tcpc/*.csv.gz
data/processed/aramburu_2024/nektar_1d/03_aorta_tcpc/*.csv.gz
data/processed/aramburu_2024/nektar_1d/04_aorta_tcpc_closedloop/*.csv.gz
```

### Numerical checks

For each 1-D vessel or network:

```text
same pressure both ends -> no drift / near-zero flow
steady pressure drop -> plausible steady flow
pulse propagation speed matches target wave speed
grid refinement changes outputs modestly
no negative A
volume conservation: inlet - outlet = d(stored volume)/dt
boundary pressure/flow signs match PhysioBlocks metrics
```

For the closed loop:

```text
no NaN/Inf
no negative vessel area
periodic steady state after sufficient cycles
TCPC mass balance passes
heart/atrium/ventricle balance passes
baseline reproduces patient data
scenario directions match paper scenarios
```

---

## 3. Calibration plan for all three models

### Shared calibration principles

Use measurements for calibration, paper model outputs for comparison/validation, and Nektar 1-D outputs for 1-D solver validation.

Primary data files:

```text
data/processed/aramburu_2024/measurements_clinical.csv
data/processed/aramburu_2024/measurements.csv
data/processed/aramburu_2024/comparison/measurements_last_cycle_clinical.csv
data/processed/aramburu_2024/paper_results/model.csv
data/processed/aramburu_2024/paper_results/submodel1.csv
...
data/processed/aramburu_2024/model_inputs/aorta_geometry.csv
data/processed/aramburu_2024/model_inputs/fontan_cross_geometry.csv
data/processed/aramburu_2024/nektar_1d/*
```

Create calibration support files:

```text
scripts/calibration/extract_targets.py
scripts/calibration/objective.py
scripts/calibration/run_calibration.py
scripts/calibration/plot_calibration.py
scripts/calibration/compare_to_paper.py
models/<family>/calibration/parameter_priors.yaml
models/<family>/calibration/parameter_bounds.yaml
models/<family>/calibration/target_weights.yaml
models/<family>/calibration/calibration_report.md
```

The objective should include:

```text
J = J_summary + J_waveform + J_prior + J_penalty
```

where:

```text
J_summary  = normalized errors in mean pressures, flows, EDV, ESV, SV, CO
J_waveform = waveform NRMSE/RPPE on phase-aligned last-cycle curves
J_prior    = penalty for moving too far from data/paper priors
J_penalty  = large penalty for failed runs, mass-balance failure, non-periodicity, negative A, NaN/Inf
```

Use scale factors, not hundreds of independent raw parameters.

Good optimizer sequence:

```text
manual coarse tuning -> Powell/Nelder-Mead -> bounded least-squares or CMA-ES for final tuning
```

Do not tune intervention scenarios. Tune baseline only, then validate on:

```text
25% pulmonary vasodilation
fenestration
LPA obstruction / LPA narrowing
```

### Shared target quantities

For all three levels, the baseline summary targets are:

```text
heart_rate
EDV, ESV, SV, CO
mean ascending aorta pressure
mean arch pressure
mean descending aorta pressure
mean SVC pressure
mean IVC pressure
mean RPA pressure
mean LPA pressure
wedge/atrial pressure proxy
ascending aorta flow per beat
DAo flow per beat
SVC flow per beat
IVC flow per beat
RPA flow per beat
LPA flow per beat
RPA/LPA flow fraction
```

Use `measurements_last_cycle_clinical.csv` for the measurement waveforms and summary values. Use `paper_results/model.csv` and `comparison/04_aorta_tcpc_closedloop_1d_last_cycle_clinical.csv` to compare against the published model behavior.

---

### 3.1 Full 0-D calibration

#### Goal

Match patient-level closed-loop means and volumes. Do not try to match detailed wave propagation.

#### Calibrate these groups

1. Heart and valves:

```text
heart_radius
heart_thickness
heart_contractility
cavity passive hyperelastic constants / scale
valve_atrium conductance/inductance
valve_arterial conductance/inductance
```

Targets:

```text
EDV, ESV, SV, CO
ventricle peak pressure
ventricle end-diastolic pressure
PV loop shape roughly
```

2. Active atrium:

```text
active_atrium.elastance_min
active_atrium.elastance_max
active_atrium.unstressed_volume
activation_start/peak/end
```

Targets:

```text
wedge pressure / atrial pressure proxy
AV valve filling behavior
active_atrium volume range
```

3. Aortic/systemic side:

```text
aortic/aao/arch/dao compliance scale
upper branch resistance scale
lower branch resistance scale
upper_ca1, upper_cv1
lower_ca2, lower_cv2
upper_rc1, upper_rv1
lower_ra4, lower_rc2, lower_rv2
```

Targets:

```text
AAo/arch/DAo mean pressures
AAo and DAo flows
SVC/IVC flows
```

4. Fontan/TCPC/pulmonary side:

```text
SVC/IVC pathway resistance scale
RPA/LPA pathway resistance scale
LPA narrowing scale
TCPC compliance
SVC/IVC/RPA/LPA compliances
right_lung and left_lung total R
right/left lung Rprox/Rdist split
right/left lung compliance
```

Targets:

```text
SVC/IVC/RPA/LPA mean pressures
RPA/LPA flow split
wedge/atrial pressure
```

#### Calibration order

1. Set `heart_rate` from measured cycle length.
2. Tune heart against EDV/ESV/SV/ventricle pressure.
3. Tune systemic afterload to get AAo/arch/DAo pressures and CO.
4. Tune upper/lower vascular beds to match SVC/IVC flows and pressures.
5. Tune TCPC/pulmonary side to match RPA/LPA pressures and split.
6. Tune active atrium and pulmonary Windkessels to match wedge/atrium pressure.
7. Fine-tune with 8-12 scale factors only.
8. Validate scenarios without retuning.

#### Expected acceptance

```text
SV/CO errors < 5%
mean pressure/flow errors < 5-10%
RPA/LPA split close
periodicity < 1-2%
mass-balance errors < 1e-2, preferably < 1e-3
```

---

### 3.2 Quasi 0-D/1-D calibration

#### Goal

Retain the full 0-D calibrated physiology while improving impedance, inertance, distributed compliance, and waveform timing. This level should still be calibrated mainly to patient means, with waveform shape as a secondary target.

#### Starting point

Start from the calibrated full 0-D parameters. Convert vessel totals into R-L-C chains while preserving:

```text
total vessel resistance
total vessel compliance
patient geometry-derived inertance
```

#### Calibrate these groups

1. Quasi aortic chain:

```text
AAo/arch R scale
DAo R scale
AAo/arch C scale
DAo C scale
AAo/arch L scale or wave-speed scale
DAo L scale or wave-speed scale
```

Targets:

```text
AAo/arch/DAo mean pressures
AAo/DAo flows
pressure pulse amplitude
approximate pressure peak timing
```

2. Quasi TCPC/caval/pulmonary limbs:

```text
SVC R/L/C scale
IVC R/L/C scale
RPA R/L/C scale
LPA R/L/C scale
LPA narrowed-segment scale
TCPC junction compliance/loss scale
```

Targets:

```text
SVC/IVC/RPA/LPA pressures
SVC/IVC/RPA/LPA flows
RPA/LPA split
TCPC pressure
```

3. Global retuning:

```text
small heart contractility scale
small systemic resistance scale
small pulmonary resistance scale
active atrium pressure level
```

Keep these changes small compared with the full-0D calibration.

#### Data to use

```text
measurements_last_cycle_clinical.csv for direct measurement waveforms
model_inputs/aorta_geometry.csv for aortic R/L/C priors
model_inputs/fontan_cross_geometry.csv for Fontan limb R/L/C priors
paper_results/model.csv for paper model comparison
```

#### Calibration order

1. Derive quasi vessel R/L/C parameters from geometry.
2. Insert chains and run smoke.
3. Preserve full-0D mean outputs by scaling total R/C if necessary.
4. Tune aortic chains against AAo/arch/DAo waveform amplitude/timing.
5. Tune TCPC limb chains against SVC/IVC/RPA/LPA waveform amplitude/timing.
6. Retune RPA/LPA split and atrial pressure.
7. Validate scenarios.

#### Expected acceptance

```text
same summary accuracy as full 0-D, or only modestly worse
better waveform amplitude/timing than full 0-D
stable periodicity
no artificial ringing from too-large inertance
```

---

### 3.3 Fully coupled 0-D/1-D calibration

#### Goal

Calibrate a true nonlinear 1-D aorta and TCPC pathway coupled to the 0-D heart and vascular beds. This level should be judged on both summary metrics and waveform-level agreement.

#### Submodel calibration first

1. Aorta 1-D open-loop.

Use:

```text
model_inputs/aorta_geometry.csv
model_inputs/aorta_waves_clinical.csv
nektar_1d/01_aorta/*
comparison/measurements_last_cycle_clinical.csv
```

Prescribe measured ascending aortic inflow initially. Calibrate:

```text
wall stiffness / wave speed
friction scale
terminal upper/lower bed parameters
branch outlet parameters
```

Targets:

```text
AAo pressure
arch pressure
DAo pressure
DAo flow
Nektar aorta outputs
```

2. TCPC 1-D open-loop.

Use:

```text
model_inputs/fontan_cross_geometry.csv
model_inputs/fontan_cross_inflows_clinical.csv
nektar_1d/02_tcpc/*
comparison/measurements_last_cycle_clinical.csv
```

Prescribe measured SVC/IVC inflows initially. Calibrate:

```text
TCPC vessel stiffness/wave speed
friction scale
LPA narrowed segment resistance/stiffness
right/left pulmonary Windkessel total R and compliance
atrial/outlet pressure level
```

Targets:

```text
SVC/IVC/RPA/LPA pressures
RPA/LPA flows
RPA/LPA split
Nektar TCPC outputs
```

3. Aorta-TCPC open-loop.

Use:

```text
comparison/03_aorta_tcpc_1d_last_cycle_clinical.csv
nektar_1d/03_aorta_tcpc/*
fo_outputs/03_aorta_tcpc.csv
```

Calibrate coupling beds:

```text
upper body bed: Ca1, Rc1, Cv1, Rv1
lower body bed: Ca2, Rc2, Cv2, Rv2
```

Targets:

```text
AAo/arch/DAo pressures and DAo flow
SVC/IVC pressures and flows
RPA/LPA pressures and flows
```

4. Closed-loop 0-D/1-D.

Use:

```text
comparison/04_aorta_tcpc_closedloop_1d_last_cycle_clinical.csv
paper_results/model.csv
measurements_last_cycle_clinical.csv
```

Calibrate only small global scales:

```text
heart contractility/passive stiffness
active atrium pressure level
systemic resistance scale
pulmonary resistance scale
junction/loss scale
```

Do not freely retune 1-D geometry.

#### Main parameters to keep fixed or tightly bounded

```text
vessel lengths and radii from geometry CSVs
blood density and viscosity
segment connectivity
measured heart rate
```

#### Main parameters to optimize

```text
wave-speed/stiffness scale per vessel family
friction scale per vessel family
junction loss coefficient if used
terminal 0-D bed resistance/compliance scales
heart/atrium scales
LPA narrowing scale
```

#### Expected acceptance

```text
summary errors comparable to or better than quasi model
waveform RPPE improved over full 0-D and quasi model
1-D submodels reproduce Nektar outputs within set tolerance
no negative area
stable boundary coupling
scenario responses plausible and close to paper Table 4
```

---

## Immediate next tasks

1. Add clean `hydraulic_resistor_block` and `hydraulic_rl_block`.
2. Update `models/full_0d` to remove `rc_block`/`valve_rl_block` workarounds only if you want a cleaner full-0D baseline; otherwise keep full-0D frozen as the current reference variant.
3. Implement `models/quasi_0d_1d` first, because it exercises the same insertion points that the true 1-D model will need.
4. Build calibration target/weight files for `models/full_0d/calibration/` using the processed Aramburu data.
5. Calibrate full 0-D baseline before tuning quasi.
6. Use quasi calibration to decide which waveform targets actually justify true 1-D.
7. Implement true 1-D only after the quasi model and submodel target extraction are stable.
