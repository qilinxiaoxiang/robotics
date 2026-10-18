# SPDX-License-Identifier: MIT
"""Offline acceptance with actual frozen community classes and ONNX models."""
import argparse
import importlib.util
import io
from unittest.mock import patch
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest
import math
import numpy as np

HERE=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('--community',required=True);p.add_argument('--overlay',required=True)
a=p.parse_args()
from prepare import build
TEMP=tempfile.TemporaryDirectory(prefix='microduck-phase1-test-')
DEST=Path(TEMP.name)/'bundle'
build(a.community,a.overlay,DEST)
subprocess.run([sys.executable,str(DEST/'phase1.py'),'check'],check=True)
sys.path.insert(0,str(DEST))
sys.path.insert(0,str(DEST/'community/src'))
from robot_controller import RobotController
from constants import MOTOR_TO_ID, MOTOR_OFFSET, MOTOR_SIGN, IMU_MOUNT_QUAT, OBSERVATION_DOF_ORDER
from moves.walk import HOME
from core import Session, Stop, NAMES, IDS, ORDER_IDS, validate_calibration, calibration_hash
from imu_mount import multiply, conjugate, rotate, create_record, validate_record, apply_mount, summarize, solve, record_hash
import observer


def axis_quat(axis, degrees):
    v=np.asarray(axis,dtype=float);v=v/np.linalg.norm(v)*math.sin(math.radians(degrees)/2)
    return np.array([math.cos(math.radians(degrees)/2), *v])


def synthetic_captures(mount):
    poses={'upright':[1,0,0,0], 'forward':axis_quat([0,1,0],20),
           'left':axis_quat([1,0,0],-20), 'right':axis_quat([1,0,0],20),
           'back':axis_quat([0,1,0],-20), 'upright_return':[1,0,0,0], 'head_lowered':[1,0,0,0]}
    return {name:[{'timestamp_s':k*3+j*.02+1, 'age_s':.01, 'valid':True,
                   'quat':multiply(q,conjugate(mount)).tolist(), 'gyro':[0,0,0]}
                  for j in range(35)] for k,(name,q) in enumerate(poses.items())}

TEST_MOUNT=create_record(synthetic_captures(IMU_MOUNT_QUAT),1,0x4A)

class Clock:
    def __init__(self):self.t=1.
    def __call__(self):return self.t
    def advance(self,t=.02):self.t+=t

class Wire:
    def __init__(self):
        self.pose={MOTOR_TO_ID[n]:float(HOME[OBSERVATION_DOF_ORDER.index(n)])+MOTOR_OFFSET[n] for n in MOTOR_TO_ID}
        self.pose[15]=0.
        self.current=[10]*15;self.voltage=[50]*15;self.error=[0]*15
        self.torque=[False]*15;self.watchdog=[0]*15;self.modes=[3]*14+[5]
        self.gain=[0]*15;self.goal_current=100;self.current_limit=150
        self.profile_velocity=[5]*15;self.profile_acceleration=[5]*15
        self.freeze_pose=False;self.calls=[];self.fail_read=False;self.fail_goal=False;self.fail_off=False
    def sync_write_torque_enable(self,ids,values):
        self.calls.append(('torque',list(ids),list(values)))
        if self.fail_off and not any(values):raise OSError('unplugged stop wire')
        for i,v in zip(ids,values):self.torque[i-1]=v
    def sync_read_torque_enable(self,ids):return [self.torque[i-1] for i in ids]
    def sync_read_model_number(self,ids):return [1200]*len(ids)
    def sync_read_operating_mode(self,ids):return [self.modes[i-1] for i in ids]
    def read_current_limit(self,i):return self.current_limit
    def read_goal_current(self,i):return self.goal_current
    def sync_read_min_voltage_limit(self,ids):return [37]*len(ids)
    def sync_read_max_voltage_limit(self,ids):return [60]*len(ids)
    def sync_read_shutdown(self,ids):return [53]*len(ids)
    def sync_read_startup_configuration(self,ids):return [0]*len(ids)
    def sync_read_drive_mode(self,ids):return [0]*len(ids)
    def sync_write_profile_velocity(self,ids,values):
        for i,v in zip(ids,values):self.profile_velocity[i-1]=v
    def sync_write_profile_acceleration(self,ids,values):
        for i,v in zip(ids,values):self.profile_acceleration[i-1]=v
    def sync_read_profile_velocity(self,ids):return [self.profile_velocity[i-1] for i in ids]
    def sync_read_profile_acceleration(self,ids):return [self.profile_acceleration[i-1] for i in ids]
    def sync_read_hardware_error_status(self,ids):return [self.error[i-1] for i in ids]
    def sync_write_bus_watchdog(self,ids,values):
        for i,v in zip(ids,values):self.watchdog[i-1]=v
    def sync_read_bus_watchdog(self,ids):return [self.watchdog[i-1] for i in ids]
    def sync_write_goal_current(self,ids,values):self.goal_current=values[0]
    def sync_write_position_p_gain(self,ids,values):
        for i,v in zip(ids,values):self.gain[i-1]=v
    def sync_read_present_current(self,ids):
        if self.fail_read:raise OSError('unplugged read wire')
        return [self.current[i-1] for i in ids]
    def sync_read_present_input_voltage(self,ids):return [self.voltage[i-1] for i in ids]
    def sync_read_present_position(self,ids):return [self.pose[i] for i in ids]
    def sync_read_present_velocity(self,ids):return [0]*len(ids)
    def sync_write_goal_position(self,ids,values):
        if self.fail_goal:raise OSError('unplugged goal wire')
        self.calls.append(('goal',list(ids),list(values)))
        if not self.freeze_pose:self.pose.update(zip(ids,values))

class Tests(unittest.TestCase):
    def setUp(self):
        self.clock=Clock();self.wire=Wire()
        self.raw=RobotController.__new__(RobotController)
        self.raw._controller=self.wire
        self.raw._id_to_sign={MOTOR_TO_ID[n]:MOTOR_SIGN[n] for n in MOTOR_TO_ID}
        self.raw._id_to_offset={MOTOR_TO_ID[n]:MOTOR_OFFSET[n] for n in MOTOR_TO_ID}
        self.imu=types.SimpleNamespace(age_s=0.,valid=True,quat=conjugate(IMU_MOUNT_QUAT),gyro=(0,0,0),bus=1,addr=0x4A)
        self.raw._imu_reader=types.SimpleNamespace(get_status=lambda:{'age_s':self.imu.age_s,'valid':self.imu.valid,'bus':self.imu.bus,'addr':self.imu.addr},
            get_latest=lambda:types.SimpleNamespace(quat=self.imu.quat,acc=(0,0,1),gyro=self.imu.gyro),stop=lambda:None)
        c=json.loads((HERE/'calibration.template.json').read_text())
        ready={n:float(HOME[OBSERVATION_DOF_ORDER.index(n)]) for n in MOTOR_TO_ID};ready['jaw']=0.
        lower=dict(ready);lower['neck_pitch']+=.1;lower['head_pitch']+=.1
        carry=dict(ready);carry['head_pitch']-=.05
        c.update(physical_calibration_confirmed=True,physical_supported_gait_ready=True,
                 physical_supported_walk_passed=True,physical_supported_pickup_passed=True)
        c['poses']={'ready':ready,'lower':lower,'carry':carry}
        c['jaw'].update(open_rad=0.,closed_rad=-.2)
        c['imu_mount']=copy.deepcopy(TEST_MOUNT)
        c['calibration_sha256']=calibration_hash(c);self.c=c
        self.s=Session(self.raw,c,clock=self.clock,supported=True)
        observer.time=types.SimpleNamespace(perf_counter=self.clock)
        self.seq=0
    def send(self,action):
        self.s.packet({'seq':self.seq,'action':action});self.seq+=1
    def advance(self,n=1):
        for i in range(n):
            self.clock.advance();self.send('heartbeat');self.s.tick()
    def arm(self):self.send('arm')
    def assert_off(self):self.assertEqual(self.wire.torque,[False]*15)
    def test_unmodified_community_rejects_jaw_position(self):
        raw=RobotController.__new__(RobotController);raw._controller=self.wire
        raw._id_to_sign={i:1 for i in range(1,15)};raw._id_to_offset={i:0 for i in range(1,15)}
        with self.assertRaises(KeyError):raw.sync_write_goal_position([15],[0.])
    def test_actual_mapping_preserves_knee_and_adds_jaw(self):
        self.arm();self.raw.sync_write_goal_position([2,7,15],[.1,.2,-.1])
        self.assertAlmostEqual(self.wire.pose[2],.1+MOTOR_OFFSET['right_knee'])
        self.assertAlmostEqual(self.wire.pose[7],.2+MOTOR_OFFSET['left_knee'])
        self.assertAlmostEqual(self.raw.sync_read_present_position([15])[0],-.1)
        self.assertEqual(len(MOTOR_TO_ID),14)
    def test_arm_preloads_measured_pose_and_enables_all15(self):
        self.arm();self.assertEqual(self.wire.torque,[True]*15)
        enabled=next(i for i,x in enumerate(self.wire.calls) if x[0]=='torque' and any(x[2]))
        self.assertEqual(self.wire.calls[enabled-1][0],'goal')
        self.assertIn(15,self.wire.calls[enabled-1][1])
    def test_guarded_pickup_lift_hold_release(self):
        self.arm();self.send('pickup');self.advance(450)
        self.assertEqual(self.s.queue,[]);self.assertIsNone(self.s.segment)
        self.assertAlmostEqual(self.s.target['jaw'],-.2)
        self.assertAlmostEqual(self.s.target['head_pitch'],self.c['poses']['carry']['head_pitch'])
        self.advance(150);self.assertAlmostEqual(self.s.target['jaw'],-.2)
        self.send('release');self.advance(200)
        self.assertEqual(self.s.target,self.c['poses']['ready'])
    def test_manual_head_and_jaw(self):
        self.arm();self.send('lower');self.advance(130)
        self.assertAlmostEqual(self.s.target['head_pitch'],self.c['poses']['lower']['head_pitch'])
        self.send('close');self.advance(100);self.assertAlmostEqual(self.s.target['jaw'],-.2)
    def test_real_walk_stand_onnx_and_jaw(self):
        self.arm();self.wire.freeze_pose=True;self.send('walk');self.advance(180)
        self.assertEqual(self.s.policy.active_policy,'stand')
        self.send('forward');self.advance(2)
        self.assertEqual(self.s.policy.active_policy,'walk')
        self.advance(20);self.assertEqual(self.s.policy.active_policy,'walk')
        self.assertEqual(self.s.velocity['vx'],0.)
        self.assertEqual(self.wire.gain[:14],[275]*14)
        self.assertEqual(len(self.s.target),15);self.assertEqual(self.s.target['jaw'],0.)
    def test_walk_to_pickup_requires_stationary_interval(self):
        self.arm();self.send('forward')
        with self.assertRaises(Stop):self.send('pickup')
    def test_walk_halt_ready_pickup_sequence(self):
        self.arm();self.wire.freeze_pose=True;self.send('walk');self.advance(180);self.send('forward');self.advance(15)
        self.assertTrue(self.s.policy.has_walked)
        self.send('halt');self.advance(60)
        self.send('ready');self.advance(200);self.send('pickup');self.advance(450)
        self.assertAlmostEqual(self.s.target['jaw'],-.2)
    def test_no_walk_during_pickup(self):
        self.arm();self.send('pickup')
        with self.assertRaises(Stop):self.send('forward')
    def test_input_loss_stops_all15_and_latches(self):
        self.arm();self.clock.advance(.61)
        with self.assertRaises(Stop):self.s.tick()
        self.assert_off()
        with self.assertRaises(Stop):self.send('arm')
    def test_duplicate_input_stops(self):
        self.send('heartbeat')
        with self.assertRaises(Stop):self.s.packet({'seq':0,'action':'heartbeat'})
        self.assert_off()
    def test_invalid_imu_stops(self):
        self.arm();self.imu.valid=False
        with self.assertRaises(Stop):self.s.tick()
        self.assert_off()
    def test_tilt_stops(self):
        self.arm();self.imu.quat=(1.,0,0,0)
        with self.assertRaises(Stop):self.s.tick()
        self.assert_off()
    def test_bus_read_failure_stops(self):
        self.arm();self.wire.fail_read=True;self.s.current_poll=-1
        with self.assertRaises(OSError):self.s.tick()
        self.assert_off()
    def test_bus_goal_failure_stops(self):
        self.arm();self.wire.fail_goal=True
        with self.assertRaises(OSError):self.s.tick()
        self.assert_off()
    def test_missing_current_stops(self):
        self.arm();self.raw.sync_read_present_current=lambda ids:[0.]*14;self.s.current_poll=-1
        with self.assertRaises(Stop):self.s.tick()
        self.assert_off()
    def test_jaw_current_limit(self):
        self.arm();self.wire.current[14]=190;self.s.current_poll=-1
        with self.assertRaises(Stop):self.s.tick()
        self.assert_off()
    def test_undervoltage_stops(self):
        self.arm();self.wire.voltage[14]=39;self.s.current_poll=-1
        with self.assertRaises(Stop):self.s.tick()
        self.assert_off()
    def test_overvoltage_stops(self):
        self.arm();self.wire.voltage[2]=56;self.s.current_poll=-1
        with self.assertRaises(Stop):self.s.tick()
        self.assert_off()
    def test_watchdog_fault_stops(self):
        self.arm();self.wire.watchdog[14]=255;self.s.current_poll=-1
        with self.assertRaises(Stop):self.s.tick()
        self.assert_off()
    def test_loop_timeout_stops(self):
        self.arm();self.clock.advance(.101);self.send('heartbeat')
        with self.assertRaises(Stop):self.s.tick()
        self.assert_off()
    def test_bad_jaw_mode_rejected_before_enable(self):
        self.wire.modes[14]=3
        with self.assertRaises(Stop):self.arm()
        self.assert_off()
    def test_changed_calibration_rejected(self):
        c=copy.deepcopy(self.c);c['jaw']['closed_rad']=-.1
        with self.assertRaises(Stop):validate_calibration(c)
    def test_blank_template_rejected(self):
        with self.assertRaises(Stop):validate_calibration(json.loads((HERE/'calibration.template.json').read_text()))
    def test_out_of_range_target_stops(self):
        self.arm();self.s.target['jaw']=3.
        with self.assertRaises(Stop):self.s.tick()
        self.assert_off()
    def test_failed_torque_off_is_reported(self):
        self.arm();self.wire.fail_off=True;self.s.off('test disconnect')
        self.assertIn('unplugged stop',self.s.last_off_error)
        self.assertEqual(self.s.events[-1]['event'],'torque_off_requested')
    def test_freestanding_gate_does_not_assert_physical_success(self):
        self.c['physical_supported_pickup_passed']=False;self.s.supported=False;self.arm()
        with self.assertRaises(Stop):self.send('pickup')

    def test_group_current_stops(self):
        self.arm();self.wire.current[0]=1150;self.wire.current[1]=1150;self.s.current_poll=-1
        with self.assertRaises(Stop):self.s.tick()
        self.assert_off()
    def test_uncommissioned_turn_rejected(self):
        self.arm()
        with self.assertRaises(Stop):self.send('left')
    def test_tested_forward_command(self):
        self.arm();self.send('forward');self.assertEqual(self.s.velocity['vx'],.30)

    def test_heading_is_held_after_zero_translation(self):
        from observer import Observation
        from input.input_source import UserInput
        import math
        self.s.policy.has_walked=True;self.s.policy._heading_target=0.
        state=self.s.observer.read_state(.02)
        state.body_quat=(math.cos(.1),0,0,math.sin(.1))
        obs=Observation(state,UserInput())
        v=self.s.policy.build_observation(obs)
        self.assertAlmostEqual(v[50],-.4,places=6)
        self.assertEqual(v[48:50],[0.,0.])
        self.assertFalse(self.s.policy.prediction_status['enabled'])
    def test_validated_latency_predictor_uses_arrived_state(self):
        from observer import Observation
        from input.input_source import UserInput
        self.s.policy.latency={'age_basis':'validated_latency_estimate','imu_sample_age_s':.02,'joint_sample_age_s':.02}
        state=self.s.observer.read_state(.02)
        state.motor_velocities={n:.5 for n in MOTOR_TO_ID}
        v=self.s.policy.build_observation(Observation(state,UserInput()))
        self.assertAlmostEqual(v[6],.01,places=6)
        self.assertTrue(self.s.policy.prediction_status['enabled'])
    def test_excessive_latency_rejected(self):
        from observer import Observation
        from input.input_source import UserInput
        self.s.policy.latency={'age_basis':'validated_latency_estimate','imu_sample_age_s':.06,'joint_sample_age_s':.02}
        with self.assertRaises(ValueError):self.s.policy.build_observation(Observation(self.s.observer.read_state(.02),UserInput()))

    def test_missing_overload_shutdown_rejected(self):
        self.wire.sync_read_shutdown=lambda ids:[1]*len(ids)
        with self.assertRaises(Stop):self.arm()
        self.assert_off()
    def test_four_volt_endpoint_is_in_tested_envelope(self):
        self.wire.voltage=[40]*15
        self.arm();self.s.tick()
        self.assertTrue(self.s.armed)
    def test_single_servo_id_assignment_readback(self):
        from assign_id import assign
        from rustypot import Xl330PyController
        for name in ('read_model_number','read_torque_enable','sync_write_id','read_id','sync_write_baud_rate','read_baud_rate'):
            self.assertTrue(hasattr(Xl330PyController,name))
        device={'id':1,'baud':57600,'torque':False}
        def factory(serial_port,baudrate,timeout):
            def read(i,key):
                if baudrate!=device['baud'] or i!=device['id']:raise RuntimeError('No response')
                return 1200 if key=='model' else device[key]
            def write_id(ids,values):device['id']=values[0]
            def write_baud(ids,values):device['baud']=1000000
            return types.SimpleNamespace(read_model_number=lambda i:read(i,'model'),read_torque_enable=lambda i:read(i,'torque'),
                sync_write_torque_enable=lambda ids,v:device.update(torque=v[0]),sync_write_id=write_id,
                read_id=lambda i:read(i,'id'),sync_write_baud_rate=write_baud,read_baud_rate=lambda i:3)
        result=assign('/fake',15,factory=factory)
        self.assertEqual(result['servo_id'],15);self.assertEqual(result['baudrate'],1000000)
        self.assertFalse(result['torque_enabled'])

    def test_id_assignment_rejects_multiple_responding_servos(self):
        from assign_id import assign
        def read(i):
            if i in (1,2):return 1200
            raise RuntimeError('No response')
        with self.assertRaises(RuntimeError):
            assign('/fake',3,factory=lambda **kwargs:types.SimpleNamespace(read_model_number=read))

    def test_walk_commands_wait_for_posture_and_policy_settle(self):
        self.arm();self.wire.freeze_pose=True;self.send('forward')
        for _ in range(100):
            self.advance();self.send('forward')
        self.assertFalse(self.s.policy.has_walked)
        for _ in range(90):
            self.advance();self.send('forward')
        self.assertTrue(self.s.policy.has_walked)

    def test_arbitrary_torso_mounts_match_real_observer_policy_and_tilt_guard(self):
        from observer import Observation
        from input.input_source import UserInput
        for mount in ([1,0,0,0],axis_quat([0,1,0],90),axis_quat([1,0,0],180),
                      axis_quat([1,2,3],137),axis_quat([1,-3,2],-59)):
            record=create_record(synthetic_captures(mount),1,0x4A)
            self.assertAlmostEqual(abs(np.dot(mount,validate_record(record))),1,places=10)
            c=copy.deepcopy(self.c);c['imu_mount']=record;c['calibration_sha256']=calibration_hash(c)
            s=Session(self.raw,c,clock=self.clock,supported=True)
            body=axis_quat([0,1,0],17)
            self.imu.quat=multiply(body,conjugate(mount))
            self.imu.gyro=rotate(mount,[.1,-.2,.3])
            state=s.observer.read_state(.02)
            self.assertAlmostEqual(abs(np.dot(state.body_quat,body)),1,places=10)
            v=s.policy.build_observation(Observation(state,UserInput()))
            np.testing.assert_allclose(v[:3],[.1,-.2,.3],atol=1e-6)
            np.testing.assert_allclose(v[3:6],rotate(conjugate(body),[0,0,-1]),atol=1e-6)
            s.check()
            self.imu.quat=multiply(axis_quat([0,1,0],55),conjugate(mount))
            with self.assertRaises(Stop):s.check()
            self.assert_off()

    def test_imu_calibration_rejects_reversed_held_out_side(self):
        captures=synthetic_captures(IMU_MOUNT_QUAT)
        captures['left'],captures['right']=captures['right'],captures['left']
        with self.assertRaisesRegex(ValueError,'left'):solve(captures)

    def test_imu_calibration_rejects_head_mounted_sensor(self):
        captures=synthetic_captures(IMU_MOUNT_QUAT)
        captures['head_lowered']=captures['forward']
        with self.assertRaisesRegex(ValueError,'head_lowered'):solve(captures)

    def test_imu_calibration_rejects_stale_moving_and_duplicate_samples(self):
        base=synthetic_captures(IMU_MOUNT_QUAT)['upright']
        for key,value in (('age_s',.11),('gyro',[.11,0,0]),('valid',False),('timestamp_s',1)):
            samples=copy.deepcopy(base)
            for sample in samples:sample[key]=value
            with self.assertRaises(ValueError):summarize(samples)

    def test_imu_mount_is_required_before_arm_and_cannot_be_forged_by_flag(self):
        c=copy.deepcopy(self.c);c['imu_mount']=None
        with self.assertRaises(Stop):validate_calibration(c)
        record=copy.deepcopy(TEST_MOUNT);record['body_to_sensor_wxyz']=[1,0,0,0]
        record['sha256']=record_hash(record)
        with self.assertRaisesRegex(ValueError,'disagrees'):validate_record(record)

    def test_imu_address_change_prevents_arm(self):
        self.imu.addr=0x4B
        with self.assertRaises(Stop):self.arm()
        self.assert_off()

    def test_arm_restores_slow_wizard_profiles(self):
        self.arm()
        self.assertEqual(self.wire.profile_velocity,[0]*14+[10])
        self.assertEqual(self.wire.profile_acceleration,[0]*15)

    def test_bad_profile_readback_prevents_arm(self):
        self.wire.sync_read_profile_velocity=lambda ids:[5]*len(ids)
        with self.assertRaises(Stop):self.arm()
        self.assert_off()

    def test_reverse_drive_mode_prevents_arm(self):
        self.wire.sync_read_drive_mode=lambda ids:[1]*len(ids)
        with self.assertRaises(Stop):self.arm()
        self.assert_off()

    def test_sensor_only_wizard_entrypoint_saves_derived_mount_without_motor_access(self):
        spec=importlib.util.spec_from_file_location('imu_entry',DEST/'imu_calibrate.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        import torso_imu, robot_controller
        cpath=DEST/'sensor-calibration.json';cpath.write_text(json.dumps(self.c))
        captures=iter(synthetic_captures(axis_quat([1,2,3],137)).values())
        reader=types.SimpleNamespace(start=lambda:None,stop=lambda:None,
            get_status=lambda:{'bus':1,'addr':0x4A,'valid':True,'age_s':.01})
        real_calibrate=module.calibrate
        with patch.object(torso_imu,'TorsoIMUReader',return_value=reader), \
             patch.object(robot_controller,'RobotController',side_effect=AssertionError('Motor port opened')), \
             patch.object(module,'calibrate',side_effect=lambda reader:real_calibrate(reader,ask=lambda x:None,collect=lambda r:next(captures))), \
             patch.object(sys,'argv',['imu_calibrate.py','calibrate','--motor-power-disconnected','--calibration',str(cpath)]):
            module.main()
        c=json.loads(cpath.read_text());validate_record(c['imu_mount'])
        self.assertFalse(c['physical_calibration_confirmed'])
        self.assertFalse(c['physical_supported_gait_ready'])

    def test_reader_does_not_refresh_quaternion_age_from_accelerometer_packets(self):
        import struct, threading, imu_reader, torso_imu
        def report(kind,components):return bytes([kind,0,0,0])+struct.pack('<'+'h'*len(components),*components)
        packets=iter([(3,report(8,[0,0,0,16384])),(3,report(2,[0,0,0])),(3,report(1,[0,0,256])),None])
        reader=torso_imu.TorsoIMUReader.__new__(torso_imu.TorsoIMUReader)
        reader._stop_event=threading.Event();reader._lock=threading.Lock();reader._error_count=0
        def next_packet():
            packet=next(packets)
            if packet is None:reader._stop_event.set()
            return packet
        reader._imu=types.SimpleNamespace(read_packet=next_packet)
        with patch.object(torso_imu,'time',types.SimpleNamespace(perf_counter=iter([1.,1.02,1.2,1.3]).__next__,sleep=lambda s:None)):
            reader._run_loop()
        self.assertTrue(reader._snapshot.valid)
        self.assertEqual(reader._snapshot.timestamp_s,1.)

    def test_actual_entrypoint_eof_cleans_up_all15(self):
        spec=importlib.util.spec_from_file_location('phase1_entry',DEST/'phase1.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        mount=axis_quat([1,2,3],137)
        c=copy.deepcopy(self.c);c['imu_mount']=create_record(synthetic_captures(mount),1,0x4A)
        c['calibration_sha256']=calibration_hash(c)
        self.imu.quat=conjugate(mount)
        cal=DEST/'calibration.json';cal.write_text(json.dumps(c))
        self.wire.torque=[True]*15
        import robot_controller
        with patch.object(robot_controller,'RobotController',return_value=self.raw), patch.object(sys,'stdin',io.StringIO('')), patch.object(sys,'argv',['phase1.py','run','--calibration',str(cal)]):
            with self.assertRaises(Stop):module.main()
        self.assert_off()
        import constants
        self.assertAlmostEqual(abs(np.dot(constants.IMU_MOUNT_QUAT,mount)),1,places=10)
        self.assertFalse(Path('/tmp/microduck_scheduler.pid').exists())
        final=json.loads(sorted(DEST.glob('session-*.jsonl'))[-1].read_text().splitlines()[-1])
        self.assertIn('Mac input stream closed',final['stop_reason'])
        self.assertTrue(final['final'])

    def test_jaw_limits_bundled_from_canonical_source(self):
        canonical=HERE.parents[2]/'guide'/'firmware'/'pi'
        for name in ('jaw_limits.py','jaw_limits.json','jaw_pose_caps.json'):
            self.assertEqual((DEST/name).read_bytes(),(canonical/name).read_bytes(),name)
    def test_bus_jaw_cap_25_degrees(self):
        self.arm();closed=self.c['jaw']['closed_rad']
        self.raw.sync_write_goal_position([15],[closed+math.radians(40)])
        self.assertAlmostEqual(self.wire.pose[15],closed+math.radians(25),places=9)
        self.raw.sync_write_goal_position([15],[closed+math.radians(25)])
        self.assertAlmostEqual(self.wire.pose[15],closed+math.radians(25),places=9)
        self.raw.sync_write_goal_position([15],[closed+math.radians(24)])
        self.assertAlmostEqual(self.wire.pose[15],closed+math.radians(24),places=9)
        self.raw.sync_write_goal_position([15],[closed-math.radians(1)])  # grip squeeze past closed stays allowed
        self.assertAlmostEqual(self.wire.pose[15],closed-math.radians(1),places=9)
    def test_bus_head_pitch_capped_only_while_jaw_open(self):
        self.arm();self.wire.freeze_pose=True;closed=self.c['jaw']['closed_rad'];self.s.jaw_measured_rad=closed
        for jaw_deg,head_deg,written in ((10,80,65),(2,80,80),(10,65,65),(10,64,64),(25,-40,-40)):
            self.raw.sync_write_goal_position([11,15],[math.radians(head_deg),closed+math.radians(jaw_deg)])
            self.assertAlmostEqual(self.wire.calls[-1][2][0],math.radians(written),places=9,msg=(jaw_deg,head_deg))
    def test_measured_open_jaw_caps_head_pitch(self):
        self.arm();self.wire.freeze_pose=True;closed=self.c['jaw']['closed_rad']
        self.wire.pose[15]=closed+math.radians(16)  # held open by an object while commanded closed
        self.s.current_poll=-math.inf;self.advance()
        self.assertAlmostEqual(self.s.jaw_measured_rad,closed+math.radians(16))
        self.raw.sync_write_goal_position([11,15],[math.radians(80),closed])
        self.assertAlmostEqual(self.wire.calls[-1][2][0],math.radians(65),places=9)
        self.assertEqual(self.s.limit_clamps,['head_pitch'])
        self.assertEqual(self.s.events[-1]['event'],'goal_limits')
    def test_measured_head_pose_read_with_jaw(self):
        self.arm();self.wire.freeze_pose=True
        self.wire.pose.update({12:math.radians(-15),11:math.radians(30),13:math.radians(-20),14:math.radians(10)})
        self.s.current_poll=-math.inf;self.advance()
        got=self.s.head_measured_rad
        for name,deg in (('neck_pitch',-15),('head_pitch',30),('head_yaw',-20),('head_roll',10)):
            self.assertAlmostEqual(got[name],math.radians(deg),places=9,msg=name)
    def write_head(self,head,jaw):
        ids=[12,11,13,14,15]
        self.raw.sync_write_goal_position(ids,[head['neck_pitch'],head['head_pitch'],head['head_yaw'],head['head_roll'],jaw])
        return self.wire.calls[-1][2][ids.index(15)]
    def test_bus_jaw_pose_cap_follows_head_pose(self):
        import jaw_limits
        self.arm();self.wire.freeze_pose=True;closed=self.c['jaw']['closed_rad']
        straight={'neck_pitch':0.,'head_pitch':0.,'head_yaw':0.,'head_roll':0.}
        self.s.head_measured_rad=dict(straight);self.s.jaw_measured_rad=closed
        self.assertAlmostEqual(self.write_head(straight,closed+math.radians(24)),closed+math.radians(24),places=9)
        # Rolled head at pitch 60 deg: CAD contact (motor 12, neck links) comes well before 25 deg.
        head={'neck_pitch':0.,'head_pitch':math.radians(60),'head_yaw':0.,'head_roll':math.radians(25)}
        cap,closed_zone,_=jaw_limits.pose_jaw_cap_deg(head,head)
        self.assertLess(cap,18.33);self.assertFalse(closed_zone)
        self.s.head_measured_rad=dict(head)
        self.assertAlmostEqual(self.write_head(head,closed+math.radians(24)),closed+math.radians(cap),places=9)
        self.assertEqual(self.s.limit_clamps,['jaw_pose'])
    def test_bus_jaw_held_closed_in_closed_zone_and_logged(self):
        import jaw_limits
        self.arm();self.wire.freeze_pose=True;closed=self.c['jaw']['closed_rad']
        head={'neck_pitch':0.,'head_pitch':math.radians(-45),'head_yaw':math.radians(140),'head_roll':0.}
        self.assertTrue(jaw_limits.pose_jaw_cap_deg(head,head)[1])
        self.s.head_measured_rad=dict(head);self.s.jaw_measured_rad=closed
        self.assertAlmostEqual(self.write_head(head,closed+math.radians(10)),closed,places=9)
        self.assertEqual(self.s.limit_clamps,['jaw_closed_zone'])
        event=self.s.events[-1]
        self.assertEqual((event['event'],event['clamped']),('goal_limits',['jaw_closed_zone']))
        self.assertAlmostEqual(event['head_measured_rad']['head_yaw'],math.radians(140),places=9)
        self.assertAlmostEqual(self.write_head(head,closed-math.radians(1)),closed-math.radians(1),places=9)  # squeeze stays allowed
    def test_bus_unknown_head_pose_gets_most_conservative_cap(self):
        import jaw_limits
        self.arm();self.wire.freeze_pose=True;closed=self.c['jaw']['closed_rad']
        self.s.head_measured_rad=None;self.s.jaw_measured_rad=closed
        cap,_=jaw_limits.cap_for_contact(jaw_limits.POSE_TABLE_MIN_CONTACT_DEG)
        self.raw.sync_write_goal_position([15],[closed+math.radians(20)])
        self.assertAlmostEqual(self.wire.calls[-1][2][0],closed+math.radians(min(cap,20)),places=9)
    def test_release_at_steep_carry_pose_keeps_head_at_65_while_jaw_open(self):
        c=copy.deepcopy(self.c);c['poses']['carry']['head_pitch']=math.radians(80);c['calibration_sha256']=calibration_hash(c)
        self.s=Session(self.raw,c,clock=self.clock,supported=True);closed=c['jaw']['closed_rad']
        self.arm();self.send('pickup');self.advance(650)  # the speed limit stretches the 60 deg head segment
        self.assertEqual(self.s.queue,[]);self.assertIsNone(self.s.segment)
        self.assertAlmostEqual(self.wire.pose[11],math.radians(80),places=6)  # jaw closed: the steep carry is allowed
        start=len(self.wire.calls);self.send('release');self.advance(400)
        head,jaw=ORDER_IDS.index(11),ORDER_IDS.index(15);clamped=0
        for kind,ids,values in self.wire.calls[start:]:
            if kind!='goal' or ids!=ORDER_IDS:continue
            if values[jaw]-closed>math.radians(2)+1e-9:
                self.assertLessEqual(values[head],math.radians(65)+1e-9)
                clamped+=values[head]>=math.radians(65)-1e-9
        self.assertGreater(clamped,0)
        self.assertEqual(self.s.target,c['poses']['ready'])

suite=unittest.defaultTestLoader.loadTestsFromTestCase(Tests)
result=unittest.TextTestRunner(verbosity=2).run(suite)
report={'offline_tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),
        'physical_robot_tests':0,'actual_classes':['RobotController','Observer','Observation','UserInput','MotorCommand','WalkMove'],
        'actual_models':['stand61.onnx','walk61.onnx'],'hardware_substitution':'Rust serial transport and IMU readings only',
        'fresh_bundle_check':True,'source_hash':json.loads((DEST/'bundle-lock.json').read_text())['files']['core.py'],
        'source_files_sha256':json.loads((DEST/'bundle-lock.json').read_text())['files'],
        'cases':[t.id() for t in unittest.defaultTestLoader.loadTestsFromTestCase(Tests)]}
(HERE/'offline-results.json').write_text(json.dumps(report,indent=2)+'\n')
TEMP.cleanup()
raise SystemExit(not result.wasSuccessful())
