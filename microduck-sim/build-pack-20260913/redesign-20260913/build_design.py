"""Build the current interface contract and readable hardware handoff."""
from pathlib import Path
import json, hashlib, html

P = Path(__file__).resolve().parent
ROOT = P.parent.parent
REV = 'microduck-charger-camera-r3'

def save(name, value):
    (P / name).write_text(json.dumps(value, indent=2) + '\n')

def connection(name, start, end, medium, length, termination, role):
    return dict(id=name, start=start, end=end, medium=medium, length=length,
                termination=termination, role=role)

context = json.loads((ROOT / 'PROJECT-CONTEXT.json').read_text())
training = context['training']
groups = [[1,2],[3,4],[5,10],[6,7],[8,9],[11,12],[13,14],[15]]
contract = {
    'revision': REV, 'problem_ids': ['P0','P5','P6'],
    'goal': context['goal'],
    'designed_capabilities': context['required_capabilities'],
    'implemented_capabilities': [],
    'implementation_scope': 'Hardware architecture and build instructions; unassembled, visual software integration remains.',
    'active_robot_sources': ['ROBOTIS SMPS 12V 5A (PS-10)'],
    'source': {'model':'ROBOTIS SMPS 12V 5A (PS-10)', 'nominal_v':12, 'rated_a':5, 'rated_w':60,
               'screen_v_min':11.5,
               'screen_v_basis':'lowest accepted reading at the XT30 female before the robot is connected (guide step pd-tether)',
               'adapter':'ROBOTIS SMPS2DXL (SMPS2Dynamixel)',
               'cable':'ROBOTIS 3-wire cable plugged into the SMPS2DXL, far servo plug cut off',
               'cable_wires':{'pin2_vdd':'+12 V, spliced to the tether red wire',
                              'pin1_gnd':'GND, found with a meter, spliced to the tether black wire',
                              'pin3_data':'cut short and insulated'},
               'origin':'owned set from an OMX-AI kit allocated to the duck (order 2034348); not the arm set, not the reserved third kit',
               'fuse':None, 'decided':'2026-10-13 (PROJECT-CONTEXT current_build.wall_power_change_20261013)'},
    'power': {'regulator':'DFRobot DFR1202', 'regulator_location':'on robot, original battery cavity',
              'regulator_output_v':5, 'continuous_budget_a':5, 'short_peak_budget_a':7.4,
              'budget_basis':'Calculation allocations at 5 V, not measured: 3 A sustained servo acceptance limit (guide step current, PROJECT-CONTEXT current_build.servo_power_path) or 5.4 A simulated 20 ms servo peaks (guide/extension-20261012-neck-audio/page/power_section.py), plus the 2 A non-motor reserve.',
              'superseded_budget':{'continuous_a':9, 'short_peak_a':9.5, 'source':'r3 screen against the 20 V/3.25 A PD source (power-calculation.json); exceeds the 60 W 12 V supply'},
              'nonmotor_reserve_a':2, 'pi_branch_budget_a':1.5,
              'long_tether_v':12, 'long_tether_m':2, 'long_tether_awg':18,
              'twelve_v_loads':['DFR1202 VIN'],
              'input_connector':'FIT0586 XT30 pair', 'input_source_contacts':'recessed female',
              'main_5v_awg':16, 'main_5v_length_m_max':0.1,
              'motor_power_via_openrb':False, 'pi_power':'parallel header leads',
              'pi_branch_budget_scope':'Unvalidated Zero-form-factor baseline; 1.5 A is not an accepted Pi 3 demand budget.',
              'pi_pwr_in_usb':'empty and covered', 'physical_current_limiter':False},
    'fuses': {'input':{'a':5,'installed':1,'spare':0},
              'motor_main':{'a':10,'installed':1,'spare':0},
              'motor_branches':{'a':3,'groups':groups},
              'pi':{'a':3,'installed':1}, 'branch_3a_spares':0,
              'audio':{'a':0.5,'installed':1,'spare':0}},
    'servo_ids':list(range(1,16)),
    'motor_data_chain':['OpenRB',15,14,13,11,12,5,4,3,2,1,6,7,8,9,10],
    'motor_branch_y_shift_toward_torso_mm':{'F7':20,'F8':30},
    'servo_order':context['current_build']['servo_order'],
    'training':{k:{'path':training[k], 'sha256':hashlib.sha256((ROOT / training[k]).read_bytes()).hexdigest()}
                for k in ('checkpoint','exported_actor')},
    'compute':{'pi':'First-generation Raspberry Pi Zero W with soldered 40-pin header; preferred integration board',
               'pi_options':['Raspberry Pi Zero W (first generation, soldered 40-pin header)', 'Raspberry Pi 3 Model B V1.2'], 'pi_selected_variant':None, 'pi_preferred_variant':'Raspberry Pi Zero W (first generation)', 'board_identity_confirmed':True,
               'pi_qualification':{'cad_envelope': 'existing Pi Zero form factor only', 'selected_board_qualified': False, 'pi3_mount_verified': False, 'pi3_power_budget_verified': False, 'zero1_runtime_verified': False, 'wireless_available_verified': False, 'connection_scope': 'Existing GPIO, SC1892 CSI ribbon and SC0727 OTG plan is a Zero-form-factor baseline. User identified Zero W with soldered 40-pin header and Pi 3B V1.2. Verify populated-board geometry, mated plugs, camera transport and USB host route before installation.'},
               'mac':'existing MacBook Pro',
               'local_loop_hz':50, 'current_runtime_motor_stop_a':5, 'runtime_limit_not_increased_without_measurement':True, 'link':'Wi-Fi', 'camera':'SC1224', 'camera_cable':'SC1892',
               'imu':'BNO085', 'audio_amp':'Adafruit 3006', 'speaker':'CMS-30204-18SP',
               'speaker_ohm':8, 'speaker_w':1, 'gain_resistor_ohm':100000,
               'otg':'SC0727', 'openrb_data_cable':'Adafruit 4472'},
    'pi_physical_pins':{'power_positive':[2,4], 'power_ground':[6,14],
                        'imu_3v3':[1], 'imu_sda':[3], 'imu_scl':[5], 'imu_ground':[9],
                        'amp_bclk':[12], 'amp_lrclk':[35], 'amp_din':[40], 'amp_ground':[20]},
    'connections':[
        connection('wall_supply','ROBOTIS SMPS 12V 5A DC plug','SMPS2DXL power jack','supply DC lead','as supplied','plug','12 V supply into the adapter board'),
        connection('tether','SMPS2DXL 3-wire cable with the far plug cut off: pin 2 VDD (+12 V) and pin 1 GND; pin 3 DATA insulated','XT30 female (tether side, recessed contacts), mating the robot XT30 male','18 AWG red/black pair, no fuse','2 m','wire-to-wire solder splices with heat shrink and cable-tie strain relief; solder the XT30 cups','12 V power'),
        connection('regulator_input','robot XT30 male solder cups','DFR1202 VIN+/GND solder pads','18 AWG pair','<=100 mm','solder both ends','12 V power'),
        connection('star_output','DFR1202 5 V/GND solder pads','insulated 5 V star distribution','16 AWG pair','<=100 mm','solder and insulate','common 5 V power'),
        connection('motor_groups','10 A motor main, then eight 3 A fuses','15 motors in declared groups','20 AWG pair per group + original 3-pin tails','250 mm per branch conductor incl20mm fuse pigtail +90mm per-servo tail','solder feeds; plug factory tails','5 V motor power'),
        connection('pi_power','3 A Pi fuse + star ground','Pi male header physical 2/4 and 6/14','2 positive + 2 ground female pre-crimp sockets, 22 AWG copper','250 mm each','solder supply joins; plug header sockets','5 V Pi/camera/OpenRB logic power'),
        connection('pi_usb','Pi USB Micro-B female','SC0727 USB-A female','SC0727 Micro-B male OTG adapter','80 mm','plug','USB host data + OpenRB logic power'),
        connection('openrb_usb','SC0727 USB-A female','OpenRB USB-C female','4472 USB-A male / USB-C male','152 mm','plug both ends','USB data + OpenRB logic power'),
        connection('motor_data','OpenRB DYNAMIXEL DATA','15 servo DATA terminals','factory data chain, external group power','14 links180mm; ID1-to-ID6 length400mm routed via torso','depin/insulate cross-group power; plug data links','bidirectional motor commands and feedback'),
        connection('camera','SC1224 camera 15-contact latch','Pi Zero 22-contact CSI latch','SC1892 flat-flex cable','200 mm','open latch, insert, lock','camera data + power'),
        connection('imu','BNO085 STEMMA QT socket','Pi header 1/3/5/9','4397 four-wire pre-crimp lead','250 mm after four-wire extension; torso routing','plug; secure strain relief','3.3 V + I2C orientation data'),
        connection('audio_power','0.5 A fused 5 V + ground','MAX98357A VIN/GND','direct 24 AWG copper pair, no service connector','up to 250 mm per conductor with service loop','solder fuse-side supply and amplifier pads; insulate and strain-relieve','5 V amplifier power'),
        connection('audio_data','Pi header 12/35/40/20','MAX98357A BCLK/LRCLK/DIN/GND','four pre-crimp signal leads','head-local','plug Pi; solder amplifier pads','digital sound'),
        connection('speaker','amplifier two speaker screw terminals','speaker two solder pads','two stranded wires','head-local','screw clamp at amp; solder at speaker','floating speaker output, neither terminal grounded'),
        connection('mac_wifi','Pi local camera/control service','Mac vision/training client','existing Wi-Fi network','test area','network setup','frames, timestamps, bounded commands, logs')
    ],
    'mechanical':{'base_instances':85, 'expected_instances':89,
                  'replace':{'head_cap':'head-cap-usb-service-print.stl'},
                  'add':['regulator-open-insert-print.stl','../assembly/print-parts/current/camera_pitch_foot.stl',
                         '../assembly/print-parts/current/camera_cradle.stl','../assembly/print-parts/current/audio_carrier_print.stl'],
                  'original_battery_envelope_mm':[22,34,63], 'owned_bank_mm':[80.9,65.9,26],
                  'owned_bank_fits_original_bay':False, 'battery_retention':'two ties; no quick-release door',
                  'usb_plug_acceptance_envelope_mm':[25,18,8], 'header_housing_acceptance_envelope_mm':[7,52,15],
                  'usb_plug_vendor_dimensions_verified':False},
    'assembly': {'schedule':'assembly-fasteners.json', 'guide':'ASSEMBLY.html',
                 'geometry_reports':['fastener-audit/electronics-fasteners.json','fastener-audit/joint-fasteners.json'],
                 'required_motor_count':15},
    'required_resources':[
        'Available first-generation Zero W with soldered 40-pin header (preferred) and Pi 3 Model B V1.2; use existing boards first. Bootable microSD, populated-board mounting, loaded power and camera transport need validation.',
        'SC0727 USB OTG adapter: preserve borrow-first policy only if the selected board requires this Zero-baseline adapter',
        'One 2x20 2.54 mm socket housing for ALL12 power/IMU/audio contacts; compatible pre-crimp contacts rated >=1.5 A; four22 AWG250mm power leads: club first',
        '18 AWG red/black 2 m each; short 16 AWG star wire; 20 AWG group wire: club first',
        'Copper heat spreader compatible with DFR1202 rear thermal pad; insulating film; open airflow: club first',
        'Print material, mounting fasteners, ties, heat shrink, solder, labels: club first',
        'Tether splice heat shrink and three cable ties for strain relief at the SMPS2DXL end: club first',
        'About0.3m26AWGsignalwire plusspliceinsulation to extendID1-to-ID6 DATA link: club first',
        'Multimeter, current/load measurement, oscilloscope and temperature probe: borrow first',
        'ROBOTIS SMPS 12V 5A + SMPS2DXL + its 3-wire cable (owned, duck-allocated OMX-AI kit), Mac, local Wi-Fi: existing',
        'Camera PCB screws: four M2x10 + nuts; one M3x20 + two M3x10 + three nuts + four washers'
    ],
    'acceptance':{'design':'Computed Zero-form-factor baseline only; does not qualify Pi 3 mounting, power, connectors or either board runtime.', 'physical_tests':0,
                   'visual_trials':0, 'old_cart_evidence':'stale after r3 substitutions'},
}
# Keep connector geometry as an explicit baseline until the borrowed board is identified.
for row in contract['connections']:
    if row['id'] in ('pi_power','pi_usb','openrb_usb','camera','imu','audio_data','mac_wifi'):
        row['board_scope']='existing_pi_zero_form_factor_baseline_unqualified_for_selected_board'
save('design-contract.json', contract)
print('Wrote', REV, 'with', len(contract['connections']), 'named connections.')
