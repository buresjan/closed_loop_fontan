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

| Order | Status | Task | Purpose | PhysioBlocks internals |
|---:|---|---|---|---|
| 001 | completed | [Freeze full 0-D reference](tasks/001-freeze-full-0d-reference.md) | Establish the current full 0-D model as the baseline reference. | No |
| 002 | completed | [Add hydraulic lumped blocks](tasks/002-add-hydraulic-lumped-blocks.md) | Add clean local resistor/RL blocks and tests. | No |
| 003 | completed | [Build calibration targets](tasks/003-build-calibration-targets.md) | Extract shared summary and waveform targets from processed Aramburu data. | No |
| 004 | completed | [Calibrate full 0-D baseline](tasks/004-calibrate-full-0d.md) | Tune the current model to patient-level means and volumes. | No |
| 004.5 | completed | [Target consistency and target policy check](tasks/004-5-target-consistency-policy.md) | Document target conflicts before quasi-vessel derivation. | No |
| 005 | completed | [Derive quasi vessel parameters](tasks/005-derive-quasi-vessel-parameters.md) | Convert geometry and priors into R-L-C chain parameters. | No |
| 006 | completed | [Implement quasi model](tasks/006-implement-quasi-model.md) | Build PhysioBlocks-only quasi 0-D/1-D configs and docs. | No |
| 007 | completed | [Add quasi metrics and scenarios](tasks/007-quasi-metrics-and-scenarios.md) | Make metrics/scenario comparison model-family aware. | No |
| 008 | completed | [Calibrate quasi model](tasks/008-calibrate-quasi-model.md) | Tune quasi model from full 0-D baseline while preserving physiology. | No |
| 008.5 | completed | [Corrective quasi calibration and non-regression gate](tasks/008-5-corrective-quasi-calibration.md) | Add hard-target gates and document that the quasi model is stable but not yet superior. | No |
| 008.6 | completed | [Quasi design audit and calibration closure](tasks/008-6-quasi-design-audit-and-calibration-closure.md) | Audit AAo/DAo signal extraction, compliance/impedance, and a small quasi design ablation matrix before Task 009. | No |
| 008.7 | completed | [Freeze quasi superiority gate](quasi_improvement_task_series/008-7-freeze-quasi-superiority-gate.md) | Freeze machine-readable promotion criteria and current quasi status before further design work. | No |
| 008.8 | completed | [Build open-loop aortic quasi diagnostic harness](quasi_improvement_task_series/008-8-openloop-aortic-quasi-diagnostic.md) | Isolate the quasi aortic chain before changing closed-loop topology. | No |
| 008.9 | completed | [Resolve AAo/DAo flow signal definitions](quasi_improvement_task_series/008-9-resolve-aortic-flow-signal-policy.md) | Finalize approved aortic flow signal policy for gates and reports. | No |
| 008.10 | blocked | [Correct quasi aortic chain design](quasi_improvement_task_series/008-10-correct-quasi-aortic-chain-design.md) | Corrected-chain candidate fixed passive drop and DAo chain health, but failed strict clinical DAo no-regression. | No |
| 008.11 | planned | [Correct Fontan/pulmonary quasi design](quasi_improvement_task_series/008-11-correct-fontan-pulmonary-quasi-design.md) | Improve Fontan and pulmonary impedance behavior. | No |
| 008.12 | planned | [Restore pump/preload compliance budget](quasi_improvement_task_series/008-12-restore-pump-preload-compliance-budget.md) | Fix preload and vascular storage before recalibration. | No |
| 008.13 | planned | [Run constrained quasi closed-loop calibration](quasi_improvement_task_series/008-13-constrained-quasi-closed-loop-calibration.md) | Calibrate only after design corrections are in place. | No |
| 008.14 | planned | [Validate and promote superior quasi model](quasi_improvement_task_series/008-14-validate-promote-superior-quasi-model.md) | Promote the quasi model only if it passes the frozen superiority gate. | No |
| 009 | planned | [Run PhysioBlocks 1-D feasibility spike](tasks/009-physioblocks-1d-feasibility-spike.md) | Decide whether local blocks/generated configs are enough for true 1-D. | Maybe |
| 010 | planned | [Prototype local 1-D numerics](tasks/010-prototype-local-1d-numerics.md) | Implement and validate wall-law/vessel residual prototypes. | Maybe |
| 011 | planned | [Build 1-D open-loop submodels](tasks/011-build-1d-openloop-submodels.md) | Validate aorta, TCPC, and combined 1-D submodels before closed loop. | Maybe |
| 012 | planned | [Build coupled closed-loop model](tasks/012-build-coupled-closed-loop-model.md) | Couple validated 1-D subdomains to the 0-D heart and beds. | Maybe |
| 013 | planned | [Calibrate and validate coupled model](tasks/013-calibrate-and-validate-coupled-model.md) | Tune small global scales and compare against measurements/paper behavior. | Maybe |

## Execution Rules

- Do tasks in order unless a task explicitly says it can run in parallel.
- Every model-behavior change must update the affected model README and schematic in the same change.
- Prefer local repository extensions over PhysioBlocks internal changes until Task 009 justifies otherwise.
- Tune only baseline configurations. Intervention scenarios are validation cases.
- Do not treat the quasi 0-D/1-D family as scientifically superior to the full
  0-D reference until it passes the frozen Task 008.7 superiority gate in
  `models/quasi_0d_1d/calibration/quasi_superiority_gate.json`.
- Do not proceed from blocked Task 008.10 to quasi promotion work until the
  clinical DAo outlet failure is either fixed or explicitly reclassified by an
  updated signal/acceptance policy.
- Keep raw Aramburu data ignored; regenerate tracked processed data through `scripts/data/prepare_aramburu_2024.py`.
- Use `pytest -q` as the default check, plus the relevant smoke/reference simulations for model changes.
