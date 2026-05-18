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

Task 009 found that true 1-D prototyping can start locally without a
PhysioBlocks fork. Current PhysioBlocks state construction is based on
class-level `internal_variables`, so block internal state size is fixed by the
registered block class, not by config values such as `number_of_cells`. The
accepted next path is:

- generate scalar/fixed-size local 1-D components from scripts and avoid
  PhysioBlocks internals for Task 010;
- keep fixed-size registered blocks available for focused probes;
- reconsider a PhysioBlocks fork/upstream contribution only if dense Jacobian
  scaling, instance-sized internal variables, area positivity safeguards, or
  boundary-coupling controls become concrete blockers.

The roadmap therefore continues to defer PhysioBlocks fork/upstream work.

Task 010 implemented the first local true 1-D numerical kernel using this path:
a fixed three-cell finite-volume vessel with cell area states, staggered
face-flow states, nonlinear momentum, a square-root pressure-area wall law,
pressure/flow ports, saved distributed quantities, and analytic Jacobian tests.
It is a validated prototype for Task 011 open-loop submodels, not yet an
accepted coupled closed-loop model.

Task 011 added validated open-loop reference specs for aorta, TCPC, and
combined aorta-TCPC 1-D submodels. These specs bind tracked patient-specific
geometry, measured inflows, Nektar reference domains, clinical comparison
targets, and validation gates. They are reference specs, not PhysioBlocks
forward-simulation launcher configs and not a closed-loop coupled model.

Task 012 is complete. After comparison with the original Nektar/paper
implementation, the dynamic finite-storage TCPC candidate and the no-loss TCPC
total-pressure candidate were not accepted as final coupled topology. The
current coupled prototype uses a massless no-loss aortic total-pressure
junction, a wall-pressure-blended dissipative TCPC total-pressure junction, a
tapered composite LPA, and a retained full 0-D LSA terminal outlet to close the
aortic mass balance without fabricating a 1-D LSA segment. The startup smoke
run passes positive-area, TCPC balance, and junction mass-balance checks. A
2.0 s TCPC diagnostic with `loss_coefficient = 2.0` removes the earlier
pre-activation SVC/TCPC pressure blow-up and keeps TCPC terminal pressures
positive and bounded. The generated 20 s baseline now passes no-NaN,
positive-area, TCPC balance, atrium balance, ventricle balance, and periodicity
checks. All generated coupled scenarios cap the time step at 0.25 ms because
the inherited 2 ms full 0-D step is too coarse for the inserted 1-D dynamics.
Task 013 is unblocked for calibration and validation.

Tasks 014-022 define a later, separate Nektar-complex coupled 0-D/1-D model
family. That series does not replace `models/coupled_0d_1d`; it creates
`models/coupled_0d_1d_nektar` after the current coupled model has a clear
calibration/validation status. The selected strategy is a local repo-owned
high-order 1-D implementation with Nektar-level numerical fidelity, not an
external Nektar co-simulation bridge.

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
| 008 | completed | [Calibrate quasi model](tasks/008-calibrate-quasi-model.md) | Accepted and standardized the canonical quasi 0-D/1-D model against the frozen full 0-D reference gate. | No |
| 009 | completed | [Run PhysioBlocks 1-D feasibility spike](tasks/009-physioblocks-1d-feasibility-spike.md) | Local generated scalar/fixed-size 1-D components are enough for the next stage; no fork now. | No fork now |
| 010 | completed | [Prototype local 1-D numerics](tasks/010-prototype-local-1d-numerics.md) | Implemented and validated the local true 1-D finite-volume vessel kernel. | No fork now |
| 011 | completed | [Build 1-D open-loop submodels](tasks/011-build-1d-openloop-submodels.md) | Validated aorta, TCPC, and combined open-loop 1-D reference specs before closed loop. | No fork now |
| 012 | completed | [Build coupled closed-loop model](tasks/012-build-coupled-closed-loop-model.md) | Generated coupled baseline completes 20 s with no NaNs, no negative 1-D areas, passing TCPC/atrium/ventricle balance, and periodic behavior. | No fork now |
| 013 | in_progress | [Calibrate and validate coupled model](tasks/013-calibrate-and-validate-coupled-model.md) | Calibrate the periodic coupled baseline using short candidate screens before submitting long 20 s validation runs. | Maybe |
| 014 | planned | [Specify Nektar-complex coupled target](tasks/014-nektar-complexity-specification.md) | Freeze the numerical/scientific target, validation gates, and simplified-vs-Nektar-complex comparison before implementation. | No implementation |
| 015 | planned | [Scaffold Nektar-complex coupled model family](tasks/015-scaffold-nektar-complex-coupled-model.md) | Add the separate `models/coupled_0d_1d_nektar` family with standardized docs, schematic, configs, and technical reference placeholders. | No fork now |
| 016 | planned | [Implement Nektar-complex 1-D solver kernel](tasks/016-implement-nektar-complex-1d-solver-kernel.md) | Build the local high-order/multi-element 1-D vessel kernel needed for Nektar-level numerical fidelity. | Maybe |
| 017 | planned | [Implement Nektar boundary and junction physics](tasks/017-implement-nektar-boundary-and-junction-physics.md) | Add characteristic boundaries, aortic/TCPC junctions, terminal 0-D coupling, and residual diagnostics. | Maybe |
| 018 | planned | [Validate open-loop Nektar equivalence](tasks/018-validate-openloop-nektar-equivalence.md) | Reproduce processed Nektar aorta, TCPC, and combined open-loop outputs before closed-loop coupling. | Maybe |
| 019 | planned | [Integrate Nektar-complex closed-loop model](tasks/019-integrate-nektar-complex-closed-loop.md) | Couple the validated Nektar-complex 1-D network to the accepted 0-D heart/foundation. | Maybe |
| 020 | planned | [Validate Nektar-complex stability and periodicity](tasks/020-validate-nektar-complex-stability-periodicity.md) | Prove closed-loop stability, periodicity, mass balance, and physiological bounds before calibration. | Maybe |
| 021 | planned | [Calibrate and validate Nektar-complex model](tasks/021-calibrate-validate-nektar-complex-model.md) | Calibrate baseline only and validate interventions against clinical, paper, Nektar, full 0-D, quasi, and simplified coupled references. | Maybe |
| 022 | planned | [Nektar-complex decision report and promotion](tasks/022-nektar-complex-decision-report-promotion.md) | Decide accepted/experimental/blocked status and update all model docs, reports, schematics, and references accordingly. | Maybe |

## Execution Rules

- Do tasks in order unless a task explicitly says it can run in parallel.
- Every model-behavior change must update the affected model README,
  schematic SVG/PNG, implementation notes, technical reference source/PDF, and
  relevant reference outputs in the same change.
- Prefer local repository extensions over PhysioBlocks internal changes until Task 009 justifies otherwise.
- Tune only baseline configurations. Intervention scenarios are validation cases.
- The canonical quasi 0-D/1-D family is accepted against the frozen full 0-D
  comparison gate in `models/quasi_0d_1d/calibration/quasi_superiority_gate.json`.
- The Nektar-complex coupled model series must remain separate from the
  simplified coupled model until a decision report accepts it explicitly.
- Clinical DAo bed-entry flow remains reported as a soft diagnostic, while DAo
  chain-health remains in the hard aortic waveform gate.
- Keep raw Aramburu data ignored; regenerate tracked processed data through `scripts/data/prepare_aramburu_2024.py`.
- Use `pytest -q` as the default check, plus the relevant smoke/reference simulations for model changes.
