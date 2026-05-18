# Full 0-D Closed-Loop Fontan Model

## Status

Accepted go-to full 0-D reference model.

This model is the repository's frozen full 0-D comparison reference. Keep its
topology, scenario set, schematic, calibration outputs, and reference metrics
stable unless a deliberate new reference decision is recorded.

## Reference policy

This section is retained as a stable test/documentation anchor. The accepted
full 0-D model is the reference for later model-family comparisons. Changes
that alter topology, parameters, scenario behavior, or accepted metrics must
update the README, implementation notes, schematic SVG/PNG, technical
reference source/PDF, and relevant reference outputs in the same change.

## Scientific Scope

The model is a closed-loop Fontan circulation built with PhysioBlocks 0-D
components and one local active-atrium block. No inlet pressure, outlet
pressure, or prescribed inflow boundary condition drives the baseline
circulation.

The model is calibrated for computational-development and comparison workflows
against processed Aramburu 2024 targets. It is not clinically validated.

## Canonical Configs

| Config | Purpose |
|---|---|
| `fontan_0d_smoke.jsonc` | Short numerical smoke case. |
| `fontan_0d_baseline.jsonc` | Accepted calibrated baseline reference. |
| `fontan_0d_vasodilation.jsonc` | Pulmonary vasodilation validation scenario. |
| `fontan_0d_fenestration.jsonc` | Fenestration validation scenario. |
| `fontan_0d_lpa_obstruction.jsonc` | LPA obstruction validation scenario. |

## Topology Summary

```text
active atrium -> AV valve -> active single ventricle -> aortic valve -> AAo
AAo -> aortic arch
aortic arch -> BCA/LCCA/LSA -> upper systemic bed -> SVC
aortic arch -> DAo -> lower systemic bed -> IVC
SVC/IVC -> Fontan conduit states -> TCPC -> RPA/LPA conduit states
RPA/LPA -> pulmonary RCR beds -> active atrium
optional high-resistance baseline path: IVC -> fenestration -> active atrium
```

The aortic outlet is a lumped tree with AAo, arch, BCA, LCCA, LSA, and DAo
states. The upper-body branches feed a shared upper vascular bed. DAo feeds a
separate lower vascular bed. The Fontan limbs use bidirectional R-L conduit
elements, local conduit compliance, and short connector resistances.

## Numerical Formulation

The model uses:

- `spherical_cavity_block` for the active single ventricle;
- `time_varying_elastance_atrium_block` from `fontan_blocks/active_atrium.py`;
- `valve_rl_block` for atrioventricular and aortic valves;
- symmetric `valve_rl_block` instances as bidirectional Fontan conduit R-L
  elements;
- `c_block` for passive pressure-volume storage;
- `rc_block` with `zero_capacitance = 0.0` as a pure hydraulic resistor;
- `rcr_block` for right and left pulmonary Windkessel beds.

## Parameter Sources and Calibration

Task 004 calibrated the baseline to the Aramburu 2024 direct-measurement
targets. The selected parameter factors are recorded in:

```text
models/full_0d/calibration/parameter_priors.yaml
models/full_0d/calibration/calibration_report.md
models/full_0d/calibration/baseline_objective.json
models/full_0d/calibration/baseline_vs_paper.json
models/full_0d/calibration/baseline_vs_nektar_closed_loop.json
```

Intervention scenarios inherit the baseline calibration and are validation
cases, not separately retuned models.

## Validation State

Current baseline highlights from
`models/full_0d/reference_outputs/baseline_metrics.json`:

| Quantity | Model | Direct target |
|---|---:|---:|
| SV | 35.87 ml | 36.80 ml |
| CO | 2.51 L/min | 2.57 L/min |
| Mean AAo pressure | 47.79 mmHg | 50.40 mmHg |
| Mean SVC pressure | 9.11 mmHg | 8.87 mmHg |
| Mean IVC pressure | 8.93 mmHg | 8.54 mmHg |
| RPA flow fraction | 0.591 | 0.591 |

The main residual gap is low descending-aorta pressure relative to the direct
measurement table.

## Run Commands

Generate a smoke run:

```bash
python3 scripts/run_one.py models/full_0d/configs/fontan_0d_smoke.jsonc --series Smoke
```

Compute metrics from the generated `main.csv`:

```bash
python3 scripts/metrics.py runs/simulations/Smoke/*/main.csv models/full_0d/configs/fontan_0d_smoke.jsonc --out models/full_0d/reference_outputs/smoke_metrics.json
```

Run the final scenarios:

```bash
python3 scripts/run_one.py models/full_0d/configs/fontan_0d_baseline.jsonc --series Baseline
python3 scripts/run_one.py models/full_0d/configs/fontan_0d_vasodilation.jsonc --series Vasodilation
python3 scripts/run_one.py models/full_0d/configs/fontan_0d_fenestration.jsonc --series Fenestration
python3 scripts/run_one.py models/full_0d/configs/fontan_0d_lpa_obstruction.jsonc --series LPAObstruction
```

Compare scenario metrics:

```bash
python3 scripts/compare_scenarios.py \
  models/full_0d/reference_outputs/baseline_metrics.json \
  models/full_0d/reference_outputs/vasodilation_metrics.json \
  models/full_0d/reference_outputs/fenestration_metrics.json \
  models/full_0d/reference_outputs/lpa_obstruction_metrics.json
```

## Reference Outputs

```text
models/full_0d/reference_outputs/smoke_metrics.json
models/full_0d/reference_outputs/baseline_metrics.json
models/full_0d/reference_outputs/vasodilation_metrics.json
models/full_0d/reference_outputs/fenestration_metrics.json
models/full_0d/reference_outputs/lpa_obstruction_metrics.json
```

## Known Limitations

- The aortic and Fontan pathways are lumped 0-D approximations, not true
  spatially resolved 1-D domains.
- The descending-aorta pressure residual remains the main direct-target gap.
- The model is a calibrated computational-development artifact, not a
  clinically validated simulator.

## Documentation Regeneration

Required model-local documentation:

```text
models/full_0d/docs/full_0d_schematic.svg
models/full_0d/docs/full_0d_schematic.png
models/full_0d/docs/implementation_notes.md
models/full_0d/docs/full_0d_technical_reference.md
models/full_0d/docs/full_0d_technical_reference.pdf
```

Regenerate the long-form technical reference after topology or parameter
changes:

```bash
python3 scripts/docs/build_model_reference_pdfs.py --model full_0d
python3 scripts/docs/check_model_docs.py --model full_0d
```
