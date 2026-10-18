from pathlib import Path
p=Path(__file__).resolve().parent.parent/'head-fit-investigation.py';ns={'__file__':str(p)};exec(p.read_text().split("report={'problemIds'")[0],ns);globals().update(ns)
S=solid('jaw_support');K=S^box([-100,-100,0],[150,-20.1,250]);fixed={k:solid(k) for k in ['jaw_frame','lower_pad','motor15','motor14','head_yaw_link','head_roll_ring_a','head_roll_ring_b']}
for y in [3.0,3.2,3.5,4.0,5.0]:
 for label,a,b in [('front',[40,y,0],[0,y,0]),('seat',[0,y,0],[0,0,0])]:
  r=samples({'keeper':K},fixed,a,b,step=.5);print(y,label,r['peakContactsMm3'],flush=True)
