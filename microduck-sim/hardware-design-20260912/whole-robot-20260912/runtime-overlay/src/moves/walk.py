# SPDX-License-Identifier: GPL-3.0-or-later
# Startup/stop transition adapted from community WalkMove, Copyright 2026 Marc Duclusaud.
"""Official 61D walk/stand adapter; retains community scheduler and hardware offsets."""
from pathlib import Path
import math
import numpy as np
import onnxruntime as ort
from constants import MOTOR_TO_ID, KP_DEFAULT, KP_RL, OBSERVATION_DOF_ORDER, IMU_MOUNT_QUAT
from imu_reader import quat_apply_inverse
from observer import Observation
from moves.move import MotorCommand, Move, MoveState

# Exact neutral reference used by this delivery's 5 V MuJoCo evaluation.
HOME=np.array([0,-.0872664626,-.457924,-.004940,.452984,.3490658504,.3490658504,
               0,0,0,.0872664626,.457924,.004940,-.452984],dtype=np.float32)
OBSERVATION_NAMES='base_ang_vel,projected_gravity,joint_pos,joint_vel,actions,command,head_command,body_command'

def body_quaternion(obs):
    q=np.asarray(obs.robot_state.body_quat,dtype=float)
    if q.shape!=(4,) or not np.all(np.isfinite(q)) or np.linalg.norm(q)<1e-8:
        raise ValueError('61D policy requires a valid trunk body_quat (w,x,y,z).')
    return q/np.linalg.norm(q)

def yaw_of(q):
    w,x,y,z=q
    return math.atan2(2*(w*z+x*y),1-2*(y*y+z*z))

class WalkMove(Move):
    """61D only. The original 51/53D model is retained by the reversible installer."""
    def __init__(self,controller=None):
        super().__init__();self._controller=controller
        if KP_RL!=200:raise ValueError('Install the accompanying constants overlay: KP_RL must be 200.')
        options=ort.SessionOptions();options.intra_op_num_threads=1;options.inter_op_num_threads=1
        folder=Path(__file__).resolve().parents[1]/'agents'
        self._sessions={k:ort.InferenceSession(str(folder/(k+'61.onnx')),sess_options=options,providers=['CPUExecutionProvider']) for k in ['walk','stand']}
        for session in self._sessions.values():
            meta=session.get_modelmeta().custom_metadata_map
            if session.get_inputs()[0].shape!=[1,61] or session.get_outputs()[0].shape!=[1,14]:raise ValueError('Expected exact 61D observation and 14 actions.')
            if meta['joint_names'].split(',')!=OBSERVATION_DOF_ORDER:raise ValueError('Policy joint order does not match hardware model order.')
            if meta['observation_names']!=OBSERVATION_NAMES:raise ValueError('Policy observation metadata differs from the tested contract.')
            if not np.allclose(np.fromstring(meta['default_joint_pos'],sep=','),HOME,atol=.0005):raise ValueError('Policy neutral pose differs.')
            if float(meta.get('action_scale','1'))!=1:raise ValueError('Expected action_scale=1.')
        self._ort_session=self._sessions['stand'];self.active_policy='stand';self.action_scale=1.0
        self._default_pose=dict(zip(OBSERVATION_DOF_ORDER,HOME.tolist()))
        self._startup_joint_names=[n for n in MOTOR_TO_ID if n in self._default_pose]
        self._last_action=[0.0]*14;self._startup_duration_s=1.5
        self._startup_start_s=None;self._startup_pose={};self._heading_target=None
        self.heading_gain=2.;self.heading_rate_limit=.8
        self._projected_gravity_z_threshold=-.5

    def set_heading(self,yaw_radians):
        """Set an absolute heading target in the BNO body_quat yaw reference."""
        if not np.isfinite(yaw_radians):raise ValueError('Heading must be finite.')
        self._heading_target=float(yaw_radians)

    def on_start(self,obs:Observation,command:MotorCommand):
        if self._startup_start_s is None:
            self._startup_start_s=obs.robot_state.time_s
            self._startup_pose={n:obs.robot_state.motor_positions.get(n,command.target_angles.get(n,0.)) for n in self._startup_joint_names}
            self._last_action=[0.]*14;self._heading_target=yaw_of(body_quaternion(obs))
        elapsed=max(0.,obs.robot_state.time_s-self._startup_start_s)
        progress=min(elapsed/self._startup_duration_s,1.);smooth=progress*progress*(3.-2.*progress)
        for n in self._startup_joint_names:command.target_angles[n]=self._startup_pose[n]+(self._default_pose[n]-self._startup_pose[n])*smooth
        if progress>=1.:
            if self._controller is not None:
                ids=list(MOTOR_TO_ID.values());self._controller.sync_write_kp(ids,[KP_RL]*len(ids))
            self._startup_start_s=None;self._startup_pose={};self.state=MoveState.ACTIVE

    def build_observation(self,obs:Observation):
        q=body_quaternion(obs);yaw=yaw_of(q)
        gyro=np.asarray(obs.robot_state.gyro,dtype=float)
        if gyro.shape!=(3,):raise ValueError('Expected three mounted-IMU gyro components.')
        # IMU_MOUNT_QUAT maps body -> sensor; inverse maps sensor gyro -> body.
        mount=np.asarray(IMU_MOUNT_QUAT,dtype=float);mount=mount/np.linalg.norm(mount)
        gyro_body=quat_apply_inverse(mount,gyro)
        gravity=quat_apply_inverse(q,[0.,0.,-1.])
        vx,vy,manual=(float(obs.user_input.velocity[n]) for n in ['vx','vy','vtheta'])
        if self._heading_target is None:self._heading_target=yaw
        moving=math.hypot(vx,vy)>.001
        if abs(manual)>.001:
            # Turning input takes precedence; release holds the reached direction.
            self._heading_target=yaw;turn=float(np.clip(manual,-self.heading_rate_limit,self.heading_rate_limit))
        elif moving:
            error=math.atan2(math.sin(self._heading_target-yaw),math.cos(self._heading_target-yaw))
            turn=float(np.clip(self.heading_gain*error,-self.heading_rate_limit,self.heading_rate_limit))
        else:turn=0.
        positions=[obs.robot_state.motor_positions[n]-self._default_pose[n] for n in OBSERVATION_DOF_ORDER]
        velocities=[obs.robot_state.motor_velocities[n] for n in OBSERVATION_DOF_ORDER]
        # 3 gyro + 3 gravity + 14 q + 14 dq + 14 last action + 3 twist + 4 head + 6 body.
        vector=np.asarray([*gyro_body,*gravity,*positions,*velocities,*self._last_action,vx,vy,turn,*([0.]*10)],dtype=np.float32)
        if vector.shape!=(61,) or not np.all(np.isfinite(vector)):raise ValueError('Invalid 61D observation.')
        return vector.tolist()

    def step(self,obs:Observation,command:MotorCommand):
        vector=np.asarray(self.build_observation(obs),dtype=np.float32)
        if vector[5]>self._projected_gravity_z_threshold:return
        self.active_policy='walk' if np.linalg.norm(vector[48:51])>.001 else 'stand'
        self._ort_session=self._sessions[self.active_policy]
        action=self._ort_session.run(None,{self._ort_session.get_inputs()[0].name:vector[None]})[0][0]
        if action.shape!=(14,) or not np.all(np.isfinite(action)):raise ValueError('Invalid policy action.')
        self._last_action=action.tolist()
        for i,n in enumerate(OBSERVATION_DOF_ORDER):command.target_angles[n]=self._default_pose[n]+float(action[i])

    def on_stop(self,obs:Observation,command:MotorCommand):
        self._startup_start_s=None;self._startup_pose={};self._heading_target=None
        if self._controller is not None:
            ids=list(MOTOR_TO_ID.values());self._controller.sync_write_kp(ids,[KP_DEFAULT]*len(ids))
        self.state=MoveState.INACTIVE
