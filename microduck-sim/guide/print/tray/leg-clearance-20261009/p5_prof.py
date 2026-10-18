import time; t=time.time()
import p5_field as P
print('build', round(time.time()-t,1), 'npts', {s: len(P.PTS[s][1]) for s in P.PTS}, flush=True)
t=time.time(); q={'left_hip_yaw':-0.2,'left_hip_roll':0.0,'left_hip_pitch':0.5,'left_knee':0.0,'left_ankle':0.45}
for _ in range(5): r,_=P.evaluate('left',q)
print('eval', round((time.time()-t)/5,3), r, flush=True)
import numpy as np
cnt=[0]; orig=P.evaluate
def ev(s,q): cnt[0]+=1; return orig(s,q)
P.evaluate=ev
t=time.time(); f,s=P.sweep('left',{'left_hip_yaw':-0.2,'left_hip_roll':0.0,'left_knee':0.0,'left_ankle':0.453},-0.4579,1.5708)
print('sweep', cnt[0], 'poses', round(time.time()-t,1), 's', f, s, flush=True)
