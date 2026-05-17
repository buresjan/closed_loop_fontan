# PhysioBlocks 1-D Feasibility Decision

Task: 009 - PhysioBlocks 1-D feasibility spike

Status: local repository path accepted for the next stage; no PhysioBlocks fork
is justified yet.

## Question

The coupled model will eventually need true 1-D aorta and TCPC subdomains. The
feasibility question was whether those subdomains can be prototyped cleanly with
repo-local PhysioBlocks extensions, or whether PhysioBlocks internals must be
changed before Task 010.

The specific risk was state sizing. PhysioBlocks builds internal state from
class-level expression definitions declared with decorators. That means an
arbitrary config-time value such as `number_of_cells` cannot resize a block's
internal variables after the class has been registered.

## Probe Implemented

`fontan_blocks.one_d_feasibility.Fixed3Cell1DProbeBlock` is a feasibility-only
block. It is deliberately not a production vessel model.

The probe uses PhysioBlocks-native extension points:

- `@register_type`
- `@dataclass`
- `Quantity`-annotated fields
- `@declares_internal_equation`
- `@declares_flux`
- `@declares_saved_quantity`

It declares a fixed three-cell vessel with:

- scalar internal area terms `area_01` through `area_03`;
- scalar internal face-flow terms `flow_00` through `flow_03`;
- vector residual functions for continuity and momentum;
- inlet/outlet pressure-node fluxes;
- vector saved cell pressure plus scalar min/max area diagnostics.

The residuals tested are:

```text
dA_i/dt + (Q_{i+1} - Q_i) / dx = 0
L dQ_j/dt + R Q_j - P_left + P_right = 0
P(A) = P_ext + beta * (sqrt(A) - sqrt(A0))
```

## Evidence

The focused tests in `tests/test_physioblocks_1d_feasibility.py` show that:

- local registered blocks can expose fixed-size 1-D-like state without changing
  PhysioBlocks internals;
- PhysioBlocks can assemble vector residual expressions when each residual row
  is mapped to fixed scalar internal terms;
- analytic gradient assembly works for the fixed scalar terms;
- inlet/outlet node flux coupling works with the existing `blood_flow` /
  `blood_pressure` flux-DOF registration;
- vector saved quantities work for cell pressure diagnostics;
- `number_of_cells` can be present as a parameter, but it cannot resize the
  state because internal variables are fixed by the registered block class.

The relevant PhysioBlocks internals confirm this:

- `ModelComponentMetaClass` collects internal variables from class-level
  decorator metadata;
- `SimulationFactory.build_state` adds those class-declared variables before
  parameters are initialized;
- `EqSystem` assembles dense residual and gradient arrays.

## Decision

Proceed locally for Task 010.

The recommended clean path is generated scalar/fixed-size local components, not
a monolithic config-sized 1-D block. The next implementation should generate
explicit cell/face state terms and block/config structure from vessel geometry,
so PhysioBlocks sees normal registered scalar terms and deterministic residual
sizes.

Do not fork PhysioBlocks at the start of Task 010.

## Rejected Alternatives

### Monolithic Config-Sized 1-D Block

Rejected for now. A block whose internal variable count depends on
`number_of_cells` is not cleanly supported by the current decorator and state
construction flow.

### Many Manually Written Fixed-Size Classes

Rejected as the primary path. It is feasible for a single probe, but it would be
hard to maintain across different aorta and TCPC mesh sizes.

### Immediate PhysioBlocks Fork

Rejected for now. The spike found a clean local route for the next task. A fork
should be considered only if later prototypes show that dense Jacobian scaling,
area positivity safeguards, or boundary-coupling controls cannot be handled
locally.

## Concrete PhysioBlocks API Changes If Needed Later

If Tasks 010 or 011 block on PhysioBlocks internals, the required changes should
be stated as concrete API work:

- instance/config-dependent internal variable declaration sizes;
- sparse residual/Jacobian assembly and sparse linear solve support;
- solver-level damping or positivity constraints for vessel area;
- explicit boundary-coupling controls for mixed pressure/flow 0-D/1-D ports.

## Next Task Guidance

Task 010 should implement local 1-D numerical prototypes using generated
scalar/fixed-size terms first. It should validate wall law, continuity,
momentum, boundary sign conventions, area positivity diagnostics, and Jacobian
behavior before any open-loop aorta or TCPC submodel is promoted.
