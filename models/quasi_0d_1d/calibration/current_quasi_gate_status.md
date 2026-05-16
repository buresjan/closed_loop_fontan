# Current Quasi Superiority Gate Status

Task 008.7 status: `not_superior_to_full_0d`

Accepted as superior: `False`

Failed gate groups: `score_non_regression, pump_non_regression, fontan_pulmonary_non_regression, aortic_waveform_no_regression`

## Summary Scores

| Score | Full 0-D reference | Current quasi | Pass |
|---|---:|---:|---|
| Hard clinical summary | 0.0433 | 0.0561 | False |
| Aggregate direct | 0.0614 | 0.0592 | True |
| Paper-model | 0.0793 | 0.0805 | False |
| AAo flow nRMSE | 0.5718 | 0.5602 | True |
| DAo chain-health flow nRMSE | 0.4337 | 0.9520 | False |

## Gate Groups

| Gate group | Pass |
|---|---|
| Stability and balance | True |
| Score non-regression | False |
| Pump target non-regression | False |
| Fontan/pulmonary target non-regression | False |
| Aortic flow waveform no-regression | False |
| Quasi-specific vascular improvement | True |

## Interpretation

The current quasi model is not superior to the full 0-D reference under the
frozen Task 008.7 gate. Later quasi candidates must pass this same gate without
relaxing thresholds or allowing soft/problematic targets to compensate for
hard pump, paper-model, stability, or aortic-flow failures.
