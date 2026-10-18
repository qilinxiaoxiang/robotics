from pathlib import Path
p=Path(__file__).resolve().parent.parent/'head-fit-investigation.py';ns={'__file__':str(p)};exec(p.read_text().split("report={'problemIds'")[0],ns);globals().update(ns)
F={k:solid(k) for k in ['jaw_support','head_bottom','motor15','motor14','head_yaw_link','head_roll_ring_a','head_roll_ring_b']};jaw=solid('jaw_frame')
for y in [-35,-30,-25]:
 arm=jaw^box([-100,-100,0],[150,y-.1,250]);main=jaw^box([-100,y+.1,0],[150,100,250]);print('PIECES',y,len(arm.decompose()),len(main.decompose()),flush=True)
 for name,s,v,f in [('main',main,[0,32,0],F),('arm',arm,[0,-32,0],F|{'main':main})]:
  print(y,name,samples({name:s},f,v,step=.5)['peakContactsMm3'],flush=True)
