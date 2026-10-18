"""Bounded 1mm occupancy translation screen, NOT acceptance; all outputs require solid tests."""
from pathlib import Path
D=Path(__file__).resolve().parent
exec((D/'build_reverse_nut_camera.py').read_text().split('cam=load')[0]);read(Path(__file__))
from matplotlib.path import Path as MPath
from scipy.signal import fftconvolve
from scipy.spatial import ConvexHull
step=1.;lo=np.array([-35.,-48.,75.]);shape=(131,97,131);fixed=np.zeros(shape,np.uint8);hashes=n['hashes'];dest=D/'occupancy-layout';dest.mkdir(exist_ok=True)
def raster(s,lo,shape):
 out=np.zeros(shape,np.uint8);b=np.array(s.bounding_box()).reshape(2,3);mn=np.maximum(0,np.floor(b[0]-lo).astype(int));mx=np.minimum(shape,np.ceil(b[1]-lo).astype(int)+1)
 if np.any(mx<=mn):return out
 xs=np.arange(mn[0],mx[0])+lo[0];ys=np.arange(mn[1],mx[1])+lo[1];X,Y=np.meshgrid(xs,ys,indexing='ij');pts=np.column_stack((X.ravel(),Y.ravel()))
 for iz in range(mn[2],mx[2]):
  polys=s.slice(float(lo[2]+iz)).to_polygons();inside=np.zeros(len(pts),np.int16)
  for poly in polys:
   p=np.asarray(poly);area=np.sum(p[:,0]*np.roll(p[:,1],-1)-p[:,1]*np.roll(p[:,0],-1));inside+=(1 if area>0 else -1)*MPath(p).contains_points(pts,radius=1e-8)
  out[mn[0]:mx[0],mn[1]:mx[1],iz]=(inside>0).reshape(len(xs),len(ys))
 return out
cache=dest/'fixed-ports-1mm.npz';meta=dest/'fixed-ports-1mm.json'
if cache.exists():
 info=json.loads(read(meta));assert all(__import__('hashlib').sha256(Path(k).read_bytes()).hexdigest()==v for k,v in info['sourceHashes'].items());a=np.load(cache);fixed=a['fixed'];outside=a['outside'];hard=a['hard'];hashes.update(info['sourceHashes'])
else:
 cap=load(H/'curved-head/community-curved-head-world.stl');mesh=cap.to_mesh64();hull=ConvexHull(mesh.vert_properties[:,:3]);eq=hull.equations;outside=np.zeros(shape,np.uint8);grid=np.indices(shape).reshape(3,-1).T+lo
 for start in range(0,len(grid),512):
  # Containment screen: exact convex hull, 0.5mm internal margin. Source hull only; exact shell remains separate.
  outside.ravel()[start:start+512]=np.any(grid[start:start+512]@eq[:,:3].T+eq[:,3]>.0,axis=1)
 del grid,hull,mesh,eq
 capmask=raster(cap,lo,shape);del cap
 for k in ['motor13','motor14','motor15','jaw_support','jaw_frame','head_yaw_link','head_roll_ring_a','head_roll_ring_b','speaker','head_bottom','upper_pad','lower_pad']:
  if k not in n['P'] and k not in n['files']:continue
  s=n['source'](k);fixed|=raster(s,lo,shape);del s;gc.collect()
 for p in [O/'camera_flip180-world.stl',H/'gpio-audio-repair/amp16z2-closed-receiving-world.stl']:
  s=load(p);fixed|=raster(s,lo,shape);del s
 rb=json.loads(read(H/'usb-access/usb-repair/openrb-component-enclosures/manifest.json'))
 for row in rb['components']:
  s=load(Path(row['mesh']));fixed|=raster(s,lo,shape);del s
 hard=fixed.copy();fixed|=capmask;np.savez_compressed(cache,fixed=fixed,hard=hard,outside=outside);meta.write_text(json.dumps({'sourceHashes':dict(hashes),'voxelPitchMm':1,'fixedOccupancyVoxels':int(fixed.sum()),'containment':'nativecap convexhull; exact shell separate; coarse only'},indent=2)+'\n')
# native orientation, front-wall flip, two side walls; horizontal four sign options.
rots=[('front',np.eye(3)),('frontFlip',np.diag([1,-1,-1])),('back',np.diag([-1,-1,1])),('sidePlus',np.array([[0,1,0],[1,0,0],[0,0,-1]])),('sideMinus',np.array([[0,1,0],[-1,0,0],[0,0,1]])),('roofDown',np.array([[0,-1,0],[0,0,-1],[1,0,0]])),('roofDownReverse',np.array([[0,1,0],[0,0,1],[1,0,0]])),('shelfUp',np.array([[0,1,0],[0,0,-1],[-1,0,0]])),('shelfUpReverse',np.array([[0,-1,0],[0,0,1],[-1,0,0]]))]
Told=np.array(json.loads(read(D/'positive-x225-pose.json'))['worldTransform']);parts=json.loads(read(O/'pi-geometry-manifest.json'))['parts'];center=np.array([68.11,-.0113773,131.0496]);results=[]
for name,rot in rots:
 T=np.eye(4);T[:3,:3]=rot;T[:3,3]=-rot@center;delta=T@np.linalg.inv(Told);bounds=[]
 for row in parts:
  s=load(H/row['mesh']).transform(delta[:3]);bounds.append(np.array(s.bounding_box()).reshape(2,3));del s
 ports=[mf.Manifold.cube([8,18,55]).translate([60.2,-.1,146.0496]).transform(T[:3]),mf.Manifold.cube([.6,4,16]).translate([65.5,32.4886208,123.0496]).transform(T[:3])]
 bounds += [np.array(s.bounding_box()).reshape(2,3) for s in ports]
 pmin=np.floor(np.min([b[0] for b in bounds],axis=0));pmax=np.ceil(np.max([b[1] for b in bounds],axis=0));pshape=tuple((pmax-pmin).astype(int)+1);occ=np.zeros(pshape,np.uint8)
 for row in parts:
  s=load(H/row['mesh']).transform(delta[:3]);occ|=raster(s,pmin,pshape);del s
 portocc=np.zeros(pshape,np.uint8)
 for port in ports:portocc|=raster(port,pmin,pshape)
 overlap=np.rint(fftconvolve(fixed.astype(np.float32),occ[::-1,::-1,::-1].astype(np.float32),mode='valid')+fftconvolve(hard.astype(np.float32),portocc[::-1,::-1,::-1].astype(np.float32),mode='valid')).astype(np.int32);ext=np.rint(fftconvolve(outside.astype(np.float32),occ[::-1,::-1,::-1].astype(np.float32),mode='valid')).astype(np.int32);score=overlap+ext*10;ordered=np.argsort(score,axis=None)[:3000];picks=[]
 for ix in ordered:
  xyz=np.array(np.unravel_index(ix,score.shape));c=lo+xyz-pmin
  if any(np.linalg.norm(c-np.array(q['centerWorldMm']))<4 for q in picks):continue
  tf=T.copy();tf[:3,3]+=c;picks.append({'centerWorldMm':c.tolist(),'overlapVoxels':int(overlap[tuple(xyz)]),'outsideVoxels':int(ext[tuple(xyz)]),'score':int(score[tuple(xyz)]),'worldTransform':tf.tolist()})
  if len(picks)>=8:break
 results.append({'orientation':name,'occupancyVoxels':int(occ.sum()),'best':picks});(dest/'screen-with-ports.json').write_text(json.dumps({'integrationReady':False,'screeningOnly':True,'portContract':'MicroB receiving8x18x25 plus30mmstraight insertion; CSI16x4x0.6; cap may get localservicehole, all otherbodyparts retained; outside containment applies PCB+population, notexternalport corridor','voxelPitchMm':1,'expectedOrientations':len(rots),'completedOrientations':len(results),'results':results,'sourceHashes':hashes},indent=2)+'\n');print(name,[(p['centerWorldMm'],p['overlapVoxels'],p['outsideVoxels']) for p in picks[:3]],flush=True);del occ,overlap,ext,score;gc.collect()
