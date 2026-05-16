# Quasi Design Audit Report

Generated for Task 008.6.

## Flow Signal Audit

- Best quasi AAo-flow candidate: `valve_arterial.flux` at `aortic-valve outlet/root inflow` with nRMSE `0.560`.
- Best quasi DAo-flow candidate: `lower_ra4.flow` at `flow from DAo pressure node into lower systemic artery` with nRMSE `0.381`.
- Sign-flipped comparisons were worse for the selected quasi candidates, so the regression is not explained by sign convention alone.
- Phase-shifted nRMSE is tracked in `dao_aao_flow_signal_audit.csv`; large improvements after phase shift indicate timing contribution, not acceptance.
- The closer DAo diagnostic is downstream of the DAo pressure node. The closure gate still tracks the DAo-chain outlet because switching only to lower systemic bed entry would hide trunk-chain waveform behavior rather than fix it.

## Compliance And Storage

- Quasi chain estimated gauge storage is `9.607` ml, small compared with retained systemic and caval endpoint storage.
- The quasi model adds chain capacitances on top of retained endpoint compliances; this is documented for later redistribution tests.

## Characteristic Impedance

- Characteristic impedance ratios are tracked in `characteristic_impedance_report.csv`.
- Large ratios are interpreted as possible artificial reflection points and should guide the ablation grid.

## Conclusion

The AAo/DAo flow failure should be treated as a real design/calibration issue until a candidate topology or R/L/C ablation removes the regression. Task 008.6 should not promote a quasi reference unless the closure gate accepts it.
