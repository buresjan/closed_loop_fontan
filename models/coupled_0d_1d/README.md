# Coupled 0-D/1-D Fontan Model

Status: executable Task 012 prototype, not an accepted calibrated model.

This model family contains the true coupled 0-D/1-D development path. It keeps
the closed-loop 0-D heart, atrium, valves, systemic beds, pulmonary RCR beds,
and fenestration from `models/full_0d`, while replacing the aortic and TCPC
shortcut pathways with local true 1-D finite-volume vessel blocks.

The current Task 012 prototype is scientifically useful as an executable
integration model, but it is not ready for calibration or promotion. The smoke
case completes with no NaNs, no negative saved 1-D vessel areas, near-zero
mass residuals at both total-pressure junctions, and passing TCPC balance after
replacing the artificial LPA pressure junction with a tapered composite LPA and
replacing the unstable no-loss TCPC closure with a wall-pressure-blended
dissipative total-pressure junction. It still does not demonstrate periodic
atrium or ventricle balance.

## Implemented Topology

Generated closed-loop configs are built by:

```bash
python3 scripts/modeling/build_coupled_configs.py
python3 scripts/modeling/build_coupled_configs.py --check
```

The generated configs are:

```text
models/coupled_0d_1d/configs/fontan_coupled_0d_1d_smoke.jsonc
models/coupled_0d_1d/configs/fontan_coupled_0d_1d_baseline.jsonc
models/coupled_0d_1d/configs/fontan_coupled_0d_1d_vasodilation.jsonc
models/coupled_0d_1d/configs/fontan_coupled_0d_1d_fenestration.jsonc
models/coupled_0d_1d/configs/fontan_coupled_0d_1d_lpa_obstruction.jsonc
```

The aorta uses four true 1-D segments derived from the Task 011 open-loop
geometry:

```text
coupled_aao       aao -> coupled_aao_arch
coupled_dao       coupled_dao_arch -> coupled_dao_out
coupled_bca       coupled_bca_arch -> coupled_bca_out
coupled_lcca      coupled_lcca_arch -> coupled_lcca_out
```

The arch split is `coupled_aortic_arch_junction`, a massless total-pressure
junction. It does not fabricate a 1-D LSA segment because that branch is absent
from the patient-specific aorta geometry table. It does retain the calibrated
full 0-D LSA terminal branch as a non-1-D aortic outlet, preserving the closed
loop upper-systemic pathway and aortic mass balance. Residual interface loss
blocks preserve the full 0-D path resistance not represented by 1-D
Poiseuille friction.

The TCPC pathway uses SVC, IVC, and RPA three-cell true 1-D segments plus one
six-cell tapered true 1-D LPA composite:

```text
coupled_svc       svc -> coupled_svc_tcpc
coupled_ivc       ivc -> coupled_ivc_tcpc
coupled_rpa       coupled_rpa_tcpc -> rpa
coupled_lpa       coupled_lpa_tcpc -> lpa
```

The TCPC junction is represented by `coupled_tcpc_junction`, a massless
four-port wall-pressure-blended dissipative total-pressure junction with
explicit SVC, IVC, RPA, and LPA branch flow states. The generated configs use
`wall_pressure_weight = 0.75`, `loss_coefficient = 2.0`, and
`characteristic_scale = 0.0`. This is closer to the branch-wall information
used by the paper's 1-D coupling than the previous finite-storage star or the
old node-pressure/no-loss TCPC closure, but it is still not a 3-D TCPC loss
model or a full characteristic/Riemann solver.

## Numerical State

Task 010 introduced `fixed_3cell_1d_vessel_block`, a local true 1-D vessel
kernel with three finite-volume area cells and four staggered flow faces. Task
012 keeps that equation set but uses `fixed_3cell_1d_log_area_vessel_block` in
the executable closed-loop configs. The state variable is `g_i = log(A_i)`, so
the area used by the wall law is always `A_i = exp(g_i)`.

This is a numerical parameterization of the same 1-D conservation equations,
not a quasi R-L-C chain.

All generated coupled scenarios cap `time.step_size` at `0.00025 s` and
`time.min_step` at `1.5625e-05 s`. The inherited full 0-D `0.002 s` baseline
step is too coarse for the inserted 1-D vessel and TCPC junction dynamics.

## Current Validation

Smoke command:

```bash
python3 scripts/run_one.py models/coupled_0d_1d/configs/fontan_coupled_0d_1d_smoke.jsonc --series CoupledSmoke
python3 scripts/metrics.py runs/simulations/CoupledSmoke/jb-work-laptop_CoupledSmoke_27/main.csv models/coupled_0d_1d/configs/fontan_coupled_0d_1d_smoke.jsonc --out models/coupled_0d_1d/reference_outputs/smoke_metrics.json
```

Current smoke result:

- launcher completed the 0.025 s startup smoke case;
- `pass_no_nan = true`;
- `pass_no_negative_coupled_1d_area = true`;
- `min_coupled_1d_area_m2 = 3.164382370839029e-05`;
- `pass_tcpc_balance = true`;
- `tcpc_cycle_balance_rel = 4.561452548443195e-05`;
- `tcpc_junction_cycle_balance_rel = 8.791954161051276e-17`;
- `max_abs_coupled_aortic_arch_junction_mass_balance_ml_s = 2.676624113323589e-13`;
- `max_abs_coupled_tcpc_junction_mass_balance_ml_s = 6.776263578034403e-14`;
- `mean_coupled_aortic_arch_junction_total_pressure_spread_mmHg = 2.030236239616579`;
- `mean_coupled_tcpc_junction_total_pressure_spread_mmHg = 0.3591252553625026`;
- TCPC terminal pressures remain bounded in the smoke window
  (`coupled_svc_tcpc`, `coupled_ivc_tcpc`, `coupled_rpa_tcpc`, and
  `coupled_lpa_tcpc` all stay between about 4.7 and 7.1 mmHg);
- `pass_atrium_balance = false`;
- `pass_ventricle_balance = false`;
- periodic closed-loop behavior has not been demonstrated.

Detailed metrics are tracked in:

```text
models/coupled_0d_1d/reference_outputs/smoke_metrics.json
models/coupled_0d_1d/reference_outputs/closed_loop_smoke_validation.json
```

A 2.0 s baseline-derived diagnostic with the generated coupled time-step cap
also completes:

- `pass_no_nan = true`;
- `negative_coupled_1d_area_count = 0`;
- `pass_tcpc_balance = true`;
- `tcpc_cycle_balance_rel = 0.00019884697373250603`;
- `max_coupled_tcpc_junction_total_pressure_spread_mmHg = 0.3590602843576907`;
- TCPC terminal pressures remain bounded between about 5.37 and 7.56 mmHg;
- `pass_atrium_balance = false`;
- `pass_ventricle_balance = false`;
- `periodicity_cavity_volume = 0.3065542811928496`.

## Reference Files

Open-loop reference specs from Task 011 remain tracked:

```text
models/coupled_0d_1d/configs/submodel_aorta_1d_openloop.jsonc
models/coupled_0d_1d/configs/submodel_tcpc_1d_openloop.jsonc
models/coupled_0d_1d/configs/submodel_aorta_tcpc_1d_openloop.jsonc
models/coupled_0d_1d/calibration/one_d_openloop_geometry.json
models/coupled_0d_1d/reference_outputs/openloop_1d_validation.json
```

Documentation artifacts:

```text
models/coupled_0d_1d/docs/coupled_0d_1d_schematic.svg
models/coupled_0d_1d/docs/coupled_0d_1d_schematic.png
models/coupled_0d_1d/docs/physioblocks_feasibility.md
models/coupled_0d_1d/docs/one_d_numerics.md
models/coupled_0d_1d/docs/openloop_1d_submodels.md
models/coupled_0d_1d/docs/implementation_notes.md
models/coupled_0d_1d/docs/coupled_0d_1d_technical_reference.md
models/coupled_0d_1d/docs/coupled_0d_1d_technical_reference.pdf
```

## Current Limitations

- The coupled model is executable but not accepted as periodic, calibrated, or
  superior to either standardized 0-D-family model.
- The aortic junction enforces mass conservation and no-loss total-pressure
  compatibility. The TCPC junction uses branch wall-pressure blending and
  signed dynamic minor losses, but not the full characteristic/Riemann coupling
  used by Nektar.
- The LSA pathway is retained as a calibrated 0-D terminal outlet because the
  extracted patient-specific aortic 1-D geometry does not include an LSA
  segment.
- The smoke run is a startup integration test; it is not a physiological cycle
  validation.
- Task 013 must not proceed as calibration until periodic atrium and ventricle
  balance are demonstrated or the roadmap is explicitly re-scoped.

The model parameters and outputs are for computational development only and are
not clinically validated.
