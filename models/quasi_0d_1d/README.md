# Quasi 0-D/1-D Fontan Model

This model family is the first executable PhysioBlocks-only quasi 0-D/1-D
Fontan model. It keeps the calibrated full 0-D heart, active atrium, valves,
systemic beds, pulmonary RCR beds, and fenestration, while replacing selected
aortic and Fontan shortcuts with distributed R-L-C chains.

The model still has no true 1-D solver parts. The quasi behavior comes from
repeated local `hydraulic_rl_block` links and `c_block` compliances.

## Configs

| Config | Purpose |
|---|---|
| `fontan_quasi_smoke.jsonc` | Short numerical smoke case. |
| `fontan_quasi_baseline.jsonc` | Baseline quasi model, assembled from the calibrated full 0-D baseline. |
| `fontan_quasi_vasodilation.jsonc` | Pulmonary vasodilation validation scenario. |
| `fontan_quasi_fenestration.jsonc` | Low-resistance fenestration validation scenario. |
| `fontan_quasi_lpa_obstruction.jsonc` | LPA obstruction validation scenario with 2x LPA quasi-chain resistance. |

Run the smoke case:

```bash
.venv/bin/python scripts/run_one.py models/quasi_0d_1d/configs/fontan_quasi_smoke.jsonc --series QuasiSmoke
```

Regenerate the executable configs from the full 0-D scenarios and the tracked
chain fragment:

```bash
.venv/bin/python scripts/modeling/build_quasi_configs.py
```

Check that the tracked configs are current:

```bash
.venv/bin/python scripts/modeling/build_quasi_configs.py --check
```

## Metrics and Scenario Outputs

Task 007 adds model-family-aware metrics for the quasi chains. The standard
per-chain outputs are:

```text
mean_<vessel>_inlet_flow_ml_s
mean_<vessel>_outlet_flow_ml_s
integral_<vessel>_inlet_flow_ml
integral_<vessel>_outlet_flow_ml
<vessel>_cycle_storage_ml
<vessel>_mass_balance_rel
```

where `<vessel>` is one of `aao_arch`, `dao`, `svc`, `ivc`, `rpa`, or `lpa`.
The metrics also retain segment-level flow outputs such as
`mean_quasi_svc_rl_02.flux_ml_s`.

The current comparison-ready outputs are tracked in:

```text
models/quasi_0d_1d/reference_outputs/baseline_metrics.json
models/quasi_0d_1d/reference_outputs/vasodilation_metrics.json
models/quasi_0d_1d/reference_outputs/fenestration_metrics.json
models/quasi_0d_1d/reference_outputs/lpa_obstruction_metrics.json
models/quasi_0d_1d/reference_outputs/scenario_comparison.txt
```

Regenerate one metrics file from a completed run:

```bash
.venv/bin/python scripts/metrics.py \
  runs/simulations/QuasiBaselineTask007/eden_QuasiBaselineTask007_1/main.csv \
  models/quasi_0d_1d/configs/fontan_quasi_baseline.jsonc \
  --out models/quasi_0d_1d/reference_outputs/baseline_metrics.json
```

Compare the tracked quasi scenarios:

```bash
.venv/bin/python scripts/compare_scenarios.py \
  models/quasi_0d_1d/reference_outputs/baseline_metrics.json \
  models/quasi_0d_1d/reference_outputs/vasodilation_metrics.json \
  models/quasi_0d_1d/reference_outputs/fenestration_metrics.json \
  models/quasi_0d_1d/reference_outputs/lpa_obstruction_metrics.json
```

Current baseline highlights:

- CO from aortic-valve flow: 2.63 L/min.
- Mean TCPC pressure: 8.06 mmHg.
- RPA flow fraction: 0.591.
- TCPC cycle balance: `1.91e-5`.

## Implemented Topology

The executable quasi model keeps these full 0-D components:

- active atrium and active spherical ventricle;
- atrioventricular and aortic valve R-L blocks;
- BCA, LCCA, and LSA resistive upper-body branches;
- upper and lower systemic vascular beds;
- pulmonary RCR beds;
- fenestration shunt.

The first quasi release replaces the following full 0-D shortcuts:

| Chain | Nodes | Segments | Resistance policy |
|---|---|---:|---|
| AAo/arch x4 | `aao -> aortic_arch` | 4 | geometry Poiseuille |
| DAo x6 | `aortic_arch -> dao` | 6 | geometry Poiseuille |
| SVC x3 | `svc -> tcpc` | 3 | calibrated full 0-D pathway prior |
| IVC x5 | `ivc -> tcpc` | 5 | calibrated full 0-D pathway prior |
| RPA x3 | `tcpc -> rpa` | 3 | calibrated full 0-D pathway prior |
| LPA x4 | `tcpc -> lpa` | 4 | calibrated full 0-D pathway prior |

The old full 0-D conduit pressure nodes (`svc_conduit`, `ivc_conduit`,
`rpa_conduit`, `lpa_conduit`) and the old `valve_rl_block` conduit workarounds
are not present in the quasi configs. `valve_rl_block` is used only for the two
physiologic valves.

## Derived Vessel Priors

`scripts/modeling/derive_quasi_vessel_parameters.py` reads the processed
Aramburu aorta/Fontan geometry, the target policy, and the calibrated full 0-D
baseline. It emits:

```text
models/quasi_0d_1d/calibration/parameter_priors.yaml
models/quasi_0d_1d/config_fragments/quasi_vessel_chains.json
```

The aortic resistance policy intentionally does not preserve the excessive
full 0-D AAo-to-DAo pressure drop. Aortic R/L/C priors are derived from geometry
and the 5.35 m/s wave-speed prior; most systemic pressure loss should stay in
the systemic beds. Fontan-limb resistances start from the calibrated full 0-D
pathway values because the current Fontan pressures and pulmonary flow split are
accepted baseline physiology.

The LPA narrowing is explicit in the generated priors as
`quasi_lpa.narrowing_radius_m = 0.003`. In the LPA obstruction scenario,
`quasi_lpa.narrowing_resistance_scale = 2.0` and the LPA chain resistance is
doubled.

## Documentation Assets

The schematic in `docs/schematic.svg` follows the same circuit style and
component set as the full 0-D schematic. The quasi-specific change is that the
aortic and Fontan pathway labels show the implemented R-L-C chain counts.
`docs/schematic.png` is the exported browser-friendly copy, and
`docs/implementation_notes.md` records the topology, assembly convention, and
parameter policy.

Every model change must update this README, `docs/schematic.svg`,
`docs/schematic.png`, and `docs/implementation_notes.md` in the same change.
