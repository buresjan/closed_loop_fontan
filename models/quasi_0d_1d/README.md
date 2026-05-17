# Quasi 0-D/1-D Fontan Model

This is the canonical PhysioBlocks-only quasi 0-D/1-D Fontan model. It keeps
the accepted full 0-D heart, active atrium, valves, systemic beds, pulmonary
RCR beds, and fenestration, while replacing the aortic and Fontan conduit
shortcuts with distributed R-L-C chains.

The model does not contain a true 1-D solver. Its quasi 1-D behavior comes from
repeated `hydraulic_rl_block` links and `c_block` compliances.

## Configs

| Config | Purpose |
|---|---|
| `fontan_quasi_smoke.jsonc` | Short numerical smoke case. |
| `fontan_quasi_baseline.jsonc` | Baseline accepted quasi model. |
| `fontan_quasi_vasodilation.jsonc` | Pulmonary vasodilation validation scenario. |
| `fontan_quasi_fenestration.jsonc` | Low-resistance fenestration validation scenario. |
| `fontan_quasi_lpa_obstruction.jsonc` | LPA obstruction validation scenario with doubled LPA quasi-chain resistance. |

Run the smoke case:

```bash
python3 scripts/run_one.py models/quasi_0d_1d/configs/fontan_quasi_smoke.jsonc --series QuasiSmoke
```

Regenerate and check the executable configs:

```bash
python3 scripts/modeling/build_quasi_configs.py
python3 scripts/modeling/build_quasi_configs.py --check
```

## Canonical Artifacts

The model-local artifacts intentionally mirror the full 0-D family:

```text
models/quasi_0d_1d/README.md
models/quasi_0d_1d/configs/
models/quasi_0d_1d/config_fragments/quasi_vessel_chains_corrected.json
models/quasi_0d_1d/calibration/calibration_factors.json
models/quasi_0d_1d/calibration/calibration_report.md
models/quasi_0d_1d/calibration/baseline_objective.json
models/quasi_0d_1d/calibration/baseline_vs_paper.json
models/quasi_0d_1d/calibration/baseline_waveforms_direct.json
models/quasi_0d_1d/calibration/current_quasi_gate_status.json
models/quasi_0d_1d/calibration/current_quasi_gate_status.md
models/quasi_0d_1d/calibration/quasi_superiority_gate.json
models/quasi_0d_1d/calibration/full0d_reference_scores.json
models/quasi_0d_1d/calibration/aortic_profile.json
models/quasi_0d_1d/calibration/aortic_signal_policy.json
models/quasi_0d_1d/calibration/aortic_signal_policy.md
models/quasi_0d_1d/reference_outputs/
models/quasi_0d_1d/docs/implementation_notes.md
models/quasi_0d_1d/docs/quasi_0d_1d_schematic.svg
models/quasi_0d_1d/docs/quasi_0d_1d_schematic.png
models/quasi_0d_1d/docs/quasi_0d_1d_technical_reference.md
models/quasi_0d_1d/docs/quasi_0d_1d_technical_reference.pdf
```

## Current Acceptance

The accepted quasi model is superior to the full 0-D reference under the frozen
comparison gate:

| Score | Full 0-D | Quasi 0-D/1-D |
|---|---:|---:|
| Hard clinical summary | 0.0433 | 0.0244 |
| Aggregate direct | 0.0614 | 0.0470 |
| Paper-model | 0.0793 | 0.0714 |
| AAo flow nRMSE | 0.5718 | 0.5701 |
| DAo chain-health flow nRMSE | 0.4337 | 0.3661 |

Scenario validation is stored in `reference_outputs/` and
`calibration/calibration_report.md`. The validation scenarios are baseline,
pulmonary vasodilation, fenestration, and LPA obstruction; no scenario-specific
retuning is used.

Regenerate the current gate:

```bash
python3 scripts/calibration/compare_quasi_to_full0d.py
```

## Implemented Topology

The executable quasi model keeps these full 0-D components:

- active atrium and active spherical ventricle;
- atrioventricular and aortic valve R-L blocks;
- BCA, LCCA, and LSA upper-body resistive branches;
- upper and lower systemic vascular beds;
- pulmonary RCR beds;
- fenestration shunt.

The quasi model replaces these full 0-D shortcuts:

| Chain | Nodes | Segments | Resistance policy |
|---|---|---:|---|
| AAo/arch x4 | `aao -> aortic_arch` | 4 | corrected aortic trunk prior |
| DAo x6 | `aortic_arch -> dao` | 6 | corrected aortic trunk prior |
| SVC x3 | `svc -> tcpc` | 3 | calibrated full 0-D pathway prior |
| IVC x5 | `ivc -> tcpc` | 5 | calibrated full 0-D pathway prior |
| RPA x3 | `tcpc -> rpa` | 3 | calibrated full 0-D pathway prior |
| LPA x4 | `tcpc -> lpa` | 4 | calibrated full 0-D pathway prior |

The old full 0-D conduit pressure nodes (`svc_conduit`, `ivc_conduit`,
`rpa_conduit`, `lpa_conduit`) and conduit workaround blocks are not present in
the accepted quasi configs.

## Parameters

The accepted calibration is recorded in
`calibration/calibration_factors.json`. The main accepted scales are:

```text
heart_contractility_scale = 1.05
lower_systemic_resistance_scale = 1.12
right_pulmonary_total_resistance_scale = 1.15
left_pulmonary_total_resistance_scale = 1.15
right_pulmonary_proximal_fraction = 0.65
left_pulmonary_proximal_fraction = 0.65
endpoint_aortic_compliance_scale = 0.02
terminal_lower_arterial_compliance_scale = 0.5
lower_systemic_proximal_resistance_fraction = 0.95
upper/lower venous compliance scale = 0.95
SVC/IVC compliance scale = 0.95
active_atrium_unstressed_volume_scale = 1.05
heart_radius_scale = 1.01
```

The LPA obstruction scenario doubles the LPA quasi-chain resistance through
`quasi_lpa.narrowing_resistance_scale = 2.0`.

## Metrics

For each quasi chain, standardized cycle metrics use the first R-L segment as
the inlet and the final R-L segment as the outlet:

```text
mean_<vessel>_inlet_flow_ml_s
mean_<vessel>_outlet_flow_ml_s
integral_<vessel>_inlet_flow_ml
integral_<vessel>_outlet_flow_ml
<vessel>_cycle_storage_ml
<vessel>_mass_balance_rel
```

`<vessel>` is one of `aao_arch`, `dao`, `svc`, `ivc`, `rpa`, or `lpa`.

## Current Limitations

- The model is computational-development infrastructure, not a clinically
  validated simulator.
- The quasi chains are lumped R-L-C chains, not nonlinear 1-D vessels.
- Clinical descending-aorta bed-entry flow remains reported as a soft waveform
  diagnostic; DAo chain-health flow is the accepted aortic trunk waveform gate.
- True coupled 1-D aorta/TCPC work is intentionally deferred to the next model
  family.
