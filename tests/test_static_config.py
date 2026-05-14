from __future__ import annotations
import json
from pathlib import Path
import fontan_blocks
from physioblocks.registers.type_register import is_registered

ROOT = Path(__file__).resolve().parents[1]
FULL_0D = ROOT / 'models' / 'full_0d'
FULL_0D_CONFIGS = FULL_0D / 'configs'
OLD_ATRIAL_COMPLIANCE = 6.000510043353685e-08

def load(name):
    return json.loads((FULL_0D_CONFIGS / name).read_text())

def test_configs_are_strict_json_and_forward_simulations():
    for path in FULL_0D_CONFIGS.glob('fontan_0d_*.jsonc'):
        cfg = json.loads(path.read_text())
        assert cfg['type'] == 'forward_simulation'
        assert cfg['net']['type'] == 'net'

def test_each_model_family_has_readme_and_schematic():
    for model_dir in (ROOT / 'models').iterdir():
        if not model_dir.is_dir():
            continue
        assert (model_dir / 'README.md').exists()
        schematics = list((model_dir / 'docs').glob('*.svg'))
        assert schematics, f'{model_dir.name} is missing an SVG schematic'

def test_uses_real_physioblocks_full_schema():
    cfg = load('fontan_0d_baseline.jsonc')
    blocks = cfg['net']['blocks']
    assert blocks['cavity']['type'] == 'block_description'
    assert blocks['cavity']['model_type'] == 'spherical_cavity_block'
    assert blocks['cavity']['submodels']['dynamics']['type'] == 'model_description'

def test_closed_loop_no_boundary_conditions():
    cfg = load('fontan_0d_baseline.jsonc')
    assert cfg['net']['boundaries_conditions'] == {}

def test_required_blocks_present():
    cfg = load('fontan_0d_baseline.jsonc')
    types = {b['model_type'] for b in cfg['net']['blocks'].values()}
    assert {'spherical_cavity_block', 'valve_rl_block', 'c_block', 'rc_block', 'rcr_block', 'time_varying_elastance_atrium_block'} <= types
    assert fontan_blocks.TimeVaryingElastanceAtriumBlock is not None
    assert is_registered('time_varying_elastance_atrium_block')

def test_active_atrium_replaces_passive_atrial_compliance():
    cfg = load('fontan_0d_baseline.jsonc')
    b = cfg['net']['blocks']
    assert 'atrial_compliance' not in b
    assert b['active_atrium']['model_type'] == 'time_varying_elastance_atrium_block'
    assert b['active_atrium']['nodes'] == {'1': 'atrial'}
    assert b['active_atrium']['pressure_external'] == 'pleural.pressure'
    p = cfg['parameters']
    assert 'atrial_compliance.capacitance' not in p
    assert abs(p['active_atrium.elastance_min'] - 1.0 / OLD_ATRIAL_COMPLIANCE) < 1e-6
    assert p['active_atrium.elastance_max'] > p['active_atrium.elastance_min']
    assert p['active_atrium.activation_start'] < p['active_atrium.activation_peak'] < p['active_atrium.activation_end']
    assert 0.0 < p['active_atrium.activation_start'] < 1.0

def test_tcpc_topology_and_resistor_orientation():
    cfg = load('fontan_0d_baseline.jsonc')
    nodes = set(cfg['net']['nodes'])
    assert {'svc_conduit', 'ivc_conduit', 'tcpc', 'rpa_conduit', 'lpa_conduit'} <= nodes
    b = cfg['net']['blocks']
    assert {'svc_tcpc', 'ivc_tcpc', 'tcpc_rpa', 'tcpc_lpa'}.isdisjoint(b)
    assert b['svc_conduit_rl']['model_type'] == 'valve_rl_block'
    assert b['ivc_conduit_rl']['model_type'] == 'valve_rl_block'
    assert b['rpa_conduit_rl']['model_type'] == 'valve_rl_block'
    assert b['lpa_conduit_rl']['model_type'] == 'valve_rl_block'
    assert b['svc_conduit_rl']['nodes'] == {'1': 'svc', '2': 'svc_conduit'}
    assert b['ivc_conduit_rl']['nodes'] == {'1': 'ivc', '2': 'ivc_conduit'}
    assert b['rpa_conduit_rl']['nodes'] == {'1': 'tcpc', '2': 'rpa_conduit'}
    assert b['lpa_conduit_rl']['nodes'] == {'1': 'tcpc', '2': 'lpa_conduit'}
    assert b['svc_conduit_junction']['nodes'] == {'1': 'tcpc', '2': 'svc_conduit'}
    assert b['ivc_conduit_junction']['nodes'] == {'1': 'tcpc', '2': 'ivc_conduit'}
    assert b['rpa_conduit_out']['nodes'] == {'1': 'rpa', '2': 'rpa_conduit'}
    assert b['lpa_conduit_out']['nodes'] == {'1': 'lpa', '2': 'lpa_conduit'}
    assert b['svc_conduit_compliance']['nodes'] == {'1': 'svc_conduit'}
    assert b['ivc_conduit_compliance']['nodes'] == {'1': 'ivc_conduit'}
    assert b['rpa_conduit_compliance']['nodes'] == {'1': 'rpa_conduit'}
    assert b['lpa_conduit_compliance']['nodes'] == {'1': 'lpa_conduit'}

def test_pulmonary_beds_are_rcr_windkessels():
    cfg = load('fontan_0d_baseline.jsonc')
    b = cfg['net']['blocks']
    assert b['right_lung']['model_type'] == 'rcr_block'
    assert b['left_lung']['model_type'] == 'rcr_block'
    assert b['right_lung']['nodes'] == {'1': 'rpa', '2': 'atrial'}
    assert b['left_lung']['nodes'] == {'1': 'lpa', '2': 'atrial'}
    assert b['right_lung']['pressure_mid'] == 'right_lung.pressure_mid'
    assert b['left_lung']['pressure_mid'] == 'left_lung.pressure_mid'
    p = cfg['parameters']
    assert 'right_lung.resistance' not in p
    assert 'left_lung.resistance' not in p
    assert p['right_lung.resistance_1'] > 0.0
    assert p['right_lung.resistance_2'] > 0.0
    assert p['left_lung.capacitance'] > 0.0

def test_aortic_tree_topology_and_resistor_orientation():
    cfg = load('fontan_0d_baseline.jsonc')
    nodes = set(cfg['net']['nodes'])
    assert {
        'aao', 'aortic_arch', 'bca', 'lcca', 'lsa', 'upper_art',
        'upper_ven', 'dao', 'lower_art', 'lower_ven'
    } <= nodes
    assert 'aorta' not in nodes
    b = cfg['net']['blocks']
    assert b['valve_arterial']['nodes'] == {'1': 'cavity', '2': 'aao'}
    assert b['aao_arch']['nodes'] == {'1': 'aortic_arch', '2': 'aao'}
    assert b['arch_bca']['nodes'] == {'1': 'bca', '2': 'aortic_arch'}
    assert b['arch_lcca']['nodes'] == {'1': 'lcca', '2': 'aortic_arch'}
    assert b['arch_lsa']['nodes'] == {'1': 'lsa', '2': 'aortic_arch'}
    assert b['arch_dao']['nodes'] == {'1': 'dao', '2': 'aortic_arch'}
    assert {'bca_body', 'lcca_body', 'lsa_body', 'lower_body'}.isdisjoint(b)
    assert b['upper_bca_to_ca1']['nodes'] == {'1': 'upper_art', '2': 'bca'}
    assert b['upper_lcca_to_ca1']['nodes'] == {'1': 'upper_art', '2': 'lcca'}
    assert b['upper_lsa_to_ca1']['nodes'] == {'1': 'upper_art', '2': 'lsa'}
    assert b['upper_rc1']['nodes'] == {'1': 'upper_ven', '2': 'upper_art'}
    assert b['upper_rv1']['nodes'] == {'1': 'svc', '2': 'upper_ven'}
    assert b['lower_ra4']['nodes'] == {'1': 'lower_art', '2': 'dao'}
    assert b['lower_rc2']['nodes'] == {'1': 'lower_ven', '2': 'lower_art'}
    assert b['lower_rv2']['nodes'] == {'1': 'ivc', '2': 'lower_ven'}
    assert b['upper_ca1']['nodes'] == {'1': 'upper_art'}
    assert b['upper_cv1']['nodes'] == {'1': 'upper_ven'}
    assert b['lower_ca2']['nodes'] == {'1': 'lower_art'}
    assert b['lower_cv2']['nodes'] == {'1': 'lower_ven'}

def test_aortic_tree_parameterization_preserves_upper_body_split():
    cfg = load('fontan_0d_baseline.jsonc')
    p = cfg['parameters']
    upper_paths = [
        p['arch_bca.resistance'] + p['upper_bca_to_ca1.resistance'],
        p['arch_lcca.resistance'] + p['upper_lcca_to_ca1.resistance'],
        p['arch_lsa.resistance'] + p['upper_lsa_to_ca1.resistance'],
    ]
    parallel_upper = 1.0 / sum(1.0 / r for r in upper_paths)
    upper_bed = p['upper_rc1.resistance'] + p['upper_rv1.resistance']
    lower_bed = p['lower_ra4.resistance'] + p['lower_rc2.resistance'] + p['lower_rv2.resistance']
    equivalent_upper = p['aao_arch.resistance'] + parallel_upper + upper_bed
    equivalent_lower = p['aao_arch.resistance'] + p['arch_dao.resistance'] + lower_bed
    assert abs(equivalent_upper - 506623600.0) < 1e-6
    assert abs(equivalent_lower - 266644000.0) < 1e-6

def test_intervention_configs_change_expected_parameters():
    base = load('fontan_0d_baseline.jsonc')['parameters']
    vaso = load('fontan_0d_vasodilation.jsonc')['parameters']
    fen = load('fontan_0d_fenestration.jsonc')['parameters']
    lpa = load('fontan_0d_lpa_obstruction.jsonc')['parameters']
    def lung_resistance(params, side):
        return params[f'{side}.resistance_1'] + params[f'{side}.resistance_2']
    assert lung_resistance(vaso, 'right_lung') < lung_resistance(base, 'right_lung')
    assert lung_resistance(vaso, 'left_lung') < lung_resistance(base, 'left_lung')
    assert fen['fenestration.resistance'] < base['fenestration.resistance']
    assert lung_resistance(lpa, 'left_lung') > lung_resistance(base, 'left_lung')
    assert lpa['lpa_conduit_rl.conductance'] < base['lpa_conduit_rl.conductance']
    assert lpa['lpa_conduit_out.resistance'] > base['lpa_conduit_out.resistance']

def test_tcpc_conduit_parameterization_preserves_previous_pathway_resistances():
    cfg = load('fontan_0d_baseline.jsonc')
    p = cfg['parameters']
    old_pathway_resistances = {
        'svc': 10665760.000000002,
        'ivc': 7999320.0,
        'rpa': 5332880.000000001,
        'lpa': 5332880.000000001,
    }
    for path, old_r in old_pathway_resistances.items():
        rl_r = 1.0 / p[f'{path}_conduit_rl.conductance']
        connector_r = p[f'{path}_conduit_junction.resistance'] if path in {'svc', 'ivc'} else p[f'{path}_conduit_out.resistance']
        assert abs((rl_r + connector_r) - old_r) < 1e-6
        assert p[f'{path}_conduit_rl.conductance'] == p[f'{path}_conduit_rl.backward_conductance']
        assert p[f'{path}_conduit_rl.inductance'] > 0.0

def test_pulmonary_windkessel_parameterization_preserves_lung_resistances():
    cfg = load('fontan_0d_baseline.jsonc')
    p = cfg['parameters']
    assert abs(p['right_lung.resistance_1'] + p['right_lung.resistance_2'] - 31997280.0) < 1e-6
    assert abs(p['left_lung.resistance_1'] + p['left_lung.resistance_2'] - 31997280.0) < 1e-6
    assert abs(p['right_lung.resistance_1'] / (p['right_lung.resistance_1'] + p['right_lung.resistance_2']) - 0.4) < 1e-12
    assert p['right_lung.capacitance'] == p['left_lung.capacitance']
    assert 'right_lung.pressure_mid' in cfg['variables_initialization']
    assert 'left_lung.pressure_mid' in cfg['variables_magnitudes']

def test_final_scenarios_run_long_enough_for_vascular_bed_settling():
    final_configs = [
        'fontan_0d_baseline.jsonc',
        'fontan_0d_vasodilation.jsonc',
        'fontan_0d_fenestration.jsonc',
        'fontan_0d_lpa_obstruction.jsonc',
    ]
    for name in final_configs:
        assert load(name)['time']['duration'] >= 8.0
    assert load('fontan_0d_smoke.jsonc')['time']['duration'] < 1.0
