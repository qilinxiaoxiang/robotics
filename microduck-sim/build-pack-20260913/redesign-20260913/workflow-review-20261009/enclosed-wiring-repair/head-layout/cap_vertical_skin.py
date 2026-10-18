import os,json
from pathlib import Path
assert os.environ.get('MICRODUCK_BOUNDED_CAD')=='1'
import trimesh as tm,numpy as np
D=Path(__file__).resolve().parent;m=tm.load(D/'native-cap-registered-world.stl',force='mesh');points=[[52.5,10],[55,10],[50,10],[60,10],[70,10],[52.5,-10],[52.5,35],[55,35],[60,35],[60,0]]
a=np.array([[x,y,165]for x,y in points]);p,ii,tri=m.ray.intersects_location(a,np.tile([0,0,-1],(len(a),1)),multiple_hits=True)
r=[{'xy':xy,'surfaceZ':sorted(p[ii==i,2].tolist(),reverse=True)}for i,xy in enumerate(points)];(D/'cap-vertical-skin.json').write_text(json.dumps(r,indent=2));print(json.dumps(r))
