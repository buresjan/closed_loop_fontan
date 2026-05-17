# Local 1-D Numerics Prototype

Task: 010 - Prototype local 1-D numerics

Status: validated local prototype; not yet an accepted coupled closed-loop
model.

## Scope

The current implementation provides the smallest true 1-D vessel kernel needed
before patient-specific aortic or TCPC open-loop networks are built. It lives in:

```text
fontan_blocks/one_d.py
fontan_blocks/one_d_geometry.py
fontan_blocks/one_d_wall_laws.py
fontan_blocks/one_d_junctions.py
```

The production-facing block is
`fontan_blocks.one_d.Fixed3CellOneDVesselBlock`. It is intentionally fixed to
three finite-volume cells and four staggered flow faces. This keeps
PhysioBlocks state declaration static while still solving spatially discretized
1-D conservation equations.

The prototype is not a calibrated coupled Fontan model. It does not yet define
patient-specific aortic segments, TCPC branches, junction losses, outlet RCR
closures, or a closed-loop coupled config.

## State Variables

For a straight vessel of length $L$ split into $N = 3$ cells,

$$\Delta x = \frac{L}{3}.$$

The cell-centered area states are:

$$A_i(t), \quad i = 1,2,3.$$

The staggered face-flow states are:

$$Q_j(t), \quad j = 0,1,2,3.$$

Positive $Q$ points from local node 1 to local node 2. PhysioBlocks node fluxes
therefore use:

$$Q_{\mathrm{node\,1}} = -Q_0,$$

$$Q_{\mathrm{node\,2}} = Q_3.$$

## Wall Law

The prototype uses a nonlinear square-root pressure-area law:

$$P(A) = P_{\mathrm{ext}} + \beta\left(\sqrt{A} - \sqrt{A_0}\right).$$

The derivative used in the momentum Jacobian is:

$$\frac{dP}{dA} = \frac{\beta}{2\sqrt{A}}.$$

The local wave speed implied by the wall law is:

$$c(A) = \sqrt{\frac{A}{\rho}\frac{dP}{dA}}.$$

For a desired reference wave speed $c_0$ at $A_0$,

$$\beta = \frac{2\rho c_0^2}{\sqrt{A_0}}.$$

## Continuity Residual

The finite-volume mass residual in cell $i$ is:

$$R_{A_i}
= \frac{A_i^{n+1} - A_i^n}{\Delta t}
+ \frac{Q_{i}^{n+1/2} - Q_{i-1}^{n+1/2}}{\Delta x}.$$

This gives the discrete volume balance:

$$\frac{V^{n+1} - V^n}{\Delta t}
= Q_0^{n+1/2} - Q_3^{n+1/2},$$

with:

$$V = \sum_{i=1}^{3} A_i \Delta x.$$

## Momentum Residual

The face-flow residual is a Crank-Nicolson discretization of the nonlinear 1-D
momentum equation:

$$
R_{Q_j}
= \frac{Q_j^{n+1} - Q_j^n}{\Delta t}
+ \left[\frac{\partial}{\partial x}
\left(\alpha\frac{Q^2}{A}\right)\right]_j^{n+1/2}
+ \frac{A_{f,j}^{n+1/2}}{\rho}
\left[\frac{\partial P}{\partial x}\right]_j^{n+1/2}
+ \kappa\frac{Q_j^{n+1/2}}{A_{f,j}^{n+1/2}}.
$$

Here $\alpha$ is the momentum correction coefficient, $\rho$ is blood density,
$A_{f,j}$ is the area interpolated to face $j$, and $\kappa$ is the linear
friction coefficient used by this prototype. Boundary pressure gradients use
half-cell distances:

$$
\left[\frac{\partial P}{\partial x}\right]_0
= \frac{P(A_1) - P_{\mathrm{in}}}{\Delta x / 2},
$$

$$
\left[\frac{\partial P}{\partial x}\right]_3
= \frac{P_{\mathrm{out}} - P(A_3)}{\Delta x / 2}.
$$

Internal pressure gradients use full cell-center spacing.

## Free Parameters

All units follow the repository SI convention.

| Parameter | Meaning | Unit |
|---|---|---|
| `length` | Straight vessel length $L$ | $\mathrm{m}$ |
| `reference_area` | Reference lumen area $A_0$ | $\mathrm{m^2}$ |
| `wall_stiffness` | Wall-law stiffness $\beta$ | $\mathrm{Pa\,m^{-1}}$ |
| `external_pressure` | External pressure $P_{\mathrm{ext}}$ | $\mathrm{Pa}$ |
| `density` | Blood density $\rho$ | $\mathrm{kg\,m^{-3}}$ |
| `friction_coefficient` | Linear friction coefficient $\kappa$ | $\mathrm{m^2\,s^{-1}}$ |
| `momentum_correction` | Momentum correction coefficient $\alpha$ | dimensionless |

## Saved Quantities

The fixed 3-cell block saves:

- `cell_pressure`: $P(A_i)$ for all cells;
- `cell_area`: midpoint cell areas;
- `face_flow`: midpoint face flows;
- `stored_volume`: $\sum_i A_i\Delta x$;
- `min_area`: minimum midpoint area;
- `negative_area_count`: count of cells with non-positive midpoint area.

## Validation Status

The focused tests in `tests/test_one_d_numerics.py` validate:

- wall-law inversion and wave-speed targeting;
- zero drift at equal inlet/outlet pressure with zero flow;
- positive forward acceleration under a pressure drop;
- characteristic speeds matching the requested wave speed;
- volume conservation against inlet-minus-outlet flow;
- non-positive area diagnostics;
- analytic Jacobian agreement with finite differences;
- PhysioBlocks residual, gradient, flux, and saved-quantity assembly.

## Limitations Before Task 011

- The block is fixed to three cells; patient-specific segment resolution should
  be generated as scalar/fixed-size components rather than configured at run
  time.
- The prototype has no characteristic, RCR, or measured-flow boundary closure.
- There are no bifurcation or TCPC junction equations yet.
- Area positivity is diagnostic only; the nonlinear solver does not yet enforce
  a positivity-preserving step.
- No open-loop aorta or TCPC model has been promoted from this prototype.
