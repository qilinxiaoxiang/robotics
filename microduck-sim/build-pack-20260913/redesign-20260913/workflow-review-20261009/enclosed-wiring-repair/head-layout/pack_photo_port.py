"""Finite 1 mm occupancy packing; not acceptance. Actual part inventories, closed cap."""
import os,json,sys,types,hashlib,gc,itertools
from pathlib import Path
assert os.environ.get('MICRODUCK_BOUNDED_CAD')=='1'
import numpy as np,trimesh as tm,manifold3d as mf
from matplotlib.path import Path as MPath
from scipy.signal import fftconvolve
from scipy.spatial import ConvexHull
D=Path(__file__).resolve().parent;R=D.parents[2];H=R/'head-redesign-20261008';W=R/'workflow-review-20261009'
sys.path.insert(0,str(H/'gpio-audio-repair'));import precision_mesh as pm
ctx=types.SimpleNamespace(np=np,tm=tm,mf=mf);sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
mp=W/'original-body-converter/fusion-import-manifest.json';man=json.loads(mp.read_text());rows={q['key']:q for q in man['parts']};hashes={str(mp):sha(mp),str(Path(__file__)):sha(Path(__file__))}
def load(p):
 p=Path(p);hashes[str(p)]=sha(p);return pm.load(ctx,p)
def source(k):
 row=rows[k];s=load(row['file']);return s.translate(row.get('importTranslationMm',[0,0,0]))
def raster(s,lo,shape):
 out=np.zeros(shape,np.uint8);b=np.array(s.bounding_box()).reshape(2,3);mn=np.maximum(0,np.floor(b[0]-lo).astype(int));mx=np.minimum(shape,np.ceil(b[1]-lo).astype(int)+1)
 if np.any(mx<=mn):return out
 xs=np.arange(mn[0],mx[0])+lo[0];ys=np.arange(mn[1],mx[1])+lo[1];X,Y=np.meshgrid(xs,ys,indexing='ij');pts=np.column_stack((X.ravel(),Y.ravel()))
 for iz in range(mn[2],mx[2]):
  inside=np.zeros(len(pts),np.int16)
  for poly in s.slice(float(lo[2]+iz)).to_polygons():
   p=np.asarray(poly);area=np.sum(p[:,0]*np.roll(p[:,1],-1)-p[:,1]*np.roll(p[:,0],-1));inside+=(1 if area>0 else -1)*MPath(p).contains_points(pts,radius=1e-8)
  out[mn[0]:mx[0],mn[1]:mx[1],iz]=(inside>0).reshape(len(xs),len(ys))
 return out
pikeys=[k for k in rows if k=='pi' or k.startswith(('zero_w_','gpio_pin_','component_'))]
retired=['openrb','openrb_usb_receiving','curved_cap_hardware','camera_ribbon_200','amplifier']+[k for k in rows if k.startswith('E-pi-')]
lo=np.array([-32.,-47.,107.]);shape=(129,95,54);dest=D/'packing-photo';dest.mkdir(exist_ok=True)
cache=D/'packing-amp-free/fixed.npz';meta=D/'packing-amp-free/fixed.json'
if cache.exists():
 info=json.loads(meta.read_text());assert all(sha(Path(k))==v for k,v in info['sourceHashes'].items() if Path(k)!=Path(__file__));a=np.load(cache);fixed=a['fixed'];outside=a['outside'];hashes.update(info['sourceHashes']);hashes[str(Path(__file__))]=sha(Path(__file__))
else:
 fixed=np.zeros(shape,np.uint8);cap=load(D/'native-cap-registered-world.stl');mesh=cap.to_mesh64();hull=ConvexHull(mesh.vert_properties[:,:3]);eq=hull.equations;outside=np.zeros(shape,np.uint8);grid=np.indices(shape).reshape(3,-1).T+lo
 for start in range(0,len(grid),512):outside.ravel()[start:start+512]=np.any(grid[start:start+512]@eq[:,:3].T+eq[:,3]>.0,axis=1)
 del grid,hull,eq,mesh
 for k,row in rows.items():
  if k in pikeys+retired:continue
  if k=='head_cap':s=cap
  elif k=='face_panel':s=load(H/'camera-ribbon-repair/positive-x225/face_three_screw_camera-world.stl')
  else:s=source(k)
  fixed|=raster(s,lo,shape);del s;gc.collect()
 np.savez_compressed(cache,fixed=fixed,outside=outside);meta.write_text(json.dumps({'sourceHashes':dict(hashes),'piKeys':pikeys,'retiredMountsAndFlexibleShapes':retired,'lo':lo.tolist(),'shape':shape,'pitch':1},indent=2)+'\n')
 del cap
# Normalize board basis then use 24 proper cardinal placements. Tilt is deferred until a coarse corridor exists.
piT=np.array(json.loads((H/'camera-ribbon-repair/fixed-pose-local-bend/pi-spacer2-pose.json').read_text())['worldTransform']);picenter=np.array([68.11,-.0113773,131.0496]);pibase=np.eye(4);pibase[:3,3]=-picenter;pibase=pibase@np.linalg.inv(piT)
rbbase=np.eye(4);ang=np.radians(3);rbbase[:3,:3]=[[np.cos(ang),0,-np.sin(ang)],[0,1,0],[np.sin(ang),0,np.cos(ang)]];rbbase[:3,3]=-rbbase[:3,:3]@np.array([25,0,140])
kind=sys.argv[1] if len(sys.argv)>1 else 'pi';mode=sys.argv[2] if len(sys.argv)>2 else 'cardinal';parts=[]
if kind=='pi':
 for k in pikeys:parts.append(source(k).transform(pibase[:3]))
 # Unknown SC0727 mould bound, kept explicit and not called manufacturer geometry.
 # Historical receiving 25 length x18 width x8 thickness, now required fully internal.
 parts.append(mf.Manifold.cube([6,13,25]).translate([61.2,2.4,146.0496]).translate(-picenter))
 base=pibase
else:
 ep=H/'usb-access/usb-repair/openrb-component-enclosures/manifest.json';hashes[str(ep)]=sha(ep)
 for r in json.loads(ep.read_text())['components']:parts.append(load(r['mesh']).transform(rbbase[:3]))
 parts.append(load(H/'usb-access/full-harness/openrb-usb-c-published-envelope-world.stl').transform(rbbase[:3]));base=rbbase
solid=mf.Manifold.batch_boolean(parts,mf.OpType.Add);del parts;gc.collect()
rots=[]
for perm in itertools.permutations(range(3)):
 for signs in itertools.product([-1,1],repeat=3):
  rot=np.eye(3)[list(perm)]*np.array(signs)[:,None]
  if np.linalg.det(rot)>.5:rots.append(rot)
if mode=='yaw':
 selected=rots[:4] if kind=='openrb' else [rots[20],rots[21]]
 rots=[]
 for src in selected:
  for degrees in [-45,-30,-15,15,30,45]:
   a=np.radians(degrees);z=np.array([[np.cos(a),-np.sin(a),0],[np.sin(a),np.cos(a),0],[0,0,1]]);rots.append(z@src)
if mode=='tilt':
 selected=[rots[20],rots[21]] if kind=='pi' else [rots[0],rots[1],rots[2],rots[3]]
 rots=[]
 for src in selected:
  for degrees in [-15,15]:
   a=np.radians(degrees)
   for axis in ['x','y']:
    q=np.array([[1,0,0],[0,np.cos(a),-np.sin(a)],[0,np.sin(a),np.cos(a)]]) if axis=='x' else np.array([[np.cos(a),0,np.sin(a)],[0,1,0],[-np.sin(a),0,np.cos(a)]])
    for yaw in [0,15]:
     b=np.radians(yaw);z=np.array([[np.cos(b),-np.sin(b),0],[np.sin(b),np.cos(b),0],[0,0,1]])
     rots.append(z@q@src)
if mode=='partition':
 selected=[rots[20],rots[21]] if kind=='pi' else rots[4:8]
 rots=[]
 for src in selected:
  for degrees in [-30,30] if kind=='pi' else [-45,-30,30,45]:
   a=np.radians(degrees)
   if kind=='openrb':rots.append(np.array([[np.cos(a),-np.sin(a),0],[np.sin(a),np.cos(a),0],[0,0,1]])@src)
   else:
    for axis in ['x','y']:
     q=np.array([[1,0,0],[0,np.cos(a),-np.sin(a)],[0,np.sin(a),np.cos(a)]]) if axis=='x' else np.array([[np.cos(a),0,np.sin(a)],[0,1,0],[-np.sin(a),0,np.cos(a)]])
     for yaw in [0,15]:
      b=np.radians(yaw);z=np.array([[np.cos(b),-np.sin(b),0],[np.sin(b),np.cos(b),0],[0,0,1]]);rots.append(z@q@src)
results=[]
for idx,rot in enumerate(rots):
 idx += 100 if mode=='yaw' else (200 if mode=='tilt' else (300 if mode=='partition' else 0))
 t=np.column_stack((rot,np.zeros(3)));s=solid.transform(t);b=np.array(s.bounding_box()).reshape(2,3);pmin=np.floor(b[0]);pmax=np.ceil(b[1]);pshape=tuple((pmax-pmin).astype(int)+1)
 if any(np.array(pshape)>shape):continue
 occ=raster(s,pmin,pshape);del s
 overlap=np.rint(fftconvolve(fixed.astype(np.float32),occ[::-1,::-1,::-1].astype(np.float32),mode='valid')).astype(np.int32)
 ext=np.rint(fftconvolve(outside.astype(np.float32),occ[::-1,::-1,::-1].astype(np.float32),mode='valid')).astype(np.int32)
 score=overlap+ext*20;order=np.argsort(score,axis=None)[:5000];picks=[]
 for ix in order:
  xyz=np.array(np.unravel_index(ix,score.shape));center=lo+xyz-pmin
  if any(np.linalg.norm(center-np.array(q['center']))<2 for q in picks):continue
  T=np.eye(4);T[:3,:3]=rot;T[:3,3]=center;T=T@base
  picks.append({'center':center.tolist(),'overlap':int(overlap[tuple(xyz)]),'outside':int(ext[tuple(xyz)]),'score':int(score[tuple(xyz)]),'currentWorldDelta':T.tolist(),'gridOrigin':xyz.tolist()})
  if len(picks)>=40:break
 results.append({'orientationId':idx,'rotation':rot.tolist(),'boundsNormalized':[pmin.tolist(),pmax.tolist()],'occupiedVoxels':int(occ.sum()),'candidates':picks})
 np.savez_compressed(dest/f'{kind}-orientation-{idx}.npz',occupancy=occ)
 report={'kind':kind,'screeningOnly':True,'integrationReady':False,'parts':pikeys if kind=='pi' else '142 component hulls + published C plug','unverifiedReceiving':'Pi microB photo-derived receiving25x13x6, not manufacturer tolerance; OpenRB C thickness7 assumed. All plug bodies constrained inside cap.','results':results,'sourceHashes':hashes}
 (dest/f'{kind}-{mode}-screen.json').write_text(json.dumps(report,indent=2)+'\n');print(kind,idx,[(p['center'],p['overlap'],p['outside'])for p in picks[:2]],flush=True)
 del occ,overlap,ext,score;gc.collect()
