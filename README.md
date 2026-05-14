# closed_loop_fontan

Closed-loop Fontan circulation models and calibration/reference data workflows.

The repository is organized for three model families:

| Model family | Status | Description |
|---|---|---|
| `models/full_0d` | active | Current full 0-D closed-loop PhysioBlocks model. |
| `models/quasi_0d_1d` | planned | Future PhysioBlocks-only quasi 0-D/1-D model with no real 1-D solver parts. |
| `models/coupled_0d_1d` | planned | Future coupled 0-D/1-D model with the aorta and TCPC represented by 1-D models. |

Each model family owns its README, schematic, configs, and model-specific notes. Model changes must keep the schematic and README synchronized.

## Setup

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
```

## Current Full 0-D Model

Run the smoke case:

```bash
python scripts/run_one.py models/full_0d/configs/fontan_0d_smoke.jsonc --series Smoke
```

Compute metrics from a generated run:

```bash
python scripts/metrics.py runs/simulations/Smoke/*/main.csv models/full_0d/configs/fontan_0d_smoke.jsonc --out models/full_0d/reference_outputs/smoke_metrics.json
```

See `models/full_0d/README.md` for the topology, scenarios, and model caveats.

## Aramburu 2024 Data

The raw `Aramburu_et_al_2024_Heliyon_e30404.zip` archive is kept locally under `data/raw/` and is not committed. Standardized calibration/reference outputs are tracked under `data/processed/aramburu_2024/`.

Regenerate the processed data:

```bash
python scripts/data/prepare_aramburu_2024.py
```

The processed package includes canonical measurement tables, paper-result tables, model-input tables, converted Nektar 1-D `.mat` outputs, `.fo` outputs, metadata, and source checksums.

## Tests

```bash
pytest -q
```

## License

Repository code is MIT licensed. Third-party data derived from Aramburu et al. 2024 is provided with provenance metadata and is not relicensed as MIT.
