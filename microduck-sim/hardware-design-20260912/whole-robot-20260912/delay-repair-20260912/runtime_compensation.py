"""Runtime-facing causal predictor, disabled when sample age is unknown.

No clock, simulator or device is opened. Callers provide already-arrived body-frame
state and separately justified IMU/joint SAMPLE ages; host receipt age is not enough.
"""
import math
import numpy as np
from compensation import compensate

def compensate_arrived_state(received_34,received_yaw,*,imu_sample_age_s=None,
                            joint_sample_age_s=None,age_basis='unknown'):
    x=np.asarray(received_34,dtype=float)
    if x.shape!=(34,) or not np.all(np.isfinite(x)) or not math.isfinite(received_yaw):
        raise ValueError('Finite received gyro3/gravity3/q14/dq14 and body yaw required')
    known=age_basis in ('device_sample_timestamp','validated_latency_estimate')
    if not known or imu_sample_age_s is None or joint_sample_age_s is None:
        return x.copy(),float(received_yaw),{'enabled':False,'reason':'sample_age_unknown'}
    ages=[float(imu_sample_age_s),float(joint_sample_age_s)]
    if any(not math.isfinite(h) or h<0 for h in ages):raise ValueError('Invalid sample age')
    if max(ages)>.040000001:
        raise ValueError('Sample age exceeds the tested 0–40 ms window; no silent age clipping')
    cfg={'delay_compensation':'constant_velocity','prediction_fraction':1.,'predict_heading':True}
    imup,yaw=compensate(x,received_yaw,ages[0],cfg)
    jointp,_=compensate(x,received_yaw,ages[1],cfg)
    result=x.copy();result[3:6]=imup[3:6];result[6:20]=jointp[6:20]
    return result,yaw,{'enabled':True,'imu_sample_age_s':ages[0],
                      'joint_sample_age_s':ages[1],'age_basis':age_basis,
                      'limitation':'Simulation tested equal packet ages; distinct per-sensor ages need deployment validation.'}
