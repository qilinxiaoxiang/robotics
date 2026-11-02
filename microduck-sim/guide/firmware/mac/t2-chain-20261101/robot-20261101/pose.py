import json,sys,os
sys.path.insert(0,'.')
import onnxruntime as ort, walk_brain as wb
O=os.path.expanduser('~/code/robotics/microduck-sim/hardware-design-20260912/whole-robot-20260912/runtime-overlay/models')
m=ort.InferenceSession(O+'/stand61.onnx').get_modelmeta().custom_metadata_map
dj=json.loads(m['default_joint_pos']) if m['default_joint_pos'].startswith('[') else [float(x) for x in m['default_joint_pos'].split(',')]
d=dict(zip(wb.OBSERVATION_DOF_ORDER,dj))
rows=[json.loads(l) for l in open(sys.argv[1]) if l.startswith('{')]
t0=1793584883.6
r=[x for x in rows if x['t']-t0>=3.88 and x['mode']=='seepick'][0]
print('pose at the hand-back minus stand61 default, rad')
for i,n in enumerate(wb.NAMES):
    print(f'  {n:18s} q {r["q"][i]:+.2f} default {d[n]:+.2f} diff {r["q"][i]-d[n]:+.2f}')
ts=[x for x in rows if x['t']-t0>=3.88 and x['mode']=='walk'][:4]
print('obs order',wb.OBSERVATION_DOF_ORDER)
print('last T2 action',[round(v,2) for v in r['action']])
for x in ts: print(round(x['t']-t0,3),x.get('policy'),[round(v,2) for v in (x['action'] or [])])
