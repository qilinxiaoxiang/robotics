import json, math, sys
O=["left_hip_yaw","left_hip_roll","left_hip_pitch","left_knee","left_ankle","neck_pitch","head_pitch","head_yaw","head_roll","right_hip_yaw","right_hip_roll","right_hip_pitch","right_knee","right_ankle"]
M={"right_hip_yaw":5,"right_hip_roll":4,"right_hip_pitch":3,"right_knee":2,"right_ankle":1,"left_hip_yaw":10,"left_hip_roll":9,"left_hip_pitch":8,"left_knee":7,"left_ankle":6,"neck_pitch":12,"head_pitch":11,"head_yaw":13,"head_roll":14}
rows=[json.loads(l) for l in open('sit-region.jsonl') if l.startswith('{')]
t0=rows[0]['t']
# episodes: contiguous mode==sit
eps=[];cur=None
for i,r in enumerate(rows):
    if r['mode']=='sit':
        if cur is None: cur=[i,i]
        cur[1]=i
    elif cur: eps.append(cur);cur=None
if cur: eps.append(cur)
def pitch(r): g=r['gb']; return math.degrees(math.atan2(g[0],-g[2]))
def j(r,n): return r['q'][O.index(n)]
for k,(a,b) in enumerate(eps):
    ts=rows[a]['t']
    # rise start = first row where cmd mode != sit
    rs=next((i for i in range(a,b+1) if rows[i]['cmd'].get('mode')!='sit'),None)
    print(f"\nEP{k} sit {ts-t0:.1f}s..{rows[b]['t']-t0:.1f}s  rise at {rows[rs]['t']-t0 if rs else None}")
    if rs is None: continue
    # seated pose just before rise
    r=rows[rs-1]
    print(f"  seated: pitch {pitch(r):+.1f} knees L{j(r,'left_knee'):+.2f} R{j(r,'right_knee'):+.2f} hipP L{j(r,'left_hip_pitch'):+.2f} R{j(r,'right_hip_pitch'):+.2f} neck {j(r,'neck_pitch'):+.2f} head {j(r,'head_pitch'):+.2f} cmd_before {rows[rs-1]['cmd']} cmd {rows[rs]['cmd']}")
    seated_s = rows[rs]['t']-ts
    print(f"  time in sit before rise: {seated_s:.2f}s")
    for i in range(rs, min(b+40,len(rows)), 5):
        r=rows[i]; act=r['action']; am=max(abs(x) for x in act) if act else None
        print(f"   +{r['t']-rows[rs]['t']:.2f} {r['mode']:5s} pitch {pitch(r):+6.1f} roll {math.degrees(math.atan2(r['gb'][1],-r['gb'][2])):+5.1f} gyroY {r['gyro_body'][1]:+5.2f} kneeL {j(r,'left_knee'):+.2f} kneeR {j(r,'right_knee'):+.2f} hipPL {j(r,'left_hip_pitch'):+.2f} hipPR {j(r,'right_hip_pitch'):+.2f} ankL {j(r,'left_ankle'):+.2f} ankR {j(r,'right_ankle'):+.2f} amax {am if am is None else round(am,2)} miss {r['missing']} v {r['servo_v']} legs_ma {r.get('legs_ma')}")
