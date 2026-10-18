"""Check integrated r3 design; keep physical and visual task acceptance separate."""
import argparse, copy, datetime, hashlib, importlib.util, json, math, subprocess, sys
from pathlib import Path
P=Path(__file__).resolve().parent
ROOT=P.parent.parent

def read(name): return json.loads((P/name).read_text())

def inspect_compute_baseline(c):
    """A Zero-envelope design screen is not qualification of the borrowed board."""
    errors=[]
    compute=c.get('compute',{}); q=compute.get('pi_qualification',{})
    if compute.get('pi_options') != ['Raspberry Pi Zero W (first generation, soldered 40-pin header)','Raspberry Pi 3 Model B V1.2']:
        errors.append('Available boards must match user-confirmed Zero W with header and Pi 3B V1.2')
    if compute.get('board_identity_confirmed') is not True:
        errors.append('User-confirmed board identity must be recorded')
    if compute.get('pi_selected_variant') is not None:
        errors.append('Final board qualification has not been completed')
    if 'Zero 2' in compute.get('pi','') or any('Zero 2' in row for row in c.get('required_resources',[])):
        errors.append('Zero 2 W incorrectly reinstated as current compute/borrowing requirement')
    if q.get('cad_envelope') != 'existing Pi Zero form factor only':
        errors.append('Existing CAD must remain explicitly limited to the Pi Zero envelope')
    for key in ('selected_board_qualified','pi3_mount_verified','pi3_power_budget_verified','zero1_runtime_verified','wireless_available_verified'):
        if q.get(key) is not False:
            errors.append('Unverified borrowed-board qualification claimed or omitted: '+key)
    if not c.get('power',{}).get('pi_branch_budget_scope') or 'does not qualify Pi 3' not in c.get('acceptance',{}).get('design',''):
        errors.append('Baseline power/design screen must not qualify Pi 3')
    for row in c.get('connections',[]):
        if row['id'] in ('pi_power','pi_usb','openrb_usb','camera','imu','audio_data','mac_wifi') and row.get('board_scope') != 'existing_pi_zero_form_factor_baseline_unqualified_for_selected_board':
            errors.append('Pi connection presented as board-independent: '+row['id'])
    return errors

def inspect(c):
    errors=inspect_compute_baseline(c)
    def require(condition, message):
        if not condition: errors.append(message)
    context=json.loads((ROOT/'PROJECT-CONTEXT.json').read_text())
    require(set(context['required_capabilities']) <= set(c['designed_capabilities']), 'Required visual capability omitted')
    require(len(c['active_robot_sources'])==1 and c['active_robot_sources'][0]==c['source']['model']=='ROBOTIS SMPS 12V 5A (PS-10)', 'One selected robot source required')
    for k,v in c['training'].items():
        path=ROOT/v['path']
        require(path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest()==v['sha256'], 'Training identity: '+k)
    expected=json.loads((ROOT/context['training']['results']).read_text())
    require(c['training']['checkpoint']['sha256']==expected['checkpointSha256'], 'Checkpoint differs from completed training')
    require(c['training']['exported_actor']['sha256']==expected['actorSha256'], 'Actor differs from validated export')
    ids=[n for g in c['fuses']['motor_branches']['groups'] for n in g]
    require(sorted(ids)==list(range(1,16)) and len(ids)==15, 'All fifteen motors must have exactly one fused group')
    require(c['fuses']['pi']['installed']==1 and c['fuses']['audio']['installed']==1, 'Logic/audio protection missing')
    require(c['compute']['camera']=='SC1224' and c['compute']['camera_cable']=='SC1892','Existing Zero-envelope camera/ribbon baseline changed; this check does not qualify the borrowed board')
    require(c['compute']['speaker_w']==1 and c['compute']['gain_resistor_ohm']==100000, 'Audio load/gain mismatch')
    pins=[p for group in c['pi_physical_pins'].values() for p in group]
    require(len(pins)==len(set(pins)) and all(1<=p<=40 for p in pins),'Header pin conflict')
    require(c['pi_physical_pins']['power_positive']==[2,4] and c['pi_physical_pins']['power_ground']==[6,14],'Pi power pin mismatch')
    conn={r['id']:r for r in c['connections']}
    require(conn['pi_usb']['end']==conn['openrb_usb']['start']=='SC0727 USB-A female','USB middle mating mismatch')
    require(conn['pi_usb']['start']=='Pi USB Micro-B female' and conn['openrb_usb']['end']=='OpenRB USB-C female','USB endpoint mismatch')
    require(all(r.get(k) for r in conn.values() for k in ('start','end','medium','length','termination','role')),'Incomplete cable definition')
    require(not c['power']['motor_power_via_openrb'],'Motor current incorrectly routed through controller')
    require(c['source']['nominal_v']==12 and c['source']['rated_a']==5 and c['source']['rated_w']==60,'12 V wall supply rating mismatch')
    require('SMPS2DXL' in c['source']['adapter'] and c['source']['cable_wires']['pin3_data']=='cut short and insulated','SMPS2DXL cable splice mismatch')
    require(c['source']['screen_v_min']<=c['source']['nominal_v'] and c['source']['fuse'] is None,'Wall-end screen voltage or fuse mismatch')
    require(c['power']['twelve_v_loads']==['DFR1202 VIN'],'12 V must reach only the DFR1202 input')
    require('12 V' in conn['tether']['role'] and 'no fuse' in conn['tether']['medium'] and conn['regulator_input']['role']=='12 V power','Tether is not the 12 V chain')
    calc=read('power-calculation.json')
    for current in [c['power']['continuous_budget_a'], c['power']['short_peak_budget_a']]:
        voltage=c['source']['screen_v_min']; eff=min(calc['assumptions']['efficiency_range']); resistance=calc['assumptions']['upstream_loop_resistance_max_ohm']
        demand=calc['assumptions']['regulator_output_v_high']*current/eff
        disc=voltage*voltage-4*resistance*demand
        source_a=(voltage-math.sqrt(disc))/(2*resistance) if disc>=0 else math.inf
        require(source_a<=c['source']['rated_a'],f'Whole robot capacity exceeds source at {current} A')
    require(c['power']['nonmotor_reserve_a']>=2,'Camera/audio/logic missing from complete-load budget')
    require(c['power']['long_tether_v']==12 and c['power']['long_tether_awg']==18,'Long high-current 5V cable regression')
    require('250 mm' in conn['motor_groups']['length'],'Motor branch wires too short')
    require('400mm' in conn['motor_data']['length'],'Ankle data link lacks routed reach')
    require(c['motor_data_chain']==['OpenRB',15,14,13,11,12,5,4,3,2,1,6,7,8,9,10],'Motor data physical chain mismatch')
    require(conn['pi_power']['length']=='250 mm each' and '22 AWG' in conn['pi_power']['medium'],'Pi harness reach/conductor mismatch')
    require('250 mm' in conn['imu']['length'],'Torso IMU harness lacks reach and service margin')
    require(c['mechanical']['expected_instances']==89 and len(c['mechanical']['add'])==4,'Print quantities omit restored functional parts')
    for name in list(c['mechanical']['replace'].values())+c['mechanical']['add']:
        require((P/name).is_file(),'Missing physical mounting/print part: '+name)
    require(c['mechanical']['owned_bank_fits_original_bay'] is False,'Oversized owned bank falsely accepted')
    require(c['acceptance']['physical_tests']==0 and c['acceptance']['visual_trials']==0,'Unmeasured hardware success claimed')
    require(c['acceptance']['old_cart_evidence']=='stale after r3 substitutions','Old basket presented as current')
    manifest=read('print-manifest.json')
    print_check=read('print-queue-verification.json')
    require(manifest['queue_count']==c['mechanical']['expected_instances']==print_check['instances'], 'Actual print queue differs from contract')
    require(hashlib.sha256((P/'current-print-queue.3mf').read_bytes()).hexdigest()==print_check['sha256'], 'Print project changed after verification')
    require(hashlib.sha256((P/'print-manifest.json').read_bytes()).hexdigest()==print_check['manifest_sha256'], 'Print manifest changed after verification')
    reach=read('harness-reach-review.json')
    require(reach['250mm_pi_lead_length_screen_passed'] and reach['250mm_imu_lead_length_screen_passed'], 'Selected cables fail model reach')
    require(calc['pi_header_input_screen']['voltage_min_v']>=4.75, 'Pi cable fails endpoint voltage screen')
    require(calc['pi_header_input_screen']['oneway_m_max']==0.25, 'Voltage calculation does not use actual Pi cable length')
    bom=json.loads((P.parent/'procurement/bom.json').read_text())
    require(bom['revision']==c['revision'],'Procurement revision differs from design')
    require(all(r['purchase']['packages']==0 for r in bom['items'] if r['id'] in ('servo','controller')), 'Already ordered hardware duplicated')
    require({r['purchase']['store'] for r in bom['items'] if r['purchase']['packages']}=={'DigiKey'},'Remaining supplier missing')
    assembly=c.get('assembly',{})
    require(assembly.get('schedule')=='assembly-fasteners.json' and assembly.get('guide')=='ASSEMBLY.html', 'Current per-connection assembly handoff omitted')
    require(c['mechanical']['header_housing_acceptance_envelope_mm']==[7,52,15], 'GPIO housing loses Pi screw-head clearance')
    if assembly:
        from verify_assembly_handoff import inspect_assembly
        errors += inspect_assembly()
    return errors

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scope',choices=['design','project'],default='design')
    args=parser.parse_args()
    c=read('design-contract.json'); errors=inspect(c)
    negative={}
    def case(name, mutate):
        altered=copy.deepcopy(c); mutate(altered); negative[name]=bool(inspect(altered))
    case('zero2_requirement_returned',lambda x:x['compute'].update(pi='Raspberry Pi Zero 2 W'))
    case('pi3_falsely_qualified',lambda x:x['compute']['pi_qualification'].update(pi3_mount_verified=True))
    case('pi3_power_falsely_qualified',lambda x:x['compute']['pi_qualification'].update(pi3_power_budget_verified=True))
    case('unconfirmed_zero_wifi',lambda x:x['compute']['pi_qualification'].update(wireless_available_verified=True))
    case('omitted_camera',lambda x:x['compute'].update(camera=None))
    case('lost_perception_goal',lambda x:x.update(designed_capabilities=['learned_jaw_control']))
    case('lost_trained_actor',lambda x:x['training']['exported_actor'].update(sha256='0'*64))
    case('two_robot_sources',lambda x:x['active_robot_sources'].append('second USB supply'))
    case('pd_20v_chain_returned',lambda x:x['source'].update(nominal_v=20))
    case('twelve_volt_on_openrb_rail',lambda x:x['power']['twelve_v_loads'].append('OpenRB VIN'))
    case('fuse_returned_to_tether',lambda x:x['connections'][1].update(medium='18 AWG pair with 5 A input fuse'))
    case('missing_fifteenth_motor',lambda x:x['fuses']['motor_branches']['groups'].pop())
    case('USB_wrong_receptacle',lambda x:x['connections'][7].update(start='USB-C female'))
    case('whole_load_10A_rejected',lambda x:x['power'].update(continuous_budget_a=10))
    case('audio_logic_budget_omitted',lambda x:x['power'].update(nonmotor_reserve_a=0))
    case('GPIO_pin_conflict',lambda x:x['pi_physical_pins'].update(amp_din=[2]))
    case('too_short_Pi_wire',lambda x:x['connections'][5].update(length='100 mm each'))
    case('too_short_motor_feed',lambda x:x['connections'][4].update(length='150 mm'))
    case('ankle_trip_wire',lambda x:x['connections'][8].update(length='all180mm acrossfeet'))
    case('camera_bracket_missing',lambda x:x['mechanical']['add'].pop())
    case('bank_wrong_fit',lambda x:x['mechanical'].update(owned_bank_fits_original_bay=True))
    case('old_cart_readback_reused',lambda x:x['acceptance'].update(old_cart_evidence='current'))
    case('simulation_relabeled_hardware',lambda x:x['acceptance'].update(physical_tests=12))
    case('missing_per_connection_fasteners',lambda x:x.pop('assembly',None))
    case('old_header_zero_head_clearance',lambda x:x['mechanical'].update(header_housing_acceptance_envelope_mm=[7,54,15]))
    if not all(negative.values()): errors.append('Negative regression failed to reject a known defect')
    dependencies={}
    for name in ['power-review-verification.json','mechanical-geometry-verification.json','usb-service-window-verification.json','print-queue-verification.json','motor-harness-reach.json']:
        item=read(name); passed=item.get('passed',item.get('all_passed',False))
        dependencies[name]=bool(passed)
        if not passed: errors.append('Dependency verification failed: '+name)
    gpio=read('gpio-housing-review.json')
    dependencies['gpio-housing-review.json']=gpio['selected_envelope_passed'] and gpio['negative_18mm_housing_rejected']
    if not dependencies['gpio-housing-review.json']: errors.append('Header housing interference not resolved')
    # Source and shape measurements are retained separately from unmeasured assembly tests.
    module_path=P.parent/'phase1/check_project_context.py'
    spec=importlib.util.spec_from_file_location('project_review',module_path); module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    project=module.review()
    if not project['training_evidence_verified']: errors+=project['training_errors']
    result={'checked_at':datetime.datetime.now().astimezone().isoformat(),'revision':c['revision'],
            'design_passed':not errors,'design_acceptance_scope':c['acceptance']['design'],
            'selected_pi_qualified':False,'pi_qualification':c['compute']['pi_qualification'],'errors':errors,'negative_regressions':negative,
            'source_geometry_dependencies':dependencies,'named_connections':len(c['connections']),
            'training_evidence_verified':project['training_evidence_verified'],
            'physical_tests':0,'visual_task_passed':project['project_handoff_ready'] and c['compute']['pi_qualification']['selected_board_qualified'],
            'visual_task_missing_capabilities':project['missing_capabilities'],
            'commissioning_required':'Receive and assemble parts; loaded voltage/current/temperature/transients, connector fit, camera/control timing and physical pickup trials.',
            'scope':args.scope}
    (P/'design-verification.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
    if errors or (args.scope=='project' and (not project['project_handoff_ready'] or not c['compute']['pi_qualification']['selected_board_qualified'])): raise SystemExit(1)

if __name__=='__main__': main()
