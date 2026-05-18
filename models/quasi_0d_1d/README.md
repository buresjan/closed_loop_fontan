# Quasi 0-D/1-D Fontan Model

## Status

Accepted go-to quasi 0-D/1-D model.

The accepted quasi model passes the frozen quasi-vs-full0D superiority gate and
is the repository's canonical PhysioBlocks-only quasi 0-D/1-D family.

## Scientific Scope

The model keeps the accepted full 0-D heart, active atrium, valves, systemic
beds, pulmonary RCR beds, and fenestration. It replaces selected aortic and
Fontan conduit shortcuts with distributed R-L-C chains.

The model does not contain a nonlinear 1-D PDE solver. Its quasi 1-D behavior
comes from repeated `hydraulic_rl_block` links and `c_block` compliances.

## Canonical Configs

| Config | Purpose |
|---|---|
| `fontan_quasi_smoke.jsonc` | Short numerical smoke case. |
| `fontan_quasi_baseline.jsonc` | Accepted quasi baseline. |
| `fontan_quasi_vasodilation.jsonc` | Pulmonary vasodilation validation scenario. |
| `fontan_quasi_fenestration.jsonc` | Fenestration validation scenario. |
| `fontan_quasi_lpa_obstruction.jsonc` | LPA obstruction validation scenario with doubled LPA quasi-chain resistance. |

## Topology Summary

```text
active atrium -> AV valve -> active single ventricle -> aortic valve
-> AAo/arch and DAo quasi chains -> systemic beds
-> SVC/IVC quasi chains -> TCPC node -> RPA/LPA quasi chains
-> pulmonary RCR beds -> active atrium
```

The accepted quasi replacements are:

| Chain | Implemented path | Segments |
|---|---|---:|
| AAo/arch x4 | `aao -> aortic_arch` | 4 |
| DAo x6 | `aortic_arch -> dao` | 6 |
| SVC x3 | `svc -> tcpc` | 3 |
| IVC x5 | `ivc -> tcpc` | 5 |
| RPA x3 | `tcpc -> rpa` | 3 |
| LPA x4 | `tcpc -> lpa` | 4 |

## Numerical Formulation

Each quasi chain segment uses:

```text
hydraulic_rl_block: upstream pressure node -> downstream pressure node
c_block: downstream pressure-node compliance
```

The positive flow orientation follows node `1 -> 2`. Chain metrics use the
first R-L segment as the vessel inlet and the final R-L segment as the vessel
outlet.

## Parameter Sources and Calibration

First-pass vessel priors are derived from:

```text
data/processed/aramburu_2024/model_inputs/aorta_geometry.csv
data/processed/aramburu_2024/model_inputs/fontan_cross_geometry.csv
data/processed/aramburu_2024/targets/target_policy.csv
models/full_0d/configs/fontan_0d_baseline.jsonc
```

Accepted executable parameters are recorded in:

```text
models/quasi_0d_1d/config_fragments/quasi_vessel_chains_corrected.json
models/quasi_0d_1d/calibration/calibration_factors.json
models/quasi_0d_1d/calibration/calibration_report.md
```

The accepted calibration uses bounded interpretable scales for contractility,
systemic resistance, pulmonary resistance partitioning, endpoint compliance,
venous compliance, active-atrium unstressed volume, and small heart geometry
adjustments. Baseline is the only calibration case; intervention scenarios are
validation cases.

## Validation State

The accepted quasi model is superior to the full 0-D reference under the frozen
comparison gate:

| Score | Full 0-D | Quasi 0-D/1-D |
|---|---:|---:|
| Hard clinical summary | 0.0433 | 0.0244 |
| Aggregate direct | 0.0614 | 0.0470 |
| Paper-model | 0.0793 | 0.0714 |
| AAo flow nRMSE | 0.5718 | 0.5701 |
| DAo chain-health flow nRMSE | 0.4337 | 0.3661 |

The accepted gate artifacts are:

```text
models/quasi_0d_1d/calibration/current_quasi_gate_status.json
models/quasi_0d_1d/calibration/current_quasi_gate_status.md
models/quasi_0d_1d/calibration/quasi_superiority_gate.json
models/quasi_0d_1d/calibration/full0d_reference_scores.json
```

## Run Commands

Regenerate and check executable configs:

```bash
python3 scripts/modeling/build_quasi_configs.py
python3 scripts/modeling/build_quasi_configs.py --check
```

Run the smoke case:

```bash
python3 scripts/run_one.py models/quasi_0d_1d/configs/fontan_quasi_smoke.jsonc --series QuasiSmoke
```

Regenerate the current superiority gate:

```bash
python3 scripts/calibration/compare_quasi_to_full0d.py
```

## Reference Outputs

```text
models/quasi_0d_1d/reference_outputs/baseline_metrics.json
models/quasi_0d_1d/reference_outputs/vasodilation_metrics.json
models/quasi_0d_1d/reference_outputs/fenestration_metrics.json
models/quasi_0d_1d/reference_outputs/lpa_obstruction_metrics.json
models/quasi_0d_1d/reference_outputs/scenario_comparison.txt
```

## Known Limitations

- The quasi chains are lumped R-L-C chains, not nonlinear 1-D vessels.
- Clinical descending-aorta bed-entry flow remains a soft waveform diagnostic;
  DAo chain-health flow is the accepted aortic trunk waveform gate.
- The model is not clinically validated.

## Documentation Regeneration

Required model-local documentation:

```text
models/quasi_0d_1d/docs/quasi_0d_1d_schematic.svg
models/quasi_0d_1d/docs/quasi_0d_1d_schematic.png
models/quasi_0d_1d/docs/implementation_notes.md
models/quasi_0d_1d/docs/quasi_0d_1d_technical_reference.md
models/quasi_0d_1d/docs/quasi_0d_1d_technical_reference.pdf
```

Regenerate the long-form technical reference after topology or parameter
changes:

```bash
python3 scripts/docs/build_model_reference_pdfs.py --model quasi_0d_1d
python3 scripts/docs/check_model_docs.py --model quasi_0d_1d
```
