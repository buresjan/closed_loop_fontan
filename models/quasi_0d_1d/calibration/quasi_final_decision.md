# Quasi Final Decision

Task 008.6 status: `stable_quasi_development_scaffold_not_scientifically_superior`

Promoted candidate: `none`

## Rationale

No Task 008.6 candidate passed all closure gates. Full 0-D remains the calibrated reference; quasi remains a stable development scaffold.

## Reference

Task 008.5 remains the canonical quasi state unless a promoted candidate is
listed above.

| Candidate | Hard score | Direct score | Paper score | Failed hard gates | Failed waveform gates |
|---|---:|---:|---:|---|---|
| task0085_reference | 0.0561 | 0.0592 | 0.0805 | edv;esv;stroke_volume;cardiac_output | ascending_aorta_flow;descending_aorta_flow |

## Best Task 008.6 Candidates

| Criterion | Candidate | Value | Failed hard gates | Failed waveform gates |
|---|---|---:|---|---|
| Hard clinical score | current_heart_099 | 0.0632 | edv;esv;rpa_pressure;lpa_pressure | ascending_aorta_flow;descending_aorta_flow;rpa_pressure |
| Waveform regression RMS | aortic_L0_5 | 0.0742 | edv;esv;rpa_pressure;lpa_pressure | ascending_aorta_flow;descending_aorta_flow;rpa_pressure |
| Aggregate direct score | current_heart_099 | 0.0624 | edv;esv;rpa_pressure;lpa_pressure | ascending_aorta_flow;descending_aorta_flow;rpa_pressure |

## Interpretation

The Task 008.6 matrix evaluated 23 candidates. No
candidate satisfied the hard, paper-comparison, waveform, stability, and
mass-balance gates together.

The best hard-score and aggregate-direct candidates still fail hard pump or
proximal pulmonary pressure gates. The best waveform candidate reduces the
waveform regression RMS but still fails AAo/DAo flow and hard-target gates.

No tracked quasi config, schematic, or implementation topology is promoted by
this closure. Candidate configs and runs remain under `runs/quasi_0086/` for
inspection only.

Task 009 can proceed with full 0-D as the calibrated reference and quasi as a
stable non-superior intermediate scaffold.
