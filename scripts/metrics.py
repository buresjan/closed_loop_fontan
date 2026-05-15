#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, math
from pathlib import Path
from typing import Any
import numpy as np
import pandas as pd

MMHG_PER_PA = 0.00750062
ML_PER_M3 = 1e6
L_MIN_PER_M3_S = 60000.0

CONDUIT_FLUXES = [
    'svc_conduit_rl.flux',
    'ivc_conduit_rl.flux',
    'rpa_conduit_rl.flux',
    'lpa_conduit_rl.flux',
]

LEGACY_PRESSURE_NODES = [
    'atrial',
    'cavity',
    'aao',
    'aortic_arch',
    'bca',
    'lcca',
    'lsa',
    'upper_art',
    'upper_ven',
    'dao',
    'lower_art',
    'lower_ven',
    'svc',
    'svc_conduit',
    'ivc',
    'ivc_conduit',
    'tcpc',
    'rpa_conduit',
    'lpa_conduit',
    'rpa',
    'lpa',
]

EDGES = {
    'aao_arch': ('aao', 'aortic_arch'),
    'arch_bca': ('aortic_arch', 'bca'),
    'upper_bca_to_ca1': ('bca', 'upper_art'),
    'arch_lcca': ('aortic_arch', 'lcca'),
    'upper_lcca_to_ca1': ('lcca', 'upper_art'),
    'arch_lsa': ('aortic_arch', 'lsa'),
    'upper_lsa_to_ca1': ('lsa', 'upper_art'),
    'upper_rc1': ('upper_art', 'upper_ven'),
    'upper_rv1': ('upper_ven', 'svc'),
    'arch_dao': ('aortic_arch', 'dao'),
    'lower_ra4': ('dao', 'lower_art'),
    'lower_rc2': ('lower_art', 'lower_ven'),
    'lower_rv2': ('lower_ven', 'ivc'),
    'svc_conduit_junction': ('svc_conduit', 'tcpc'),
    'ivc_conduit_junction': ('ivc_conduit', 'tcpc'),
    'rpa_conduit_out': ('rpa_conduit', 'rpa'),
    'lpa_conduit_out': ('lpa_conduit', 'lpa'),
    'fenestration': ('ivc', 'atrial'),
}

RCR_BEDS = {
    'right_lung': ('rpa', 'atrial'),
    'left_lung': ('lpa', 'atrial'),
}

FULL_0D_VESSEL_FLOWS = {
    'aao_arch': ('aao_arch.flow', 'aao_arch.flow'),
    'dao': ('arch_dao.flow', 'arch_dao.flow'),
    'svc': ('svc_conduit_rl.flux', 'svc_conduit_junction.flow'),
    'ivc': ('ivc_conduit_rl.flux', 'ivc_conduit_junction.flow'),
    'rpa': ('rpa_conduit_rl.flux', 'rpa_conduit_out.flow'),
    'lpa': ('lpa_conduit_rl.flux', 'lpa_conduit_out.flow'),
}

QUASI_CHAINS = ['aao_arch', 'dao', 'svc', 'ivc', 'rpa', 'lpa']

def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())

def with_resistor_flows(df: pd.DataFrame, cfg: dict[str, Any]) -> pd.DataFrame:
    df = df.copy()
    params = cfg['parameters']
    blocks = cfg['net']['blocks']
    for name, (src, dst) in EDGES.items():
        if name not in blocks:
            continue
        key = f'{name}.resistance'
        if key not in params:
            continue
        psrc = f'{src}.blood_pressure'
        pdst = f'{dst}.blood_pressure'
        if psrc in df and pdst in df:
            df[f'{name}.flow'] = (df[psrc] - df[pdst]) / float(params[key])
    for name, (src, dst) in RCR_BEDS.items():
        block = blocks.get(name)
        if block is None or block.get('model_type') != 'rcr_block':
            continue
        r1_key = f'{name}.resistance_1'
        r2_key = f'{name}.resistance_2'
        psrc = f'{src}.blood_pressure'
        pmid = f'{name}.pressure_mid'
        pdst = f'{dst}.blood_pressure'
        if r1_key in params and psrc in df and pmid in df:
            df[f'{name}_prox.flow'] = (df[psrc] - df[pmid]) / float(params[r1_key])
        if r2_key in params and pmid in df and pdst in df:
            df[f'{name}_dist.flow'] = (df[pmid] - df[pdst]) / float(params[r2_key])
            df[f'{name}.flow'] = df[f'{name}_dist.flow']
    return df

def pressure_nodes(cfg: dict[str, Any]) -> list[str]:
    nodes = list(cfg['net'].get('nodes', []))
    for node in LEGACY_PRESSURE_NODES:
        if node not in nodes:
            nodes.append(node)
    return nodes

def quasi_chain_flux_columns(df: pd.DataFrame, cfg: dict[str, Any], chain: str) -> list[str]:
    blocks = cfg['net']['blocks']
    prefix = f'quasi_{chain}_rl_'
    cols = [
        f'{name}.flux'
        for name, block in sorted(blocks.items())
        if name.startswith(prefix)
        and block.get('model_type') == 'hydraulic_rl_block'
        and f'{name}.flux' in df
    ]
    return cols

def vessel_flow_columns(
    df: pd.DataFrame,
    cfg: dict[str, Any],
) -> dict[str, dict[str, str | list[str]]]:
    vessels: dict[str, dict[str, str | list[str]]] = {}

    for vessel, (inlet, outlet) in FULL_0D_VESSEL_FLOWS.items():
        if inlet in df and outlet in df:
            internal = [] if inlet == outlet else [inlet, outlet]
            vessels[vessel] = {
                'inlet': inlet,
                'outlet': outlet,
                'internal': internal,
            }

    for vessel in QUASI_CHAINS:
        cols = quasi_chain_flux_columns(df, cfg, vessel)
        if cols:
            vessels[vessel] = {
                'inlet': cols[0],
                'outlet': cols[-1],
                'internal': cols,
            }

    return vessels

def last_cycle(df: pd.DataFrame, period: float) -> pd.DataFrame:
    return df[df['time'] >= df['time'].max() - period].copy()

def integ(sub: pd.DataFrame, col: str) -> float:
    if col not in sub or len(sub) < 2:
        return 0.0
    trapz = getattr(np, 'trapezoid', None)
    if trapz is None:
        trapz = np.trapz
    return float(trapz(sub[col].to_numpy(), sub['time'].to_numpy()))

def periodicity(df: pd.DataFrame, col: str, period: float) -> float:
    if col not in df:
        return math.nan
    tmax = df['time'].max()
    a = df[df['time'] >= tmax - period][['time', col]].copy()
    b = df[(df['time'] >= tmax - 2 * period) & (df['time'] < tmax - period)][['time', col]].copy()
    if len(a) < 5 or len(b) < 5:
        return math.nan
    b_t = b['time'].to_numpy() + period
    interp = np.interp(a['time'].to_numpy(), b_t, b[col].to_numpy())
    denom = max(float(a[col].max() - a[col].min()), 1e-12)
    return float(np.max(np.abs(a[col].to_numpy() - interp)) / denom)

def add_flow_summary(out: dict[str, Any], sub: pd.DataFrame, col: str) -> None:
    out[f'mean_{col}_ml_s'] = float(sub[col].mean() * ML_PER_M3)
    out[f'integral_{col}_ml'] = float(integ(sub, col) * ML_PER_M3)

def add_vessel_storage_metrics(
    out: dict[str, Any],
    sub: pd.DataFrame,
    vessels: dict[str, dict[str, str | list[str]]],
) -> None:
    for vessel, cols in vessels.items():
        inlet = str(cols['inlet'])
        outlet = str(cols['outlet'])
        if inlet not in sub or outlet not in sub:
            continue
        q_in = integ(sub, inlet)
        q_out = integ(sub, outlet)
        storage = q_in - q_out
        out[f'mean_{vessel}_inlet_flow_ml_s'] = float(sub[inlet].mean() * ML_PER_M3)
        out[f'mean_{vessel}_outlet_flow_ml_s'] = float(sub[outlet].mean() * ML_PER_M3)
        out[f'integral_{vessel}_inlet_flow_ml'] = float(q_in * ML_PER_M3)
        out[f'integral_{vessel}_outlet_flow_ml'] = float(q_out * ML_PER_M3)
        out[f'{vessel}_cycle_storage_ml'] = float(storage * ML_PER_M3)
        out[f'{vessel}_mass_balance_rel'] = float(
            abs(storage) / (abs(q_in) + abs(q_out) + 1e-15)
        )

def balance_rel(integrals_in: list[float], integrals_out: list[float]) -> float:
    numerator = abs(sum(integrals_in) - sum(integrals_out))
    denominator = sum(abs(v) for v in [*integrals_in, *integrals_out]) + 1e-15
    return float(numerator / denominator)

def compute(csv: Path, config: Path) -> dict[str, Any]:
    cfg = load(config)
    df = with_resistor_flows(pd.read_csv(csv), cfg)
    period = 60.0 / float(cfg['parameters']['heart_rate'])
    sub = last_cycle(df, period)
    vessels = vessel_flow_columns(sub, cfg)
    out: dict[str, Any] = {}
    for node in pressure_nodes(cfg):
        col = f'{node}.blood_pressure'
        if col in sub:
            out[f'mean_{node}_pressure_mmHg'] = float(sub[col].mean() * MMHG_PER_PA)
            out[f'min_{node}_pressure_mmHg'] = float(sub[col].min() * MMHG_PER_PA)
            out[f'max_{node}_pressure_mmHg'] = float(sub[col].max() * MMHG_PER_PA)
    for name in ['right_lung', 'left_lung']:
        col = f'{name}.pressure_mid'
        if col in sub:
            out[f'mean_{name}_pressure_mid_mmHg'] = float(sub[col].mean() * MMHG_PER_PA)
            out[f'min_{name}_pressure_mid_mmHg'] = float(sub[col].min() * MMHG_PER_PA)
            out[f'max_{name}_pressure_mid_mmHg'] = float(sub[col].max() * MMHG_PER_PA)
    if 'active_atrium.volume' in sub:
        out['mean_active_atrium_volume_ml'] = float(sub['active_atrium.volume'].mean() * ML_PER_M3)
        out['min_active_atrium_volume_ml'] = float(sub['active_atrium.volume'].min() * ML_PER_M3)
        out['max_active_atrium_volume_ml'] = float(sub['active_atrium.volume'].max() * ML_PER_M3)
    if 'active_atrium.activation' in sub:
        out['max_active_atrium_activation'] = float(sub['active_atrium.activation'].max())
    if 'active_atrium.elastance' in sub:
        out['min_active_atrium_elastance'] = float(sub['active_atrium.elastance'].min())
        out['max_active_atrium_elastance'] = float(sub['active_atrium.elastance'].max())
    if 'cavity.volume' in sub:
        out['EDV_ml'] = float(sub['cavity.volume'].max() * ML_PER_M3)
        out['ESV_ml'] = float(sub['cavity.volume'].min() * ML_PER_M3)
        out['SV_from_volume_ml'] = out['EDV_ml'] - out['ESV_ml']
        out['periodicity_cavity_volume'] = periodicity(df, 'cavity.volume', period)
    for col in ['valve_atrium.flux', 'valve_arterial.flux']:
        if col in sub:
            out[f'integral_{col}_ml'] = float(integ(sub, col) * ML_PER_M3)
            out[f'CO_from_{col}_L_min'] = float(sub[col].mean() * L_MIN_PER_M3_S)
            out[f'periodicity_{col}'] = periodicity(df, col, period)
    for col in [c for c in sub.columns if c.endswith('.flow')]:
        add_flow_summary(out, sub, col)
    for col in CONDUIT_FLUXES:
        if col in sub:
            add_flow_summary(out, sub, col)
    for vessel_cols in vessels.values():
        for col in vessel_cols.get('internal', []):
            if col in sub and f'mean_{col}_ml_s' not in out:
                add_flow_summary(out, sub, col)
    add_vessel_storage_metrics(out, sub, vessels)
    if {'svc', 'ivc', 'rpa', 'lpa'} <= set(vessels):
        q_svc = integ(sub, str(vessels['svc']['inlet']))
        q_ivc = integ(sub, str(vessels['ivc']['inlet']))
        q_rpa = integ(sub, str(vessels['rpa']['outlet']))
        q_lpa = integ(sub, str(vessels['lpa']['outlet']))
        out['tcpc_cycle_balance_rel'] = balance_rel([q_svc, q_ivc], [q_rpa, q_lpa])
        q_svc_j = integ(sub, str(vessels['svc']['outlet']))
        q_ivc_j = integ(sub, str(vessels['ivc']['outlet']))
        q_rpa_j = integ(sub, str(vessels['rpa']['inlet']))
        q_lpa_j = integ(sub, str(vessels['lpa']['inlet']))
        out['tcpc_junction_cycle_balance_rel'] = balance_rel(
            [q_svc_j, q_ivc_j],
            [q_rpa_j, q_lpa_j],
        )
    else:
        out['tcpc_cycle_balance_rel'] = math.nan
        out['tcpc_junction_cycle_balance_rel'] = math.nan
    q_pulm = integ(sub, 'right_lung.flow') + integ(sub, 'left_lung.flow')
    q_fen = integ(sub, 'fenestration.flow')
    q_av = integ(sub, 'valve_atrium.flux')
    out['atrium_cycle_balance_rel'] = abs(q_pulm + q_fen - q_av) / (abs(q_pulm)+abs(q_fen)+abs(q_av)+1e-15)
    q_ao = integ(sub, 'valve_arterial.flux')
    out['ventricle_cycle_balance_rel'] = abs(q_av - q_ao) / (abs(q_av)+abs(q_ao)+1e-15)
    if {'rpa', 'lpa'} <= set(vessels):
        mr = sub[str(vessels['rpa']['outlet'])].mean()
        ml = sub[str(vessels['lpa']['outlet'])].mean()
    else:
        mr = sub['rpa_conduit_out.flow'].mean() if 'rpa_conduit_out.flow' in sub else math.nan
        ml = sub['lpa_conduit_out.flow'].mean() if 'lpa_conduit_out.flow' in sub else math.nan
    out['rpa_flow_fraction'] = float(mr / (mr + ml + 1e-15))
    out['pass_no_nan'] = bool(not df.isna().any().any())
    out['pass_tcpc_balance'] = bool(out['tcpc_cycle_balance_rel'] < 1e-2 and out['tcpc_junction_cycle_balance_rel'] < 1e-2)
    out['pass_atrium_balance'] = bool(out['atrium_cycle_balance_rel'] < 1e-2)
    out['pass_ventricle_balance'] = bool(out['ventricle_cycle_balance_rel'] < 1e-2)
    return out

def main():
    p = argparse.ArgumentParser()
    p.add_argument('csv', type=Path)
    p.add_argument('config', type=Path)
    p.add_argument('--out', type=Path)
    args = p.parse_args()
    data = compute(args.csv, args.config)
    text = json.dumps(data, indent=2, sort_keys=True)
    print(text)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + '\n')
if __name__ == '__main__':
    main()
