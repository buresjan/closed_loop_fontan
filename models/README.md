# Fontan Model Families

This directory contains the standardized closed-loop Fontan model families used
by the repository. Each family has the same documentation contract so models can
be compared without guessing which files are authoritative.

## Model Status

| Model | Current role | Numerical formulation | Acceptance state |
|---|---|---|---|
| `full_0d` | Go-to full 0-D reference | Lumped PhysioBlocks closed loop | Accepted calibrated reference |
| `quasi_0d_1d` | Go-to quasi 0-D/1-D model | PhysioBlocks R-L-C vessel chains | Accepted against the frozen quasi superiority gate |
| `coupled_0d_1d` | True 0-D/1-D development model | Local finite-volume 1-D aorta and TCPC blocks coupled to the 0-D loop | Executable and periodic at the Task 012 baseline; Task 013 calibration is in progress |

The planned Nektar-complex model series must be added as a separate family,
`coupled_0d_1d_nektar`, only after its scaffold task creates the complete
standard artifact set.

## Required Artifact Contract

Every model family must contain:

```text
models/<model>/README.md
models/<model>/configs/
models/<model>/calibration/
models/<model>/reference_outputs/
models/<model>/docs/implementation_notes.md
models/<model>/docs/<model>_schematic.svg
models/<model>/docs/<model>_schematic.png
models/<model>/docs/<model>_technical_reference.md
models/<model>/docs/<model>_technical_reference.pdf
```

The model README is the quick operational entry point. It must use the shared
section order:

```text
Status
Scientific Scope
Canonical Configs
Topology Summary
Numerical Formulation
Parameter Sources and Calibration
Validation State
Run Commands
Reference Outputs
Known Limitations
Documentation Regeneration
```

The implementation notes are the engineering contract. They must use the shared
section order:

```text
Status
Scope and Canonical Configs
Topology and Naming
Block and Numerical Conventions
Parameter and Unit Conventions
Calibration and Validation Policy
Scenario Policy
Documentation Regeneration
Current Limitations
```

The technical references are generated long-form documents with equations,
segment inventory, and free-parameter tables. Regenerate them with:

```bash
python3 scripts/docs/build_model_reference_pdfs.py --model full_0d
python3 scripts/docs/build_model_reference_pdfs.py --model quasi_0d_1d
python3 scripts/docs/build_model_reference_pdfs.py --model coupled_0d_1d
```

Check the documentation contract with:

```bash
python3 scripts/docs/check_model_docs.py
```

## Scientific Status Rules

Documentation must distinguish these claims:

- `executable`: the launcher completes for the stated smoke or baseline case;
- `numerically stable`: no NaNs, positive vessel areas where applicable, and
  mass-balance checks pass over the stated validation window;
- `periodic`: atrium, ventricle, and relevant junction balance checks pass over
  the stated final cycle;
- `calibrated`: baseline targets have been optimized and scored against the
  documented target set;
- `accepted`: the model has passed the model-family acceptance gate and its
  reference outputs, calibration reports, schematic, implementation notes, and
  technical reference have all been updated together.

Do not use a lower aggregate objective score alone to claim acceptance if hard
targets, waveform checks, mass balance, stability, or scenario validation fail.
