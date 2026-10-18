from pathlib import Path
import sys,json,hashlib,itertools
import numpy as np,trimesh,manifold3d as mf
from scipy.spatial import ConvexHull
D=Path(__file__).resolve().parent;sys.path.insert(0,str(D.parent));import conditional_u_route as c
H=c.H;C=c.C;G=c.G;cfgp=H/'viewer-candidate.json';cfg=json.loads(cfgp.read_text());assert not cfg['transforms']
files={k:C/(k+'-world.stl') for k in ['zero_w_components','zero_w_header_and_housing','zero_w_gpio_solder_tails','zero_w_usb_moulding']}
parts={'pi':c.dec('pi')}|{k:c.man(trimesh.load_mesh(p)) for k,p in files.items()};corekeys=[k for k in parts if k!='zero_w_usb_moulding'];center=np.array([68.11,-.0113773,131.0496]);B=np.array([[0,0,1],[1,0,0],[0,1,0]],float)
local=np.concatenate([(c.tri(parts[k]).vertices-center)@B for k in corekeys])
removed=set(cfg['removedParts'])|{'pi'};obs={k:c.dec(k) for k in c.P if k not in removed};sourcefiles=list(files.values())
for k,rel in cfg['replacementMeshes'].items():p=H/rel;obs[k]=c.man(trimesh.load_mesh(p));sourcefiles.append(p)
for a in cfg['additionalParts']:
 if a['key'] in ['zero_w_populated_receiving','pi_usb_receiving']:continue
 p=H/a['mesh'];obs[a['key']]=c.man(trimesh.load_mesh(p));sourcefiles.append(p)
# Convexhullisgenerousouterboundscreen; finalsolidchecksretainallshells.
outer=trimesh.util.concatenate([c.tri(obs[k]) for k in ['head_cap','head_bottom','face_panel']]);hull=ConvexHull(outer.vertices);A=hull.equations[:,:3];bb=hull.equations[:,3]
near={k:v for k,v in obs.items() if v.bounding_box()[5]>100};union=mf.Manifold.batch_boolean(list(near.values()),mf.OpType.Add)
rotations=[]
for ls,ws in itertools.product([-1,1],repeat=2):
 L=np.array([ls,0,0]);W=np.array([0,0,ws]);rotations.append(np.stack([L,W,np.cross(L,W)],axis=1))
xs=[-5,0,5,10,15,20,25,30,35,40,45];ys=[-32,-30,-29,-28,-26,-24,-22,22,24,26,28,29,30,32];zs=[119,122,125,128,131,134,137,140]
rows=[];outside=0;total=0;clear=[];best=[]
for ri,R in enumerate(rotations):
 support=np.max((local@R.T)@A.T,axis=0)
 for x,y,z in itertools.product(xs,ys,zs):
  total+=1;pos=np.array([x,y,z],float)
  if np.any(support+A@pos+bb>.01):outside+=1;continue
  T=np.eye(4);T[:3,:3]=R@B.T;T[:3,3]=pos-T[:3,:3]@center;moved={k:o.transform(T[:3]) for k,o in parts.items()};core=mf.Manifold.batch_boolean([moved[k] for k in corekeys],mf.OpType.Add);v=max(0,(core^union).volume())
  # Broadphaseunion fastreject; exactpairsretainclosestandclearposes.
  if v>100:best.append((v,ri,pos,T));best.sort(key=lambda a:a[0]);best=best[:5];continue
  hits={k:max(0,(core^o).volume()) for k,o in near.items()};hits={k:v for k,v in hits.items() if v>1e-5};usb={k:max(0,(moved['zero_w_usb_moulding']^o).volume()) for k,o in near.items()};usb={k:v for k,v in usb.items() if v>1e-5}
  mouth=T[:3,:3]@np.array([65.8,32.4886208,131.0496])+T[:3,3];cam=np.array([74.73,-.0913783,140.5766]);lb=float(np.linalg.norm(cam-mouth))+9.4
  row={'rotationIndex':ri,'centerWorldMm':pos.tolist(),'worldTransform':T.tolist(),'coreIntersectionUnionMm3':v,'coreCollisionsMm3':hits,'usbCollisionsMm3':usb,'coreClear':not bool(hits),'usbAlsoClear':not bool(usb),'piMouthWorldMm':mouth.tolist(),'straightCsiLowerBoundMm':lb};rows.append(row)
  if not hits:clear.append(row)
  best.append((v,ri,pos,T));best.sort(key=lambda a:a[0]);best=best[:5]
 print('rotation',ri,'total',total,'outside',outside,'clear',len(clear),flush=True)
for i,(_,ri,pos,T) in enumerate(best):
 m=mf.Manifold.batch_boolean([parts[k].transform(T[:3]) for k in corekeys],mf.OpType.Add);c.tri(m).export(D/f'candidate-{i+1}-core-world.stl')
# Completepairreadbackofbest5 eveniftheyfailedthe100mm3fastcutoff.
bestrows=[]
for v,ri,pos,T in best:
 m=mf.Manifold.batch_boolean([parts[k].transform(T[:3]) for k in corekeys],mf.OpType.Add);h={k:max(0,(m^o).volume()) for k,o in near.items()};bestrows.append({'rotationIndex':ri,'centerWorldMm':pos.tolist(),'worldTransform':T.tolist(),'coreIntersectionUnionMm3':v,'hitsMm3':{k:v for k,v in h.items() if v>1e-5}})
report={'date':'2026-10-08','status':'CLEAR_PLACEMENT_ONLY' if clear else 'NO_CLEAR_POSE_IN_FINITE_SIDEWALL_SCAN','assemblyAcceptance':False,'cameraRemainsOriginalUpward':True,'normalAxis':'worldY±','longAxis':'worldX±65mm','widthAxis':'worldZ±30mm','poseCount':total,'outsideGenerousHullCount':outside,'insideHullCount':total-outside,'clearCoreCount':len(clear),'clearCoreAndUsbCount':sum(a['usbAlsoClear'] for a in clear),'grid':{'X':xs,'Y':ys,'Z':zs},'coreParts':corekeys,'coreDimensionalBoundary':'40-pinmatehousing15mmreceivingdepth and2mmsoldertails arethecurrentreceivingenvelopes,notphysicalmeasurementcertificate.','clearPlacements':clear,'nearClearOrClear':rows,'best5':bestrows,'obstacleKeys':list(near),'mechanicalScope':'Placementonly; nomountsretentionornewserviceopeningdesigned. USB-onlyshellcrossingwouldneedactualopening,notnativecapstaticpass.','cableScope':'200mmownedSC1892; straightmouthlowerbound only, nofullroute/closureorstrainreliefacceptance.','sourceHashes':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [*sourcefiles,cfgp,G/'full-build-data.json',D/'probe.py']}}
(D/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:report[k] for k in ['status','poseCount','insideHullCount','clearCoreCount','clearCoreAndUsbCount','best5']},indent=2))
