"""Independent rigid-rotation/constant-velocity checks and runtime age contract."""
from pathlib import Path
import ast,json,numpy as np
from scipy.spatial.transform import Rotation
from compensation import compensate
from runtime_compensation import compensate_arrived_state
P=Path(__file__).resolve().parent
cfg={'delay_compensation':'constant_velocity','prediction_fraction':1.,'predict_heading':True}
x=np.r_[[.3,-.2,.7],[.2,.3,-np.sqrt(.87)],np.linspace(-.4,.4,14),np.linspace(-2,2,14)]
before=x.copy();h=.04;pred,yaw=compensate(x,.5,h,cfg)
np.testing.assert_allclose(pred[3:6],Rotation.from_rotvec(-x[:3]*h).apply(x[3:6]),atol=1e-14)
np.testing.assert_allclose(pred[6:20],x[6:20]+h*x[20:34],atol=1e-14)
np.testing.assert_array_equal(x,before)
out,oldyaw,status=compensate_arrived_state(x,.5)
np.testing.assert_array_equal(out,x);assert oldyaw==.5 and not status['enabled']
# A host receipt timestamp alone explicitly leaves prediction off.
out,_,status=compensate_arrived_state(x,.5,imu_sample_age_s=.04,joint_sample_age_s=.04,age_basis='host_receipt_timestamp')
np.testing.assert_array_equal(out,x);assert not status['enabled']
out,newyaw,status=compensate_arrived_state(x,.5,imu_sample_age_s=.04,joint_sample_age_s=.04,age_basis='validated_latency_estimate')
np.testing.assert_allclose(out,pred,atol=1e-14);assert newyaw==yaw and status['enabled']
mixed,_,_=compensate_arrived_state(x,.5,imu_sample_age_s=.02,joint_sample_age_s=.04,age_basis='device_sample_timestamp')
np.testing.assert_allclose(mixed[3:6],Rotation.from_rotvec(-x[:3]*.02).apply(x[3:6]),atol=1e-14)
np.testing.assert_allclose(mixed[6:20],pred[6:20],atol=1e-14)
try:compensate_arrived_state(x,.5,imu_sample_age_s=.06,joint_sample_age_s=.04,age_basis='validated_latency_estimate');raise AssertionError('Accepted 60 ms')
except ValueError:pass
simple=np.zeros(34);simple[2]=1.;simple[5]=-1
_,angle=compensate(simple,np.pi-.01,.04,cfg);assert abs(angle-(-np.pi+.03))<1e-12
imports=[n.names[0].name for n in ast.walk(ast.parse((P/'compensation.py').read_text())) if isinstance(n,ast.Import)]
assert set(imports)=={'math','numpy'}
report={'passed':True,'checks':['independent SciPy rotation equivalence','constant joint velocity analytic result','input immutability','unknown age disables prediction','host receipt age alone rejected as sample age','known equal age equals simulated predictor','separate IMU/joint ages','60ms explicitly rejected','yaw wrap','pure helper imports no simulator/hardware'],
        'causality':'Core signature only accepts arrived 34D state, arrived yaw, age and scalar config. No current MuJoCo state is passed.'}
(P/'compensation-tests.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
