# Implementation notes

## Current state

The coupled 0-D/1-D model family is reserved for later tasks and is not
executable yet. No coupled configs, 1-D vessel blocks, coupling interfaces, or
reference outputs are accepted at this stage.

## Intended scope

The intended model keeps the calibrated 0-D heart, atrium, valves, systemic
beds, pulmonary Windkessel beds, and fenestration while replacing the aortic
and TCPC pathways with true 1-D subdomains:

```text
0-D heart / valves -> 1-D aorta -> 0-D systemic beds
0-D caval returns -> 1-D TCPC -> 0-D pulmonary beds
0-D pulmonary beds -> 0-D active atrium
```

The aorta and TCPC parts must be validated as open-loop 1-D submodels before
they are inserted into the closed loop.

## Documentation convention

This model family must follow the same documentation discipline as `full_0d`
and `quasi_0d_1d`:

```text
README.md
docs/coupled_0d_1d_schematic.svg
docs/coupled_0d_1d_schematic.png
docs/coupled_0d_1d_technical_reference.md
docs/coupled_0d_1d_technical_reference.pdf
docs/implementation_notes.md
```

When the coupled topology is implemented, update the README, SVG schematic,
PNG export, implementation notes, technical reference source, and technical
reference PDF in the same change.
