# Quasi 0-D/1-D Fontan Model

This model family is reserved for the future quasi 0-D/1-D Fontan closed-loop model.
Task 005 adds the first parameter layer for that model: geometry-derived
R-L-C chain priors and a JSON config fragment for later executable configs.

Planned intent:

- remain entirely PhysioBlocks-based;
- represent additional quasi-1-D structure without coupling to a true 1-D solver;
- use the standardized Aramburu 2024 data package for calibration and comparison.

Executable configs, run commands, scenario outputs, and calibration reports are
still pending. Every model change must update this README and the schematic in
`docs/`.

## Derived vessel priors

`scripts/modeling/derive_quasi_vessel_parameters.py` reads the processed
Aramburu aorta/Fontan geometry, the target policy, and the calibrated full 0-D
baseline. It emits:

```text
models/quasi_0d_1d/calibration/parameter_priors.yaml
models/quasi_0d_1d/config_fragments/quasi_vessel_chains.json
```

The first-pass chain counts are:

| Chain | Source geometry | Segments | Resistance policy |
|---|---|---:|---|
| AAo/arch | Ascending aorta | 4 | geometry Poiseuille |
| DAo | Thoracic aorta | 6 | geometry Poiseuille |
| SVC | SVC | 3 | calibrated full 0-D pathway prior |
| IVC | IVC | 5 | calibrated full 0-D pathway prior |
| RPA | RPA | 3 | calibrated full 0-D pathway prior |
| LPA | LPA I + LPA II | 4 | calibrated full 0-D pathway prior |

The aortic resistance policy intentionally does not preserve the excessive
full 0-D AAo-to-DAo pressure drop. Aortic R/L/C priors are derived from geometry
and the 5.35 m/s wave-speed prior; most systemic pressure loss should stay in
the systemic beds. Fontan-limb resistances start from the calibrated full 0-D
pathway values because the current Fontan pressures and pulmonary flow split are
accepted baseline physiology.

The LPA narrowing is explicit in the generated priors as
`quasi_lpa.narrowing_radius_m = 0.003`.

The JSON fragment uses `hydraulic_rl_block` and `c_block` entries only. It is a
construction input for Task 006, not a runnable closed-loop config.

The schematic in `docs/schematic.svg` intentionally follows the same circuit
style and component set as the full 0-D schematic. The quasi-specific change is
that the aortic and Fontan pathway labels show the derived R-L-C chain counts.
`docs/schematic.png` is the exported browser-friendly copy, and
`docs/implementation_notes.md` records the current topology and parameter
conventions.
