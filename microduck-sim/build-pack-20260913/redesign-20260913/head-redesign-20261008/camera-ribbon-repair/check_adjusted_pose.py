"""One saved pose, one obstacle at a time. Run only via run_bounded_cad.py."""
from pathlib import Path
import os,json,base64,gc,hashlib,math,sys
assert os.environ.get('MICRODUCK_BOUNDED_CAD')=='1','Use bounded CAD launcher'
import numpy as np,trimesh,manifold3d as mf
D=Path(__file__).resolve().parent;H=D.parent;G=H.parent/'leg-guide-20261006';hashes={}
def read(p):
 b=p.read_bytes();hashes[str(p.resolve())]=hashlib.sha256(b).hexdigest();return b
C=D/'head-source-cache';cache=json.loads(read(C/'index.json'));P=cache['parts'];hashes[cache['sourceFile']]=cache['sourceDataSha256'];cfg=json.loads(read(H/'viewer-candidate.json'));files=cfg['replacementMeshes']|{p['key']:p['mesh'] for p in cfg['additionalParts']}
def man(m):return mf.Manifold(mf.Mesh(np.asarray(m.vertices,np.float32),np.asarray(m.faces,np.uint32)))
def mesh(s):
 q=s.to_mesh();return trimesh.Trimesh(q.vert_properties[:,:3],q.tri_verts,process=True)
def loadfile(p):return man(trimesh.load(p,force='mesh'))
def source(k):
 if k in files:
  p=H/files[k];read(p);return loadfile(p)
 p=json.loads(read(C/P[k]));return man(trimesh.Trimesh(np.frombuffer(base64.b64decode(p['positionB64']),'<f4').reshape(-1,3),np.frombuffer(base64.b64decode(p['indexB64']),'<u4').reshape(-1,3),process=True))
def volume(a,b):
 aa=np.array(a.bounding_box()).reshape(2,3);bb=np.array(b.bounding_box()).reshape(2,3)
 if np.any(aa[0]>=bb[1]) or np.any(bb[0]>=aa[1]):return 0.,None
 q=a^b;v=max(0,float(q.volume()));return v,list(q.bounding_box()) if v>1e-7 else None
resume=json.loads(read(D/'RESUME-STATE.json'));v=list(resume['lastInterruptedCandidate']['x']);v[1]-=2;v[2]-=1;rx,ry,rz=np.deg2rad(v[3:]);cx,sx=math.cos(rx),math.sin(rx);cy,sy=math.cos(ry),math.sin(ry);cz,sz=math.cos(rz),math.sin(rz)
rot=np.array([[cz,-sz,0],[sz,cz,0],[0,0,1.]])@np.array([[cy,0,sy],[0,1,0],[-sy,0,cy]])@np.array([[1,0,0],[0,cx,-sx],[0,sx,cx]])
center=np.array([68.11,-.0113773,131.0496]);T=np.eye(4);T[:3,:3]=rot;T[:3,3]=center+v[:3]-rot@center
parts={'pi':source('pi')}
for k in ['zero_w_components','zero_w_gpio_solder_tails']:
 p=H/'curved-head'/(k+'-world.stl');read(p);parts[k]=loadfile(p)
p=H/'gpio-audio-repair/gpio-discrete12-18mm-world.stl';read(p);parts['gpio_discrete12_receiving']=loadfile(p)
mouth=np.array([65.8,32.4886208,131.0496]);parts['csi_free_straight_receiving']=mf.Manifold.cube([.6,4,16],True).translate(mouth+[0,2,0])
parts={k:s.transform(T[:3]) for k,s in parts.items()};skip=set(cfg['removedParts'])|{'pi','zero_w_populated_receiving','pi_usb_receiving'}
report={'status':'ONE_SAVED_POSE_IN_PROGRESS','accepted':False,'worldTransform':T.tolist(),'eulerConvention':'Rz@Ry@Rx, degrees, about originalPi center, then translation','parameters':v,'piCenterWorldMm':(center+v[:3]).tolist(),'csiMouthWorldMm':(rot@mouth+T[:3,3]).tolist(),'csiOutwardAxis':(rot@[0,1,0]).tolist(),'csiWidthAxis':(rot@[0,0,1]).tolist(),'usbShoulderWorldMm':(rot@np.array([64.2,8.9,146.0496])+T[:3,3]).tolist(),'usbOutwardAxis':(rot@[0,0,1]).tolist(),'remainingPairs':[],'checks':[],'sourceHashes':hashes,'receivingBoundary':'18mm discrete12 female receiver; unusedmale8.5mm. CSIfree4mm straight x16width x0.6thickness is explicit design bound, not manufacturer stiffener measurement; no full200mm acceptance.'}
def save():
 report['sourceHashes']=hashes;(D/'adjusted-pose-pair-checks.json').write_text(json.dumps(report,indent=2)+'\n')
dest=D/'adjusted-pose-pair-checks.json'
if dest.exists():
 old=json.loads(dest.read_text());assert old['worldTransform']==report['worldTransform'];report['checks']=old['checks'];report['remainingPairs']=old['remainingPairs'];hashes.update(old['sourceHashes'])
save()
for k in [sys.argv[1]]:
 if k in skip:continue
 o=source(k)
 for name,s in parts.items():
  vol,bb=volume(s,o);row={'moving':name,'fixed':k,'overlapMm3':vol,'intersectionBoundsMm':bb};report['checks'].append(row)
  if vol>1e-5:report['remainingPairs'].append(row)
 save();del o;gc.collect()
for k,s in (parts.items() if '--export' in sys.argv else []):
 file=D/(k+'-adjusted-pose-world.stl');mesh(s).export(file);read(file)
report['status']='SINGLE_OBSTACLE_DONE_NOT_ASSEMBLY_RELEASE';report['checkedObstacles']=len(report['checks'])//len(parts);save();print(sys.argv[1], 'complete', flush=True)
