# Quasi 0-D/1-D Calibration Report

Status: `accepted_superior_to_full_0d`

Accepted model: `models/quasi_0d_1d/configs/fontan_quasi_baseline.jsonc`

Reference model: `models/full_0d/configs/fontan_0d_baseline.jsonc`

## Summary Scores

| Score | Full 0-D reference | Quasi 0-D/1-D |
|---|---:|---:|
| Hard clinical summary | 0.0433 | 0.0244 |
| Aggregate direct | 0.0614 | 0.0470 |
| Paper-model | 0.0793 | 0.0714 |
| AAo flow nRMSE | 0.5718 | 0.5701 |
| DAo chain-health flow nRMSE | 0.4337 | 0.3661 |

The accepted quasi model passes the frozen comparison gate in
`quasi_superiority_gate.json`. Gate details are stored in
`current_quasi_gate_status.json` and `current_quasi_gate_status.md`.

## Accepted Parameterization

The accepted calibration factors are tracked in `calibration_factors.json`.
The important scales are:

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

These factors are applied by `scripts/modeling/build_quasi_configs.py` through
`scripts/calibration/quasi.py`.

## Scenario Validation

The accepted quasi model was validated without scenario-specific retuning.
Reference metrics are stored under `models/quasi_0d_1d/reference_outputs/`.

Expected scenario directions are preserved:

| Scenario | Expected response | Status |
|---|---|---|
| Vasodilation | CO/SV increase, TCPC pressure decreases, pulmonary flow increases | pass |
| Fenestration | Fenestration flow is positive and CO remains plausible | pass |
| LPA obstruction | LPA flow decreases and RPA flow fraction increases | pass |

## Reproduction Commands

```bash
python3 scripts/modeling/build_quasi_configs.py --check
python3 scripts/run_one.py models/quasi_0d_1d/configs/fontan_quasi_smoke.jsonc --series QuasiSmoke
python3 scripts/run_one.py models/quasi_0d_1d/configs/fontan_quasi_baseline.jsonc --series QuasiBaseline
python3 scripts/calibration/compare_quasi_to_full0d.py
python3 -m pytest -q
```

## Scientific Caveat

The model is accepted for computational development against the repository's
frozen full 0-D comparison gate. It is not clinically validated, and its
distributed R-L-C chains are not a substitute for true nonlinear 1-D
hemodynamics.
