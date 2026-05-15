#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from pathlib import Path

def load(p: Path): return json.loads(p.read_text())
def pct(a, b): return 100.0 * (a-b) / b if b else float('nan')

def main():
    p = argparse.ArgumentParser()
    p.add_argument('baseline', type=Path)
    p.add_argument('vasodilation', type=Path)
    p.add_argument('fenestration', type=Path)
    p.add_argument('lpa_obstruction', type=Path)
    a = p.parse_args()
    base = load(a.baseline)
    for name, path in [('vasodilation', a.vasodilation), ('fenestration', a.fenestration), ('lpa_obstruction', a.lpa_obstruction)]:
        m = load(path)
        print(f'\n{name}')
        keys = [
            'CO_from_valve_arterial.flux_L_min',
            'mean_tcpc_pressure_mmHg',
            'mean_active_atrium_volume_ml',
            'max_active_atrium_activation',
            'mean_right_lung_pressure_mid_mmHg',
            'mean_left_lung_pressure_mid_mmHg',
            'mean_svc_inlet_flow_ml_s',
            'mean_svc_outlet_flow_ml_s',
            'mean_ivc_inlet_flow_ml_s',
            'mean_ivc_outlet_flow_ml_s',
            'mean_rpa_inlet_flow_ml_s',
            'mean_rpa_outlet_flow_ml_s',
            'mean_lpa_inlet_flow_ml_s',
            'mean_lpa_outlet_flow_ml_s',
            'mean_right_lung.flow_ml_s',
            'mean_left_lung.flow_ml_s',
            'mean_right_lung_prox.flow_ml_s',
            'mean_left_lung_prox.flow_ml_s',
            'rpa_flow_fraction',
            'mean_fenestration.flow_ml_s',
            'svc_cycle_storage_ml',
            'ivc_cycle_storage_ml',
            'rpa_cycle_storage_ml',
            'lpa_cycle_storage_ml',
            'svc_mass_balance_rel',
            'ivc_mass_balance_rel',
            'rpa_mass_balance_rel',
            'lpa_mass_balance_rel',
            'tcpc_cycle_balance_rel',
            'tcpc_junction_cycle_balance_rel',
            'atrium_cycle_balance_rel',
            'ventricle_cycle_balance_rel',
        ]
        for key in keys:
            if key in m and key in base:
                print(f'  {key}: {m[key]:.6g} ({pct(m[key], base[key]):+.2f}%)')
            elif key in m:
                print(f'  {key}: {m[key]:.6g}')
if __name__ == '__main__': main()
