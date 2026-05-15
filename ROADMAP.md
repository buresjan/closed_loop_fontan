# ROADMAP

This roadmap converts `fontan_implementation_and_calibration_plans.md` into an ordered execution sequence. The plan is broadly sound: keep the current full 0-D model as the reference, build the quasi 0-D/1-D PhysioBlocks-only model next, and delay the true 0-D/1-D coupled model until calibration targets and open-loop 1-D validation are stable.

## Review Summary

- Keep `models/full_0d` frozen as the current reference variant. Cleaning up the existing `rc_block` and `valve_rl_block` workarounds can be done by adding local hydraulic blocks, but should not change accepted full 0-D behavior unless a deliberate new reference baseline is created.
- Implement `models/quasi_0d_1d` before the true coupled model. It exercises the same insertion points, metrics, geometry priors, calibration files, and schematic discipline without introducing the full numerical risk of a nonlinear 1-D solver.
- Build calibration infrastructure early and share it across all three model families. Baseline-only tuning plus intervention validation is the right calibration policy.
- Treat true 1-D as a staged solver project, not a direct config edit. It needs wall-law, vessel, boundary, junction, and open-loop validation before closed-loop coupling.

## PhysioBlocks Impact Assessment

No PhysioBlocks internals are needed for the next several tasks:

- local custom blocks are already supported, as shown by `fontan_blocks/active_atrium.py`;
- clean scalar `hydraulic_resistor_block` and `hydraulic_rl_block` can live in `fontan_blocks/`;
- quasi R-L-C chains can be built from repeated local blocks plus existing `c_block` nodes;
- calibration, target extraction, metrics, scenarios, documentation, and schematics all stay in this repository.

True 1-D may require PhysioBlocks changes, but only after a feasibility spike. Current PhysioBlocks state construction is based on class-level `internal_variables`, so block internal state size is effectively fixed by the registered block class, not by config values such as `number_of_cells`. A configurable `nonlinear_vessel_1d_block` with arbitrary cell count may therefore need one of these approaches:

- generate many scalar/local block instances from scripts and avoid PhysioBlocks internals;
- generate/register fixed-size vessel block classes for selected cell counts;
- upstream or fork PhysioBlocks support for instance/config-dependent internal variable sizes, better sparse Jacobian handling, positivity safeguards for vessel area, and robust boundary-coupling solver controls.

The roadmap therefore defers any PhysioBlocks fork/upstream work until Task 009 has produced evidence that local blocks or generated configs are insufficient.

## Ordered Tasks

| Order | Task | Purpose | PhysioBlocks internals |
|---:|---|---|---|
| 001 | [Freeze full 0-D reference](tasks/001-freeze-full-0d-reference.md) | Establish the current full 0-D model as the baseline reference. | No |
| 002 | [Add hydraulic lumped blocks](tasks/002-add-hydraulic-lumped-blocks.md) | Add clean local resistor/RL blocks and tests. | No |
| 003 | [Build calibration targets](tasks/003-build-calibration-targets.md) | Extract shared summary and waveform targets from processed Aramburu data. | No |
| 004 | [Calibrate full 0-D baseline](tasks/004-calibrate-full-0d.md) | Tune the current model to patient-level means and volumes. | No |
| 005 | [Derive quasi vessel parameters](tasks/005-derive-quasi-vessel-parameters.md) | Convert geometry and priors into R-L-C chain parameters. | No |
| 006 | [Implement quasi model](tasks/006-implement-quasi-model.md) | Build PhysioBlocks-only quasi 0-D/1-D configs and docs. | No |
| 007 | [Add quasi metrics and scenarios](tasks/007-quasi-metrics-and-scenarios.md) | Make metrics/scenario comparison model-family aware. | No |
| 008 | [Calibrate quasi model](tasks/008-calibrate-quasi-model.md) | Tune quasi model from full 0-D baseline while preserving physiology. | No |
| 009 | [Run PhysioBlocks 1-D feasibility spike](tasks/009-physioblocks-1d-feasibility-spike.md) | Decide whether local blocks/generated configs are enough for true 1-D. | Maybe |
| 010 | [Prototype local 1-D numerics](tasks/010-prototype-local-1d-numerics.md) | Implement and validate wall-law/vessel residual prototypes. | Maybe |
| 011 | [Build 1-D open-loop submodels](tasks/011-build-1d-openloop-submodels.md) | Validate aorta, TCPC, and combined 1-D submodels before closed loop. | Maybe |
| 012 | [Build coupled closed-loop model](tasks/012-build-coupled-closed-loop-model.md) | Couple validated 1-D subdomains to the 0-D heart and beds. | Maybe |
| 013 | [Calibrate and validate coupled model](tasks/013-calibrate-and-validate-coupled-model.md) | Tune small global scales and compare against measurements/paper behavior. | Maybe |

## Execution Rules

- Do tasks in order unless a task explicitly says it can run in parallel.
- Every model-behavior change must update the affected model README and schematic in the same change.
- Prefer local repository extensions over PhysioBlocks internal changes until Task 009 justifies otherwise.
- Tune only baseline configurations. Intervention scenarios are validation cases.
- Keep raw Aramburu data ignored; regenerate tracked processed data through `scripts/data/prepare_aramburu_2024.py`.
- Use `pytest -q` as the default check, plus the relevant smoke/reference simulations for model changes.
