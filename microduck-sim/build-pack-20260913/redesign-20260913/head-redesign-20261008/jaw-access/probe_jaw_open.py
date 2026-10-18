from pathlib import Path
p=Path(__file__).resolve().parent.parent/'head-fit-investigation.py';ns={'__file__':str(p)};exec(p.read_text().split("report={'problemIds'")[0],ns);globals().update(ns)
F={k:solid(k) for k in ['jaw_support','head_bottom','motor15','motor14','head_yaw_link','head_roll_ring_a','head_roll_ring_b']};jaw=solid('jaw_frame');arm=jaw^box([-100,-100,0],[150,-30.1,250]);main=jaw^box([-100,-29.9,0],[150,100,250]);p=np.array([26.1,0,118.6146])
for a in [15,20,30]:
 def pose(m):return m.translate(-p).rotate([0,a,0]).translate(p)
 j=pose(main);ar=pose(arm);pad=pose(solid('lower_pad'))
 print(a,'mainpad',samples({'main':j,'pad':pad},F,[0,32,0],step=.5)['peakContactsMm3'],flush=True)
 print(a,'arm',samples({'arm':ar},F|{'main':j,'pad':pad},[0,-32,0],step=.5)['peakContactsMm3'],flush=True)
