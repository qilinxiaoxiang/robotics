from pathlib import Path
import json,numpy as np,trimesh,manifold3d as mf
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
D=Path(__file__).resolve().parent;W=D.parents[2];M=json.loads((W/'original-body-converter/fusion-import-manifest.json').read_text());P={q['key']:q for q in M['parts']}
def solid(p):
 m=trimesh.load_mesh(p);assert m.is_volume,p;return mf.Manifold(mf.Mesh64(np.ascontiguousarray(m.vertices),np.ascontiguousarray(m.faces,dtype=np.uint64)))
G=json.loads((W.parent/'leg-guide-20261006/full-build-data.json').read_text());T={p['key']:np.array(p.get('sourceTransformWorld',np.eye(4)))for p in G['parts']}
nm=json.loads((W/'enclosed-wiring-repair/ankle-wires/native-motors/manifest.json').read_text());ms=[p for p in nm['parts']if p['motor']==2]
def sources(k):
 if k.startswith('motor'):
  for p in ms:yield solid(p['file']).transform((T[k]@np.linalg.inv(p['worldTransform']))[:3])
 else:
  p=P[k];yield solid(p['file']).translate(p.get('importTranslationMm',[0,0,0]))
fig,axes=plt.subplots(1,4,figsize=(16,5))
for ax,z in zip(axes,[99.8,100.5,101.2,102]):
 for k,color in [('head_bottom','#ff8800'),('head_yaw_link','#333333'),('neck_pitch','#333333'),('motor13','#5577cc'),('motor14','#5577cc')]:
  for s in sources(k):
   for poly in s.slice(z).to_polygons():
    a=np.asarray(poly);ax.plot(a[:,0],a[:,1],color=color,lw=1)
 ax.set(xlim=(-45,50),ylim=(-50,40),aspect='equal',title=f'Z={z} mm',xlabel='X mm',ylabel='Y mm');ax.grid()
fig.tight_layout();fig.savefig(D/'neck-floor-sections.png',dpi=100)
# Plug exact receiving bounds from source binary mesh.
H=W/'enclosed-wiring-repair/head-layout/body-partition'
for name in ['USB_C_mould22','USB_C_strain5']:
 m=trimesh.load_mesh(H/(name+'-world.stl'));print(name,(m.bounds+[-.5,0,0]).tolist())
