"""Finite sensitivity and one early camera bend; never certifies an entire cable."""
from pathlib import Path
import os,json,math,gc,ast,hashlib
assert os.environ.get('MICRODUCK_BOUNDED_CAD')=='1'
D=Path(__file__).resolve().parent;H=D.parent;O=D/'positive-x225';Q=D/'fixed-pose-local-bend';Q.mkdir(exist_ok=True)
exec((D/'build_reverse_nut_camera.py').read_text().split('cam=load')[0]);O=Q
trimesh=tm
import developable_ribbon_inner_entry as dr
read(Path(__file__));read(D/'developable_ribbon_inner_entry.py')
m=json.loads(read(D/'positive-x225/candidate-manifest.json'));pose=json.loads(read(D/'positive-x225-pose.json'));dr.T=np.array(pose['worldTransform']);dr.mouth=np.array(pose['csiMouthWorldMm']);dr.initial=(dr.mouth-4.4*dr.T[:3,1],dr.T[:3,1],dr.T[:3,2]);dr.cam=np.array([75.63,9.3706236,131.1145958]);dr.target=dr.cam-[0,5,0]
x=np.array(json.loads(read(D/'positive-x225/fixed-u80-search.json'))['best']['parameters'])
src=read(D/'optimize_x225_u80.py').decode();node=next(a for a in ast.parse(src).body if isinstance(a,ast.FunctionDef) and a.name=='construct');code=ast.unparse(node).replace('np.linspace(-8, 8, width_step + 1)','np.linspace(-WIDTH/2, WIDTH/2, width_step + 1)').replace('0.3 * norms','THICKNESS/2 * norms');exec(code)
def prefix(width,thickness):
 # Mouth→4mm free straight→90deg R3 toward -X→4mm inward. No insertion-depth subtraction.
 mouth=np.array([75.63,9.3706236,131.1145958]);R=3;L=8+math.pi*R/2;ss=np.unique(np.r_[np.linspace(0,L,160),4,4+math.pi*R/2]);vv=np.linspace(-width/2,width/2,17);cs=[];ns=[]
 for s in ss:
  if s<=4:q=mouth+[0,s,0];normal=np.array([1.,0,0])
  elif s<=4+math.pi*R/2:
   a=(s-4)/R;q=mouth+[-R*(1-math.cos(a)),4+R*math.sin(a),0];normal=np.array([math.cos(a),math.sin(a),0])
  else:q=mouth+[-R-(s-4-math.pi*R/2),4+R,0];normal=np.array([0.,1,0])
  for v in vv:cs.append(q+[0,0,v]);ns.append(normal)
 cs=np.array(cs);ns=np.array(ns);N=len(cs);nv=len(vv);faces=[]
 for i in range(len(ss)-1):
  for j in range(nv-1):
   a=i*nv+j;b=a+1;c=b+nv;d=a+nv;faces.extend([[a,c,b],[a,d,c],[a+N,b+N,c+N],[a+N,c+N,d+N]])
 for i in range(len(ss)-1):
  for j in [0,nv-1]:a=i*nv+j;b=a+nv;faces.extend([[a,b,b+N],[a,b+N,a+N]])
 for i in [0,len(ss)-1]:
  for j in range(nv-1):a=i*nv+j;b=a+1;faces.extend([[a,b,b+N],[a,b+N,a+N]])
 mesh=tm.Trimesh(np.r_[cs-thickness/2*ns,cs+thickness/2*ns],faces,process=True);tm.repair.fix_normals(mesh);assert mesh.is_watertight
 s=mf.Manifold(mf.Mesh64(mesh.vertices.astype(np.float64),mesh.faces.astype(np.uint64)));assert s.status()==mf.Error.NoError;return s
base=json.loads(read(H/'viewer-candidate.json'));files=(base['replacementMeshes']|{p['key']:p['mesh'] for p in base['additionalParts']})|(m['replacementMeshes']|{p['key']:p['mesh'] for p in m['additionalParts']});removed=set(base['removedParts'])|set(m['removedParts']);files['amplifier']='gpio-audio-repair/amp16z2-closed-receiving-world.stl';files['head_cap']='gpio-audio-repair/speaker-rewire/cap-audio-speaker-restraint-print-candidate-world.stl'
keys=sorted((set(n['P'])|set(files))-removed);targets=['head_cap','pi','E-pi-04_revision_screw','amplifier','face_panel','camera_retainer']
r={'accepted':False,'integrationReady':False,'purpose':'Fixed geometry; distinguish old full200 U failures from width/thickness assumptions, then test single early camera bend. No whole200 solution implied.','thicknessBoundary':'0.6 is receiving assumption;0.2 sensitivity only, not measured SC1892 thickness.','widthBoundary':'16 Rev1 body and conservative Rev2 bound;11.5 Rev2 midbody only. The16-wide camera termination must still be retained.','earlyBend':{'freeStraightMm':4,'centerlineRadiusMm':3,'freePrefixLengthMm':8+math.pi*3/2,'mouthMm':[75.63,9.3706236,131.1145958],'endMm':[68.63,16.3706236,131.1145958],'manufacturingPartChanges':0,'unresolved':'Complete200 material closure, width transition/stiffeners, installation/closing and actual cable bend suitability'},'cases':[],'sourceHashes':n['hashes']}
def save():(Q/'report.json').write_text(json.dumps(r,indent=2)+'\n')
for WIDTH,THICKNESS in [(16,.6),(16,.2),(11.5,.6),(11.5,.2)]:
 row={'widthMm':WIDTH,'thicknessMm':THICKNESS,'full200Checks':[],'earlyBendChecks':[]};r['cases'].append(row);full=construct(4.4,200,.35,x,16);local=prefix(WIDTH,THICKNESS)
 for key in keys:
  if key=='openrb':
   em=json.loads(read(H/'usb-access/usb-repair/openrb-component-enclosures/manifest.json'));bb=np.array(local.bounding_box()).reshape(2,3);mins=[]
   for e in em['components']:
    obb=np.array(e['bounds']);mins.append(float(np.linalg.norm(np.maximum(np.maximum(bb[0]-obb[1],obb[0]-bb[1]),0))))
   assert min(mins)>0;row['earlyBendChecks'].append({'obstacle':key,'overlapMm3':0,'gapLowerBoundMm':min(mins),'method':'all142conservativecomponent bounds separation'});continue
  ob=load(H/files[key]) if key in files else n['source'](key)
  assert ob.status()==mf.Error.NoError and ob.volume()>0,key
  v,b=n['volume'](local,ob);row['earlyBendChecks'].append({'obstacle':key,'overlapMm3':v,'boundsMm':b,'minimumGapCapped2Mm':float(local.min_gap(ob,2))})
  if key in targets:
   v,b=n['volume'](full,ob);row['full200Checks'].append({'obstacle':key,'overlapMm3':v,'boundsMm':b})
  del ob;gc.collect();save()
 row['expectedEarlyBendObstacles']=len(keys);row['completedEarlyBendObstacles']=len(row['earlyBendChecks']);row['expectedFull200DiagnosticObstacles']=len(targets);row['completedFull200DiagnosticObstacles']=len(row['full200Checks']);row['prefixMesh']=export(local,f'early-camera-bend-w{WIDTH}-t{THICKNESS}');del full,local;gc.collect();save();print(WIDTH,THICKNESS,[q for q in row['earlyBendChecks'] if q['overlapMm3']>1e-5],flush=True)
r['sourceHashes']=n['hashes'];save()
