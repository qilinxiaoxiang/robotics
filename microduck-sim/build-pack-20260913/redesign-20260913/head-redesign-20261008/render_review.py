"""Offline orthographic render of actual source/candidate meshes, no browser."""
from pathlib import Path
import json,base64
import numpy as np,trimesh
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from matplotlib.colors import to_rgb
D=Path(__file__).resolve().parent;G=D.parent/'leg-guide-20261006';data=json.loads((G/'full-build-data.json').read_text());config=json.loads((D/'viewer-candidate.json').read_text())
keys=['head_cap','head_bottom','face_panel','eye_trim','jaw_frame','upper_pad','lower_pad','jaw_support','motor14','motor15','head_yaw_link','head_roll_ring_a','head_roll_ring_b','pi','openrb','audio_carrier','amplifier','speaker','camera_board','camera_pitch_foot','camera_cradle']
parts=[]
for p in data['parts']:
 if p['key'] not in keys:continue
 m=trimesh.Trimesh(np.frombuffer(base64.b64decode(p['positionB64']),'<f4').reshape(-1,3),np.frombuffer(base64.b64decode(p['indexB64']),'<u4').reshape(-1,3),process=True)
 parts.append((p,m))
for spec in config.get('additionalParts',[]):
 if spec.get('plugEnvelope'):continue
 parts.append(({**spec,'candidateOnly':True},trimesh.load(D/spec['mesh'],force='mesh')))
view=np.array([1.,-.70,.32]);view/=np.linalg.norm(view);right=np.cross([0,0,1],view);right/=np.linalg.norm(right);up=np.cross(view,right);R=np.array([right,up,view]);light=np.array([1,-1,2]);light=light/np.linalg.norm(light)
fig,axes=plt.subplots(1,2,figsize=(15,8),facecolor='#f3f3ee')
for ax,candidate in zip(axes,[False,True]):
 poly=[];col=[];depth=[]
 for p,original in parts:
  k=p['key'];m=original.copy()
  if p.get('candidateOnly') and not candidate:continue
  if candidate and k in config.get('removedParts',[]):continue
  if candidate and k in config.get('replacementMeshes',{}):m=trimesh.load(D/config['replacementMeshes'][k],force='mesh')
  if candidate and k in config.get('transforms',{}):m.apply_transform(config['transforms'][k])
  tr=m.triangles;screen=tr@R.T;norm=m.face_normals
  front=(norm@view)>0
  tri=screen[front];shade=.55+.45*np.maximum(0,norm[front]@light)
  rgb=np.array(to_rgb('#121d19' if k=='camera_board' else p['color']))
  colors=np.clip(shade[:,None]*rgb[None,:],0,1)
  poly.extend(tri[:,:,:2]);depth.extend(tri[:,:,2].mean(axis=1));col.extend(colors)
 # Per-pixel depth test prevents a large shell triangle covering nearer faces.
 W,H=1250,1000;xlo,xhi=-92,85;ylo,yhi=78,205
 rgb=np.ones((H,W,3))*np.array([243,243,238])/255;zbuf=np.full((H,W),-np.inf)
 # Rebuild triangles with their vertex depths (painter ordering is insufficient).
 for p,original in parts:
  k=p['key'];m=original.copy()
  if p.get('candidateOnly') and not candidate:continue
  if candidate and k in config.get('removedParts',[]):continue
  if candidate and k in config.get('replacementMeshes',{}):m=trimesh.load(D/config['replacementMeshes'][k],force='mesh')
  if candidate and k in config.get('transforms',{}):m.apply_transform(config['transforms'][k])
  screen=m.triangles@R.T;norm=m.face_normals;front=(norm@view)>0
  base=np.array(to_rgb('#202a25' if k=='camera_board' else p['color']))
  for tri,n in zip(screen[front],norm[front]):
   px=(tri[:,0]-xlo)/(xhi-xlo)*(W-1);py=(yhi-tri[:,1])/(yhi-ylo)*(H-1)
   xa=max(0,int(np.floor(px.min())));xb=min(W-1,int(np.ceil(px.max())));ya=max(0,int(np.floor(py.min())));yb=min(H-1,int(np.ceil(py.max())))
   if xa>xb or ya>yb:continue
   den=(py[1]-py[2])*(px[0]-px[2])+(px[2]-px[1])*(py[0]-py[2])
   if abs(den)<1e-9:continue
   xx,yy=np.meshgrid(np.arange(xa,xb+1)+.5,np.arange(ya,yb+1)+.5)
   a=((py[1]-py[2])*(xx-px[2])+(px[2]-px[1])*(yy-py[2]))/den
   b=((py[2]-py[0])*(xx-px[2])+(px[0]-px[2])*(yy-py[2]))/den;c=1-a-b
   z=a*tri[0,2]+b*tri[1,2]+c*tri[2,2];mask=(a>=-1e-8)&(b>=-1e-8)&(c>=-1e-8)&(z>zbuf[ya:yb+1,xa:xb+1])
   zbuf[ya:yb+1,xa:xb+1][mask]=z[mask];rgb[ya:yb+1,xa:xb+1][mask]=np.clip(base*(.6+.4*max(0,n@light)),0,1)
 ax.imshow(rgb,extent=[xlo,xhi,ylo,yhi]);ax.set_aspect('equal');ax.axis('off');ax.set_title('Restored curved head · eye camera' if candidate else 'Rejected earlier box shell',fontsize=19,color='#20382c',pad=16)
fig.text(.06,.955,'MICRODUCK  /  HEAD LAYOUT',fontsize=12,color='#4c6455',weight='bold');fig.text(.06,.05,'Zero W with soldered 40-pin header preferred; Pi 3 fit unverified.\nShell comparison; USB plug clearance shown separately online. Full cabling and physical fit remain unverified.',fontsize=11,color='#53675a');fig.subplots_adjust(left=.025,right=.985,top=.89,bottom=.12,wspace=.04);fig.savefig(D/'eye-camera-comparison.png',dpi=150,facecolor=fig.get_facecolor());print('OFFLINE_CAD_RENDER_PASS')
