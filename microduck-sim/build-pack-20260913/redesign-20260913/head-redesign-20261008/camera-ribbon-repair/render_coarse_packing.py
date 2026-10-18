from pathlib import Path
import os,json,base64,hashlib,gc
assert os.environ.get('MICRODUCK_BOUNDED_CAD')=='1'
import numpy as np,trimesh as tm
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection,LineCollection
D=Path(__file__).resolve().parent;H=D.parent;O=D/'roof-tilted-layout'
cfg=json.loads((H/'viewer-candidate.json').read_text());files=cfg['replacementMeshes']|{p['key']:p['mesh'] for p in cfg['additionalParts']};cache=json.loads((D/'head-source-cache/index.json').read_text())['parts'];hashes={}
def read(p):
 b=p.read_bytes();hashes[str(p)]=hashlib.sha256(b).hexdigest();return b
def source(k):
 if k in files:
  p=H/files[k];read(p);return tm.load(p,force='mesh')
 p=D/'head-source-cache'/cache[k];a=json.loads(read(p));return tm.Trimesh(np.frombuffer(base64.b64decode(a['positionB64']),'<f4').reshape(-1,3),np.frombuffer(base64.b64decode(a['indexB64']),'<u4').reshape(-1,3),process=False)
fig,axes=plt.subplots(1,3,figsize=(18,7));projections=[(0,1,'Top: X / Y'),(0,2,'Side: X / Z'),(1,2,'Front: Y / Z')]
for ax,(a,b,title) in zip(axes,projections):ax.set_aspect('equal');ax.set_title(title);ax.set_xlabel('XYZ'[a]+' (mm)');ax.set_ylabel('XYZ'[b]+' (mm)');ax.grid(alpha=.15)
rows=[]
def draw(k,m,c,alpha=.22,z=2):
 rows.append({'key':k,'boundsMm':m.bounds.tolist()});tri=m.triangles;step=max(1,len(tri)//2200);tri=tri[::step]
 for ax,(a,b,_) in zip(axes,projections):
  ax.add_collection(PolyCollection(tri[:,:,[a,b]],facecolors=c,edgecolors='none',alpha=alpha,zorder=z));cen=m.bounds.mean(0);ax.text(cen[a],cen[b],k,fontsize=6,zorder=8,color=c)
 del tri;gc.collect()
p=H/'curved-head/community-curved-head-world.stl';read(p);cap=tm.load(p,force='mesh')
for ax,(a,b,_) in zip(axes,projections):
 other=({0,1,2}-{a,b}).pop();normal=np.eye(3)[other];origin=cap.bounds.mean(0);origin[other]=0 if other==1 else origin[other]
 lines=tm.intersections.mesh_plane(cap,normal,origin);ax.add_collection(LineCollection(lines[:,:,[a,b]],color='#777777',linewidth=.6,zorder=0))
 bbox=cap.bounds;ax.set_xlim(bbox[0,a]-4,bbox[1,a]+4);ax.set_ylim(bbox[0,b]-4,bbox[1,b]+4)
del cap
for k in ['motor13','motor14','motor15','head_yaw_link','jaw_support','jaw_frame','speaker','head_bottom']:
 try:draw(k,source(k),'#8a5555',.1,1)
 except KeyError:pass
r=json.loads(read(O/'pi-roof-coarse.json'))
for row in r['parts']:
 p=H/row['mesh'];read(p);draw(row['key'].replace('gpio_pin_','P').replace('_receiving','').replace('zero_w_',''),tm.load(p,force='mesh'),'#197349',.35,3)
p=H/'curved-head/openrb-curved-layout-world.stl';read(p);m=tm.load(p,force='mesh');T=np.array([[1,0,0,5],[0,0,1,-161.7646],[0,-1,0,127],[0,0,0,1]]);m.apply_transform(T);draw('OpenRB proposed',m,'#287bc2',.2,3)
p=H/'gpio-audio-repair/amp16z2-closed-receiving-world.stl';read(p);m=tm.load(p,force='mesh');m.apply_translation([0,46.4,0]);draw('amp proposed',m,'#ae7600',.22,3)
p=D/'positive-x225/camera_flip180-world.stl';read(p);draw('camera reversed',tm.load(p,force='mesh'),'#8a3dad',.3,3)
fig.suptitle('COARSE ARCHITECTURE — NOT ACCEPTED\nGray: native shell central sections; brown: mechanics; green: tilted Pi + real headers; blue: proposed OpenRB; gold: proposed amp',fontsize=11)
fig.tight_layout();out=O/'coarse-packing-three-views.png';fig.savefig(out,dpi=145);plt.close(fig)
(O/'coarse-packing-render.json').write_text(json.dumps({'status':'illustration only; sampled triangles; no clearance claim','image':str(out),'objects':rows,'proposedOpenRbTransform':T.tolist(),'sourceHashes':hashes},indent=2)+'\n');print(out)
