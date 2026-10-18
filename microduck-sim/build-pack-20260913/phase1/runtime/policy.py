# SPDX-License-Identifier: GPL-3.0-or-later
"""Phase 1 gait choices layered on the frozen official 61D adapter.

Build-observation and startup remain the real community/official overlay path.
After forward walking begins, the same walk61 model receives zero command to stop.
There is no action blending and no automatic switch back to stand61.
"""
import math
import numpy as np
from moves.walk import WalkMove, body_quaternion, yaw_of
from runtime_compensation import compensate_arrived_state

BODY_KP = 275

class GainController:
    def __init__(self, raw):self.raw=raw
    def sync_write_kp(self, ids, gains):
        return self.raw.sync_write_kp(ids,[BODY_KP]*len(ids))

class Phase1Walk(WalkMove):
    def __init__(self, controller=None, latency=None):
        super().__init__(controller=GainController(controller) if controller is not None else None)
        self.has_walked=False
        self.latency=latency or {'age_basis':'unknown'}
        self.prediction_status={'enabled':False,'reason':'sample_age_unknown'}

    def build_observation(self, obs):
        vector=np.asarray(super().build_observation(obs),dtype=np.float32)
        yaw=yaw_of(body_quaternion(obs))
        sensed, used_yaw, self.prediction_status=compensate_arrived_state(
            vector[:34],yaw,**self.latency)
        vector[:34]=sensed
        manual=float(obs.user_input.velocity['vtheta'])
        moving=math.hypot(float(vector[48]),float(vector[49]))>.001
        if abs(manual)>.001:
            self._heading_target=used_yaw
            vector[50]=np.clip(manual,-.8,.8)
        elif moving or self.has_walked:
            error=math.atan2(math.sin(self._heading_target-used_yaw),math.cos(self._heading_target-used_yaw))
            vector[50]=np.clip(2.*error,-.8,.8)
        else:vector[50]=0.
        return vector.tolist()

    def step(self, obs, command):
        vector=np.asarray(self.build_observation(obs),dtype=np.float32)
        if vector[5]>self._projected_gravity_z_threshold:return
        self.has_walked=self.has_walked or np.linalg.norm(vector[48:51])>.001
        self.active_policy='walk' if self.has_walked else 'stand'
        self._ort_session=self._sessions[self.active_policy]
        action=self._ort_session.run(None,{self._ort_session.get_inputs()[0].name:vector[None]})[0][0]
        if action.shape!=(14,) or not np.all(np.isfinite(action)):raise ValueError('Invalid policy action')
        self._last_action=action.tolist()
        from constants import OBSERVATION_DOF_ORDER
        for i,n in enumerate(OBSERVATION_DOF_ORDER):
            command.target_angles[n]=self._default_pose[n]+float(action[i])
