# 012 - Build Coupled Closed-Loop 0-D/1-D Model

Status: completed

Depends on: Task 011

## Goal

Build the true coupled closed-loop model with 1-D aorta and TCPC pathways attached to the 0-D heart, atrium, valves, beds, pulmonary Windkessels, and fenestration.

## Implementation

- Start from the Task 011 open-loop reference specs:
  - `models/coupled_0d_1d/configs/submodel_aorta_1d_openloop.jsonc`
  - `models/coupled_0d_1d/configs/submodel_tcpc_1d_openloop.jsonc`
  - `models/coupled_0d_1d/configs/submodel_aorta_tcpc_1d_openloop.jsonc`
- Use `models/coupled_0d_1d/calibration/one_d_openloop_geometry.json` as the
  source of patient-specific segment geometry and Nektar domain mapping.
- Preserve the Task 011 geometry policy: do not invent a normal 1-D LSA
  segment, but retain the calibrated full 0-D LSA terminal pathway in the
  closed loop unless creating a separately documented idealized variant.
- Add configs:
  - `fontan_coupled_0d_1d_smoke.jsonc`
  - `fontan_coupled_0d_1d_baseline.jsonc`
  - `fontan_coupled_0d_1d_vasodilation.jsonc`
  - `fontan_coupled_0d_1d_fenestration.jsonc`
  - `fontan_coupled_0d_1d_lpa_obstruction.jsonc`
- Couple 1-D vessel ports to PhysioBlocks pressure nodes without prescribing both pressure and flow.
- Do not use measured open-loop pressure and measured open-loop flow
  simultaneously at the same coupled boundary to manufacture agreement.
- Implement the TCPC junction initially with mass conservation and pressure or total-pressure compatibility, with an optional loss coefficient.
- Update `models/coupled_0d_1d/README.md`, schematic SVG/PNG,
  `docs/implementation_notes.md`, and technical reference source/PDF in the
  same change.
- Extend metrics for 1-D vessel stored volume, inlet/outlet flow, negative area, and boundary sign diagnostics.

## Acceptance

- Coupled smoke case runs.
- Baseline can reach a periodic state after sufficient cycles.
- No NaN/Inf and no negative vessel area.
- TCPC, atrium, and ventricle mass-balance checks pass.
- README, schematic, implementation notes, and technical reference PDF/source
  match the implemented topology.

## Current Task 012 Result

Task 012 now has an executable generated closed-loop prototype with a stabilized
paper-aligned TCPC closure:

- `scripts/modeling/build_coupled_configs.py` generates the smoke, baseline,
  vasodilation, fenestration, and LPA obstruction coupled configs.
- The generated configs remove the full 0-D aortic and TCPC shortcut paths,
  insert seven three-cell true 1-D log-area vessel blocks, one six-cell tapered
  LPA composite block, one massless aortic total-pressure junction, one
  massless wall-pressure-blended dissipative TCPC total-pressure junction, and
  three downstream aortic residual interface loss blocks.
- The generated configs retain the calibrated full 0-D LSA terminal branch as
  a non-1-D aortic outlet because no patient-specific LSA 1-D geometry is
  available. This closes the aortic mass balance without fabricating an LSA
  vessel segment.
- The coupled executable uses `fixed_3cell_1d_log_area_vessel_block`, with
  `A = exp(g)` so saved vessel areas remain in the positive domain during the
  smoke run.
- All generated coupled scenarios cap `time.step_size` at `0.00025 s` and
  `time.min_step` at `1.5625e-05 s`. The inherited full 0-D `0.002 s` scenario
  step is too coarse for the inserted 1-D and TCPC dynamics and can make the
  first coupled nonlinear solve intractable.
- The aortic residual interface loss blocks preserve full 0-D path resistance
  not represented by 1-D Poiseuille friction.
- The aortic junction enforces no-loss total-pressure compatibility. The TCPC
  junction uses branch wall-pressure blending (`wall_pressure_weight = 0.75`)
  and signed dynamic minor losses (`loss_coefficient = 2.0`) while preserving
  algebraic mass conservation.
- `scripts/metrics.py` reports coupled 1-D inlet/outlet flows, stored volume,
  saved area minima/maxima, negative-area counts, junction mass residuals, and
  junction total-pressure spreads.

The short smoke case now reaches launcher completion:

```bash
python3 scripts/run_one.py models/coupled_0d_1d/configs/fontan_coupled_0d_1d_smoke.jsonc --series CoupledSmoke
python3 scripts/metrics.py runs/simulations/CoupledSmoke/jb-work-laptop_CoupledSmoke_27/main.csv models/coupled_0d_1d/configs/fontan_coupled_0d_1d_smoke.jsonc --out models/coupled_0d_1d/reference_outputs/smoke_metrics.json
```

Smoke metrics:

- `pass_no_nan = true`
- `pass_no_negative_coupled_1d_area = true`
- `negative_coupled_1d_area_count = 0`
- `min_coupled_1d_area_m2 = 3.164382370839029e-05`
- `pass_tcpc_balance = true`
- `tcpc_cycle_balance_rel = 4.561452548443195e-05`
- `tcpc_junction_cycle_balance_rel = 8.791954161051276e-17`
- `max_abs_coupled_aortic_arch_junction_mass_balance_ml_s = 2.676624113323589e-13`
- `max_abs_coupled_tcpc_junction_mass_balance_ml_s = 6.776263578034403e-14`
- `mean_coupled_aortic_arch_junction_total_pressure_spread_mmHg = 2.030236239616579`
- `mean_coupled_tcpc_junction_total_pressure_spread_mmHg = 0.3591252553625026`
- TCPC terminal pressures remain bounded in the smoke window:
  `5.91-7.02 mmHg` for SVC, `5.85-6.94 mmHg` for IVC,
  `4.68-6.89 mmHg` for RPA, and `4.77-6.89 mmHg` for LPA.
- `pass_atrium_balance = false`
- `pass_ventricle_balance = false`

Longer-run diagnostic commands:

```bash
jq '.time.duration = 2.0' models/coupled_0d_1d/configs/fontan_coupled_0d_1d_smoke.jsonc > runs/tmp/fontan_coupled_loss2_2p0.jsonc
python3 scripts/run_one.py runs/tmp/fontan_coupled_loss2_2p0.jsonc --series CoupledLoss2MultiCycle
python3 scripts/metrics.py runs/simulations/CoupledLoss2MultiCycle/jb-work-laptop_CoupledLoss2MultiCycle_1/main.csv runs/tmp/fontan_coupled_loss2_2p0.jsonc --out runs/tmp/coupled_loss2_2p0_metrics.json

jq '.time.duration = 2.0' models/coupled_0d_1d/configs/fontan_coupled_0d_1d_baseline.jsonc > runs/tmp/fontan_coupled_baseline_2p0.jsonc
python3 scripts/run_one.py runs/tmp/fontan_coupled_baseline_2p0.jsonc --series CoupledBaseline2s
python3 scripts/metrics.py runs/simulations/CoupledBaseline2s/jb-work-laptop_CoupledBaseline2s_1/main.csv runs/tmp/fontan_coupled_baseline_2p0.jsonc --out runs/tmp/coupled_baseline_2p0_metrics.json
```

Longer-run diagnostic findings for `loss_coefficient = 2.0`:

- the 2.0 s diagnostic reaches launcher completion;
- `pass_no_nan = true`;
- `negative_coupled_1d_area_count = 0`;
- `pass_tcpc_balance = true`;
- `tcpc_cycle_balance_rel = 0.00019884697373250603`;
- `max_abs_coupled_tcpc_junction_mass_balance_ml_s = 6.606856988583544e-13`;
- `max_coupled_tcpc_junction_total_pressure_spread_mmHg = 0.3590602843576907`;
- TCPC terminal pressures remain positive and bounded:
  SVC `5.91-7.47 mmHg`, IVC `5.85-7.51 mmHg`, RPA `4.27-7.55 mmHg`,
  and LPA `4.77-7.34 mmHg`.
- the baseline-derived 2.0 s diagnostic also reaches launcher completion with
  `pass_no_nan = true`, `negative_coupled_1d_area_count = 0`,
  `pass_tcpc_balance = true`, `tcpc_cycle_balance_rel = 0.00019884697373250603`,
  `max_coupled_tcpc_junction_total_pressure_spread_mmHg = 0.3590602843576907`,
  `pass_atrium_balance = false`, `pass_ventricle_balance = false`, and
  `periodicity_cavity_volume = 0.3065542811928496`.

Decision: the specific TCPC/SVC boundary-formulation instability is resolved by
the wall-pressure-blended dissipative TCPC closure. The generated 20 s baseline
now demonstrates periodic behavior and atrium/ventricle mass balance, so Task
012 is complete. Task 013 must not claim calibration success from the smoke,
2.0 s diagnostic, or uncalibrated 20 s baseline alone.

## Completion Notes

Completed on 2026-05-17.

The generated 20 s coupled baseline reached launcher completion:

```bash
python3 scripts/run_one.py models/coupled_0d_1d/configs/fontan_coupled_0d_1d_baseline.jsonc --series CoupledBaseline
python3 scripts/metrics.py runs/simulations/CoupledBaseline/jb-work-laptop_CoupledBaseline_2/main.csv runs/simulations/CoupledBaseline/jb-work-laptop_CoupledBaseline_2/fontan_coupled_0d_1d_baseline.jsonc --out runs/tmp/coupled_baseline_20s_metrics.json
cp runs/tmp/coupled_baseline_20s_metrics.json models/coupled_0d_1d/reference_outputs/baseline_20s_metrics.json
```

Key 20 s baseline metrics:

- `pass_no_nan = true`
- `pass_no_negative_coupled_1d_area = true`
- `negative_coupled_1d_area_count = 0`
- `pass_tcpc_balance = true`
- `pass_atrium_balance = true`
- `pass_ventricle_balance = true`
- `periodicity_cavity_volume = 0.00024257533848672484`
- `periodicity_valve_atrium.flux = 0.0008235401311557643`
- `periodicity_valve_arterial.flux = 0.0010911304978085486`
- `atrium_cycle_balance_rel = 3.9825278506877785e-06`
- `ventricle_cycle_balance_rel = 0.0003381919503314924`
- `tcpc_cycle_balance_rel = 9.1130746331995e-07`
- `CO_from_valve_arterial.flux_L_min = 2.546669507876757`
- `EDV_ml = 72.36704173216829`
- `ESV_ml = 35.906736876718135`
- `SV_from_volume_ml = 36.460304855450154`
- `mean_coupled_tcpc_junction_total_pressure_spread_mmHg = 0.35906016877211905`

This completes topology/stability acceptance for Task 012, not calibration or
scientific promotion. The accepted Task 012 output is an executable periodic
closed-loop coupled prototype ready for Task 013 calibration and validation.

## PhysioBlocks Impact

No immediate fork at task start. Tasks 009-011 selected and validated a local
fixed-size/generated path. Revisit PhysioBlocks internals only for a concrete
Task 012 blocker such as sparse Jacobian scaling, area positivity enforcement,
or boundary-condition control that cannot be handled locally.

The area-positivity blocker was handled locally with log-area 1-D blocks. The
artificial LPA-junction transient was handled locally with a tapered composite
LPA. The finite-storage TCPC star and shared aortic pressure node were replaced
with local total-pressure junction blocks. The periodic closed-loop behavior
and pump/atrium mass-balance blocker is resolved without a PhysioBlocks fork.
