# Aramburu 2024 Processed Data

This directory contains standardized calibration/reference data derived from `Aramburu_et_al_2024_Heliyon_e30404.zip`.

Tracked outputs include:

- `measurements.csv`: canonical SI measurement waveforms.
- `measurements_clinical.csv`: comparison-friendly waveforms in mmHg, ml/s, and ml.
- `paper_results/`: CSV exports of `results.xlsx`.
- `model_inputs/`: curated geometry, waveform, coupling, and closed-loop input tables from `data.xlsx`.
- `nektar_1d/`: converted selected Nektar 1-D MATLAB fields as gzipped per-domain CSV files.
- `fo_outputs/`: converted `.fo` 0-D/coupled output files.
- `comparison/`: last-cycle clinical tables aligned with the MATLAB comparison scripts.
- `targets/`: shared summary and waveform calibration targets generated after
  data preparation with `scripts/calibration/extract_targets.py`.
- `manifest.yaml`: source checksums and provenance.
- `variables.yaml`: canonical variable names, units, and conversions.

The raw archive and extracted raw files stay under `data/raw/` and are ignored by Git.
