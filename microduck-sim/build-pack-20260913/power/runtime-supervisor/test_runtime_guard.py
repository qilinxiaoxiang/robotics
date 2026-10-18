"""Actual community observer/scheduler/main; substituted hardware, no device I/O."""
import argparse
import hashlib
import importlib
import json
from pathlib import Path
import sys
import types
import unittest

from runtime_guard import GuardController, SafetyStop, IDS
from guarded_main import run_main

class Clock:
    def __init__(self): self.t=0.
    def __call__(self): return self.t

class Raw:
    def __init__(self, quat):
        self.quat=quat;self.age=0.;self.valid=True;self.current=[.017]*15
        self.calls=[];self.current_ids=[];self.fail_current=False;self.fail_off=False
    def get_imu_status(self):return dict(valid=self.valid,age_s=self.age)
    def read_quat(self,dt):return self.quat
    def read_acc(self):return (0,0,1)
    def read_gyro(self):return (0,0,0)
    def sync_read_present_current(self,ids):
        self.current_ids.append(ids)
        if self.fail_current:raise OSError('injected serial failure')
        return self.current
    def sync_write_torque_enable(self,ids,values):
        self.calls.append(('torque',list(ids),list(values)))
        if self.fail_off and not any(values):raise OSError('injected failed torque-off')
    def sync_read_present_position(self,ids):return [0.]*len(ids)
    def sync_read_present_velocity(self,ids):return [0.]*len(ids)
    def sync_write_goal_position(self,ids,positions):self.calls.append(('goal',ids,positions))
    def sync_write_status_return_level(self,*a):pass
    def sync_write_kp(self,*a):pass
    def shutdown(self):self.calls.append(('shutdown',))

class Tests(unittest.TestCase):
    def setUp(self):
        self.clock=Clock();self.raw=Raw(self.qsensor((1,0,0,0)))
        self.guard=GuardController(self.raw,self.imu_to_body,clock=self.clock)
    def assert_off15(self):
        self.assertTrue(any(c==('torque',list(IDS),[False]*15) for c in self.raw.calls))
    def trip(self):
        with self.assertRaises(SafetyStop):self.guard.check()
        self.assert_off15()
    def test_upright_and_real_observer(self):
        state=self.Observer(self.guard).read_state(.02)
        self.assertEqual(len(state.motor_positions),14)
        self.assertAlmostEqual(state.body_quat[0],1.)
        self.assertEqual(self.raw.current_ids[-1],list(IDS))
    def test_fall(self):
        self.raw.quat=self.qsensor((.7071067811865476,.7071067811865476,0,0));self.trip()
    def test_stale(self):self.raw.age=.101;self.trip()
    def test_invalid(self):self.raw.valid=False;self.trip()
    def test_nan_quaternion(self):self.raw.quat=(float('nan'),0,0,0);self.trip()
    def test_zero_quaternion(self):self.raw.quat=(0,0,0,0);self.trip()
    def test_time_limit(self):self.clock.t=120.;self.trip()
    def test_15th_mouth_current(self):
        self.raw.current[14]=1.47;self.guard.check();self.clock.t=.21;self.trip()
    def test_group_current(self):
        self.raw.current[:2]=[1.2,1.2];self.guard.check();self.clock.t=.21;self.trip()
    def test_total_current(self):
        self.raw.current=[.4]*15;self.guard.check();self.clock.t=.21;self.trip()
    def test_current_below_dwell_does_not_trip(self):
        self.raw.current[14]=1.47;self.guard.check();self.clock.t=.11
        self.raw.current[14]=.017;self.guard.check();self.assertIsNone(self.guard.latched_reason)
    def test_missing_current(self):self.raw.current=[.017]*14;self.trip()
    def test_signed_current(self):
        self.raw.current[14]=65.535;self.guard.check();self.assertAlmostEqual(self.guard.last_current_a[15],-.001)
    def test_serial_current_failure(self):self.raw.fail_current=True;self.trip()
    def test_latched_reenable(self):
        self.raw.age=1;self.trip();self.raw.age=0
        with self.assertRaises(SafetyStop):self.guard.sync_write_torque_enable([1],[True])
        self.assertFalse(any(c[0]=='torque' and any(c[2]) for c in self.raw.calls))
    def test_goal_blocked(self):
        self.raw.age=1
        with self.assertRaises(SafetyStop):self.guard.sync_write_goal_position([1],[.1])
        self.assertFalse(any(c[0]=='goal' for c in self.raw.calls))
    def test_failed_torqueoff_recorded(self):
        self.raw.fail_off=True;self.raw.age=1;self.trip()
        self.assertIn('injected failed torque-off',self.guard.last_torque_off_error)
    def test_actual_scheduler_fall_cleanup(self):
        self.raw.quat=self.qsensor((0,1,0,0))
        scheduler=self.Scheduler(controller=self.guard,moves={},stop_flag_path='/tmp/microduck-supervisor-offline-nonexistent.stop')
        with self.assertRaises(SafetyStop):scheduler.run()
        self.assertTrue(scheduler._cleanup_done);self.assert_off15()
    def test_actual_main_preload_exception(self):
        mod=self.community_main
        saved={k:getattr(mod,k) for k in ('_another_session_running','PID_FILE','ramp_to_neutral','WalkMove','build_input_source')}
        class PID:
            def write_text(self,*a,**k):pass
            def exists(self):return False
        class BadModel:
            def __init__(self,*a,**k):raise ValueError('injected model-load failure after torque enable')
        try:
            mod._another_session_running=lambda:False;mod.PID_FILE=PID()
            mod.ramp_to_neutral=lambda *a,**k:None;mod.WalkMove=BadModel;mod.build_input_source=lambda:None
            with self.assertRaisesRegex(ValueError,'injected model-load failure'):
                run_main(mod,lambda:self.raw,self.imu_to_body)
            self.assertTrue(any(c[0]=='torque' and any(c[2]) for c in self.raw.calls))
            self.assert_off15()
            self.assertEqual([c for c in self.raw.calls if c[0]=='torque'][-1],('torque',list(IDS),[False]*15))
        finally:
            for k,v in saved.items():setattr(mod,k,v)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('community',type=Path);a=ap.parse_args()
    source=a.community.resolve()/'src';sys.path.insert(0,str(source))
    # Only the hardware-opening class is substituted; actual application modules load.
    substitute=types.ModuleType('robot_controller');substitute.RobotController=Raw
    sys.modules['robot_controller']=substitute
    # Unused squat IK dependency; the tested scheduler is passed an empty move set.
    sys.modules['placo']=types.ModuleType('placo')
    import constants
    from imu_reader import imu_quat_to_body,_quat_mul
    from observer import Observer
    from scheduler import Scheduler
    import main as community_main
    mount=constants.IMU_MOUNT_QUAT
    Tests.qsensor=staticmethod(lambda body:_quat_mul(body,(mount[0],-mount[1],-mount[2],-mount[3])))
    Tests.imu_to_body=staticmethod(imu_quat_to_body)
    Tests.Observer=Observer;Tests.Scheduler=Scheduler;Tests.community_main=community_main
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(Tests)
    result=unittest.TextTestRunner(verbosity=1).run(suite)
    out=dict(passed=result.wasSuccessful(),tests_run=result.testsRun,hardware_access=False,
        actual_community_modules=['observer.py','scheduler.py','main.py','imu_reader.py'],
        failures=[str(x) for x in result.failures+result.errors],
        community_source_sha256={n:hashlib.sha256((source/n).read_bytes()).hexdigest() for n in ['observer.py','scheduler.py','main.py','imu_reader.py','robot_controller.py']},
        limitations=['synthetic current and IMU inputs; no real timing, torque response or hardware voltage/cell measurement',
        'no independent watchdog, no physical EN driver, no automatic cell cutoff; software process or serial failure still needs manual EN/EC2'])
    (Path(__file__).parent/'offline-checks.json').write_text(json.dumps(out,indent=2)+'\n')
    raise SystemExit(0 if result.wasSuccessful() else 1)
