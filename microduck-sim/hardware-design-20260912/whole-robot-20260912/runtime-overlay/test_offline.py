"""Real community Observation + real ONNX forwards. No serial/I2C/controller opened."""
from pathlib import Path
import argparse,hashlib,json,shutil,sys,tempfile
import numpy as np
from install import install,uninstall
P=Path(__file__).resolve().parent
def R(q):
    w,x,y,z=np.asarray(q)/np.linalg.norm(q)
    return np.array([[1-2*(y*y+z*z),2*(x*y-w*z),2*(x*z+w*y)],
      [2*(x*y+w*z),1-2*(x*x+z*z),2*(y*z-w*x)],
      [2*(x*z-w*y),2*(y*z+w*x),1-2*(x*x+y*y)]])
def run(source):
    with tempfile.TemporaryDirectory(prefix='microduck-overlay61-') as td:
        target=Path(td)/'microduck';shutil.copytree(source/'src',target/'src')
        before={n:hashlib.sha256((target/n).read_bytes()).hexdigest() for n in ['src/moves/walk.py','src/constants.py','src/agents/walk.onnx']}
        install(target);sys.path.insert(0,str(target/'src'))
        from observer import Observation,RobotState
        from input.input_source import UserInput
        from moves.move import MotorCommand,MoveState
        from moves.walk import WalkMove,HOME
        import constants as C
        assert C.KP_RL==200 and C.BAM_VIN==5 and C.BAM_VIN_MIN==4 and C.BAM_MAX_CURRENT==1.47
        assert C.MOTOR_OFFSET['right_knee']==np.deg2rad(45) and C.MOTOR_OFFSET['left_knee']==np.deg2rad(-45)
        class Recorder:
            calls=[]
            def sync_write_kp(self,ids,gains):self.calls.append((ids,gains))
        rec=Recorder();move=WalkMove(rec)
        names=C.OBSERVATION_DOF_ORDER
        def obs(q=(1,0,0,0),gyro=(.12,-.25,.31),velocity=(.15,0,0),t=0.):
            return Observation(RobotState(time_s=t,body_quat=list(q),gyro=(R(C.IMU_MOUNT_QUAT)@gyro).tolist(),
                projected_gravity=[9,8,7],motor_positions=dict(zip(names,HOME+np.arange(14)*.001)),
                motor_velocities=dict(zip(names,np.linspace(-.2,.2,14)))),
                UserInput(velocity=dict(zip(['vx','vy','vtheta'],velocity))))
        command=MotorCommand();start=obs();move.state=MoveState.STARTING
        move.on_start(start,command);assert move.state==MoveState.STARTING
        move.on_start(obs(t=1.5),command);assert move.state==MoveState.ACTIVE and rec.calls[-1][1]==[200]*14
        np.testing.assert_allclose([command.target_angles[n] for n in names],HOME)
        q=np.array([.94,.1,-.2,.22]);q/=np.linalg.norm(q)
        sample=obs(q,velocity=(.15,-.04,.23));vector=np.array(move.build_observation(sample),np.float32)
        expected=np.r_[[.12,-.25,.31],R(q).T@[0,0,-1],np.arange(14)*.001,np.linspace(-.2,.2,14),np.zeros(14),[.15,-.04,.23],np.zeros(10)].astype(np.float32)
        np.testing.assert_allclose(vector,expected,atol=1e-7)
        move._last_action=np.linspace(-.3,.3,14).tolist();v=np.array(move.build_observation(sample),np.float32)
        np.testing.assert_allclose(v[34:48],move._last_action,atol=1e-7)
        session=move._sessions['walk'];direct=session.run(None,{session.get_inputs()[0].name:v[None]})[0][0]
        move.step(sample,command);assert move.active_policy=='walk'
        np.testing.assert_allclose([command.target_angles[n] for n in names],HOME+direct,atol=1e-7)
        upright=obs(velocity=(0,0,0));move.step(upright,command);assert move.active_policy=='stand'
        np.testing.assert_allclose(move.build_observation(upright)[3:6],[0,0,-1],atol=1e-7)
        move.set_heading(.3);heading=np.array(move.build_observation(obs()));assert np.isclose(heading[50],.6)
        move.set_heading(2);assert np.isclose(move.build_observation(obs())[50],.8)
        # A deliberate turn overrides hold, and subsequent straight motion keeps the new yaw.
        yaw=.5;q_yaw=[np.cos(yaw/2),0,0,np.sin(yaw/2)]
        assert np.isclose(move.build_observation(obs(q_yaw,velocity=(.15,0,.2)))[50],.2)
        assert abs(move.build_observation(obs(q_yaw))[50])<1e-6
        move.set_heading(-np.pi+.02);q_wrap=[np.cos((np.pi-.02)/2),0,0,np.sin((np.pi-.02)/2)]
        assert np.isclose(move.build_observation(obs(q_wrap))[50],.08,atol=1e-6)
        before_fall=command.target_angles.copy();move.step(obs((0,1,0,0)),command);assert command.target_angles==before_fall
        try:move.build_observation(obs((0,0,0,0)));raise AssertionError('Invalid quaternion accepted')
        except ValueError:pass
        move.on_stop(upright,command);assert move.state==MoveState.INACTIVE and rec.calls[-1][1]==[C.KP_DEFAULT]*14
        uninstall(target)
        for n,h in before.items():assert hashlib.sha256((target/n).read_bytes()).hexdigest()==h
        assert not (target/'src/agents/walk61.onnx').exists()
        return {'passed':True,'real_observation_class':str(Observation),'real_onnx_sessions':['walk61.onnx','stand61.onnx'],
                'observation_shape':[1,61],'action_shape':[1,14],'checks':['61 fields and order','negative-Z body gravity','inverse mount gyro','metadata','previous action','walk direct-forward parity','stand switching','1.5s startup and KP200','offset preservation','heading gain/saturation/manual turn/wrap','fall hold','invalid quaternion rejection','stop gain restoration','install/uninstall byte-for-byte restoration'],
                'hardware_access':False,'scope':'Offline compatibility; not Pi timing or real-servo validation.'}
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('community_microduck',type=Path);a=ap.parse_args();result=run(a.community_microduck.resolve())
    (P/'offline-verification.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
