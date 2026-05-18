# Coupled 0-D/1-D Fontan Model

## Status

Executable true 0-D/1-D development model. Task 012 demonstrated a stable,
periodic 20 s baseline run. Task 013 calibration and validation are in
progress, so this model is not yet an accepted calibrated model.

## Scientific Scope

This model keeps the accepted full 0-D heart, active atrium, valves, systemic
beds, pulmonary RCR beds, and fenestration. It replaces selected aortic and
TCPC shortcut pathways with local true 1-D finite-volume vessel blocks.

The current model is deliberately simpler than the paper's Nektar solver. It
uses fixed-size local PhysioBlocks-compatible 1-D blocks and algebraic
total-pressure junctions, not Nektar's high-order domains or full
characteristic/Riemann boundary treatment.

## Canonical Configs

| Config | Purpose |
|---|---|
| `fontan_coupled_0d_1d_smoke.jsonc` | Short startup smoke case. |
| `fontan_coupled_0d_1d_baseline.jsonc` | Baseline true 0-D/1-D case. |
| `fontan_coupled_0d_1d_vasodilation.jsonc` | Pulmonary vasodilation validation scenario. |
| `fontan_coupled_0d_1d_fenestration.jsonc` | Fenestration validation scenario. |
| `fontan_coupled_0d_1d_lpa_obstruction.jsonc` | LPA obstruction validation scenario. |

Open-loop reference specs:

```text
models/coupled_0d_1d/configs/submodel_aorta_1d_openloop.jsonc
models/coupled_0d_1d/configs/submodel_tcpc_1d_openloop.jsonc
models/coupled_0d_1d/configs/submodel_aorta_tcpc_1d_openloop.jsonc
```

## Topology Summary

The aorta uses four true 1-D blocks derived from Task 011 open-loop geometry:

```text
coupled_aao   : aao -> coupled_aao_arch
coupled_dao   : coupled_dao_arch -> coupled_dao_out
coupled_bca   : coupled_bca_arch -> coupled_bca_out
coupled_lcca  : coupled_lcca_arch -> coupled_lcca_out
```

The arch split is `coupled_aortic_arch_junction`, a massless no-loss
total-pressure junction. The calibrated full 0-D LSA terminal branch is
retained because no patient-specific LSA 1-D geometry is available.

The TCPC pathway uses SVC, IVC, RPA, and tapered composite LPA 1-D blocks:

```text
coupled_svc   : svc -> coupled_svc_tcpc
coupled_ivc   : ivc -> coupled_ivc_tcpc
coupled_rpa   : coupled_rpa_tcpc -> rpa
coupled_lpa   : coupled_lpa_tcpc -> lpa
```

The TCPC confluence is `coupled_tcpc_junction`, a massless
wall-pressure-blended dissipative total-pressure junction.

## Numerical Formulation

The executable closed-loop configs use log-area finite-volume vessel blocks.
The state is `g_i = log(A_i)` and the physical area is `A_i = exp(g_i)`, so
the nonlinear solve remains inside the positive-area domain.

The generated scenarios cap `time.step_size` at `0.00025 s` and `time.min_step`
at `1.5625e-05 s`. The inherited full 0-D `0.002 s` step is too coarse for the
inserted 1-D vessel and TCPC junction dynamics.

The TCPC junction currently uses:

```text
wall_pressure_weight = 0.75
loss_coefficient = 2.0
characteristic_scale = 0.0
```

## Parameter Sources and Calibration

Geometry and open-loop validation inputs are tracked in:

```text
models/coupled_0d_1d/calibration/one_d_openloop_geometry.json
models/coupled_0d_1d/reference_outputs/openloop_1d_validation.json
```

Task 013 candidate calibration is baseline-only. Intervention scenarios remain
validation cases and must not be retuned independently.

Current uncalibrated 20 s baseline comparison outputs:

```text
models/coupled_0d_1d/calibration/baseline_objective.json
models/coupled_0d_1d/calibration/baseline_vs_paper.json
models/coupled_0d_1d/calibration/baseline_vs_nektar_closed_loop.json
```

## Validation State

Task 012 20 s baseline metrics are tracked in:

```text
models/coupled_0d_1d/reference_outputs/baseline_20s_metrics.json
```

Key 20 s baseline results:

| Gate or quantity | Result |
|---|---:|
| No NaNs | pass |
| Negative coupled 1-D areas | 0 |
| TCPC balance | pass |
| Atrium balance | pass |
| Ventricle balance | pass |
| Cavity-volume periodicity | 0.000243 |
| CO | 2.55 L/min |
| SV | 36.46 ml |
| Mean AAo pressure | 47.45 mmHg |
| Mean SVC/IVC pressure | 8.74 / 8.72 mmHg |
| Mean RPA/LPA pressure | 8.21 / 7.73 mmHg |

The uncalibrated coupled baseline is stable and periodic, but it is not yet
accepted. Its direct clinical summary score remains worse than the accepted
full 0-D and quasi 0-D/1-D references, while its paper/Nektar summary score is
already competitive.

## Run Commands

Regenerate and check executable configs:

```bash
python3 scripts/modeling/build_coupled_configs.py
python3 scripts/modeling/build_coupled_configs.py --check
```

Run the smoke case:

```bash
python3 scripts/run_one.py models/coupled_0d_1d/configs/fontan_coupled_0d_1d_smoke.jsonc --series CoupledSmoke
```

Compute metrics from a completed run:

```bash
python3 scripts/metrics.py runs/simulations/CoupledSmoke/*/main.csv models/coupled_0d_1d/configs/fontan_coupled_0d_1d_smoke.jsonc --out models/coupled_0d_1d/reference_outputs/smoke_metrics.json
```

## Reference Outputs

```text
models/coupled_0d_1d/reference_outputs/openloop_1d_validation.json
models/coupled_0d_1d/reference_outputs/closed_loop_smoke_validation.json
models/coupled_0d_1d/reference_outputs/smoke_metrics.json
models/coupled_0d_1d/reference_outputs/baseline_20s_metrics.json
```

## Known Limitations

- The model is executable and periodic at baseline, but not yet calibrated or
  accepted.
- The aortic junction is an algebraic no-loss total-pressure coupler.
- The TCPC junction uses branch wall-pressure blending and signed dynamic minor
  losses, not Nektar's full characteristic/Riemann coupling or a 3-D TCPC loss
  model.
- The LSA pathway remains a calibrated 0-D terminal outlet because extracted
  patient-specific aortic 1-D geometry does not include an LSA segment.
- The model is not clinically validated.

## Documentation Regeneration

Required model-local documentation:

```text
models/coupled_0d_1d/docs/coupled_0d_1d_schematic.svg
models/coupled_0d_1d/docs/coupled_0d_1d_schematic.png
models/coupled_0d_1d/docs/implementation_notes.md
models/coupled_0d_1d/docs/coupled_0d_1d_technical_reference.md
models/coupled_0d_1d/docs/coupled_0d_1d_technical_reference.pdf
```

Regenerate the long-form technical reference after topology or parameter
changes:

```bash
python3 scripts/docs/build_model_reference_pdfs.py --model coupled_0d_1d
python3 scripts/docs/check_model_docs.py --model coupled_0d_1d
```
