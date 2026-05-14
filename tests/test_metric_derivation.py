from __future__ import annotations
import json
from pathlib import Path
import pandas as pd
from scripts.metrics import with_resistor_flows

ROOT = Path(__file__).resolve().parents[1]
FULL_0D_CONFIGS = ROOT / 'models' / 'full_0d' / 'configs'

def test_resistor_flow_is_source_pressure_minus_target_pressure():
    cfg = json.loads((FULL_0D_CONFIGS / 'fontan_0d_baseline.jsonc').read_text())
    df = pd.DataFrame({'time': [0.0], 'svc_conduit.blood_pressure': [1600.0], 'tcpc.blood_pressure': [1200.0]})
    out = with_resistor_flows(df, cfg)
    assert out['svc_conduit_junction.flow'].iloc[0] == (1600.0 - 1200.0) / cfg['parameters']['svc_conduit_junction.resistance']

def test_upper_and_lower_bed_flow_orientations():
    cfg = json.loads((FULL_0D_CONFIGS / 'fontan_0d_baseline.jsonc').read_text())
    df = pd.DataFrame({
        'time': [0.0],
        'upper_art.blood_pressure': [9000.0],
        'upper_ven.blood_pressure': [4000.0],
        'lower_art.blood_pressure': [8000.0],
        'lower_ven.blood_pressure': [3000.0],
    })
    out = with_resistor_flows(df, cfg)
    assert out['upper_rc1.flow'].iloc[0] == (9000.0 - 4000.0) / cfg['parameters']['upper_rc1.resistance']
    assert out['lower_rc2.flow'].iloc[0] == (8000.0 - 3000.0) / cfg['parameters']['lower_rc2.resistance']

def test_pulmonary_rcr_flows_use_mid_pressure():
    cfg = json.loads((FULL_0D_CONFIGS / 'fontan_0d_baseline.jsonc').read_text())
    df = pd.DataFrame({
        'time': [0.0],
        'rpa.blood_pressure': [1500.0],
        'right_lung.pressure_mid': [1100.0],
        'atrial.blood_pressure': [700.0],
    })
    out = with_resistor_flows(df, cfg)
    assert out['right_lung_prox.flow'].iloc[0] == (1500.0 - 1100.0) / cfg['parameters']['right_lung.resistance_1']
    assert out['right_lung_dist.flow'].iloc[0] == (1100.0 - 700.0) / cfg['parameters']['right_lung.resistance_2']
    assert out['right_lung.flow'].iloc[0] == out['right_lung_dist.flow'].iloc[0]
