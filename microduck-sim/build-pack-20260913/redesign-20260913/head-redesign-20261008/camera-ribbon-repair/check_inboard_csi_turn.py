from pathlib import Path
import os,json,gc
assert os.environ.get('MICRODUCK_BOUNDED_CAD')=='1'
import numpy as np,trimesh,manifold3d as mf
D=Path(__file__).resolve().parent;H=D.parent;p=D/'check_saved_pose.py';n={'__file__':str(p)};exec(p.read_text().split('resume=')[0],n);source=n['source'];man=n['man'];volume=n['volume'];mesh=n['mesh'];r=json.loads((D/'inboard-pose-pair-checks.json').read_text());T=np.array(r['worldTransform']);mouth=np.array(r['csiMouthWorldMm']);d=T[:3,1];w=T[:3,2];normal=T[:3,0]
def strip(pts,width=16,thick=.6):
 tan=np.gradient(pts,axis=0);tan/=np.linalg.norm(tan,axis=1)[:,None];ns=np.cross(tan,w);ns/=np.linalg.norm(ns,axis=1)[:,None];verts=[]
 for q,nn in zip(pts,ns):verts.extend([q-w*width/2-nn*thick/2,q+w*width/2-nn*thick/2,q+w*width/2+nn*thick/2,q-w*width/2+nn*thick/2])
 faces=[[0,2,1],[0,3,2]]
 for i in range(len(pts)-1):
  for j in range(4):a=4*i+j;b=4*i+(j+1)%4;faces.extend([[a,b,b+4],[a,b+4,a+4]])
 end=len(verts);faces.extend([[end-4,end-3,end-2],[end-4,end-2,end-1]]);m=trimesh.Trimesh(verts,faces,process=True);trimesh.repair.fix_normals(m);assert m.is_watertight;return man(m)
rows=[]
for sign in [-1,1]:
 start=mouth+d*4;v=sign*normal;pts=list(np.linspace(mouth,start,28))
 for th in np.linspace(0,np.pi/2,33)[1:]:pts.append(start+d*3*np.sin(th)+v*3*(1-np.cos(th)))
 bendend=np.array(pts[-1]);pts+=list(np.linspace(bendend,bendend+v*6,42)[1:]);s=strip(np.array(pts));hh=[]
 for k in ['head_cap','face_panel','camera_board','camera_retainer','head_bottom','openrb']:
  o=source(k);vol,bb=volume(s,o);hh.append({'obstacle':k,'volumeMm3':vol,'bounds':bb});del o;gc.collect()
 for k in ['pi','zero_w_components','zero_w_gpio_solder_tails','gpio_discrete12_receiving']:
  o=n['loadfile'](D/(k+'-inboard-pose-world.stl'));vol,bb=volume(s,o);hh.append({'obstacle':k,'volumeMm3':vol,'bounds':bb});del o;gc.collect()
 mesh(s).export(D/('pi-inboard-end-turn-'+str(sign)+'-world.stl'));rows.append({'sign':sign,'straightMm':4,'radiusMm':3,'widthMm':16,'thicknessMm':.6,'points':np.array(pts).tolist(),'checks':hh});(D/'csi-inboard-turn-probe.json').write_text(json.dumps({'rows':rows,'accepted':False,'sourceHashes':n['hashes']},indent=2)+'\n');print(sign,[h for h in hh if h['volumeMm3']>1e-5],flush=True)
