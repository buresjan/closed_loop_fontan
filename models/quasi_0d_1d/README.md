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
| `submodel_aorta_quasi_openloop.jsonc` | Task 008.8 diagnostic submodel with prescribed AAo inflow and terminal pressure boundaries. |

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

The tracked configs include the Task 008.5 corrective calibration factors from
`models/quasi_0d_1d/calibration/calibration_factors.json`. Use
`--uncalibrated` only when inspecting the raw Task 006 assembly before
calibration.

Run and evaluate the aortic open-loop diagnostic:

```bash
.venv/bin/python scripts/quasi/run_aorta_quasi_openloop.py
.venv/bin/python scripts/quasi/evaluate_aorta_quasi_openloop.py
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
models/quasi_0d_1d/calibration/calibration_report.md
models/quasi_0d_1d/calibration/non_regression_gate.json
models/quasi_0d_1d/calibration/design_audit_report.md
models/quasi_0d_1d/calibration/quasi_ablation_summary.csv
models/quasi_0d_1d/calibration/quasi_final_decision.md
models/quasi_0d_1d/calibration/quasi_superiority_gate.json
models/quasi_0d_1d/calibration/current_quasi_gate_status.md
models/quasi_0d_1d/calibration/aortic_signal_policy.md
models/quasi_0d_1d/calibration/aortic_signal_policy.json
models/quasi_0d_1d/calibration/aorta_quasi_openloop_report.md
models/quasi_0d_1d/calibration/aorta_quasi_openloop_metrics.json
models/quasi_0d_1d/calibration/aorta_quasi_openloop_waveforms.csv
models/quasi_0d_1d/docs/attempt_log.md
models/quasi_0d_1d/reference_outputs/baseline_metrics.json
models/quasi_0d_1d/reference_outputs/vasodilation_metrics.json
models/quasi_0d_1d/reference_outputs/fenestration_metrics.json
models/quasi_0d_1d/reference_outputs/lpa_obstruction_metrics.json
models/quasi_0d_1d/reference_outputs/scenario_comparison.txt
```

Regenerate one metrics file from a completed run:

```bash
.venv/bin/python scripts/metrics.py \
  runs/simulations/QuasiBaseline/.../main.csv \
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

- CO from aortic-valve flow: 2.47 L/min.
- Mean TCPC pressure: 8.16 mmHg.
- RPA flow fraction: 0.591.
- TCPC cycle balance: `2.28e-5`.
- Direct-measurement weighted RMS target error: `0.0592`.
- Task 008.6 closure status:
  `stable_quasi_development_scaffold_not_scientifically_superior`.

Task 008.5 improves the aggregate direct score and fixes the RPA/LPA pressure
and SVC-flow non-regression gates. EDV, ESV, SV, CO, paper-model score, and the
AAo/DAo flow waveform gates still fail, so this model should not be presented
as a final calibrated quasi model.

Task 008.6 audits the AAo/DAo flow signal extraction, compliance/storage
budget, characteristic impedance, and 23 quasi ablation/design candidates. No
candidate passes all hard, paper, waveform, stability, and mass-balance gates,
so the Task 008.5 configs remain canonical and Task 009 proceeds with full 0-D
as the calibrated reference.

Task 008.7 freezes the promotion criteria in
`calibration/quasi_superiority_gate.json`. The current quasi model is recorded
as `not_superior_to_full_0d` in `calibration/current_quasi_gate_status.md`.
Later quasi candidates must pass that same script and gate before any promotion
claim.

Task 008.8 isolates the quasi aortic chain in
`submodel_aorta_quasi_openloop.jsonc`. The current diagnostic status is
`fail_open_loop_aortic_diagnostic`: the prescribed AAo inflow is reproduced and
the DAo chain outlet plus `lower_ra4.flow` are both reported, but the pressure
profile and pulse pressure are too damped. This is a diagnostic submodel only;
it does not promote a new closed-loop quasi topology.

Task 008.9 freezes aortic signal mapping in
`calibration/aortic_signal_policy.json`. Clinical DAo flow now maps to
`lower_ra4.flow`, while DAo chain-health flow remains
`quasi_dao_rl_06.flux` and stays in the aortic waveform no-regression gate. The
current quasi model still fails that gate because DAo chain-health nRMSE is
`0.952` versus full 0-D reference `0.434`.

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
parameter policy. `docs/attempt_log.md` consolidates every quasi modeling,
calibration, diagnostic, and blocked-promotion attempt tried so far.

Every model change must update this README, `docs/schematic.svg`,
`docs/schematic.png`, and `docs/implementation_notes.md` in the same change.
Task 008.6 did not promote a topology or parameterization change into the
tracked quasi configs, so the schematic remains the Task 008.5 executable
topology.

Task 008.8 adds an open-loop diagnostic config for the existing aortic chain
without changing the promoted closed-loop topology, so the schematic remains
unchanged.
