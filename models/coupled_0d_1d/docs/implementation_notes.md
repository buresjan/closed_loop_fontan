# Coupled 0-D/1-D Implementation Notes

## Status

Executable true 0-D/1-D development model. The Task 012 baseline completes a
20 s run with no NaNs, no negative saved 1-D areas, passing TCPC/atrium/
ventricle balance, and periodic cavity volume. Task 013 calibration and
validation are in progress, so the model is not yet an accepted calibrated
reference.

## Scope and Canonical Configs

The coupled model keeps the accepted full 0-D heart, atrium, valves, systemic
beds, pulmonary RCR beds, and fenestration, and replaces selected aortic and
TCPC shortcut pathways with true 1-D finite-volume vessel blocks.

Canonical configs:

```text
models/coupled_0d_1d/configs/fontan_coupled_0d_1d_smoke.jsonc
models/coupled_0d_1d/configs/fontan_coupled_0d_1d_baseline.jsonc
models/coupled_0d_1d/configs/fontan_coupled_0d_1d_vasodilation.jsonc
models/coupled_0d_1d/configs/fontan_coupled_0d_1d_fenestration.jsonc
models/coupled_0d_1d/configs/fontan_coupled_0d_1d_lpa_obstruction.jsonc
```

## Topology and Naming

Coupled 1-D blocks use the `coupled_<vessel>` naming pattern. Aortic inserted
vessels are `coupled_aao`, `coupled_dao`, `coupled_bca`, and `coupled_lcca`.
TCPC inserted vessels are `coupled_svc`, `coupled_ivc`, `coupled_rpa`, and
`coupled_lpa`. Algebraic junction blocks use explicit `coupled_*_junction`
names.

## Block and Numerical Conventions

The executable closed-loop configs use fixed-size log-area finite-volume 1-D
vessel blocks. They solve area/flow conservation equations with the physical
area recovered as `A = exp(g)`. Aortic and TCPC confluences are massless
total-pressure junction blocks rather than finite-storage pressure nodes.

## Parameter and Unit Conventions

1-D segment geometry uses metres and square metres. Pressures are stored in
pascal, flows in cubic metres per second, density in kilograms per cubic metre,
and wall stiffness in pascal per metre. Junction loss and wall-pressure
weights are dimensionless. Metrics convert outputs to clinical units.

## Calibration and Validation Policy

Task 013 may calibrate the baseline only. Scenario configs are validation cases
and must not be retuned independently. Candidate screening should use short
runs first; expensive 20 s runs are reserved for promising candidates and final
validation.

## Scenario Policy

Generated scenarios inherit the coupled baseline topology and time-step cap.
Pulmonary vasodilation, fenestration, and LPA obstruction are represented by
the same intervention parameter changes used in the other standardized model
families, adapted to the inserted 1-D paths.

## Documentation Regeneration

When coupled topology, 1-D block equations, junction equations,
parameterization, behavior, or accepted reference outputs change, update this
file, `README.md`, the SVG schematic, PNG schematic export, and the generated
technical reference together.

```bash
python3 scripts/modeling/build_coupled_configs.py --check
python3 scripts/docs/build_model_reference_pdfs.py --model coupled_0d_1d
python3 scripts/docs/check_model_docs.py --model coupled_0d_1d
```

## Current Limitations

The coupled model is executable and periodic at the current baseline, but it
is not yet calibrated or accepted. The aortic and TCPC junctions are algebraic
PhysioBlocks-compatible closures, not Nektar's full characteristic/Riemann
boundary treatment. The model is not clinically validated.

## Detailed Engineering Notes

### Scope

The coupled 0-D/1-D model keeps the accepted full 0-D closed-loop heart,
atrium, valves, systemic beds, pulmonary RCR beds, and fenestration, and
replaces selected aortic and TCPC shortcut pathways with true 1-D finite-volume
vessel blocks.

The model remains a local PhysioBlocks extension. Task 009 found that a local
generated/fixed-size implementation is appropriate for this stage, avoiding a
PhysioBlocks fork until a concrete solver or API blocker justifies it.

### Paper Implementation Alignment

The local Nektar implementation under
`/home/bures/geraldine/bures/2026/02-24-nektar/nektar` builds the coupled
aorta-TCPC and closed-loop cases from nine 1-D domains: four aortic domains
and five TCPC domains. Its closed-loop input builder keeps the paper's 1-D
geometry, terminal pulmonary Windkessels, and 0-D systemic coupling from aorta
to TCPC, while the Nektar solver handles characteristic/Riemann boundary
coupling internally.

The PhysioBlocks model mirrors the crucial topology where possible:

- four aortic 1-D segments and five TCPC source segments are preserved;
- LPA I and LPA II are represented as one six-cell tapered 1-D composite to
  avoid an artificial internal pressure junction;
- the aortic confluence is a massless total-pressure junction rather than a
  shared pressure node;
- the TCPC confluence is a massless wall-pressure-blended dissipative
  total-pressure junction rather than a finite-storage 0-D star junction;
- the accepted PhysioBlocks heart/atrium remain in place instead of copying
  the Nektar closed-loop heart code.

The important remaining difference is deliberate and documented: the TCPC
closure is closer to the paper's branch-wall/Riemann boundary treatment than
the old node-pressure junction, but it is still a local algebraic
PhysioBlocks closure. It uses branch wall-law pressure information and signed
dynamic minor losses, not Nektar's full characteristic boundary solver or a
3-D TCPC loss model.

### Config Generation

Closed-loop configs are generated by
`scripts/modeling/build_coupled_configs.py` from the corresponding
`models/full_0d/configs/fontan_0d_*.jsonc` files.

The generator caps all coupled scenario time steps at
\(\Delta t = 2.5\times 10^{-4}\,\mathrm{s}\) with minimum step
\(1.5625\times 10^{-5}\,\mathrm{s}\). This is a numerical stability constraint
from the inserted 1-D vessel and TCPC junction dynamics; the inherited full
0-D scenario step of \(2.0\times 10^{-3}\,\mathrm{s}\) can make the initial
coupled nonlinear solve intractable.

The generator removes these full 0-D shortcut blocks:

```text
aao_arch, arch_dao, arch_bca, arch_lcca,
svc_conduit_compliance, ivc_conduit_compliance,
rpa_conduit_compliance, lpa_conduit_compliance,
svc_conduit_rl, ivc_conduit_rl, rpa_conduit_rl, lpa_conduit_rl,
svc_conduit_junction, ivc_conduit_junction,
rpa_conduit_out, lpa_conduit_out,
tcpc_compliance
```

It also removes the shortcut nodes `svc_conduit`, `ivc_conduit`,
`rpa_conduit`, `lpa_conduit`, and `tcpc`.

The full 0-D LSA terminal pathway is retained and rewired to the new aortic
total-pressure junction. This avoids inventing a 1-D LSA segment that is absent
from the extracted patient-specific geometry while preserving upper-systemic
mass balance.

### 1-D Vessel Blocks

The Task 010 kernel solves a straight-vessel, three-cell, finite-volume 1-D
system. Task 012 uses the log-area executable variant:

```text
model_type = fixed_3cell_1d_log_area_vessel_block
state      = log_area_01, log_area_02, log_area_03, flow_00..flow_03
saved      = area_01..area_03, cell_pressure, cell_area, face_flow,
             stored_volume, min_area, negative_area_count
```

The physical cross-sectional area is recovered as:

```math
A_i = \exp(g_i)
```

where `g_i` is `log_area_i`. This preserves the positive-area domain during
closed-loop Newton iterations while keeping the same conservation equations as
the area-state prototype.

The LPA uses `fixed_6cell_tapered_1d_log_area_vessel_block`, a fixed six-cell
variant with per-cell lengths, reference areas, wall stiffnesses, and friction
coefficients. The first three cells come from LPA I and the last three cells
from LPA II, so the coupled closed-loop model no longer inserts a massless
internal LPA pressure node.

The square-root wall law is:

```math
P(A) = P_{\mathrm{ext}} + \beta\left(\sqrt{A} - \sqrt{A_0}\right)
```

and the wave speed implied by the wall law is:

```math
c(A) = \sqrt{\frac{A}{\rho}\frac{dP}{dA}},
\qquad
\frac{dP}{dA} = \frac{\beta}{2\sqrt{A}} .
```

The finite-volume continuity residual is:

```math
R_{A_i} =
\frac{A_i^{n+1}-A_i^n}{\Delta t}
+ \frac{Q_i^{n+1/2}-Q_{i-1}^{n+1/2}}{\Delta x}.
```

The face momentum residual is:

```math
R_{Q_j} =
\frac{Q_j^{n+1}-Q_j^n}{\Delta t}
+ \left[\frac{\partial}{\partial x}
\left(\alpha\frac{Q^2}{A}\right)\right]_j^{n+1/2}
+ \frac{A_{f,j}^{n+1/2}}{\rho}
\left[\frac{\partial P}{\partial x}\right]_j^{n+1/2}
+ \kappa\frac{Q_j^{n+1/2}}{A_{f,j}^{n+1/2}}.
```

For log-area Jacobian columns, the generator relies on the chain rule:

```math
\frac{\partial R}{\partial g_i}
=
\frac{\partial R}{\partial A_i}
\frac{\partial A_i}{\partial g_i}
=
\frac{\partial R}{\partial A_i} A_i .
```

### Aortic Topology

Task 012 inserts four aortic 1-D blocks:

| Block | Upstream node | Downstream node | Source segment |
| --- | --- | --- | --- |
| `coupled_aao` | `aao` | `coupled_aao_arch` | Ascending aorta |
| `coupled_dao` | `coupled_dao_arch` | `coupled_dao_out` | Thoracic aorta |
| `coupled_bca` | `coupled_bca_arch` | `coupled_bca_out` | Brachiocephalic |
| `coupled_lcca` | `coupled_lcca_arch` | `coupled_lcca_out` | Carotic left |

The massless aortic junction is represented by
`coupled_aortic_arch_junction`. Positive AAo flow enters; positive DAo, BCA,
LCCA, and retained LSA flows leave. The residuals are:

```math
Q_{\mathrm{AAo}} - Q_{\mathrm{DAo}} - Q_{\mathrm{BCA}}
- Q_{\mathrm{LCCA}} - Q_{\mathrm{LSA}} = 0,
```

```math
H_{\mathrm{AAo}} - H_k = 0,
\qquad k \in \{\mathrm{DAo},\mathrm{BCA},\mathrm{LCCA}\},
```

```math
H_{\mathrm{AAo}} - P_{\mathrm{LSA,port}} = 0,
```

where

```math
H = P + \frac{1}{2}\rho\left(\frac{Q}{A}\right)^2 .
```

The LSA port uses static pressure compatibility because no patient-specific
LSA 1-D area is available. The downstream retained `arch_lsa`,
`lsa_compliance`, and `upper_lsa_to_ca1` blocks preserve the calibrated 0-D
terminal branch.

Residual interface losses are represented by `coupled_dao_loss`,
`coupled_bca_loss`, and `coupled_lcca_loss`. Each preserves the difference
between the original full 0-D shortcut resistance and the segment Poiseuille
resistance already represented inside the 1-D block.

### TCPC Topology

Task 012 inserts SVC, IVC, and RPA three-cell TCPC 1-D blocks plus one six-cell
tapered LPA composite:

| Block | Upstream node | Downstream node | Source segment |
| --- | --- | --- | --- |
| `coupled_svc` | `svc` | `coupled_svc_tcpc` | SVC |
| `coupled_ivc` | `ivc` | `coupled_ivc_tcpc` | IVC |
| `coupled_rpa` | `coupled_rpa_tcpc` | `rpa` | RPA |
| `coupled_lpa` | `coupled_lpa_tcpc` | `lpa` | LPA I + LPA II |

The TCPC junction is represented by `coupled_tcpc_junction`, a massless
four-port wall-pressure-blended dissipative total-pressure junction with state
variables `svc_flow`, `ivc_flow`, `rpa_flow`, and `lpa_flow`. Positive SVC and
IVC branch flows enter the junction; positive RPA and LPA branch flows leave.
The mass residual is:

```math
Q_{\mathrm{SVC}} + Q_{\mathrm{IVC}}
- Q_{\mathrm{RPA}} - Q_{\mathrm{LPA}} = 0,
```

Each branch effective total pressure is:

```math
H_i^\ast = H_i + L_i,
```

```math
H_i =
w\,P_{\mathrm{wall},i}
+ (1-w)P_{\mathrm{node},i}
+ \frac{1}{2}\rho\left(\frac{Q_i}{A_i}\right)^2,
```

where `wall_pressure_weight` is currently \(w = 0.75\). The signed minor-loss
term uses the flow direction from the junction into each branch:

```math
L_i =
\frac{1}{2}\rho K
\frac{
q_{\mathrm{out},i}\sqrt{q_{\mathrm{out},i}^2+\epsilon_Q^2}
}{A_i^2},
```

where the numerator is the product
\(q_{\mathrm{out},i}\sqrt{q_{\mathrm{out},i}^2+\epsilon_Q^2}\),
dimensionless `loss_coefficient` \(K = 2.0\), and
\(\epsilon_Q = 10^{-10}\,\mathrm{m^3\,s^{-1}}\). The sign convention is
\(q_{\mathrm{out}}=-Q\) for SVC/IVC and \(q_{\mathrm{out}}=Q\) for RPA/LPA.

The compatibility residuals are:

```math
H_k^\ast - H_{\mathrm{RPA}}^\ast = 0,
\qquad k \in \{\mathrm{SVC},\mathrm{IVC},\mathrm{LPA}\}.
```

The block also exposes linearized characteristic-impedance diagnostics and a
`characteristic_scale` parameter. The current accepted startup-stable setting
keeps `characteristic_scale = 0.0`; nonzero characteristic blending remains
deferred until it can be validated as a full boundary treatment rather than a
numerical patch.

This junction removes the previous finite-storage star approximation and the
old no-loss algebraic TCPC candidate. It is scientifically defensible as a
minor-loss/dissipation correction for a TCPC confluence, but it is still not a
full Nektar characteristic/Riemann boundary treatment and does not replace a
3-D TCPC loss model.

### Free Parameters

Each 1-D block has:

- `length` in $\mathrm{m}$;
- `reference_area` in $\mathrm{m^2}$;
- `wall_stiffness` in $\mathrm{Pa\,m^{-1}}$;
- `external_pressure` in $\mathrm{Pa}$;
- `density` in $\mathrm{kg\,m^{-3}}$;
- `friction_coefficient` in $\mathrm{m^2\,s^{-1}}$;
- dimensionless `momentum_correction`.

The tapered LPA composite has per-cell `cell_length_01` through
`cell_length_06`, `reference_area_01` through `reference_area_06`,
`wall_stiffness_01` through `wall_stiffness_06`, and
`friction_coefficient_01` through `friction_coefficient_06`.

The aortic total-pressure junction has no compliance, resistance, or inertance
free parameters. Its only physical parameter is density in
\(\mathrm{kg\,m^{-3}}\); its flow states are solved by algebraic mass and
compatibility residuals.

The TCPC junction has density in \(\mathrm{kg\,m^{-3}}\), dimensionless
`wall_pressure_weight`, dimensionless `loss_coefficient`, and dimensionless
`characteristic_scale`. Current generated configs use:

```text
coupled_tcpc_junction.wall_pressure_weight = 0.75
coupled_tcpc_junction.loss_coefficient = 2.0
coupled_tcpc_junction.characteristic_scale = 0.0
```

The TCPC branch reference areas, wall stiffnesses, and external pressures are
not new fitted junction parameters; they are passed from the adjacent 1-D
segments so the junction can evaluate branch wall pressure consistently.

The executable closed-loop prototype currently uses a stiff-conduit wall scale
for TCPC blocks to keep the startup smoke numerically tractable. This setting
is not calibrated and must not be interpreted as a validated material estimate.

### Validation State

Validated:

- generated configs are reproducible with `build_coupled_configs.py --check`;
- structural tests confirm full 0-D shortcut removal and true 1-D block
  insertion;
- log-area 1-D block unit tests pass;
- tapered six-cell LPA block and total-pressure junction unit tests pass;
- the 0.025 s startup smoke case reaches launcher completion with the generated
  wall-pressure-blended dissipative TCPC closure;
- smoke metrics report no NaNs, no negative saved 1-D areas, near-zero aortic
  and TCPC junction mass residuals, passing TCPC balance, and bounded TCPC
  effective total-pressure spread around \(0.36\,\mathrm{mmHg}\).
- a 2.0 s baseline-derived diagnostic reaches launcher completion with
  `pass_no_nan = true`, `negative_coupled_1d_area_count = 0`,
  `pass_tcpc_balance = true`, and
  `tcpc_cycle_balance_rel = 0.00019884697373250603`.
- the 20 s baseline reaches launcher completion with `pass_no_nan = true`,
  `pass_no_negative_coupled_1d_area = true`, `pass_tcpc_balance = true`,
  `pass_atrium_balance = true`, `pass_ventricle_balance = true`, and
  `periodicity_cavity_volume = 0.00024257533848672484`.

Not accepted:

- the smoke case is not a periodic validation window;
- the 2.0 s diagnostic is useful for candidate screening but not final
  physiological validation;
- the 20 s baseline proves numerical viability but has not passed Task 013
  calibration and scenario-validation acceptance.

Current validation reports:

```text
models/coupled_0d_1d/reference_outputs/smoke_metrics.json
models/coupled_0d_1d/reference_outputs/closed_loop_smoke_validation.json
models/coupled_0d_1d/reference_outputs/baseline_20s_metrics.json
```

Task 013 must calibrate and validate the baseline/scenarios before any accepted
coupled-model claim is made.
