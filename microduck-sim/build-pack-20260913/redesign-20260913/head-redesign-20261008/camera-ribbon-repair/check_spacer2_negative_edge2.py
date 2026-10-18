"""Full200 Rev2 candidate, exactdevelopable map withadaptive sampling, singleobstacle streaming."""
from pathlib import Path
import os,json,math,gc
assert os.environ.get('MICRODUCK_BOUNDED_CAD')=='1'
D=Path(__file__).resolve().parent;H=D.parent
exec((D/'build_reverse_nut_camera.py').read_text().split('cam=load')[0]);O=D/'fixed-pose-local-bend';read(Path(__file__))
import fit_spacer2_negative_edge2 as route
read(D/'fit_spacer2_negative_edge2.py');fit=json.loads(read(O/'spacer2-negative-edge2-fit.json'));x=np.array(fit['parameters']);p,t,w,L,bends,pr=route.family(x);assert abs(L-200)<.001 and max(abs(route.residual(x)))<.001
m=json.loads(read(D/'positive-x225/candidate-manifest.json'));base=json.loads(read(H/'viewer-candidate.json'));files=(base['replacementMeshes']|{q['key']:q['mesh'] for q in base['additionalParts']})|(m['replacementMeshes']|{q['key']:q['mesh'] for q in m['additionalParts']});files['head_cap']='gpio-audio-repair/speaker-rewire/cap-audio-speaker-restraint-print-candidate-world.stl';files['amplifier']='gpio-audio-repair/amp16z2-closed-receiving-world.stl';removed=set(base['removedParts'])|set(m['removedParts']);ps=json.loads(read(O/'pi-spacer2-parts.json'))
for row in ps['rows']:files[row['id']+'_revision_screw']=row['screwMesh'];files[row['id']+'_spacer2']=row['spacerMesh']
shiftKeys=set(q['key'] for q in json.loads(read(D/'positive-x225/pi-geometry-manifest.json'))['parts']);T=np.array(json.loads(read(D/'positive-x225-pose.json'))['worldTransform']);delta=-2*T[:3,0]
def at(s,v):
 for b in bends:
  ds=s-b['s0'];phi=b['phi'];ac=ds*math.sin(phi)+v*math.cos(phi);bc=ds*math.cos(phi)-v*math.sin(phi);R=b['R']
  if bc<0:return b['p']+b['t']*ds+b['w']*v,b['n']
  if bc<=R*b['angle']:
   a=bc/R;return b['p']+b['e']*ac+b['q']*R*math.sin(a)+b['n']*(b['sign']*R*(1-math.cos(a))),b['n']*math.cos(a)-b['q']*(b['sign']*math.sin(a))
 return p+t*(s-L)+w*v,np.cross(t,w)
def width(s):return 16. if s<=35 else 16-(s-35)*.9 if s<40 else 11.5
def build(s0,s1):
 vals=[s0,s1,*np.arange(s0,s1,1),35,40]
 for b in bends:
  edge=8*abs(math.tan(b['phi']));lo=max(s0,b['s0']-edge);hi=min(s1,b['s1']+edge)
  if hi>lo:vals.extend(np.linspace(lo,hi,math.ceil((hi-lo)/.1)+1))
 ss=sorted(set(float(z) for z in vals if s0<=z<=s1));vv=np.linspace(-.5,.5,17);coords=[];norms=[]
 for s in ss:
  for v in vv:
   q,nn=at(s,v*width(s));coords.append(q);norms.append(nn)
 coords=np.array(coords);norms=np.array(norms);N=len(coords);nv=len(vv);faces=[]
 for i in range(len(ss)-1):
  for j in range(nv-1):
   a=i*nv+j;b=a+1;c=b+nv;d=a+nv;faces.extend([[a,c,b],[a,d,c],[a+N,b+N,c+N],[a+N,c+N,d+N]])
 for i in range(len(ss)-1):
  for j in [0,nv-1]:a=i*nv+j;b=a+nv;faces.extend([[a,b,b+N],[a,b+N,a+N]])
 for i in [0,len(ss)-1]:
  for j in range(nv-1):a=i*nv+j;b=a+1;faces.extend([[a,b,b+N],[a,b+N,a+N]])
 mesh=tm.Trimesh(np.r_[coords-.15*norms,coords+.15*norms],faces,process=True);tm.repair.fix_normals(mesh);assert mesh.is_watertight
 solid=mf.Manifold(mf.Mesh64(mesh.vertices.astype(np.float64),mesh.faces.astype(np.uint64)));assert solid.status()==mf.Error.NoError;return solid
overlay=json.loads(read(H/'current-closure/restored-source-overlay.json'));files.update(overlay['replacementMeshes']);files.update({z['key']:z['mesh'] for z in overlay['additionalParts']});removed.update(overlay['removedParts'])
keys=sorted((set(n['P'])|set(files))-removed);r={'integrationReady':False,'accepted':False,'materialLengthMm':L,'endpointResidualMm':float(np.linalg.norm(p-route.target)),'bendRadiiMm':[z['R'] for z in bends],'bodyWidthMm':11.5,'standardEndReceiving':{'widthMm':16,'fromCameraTipLengthMm':35,'taperReceivingMm':5,'boundary':'Conservative fullwidth terminal length; notofficialdimension. Photo identifiesnarrowmajorityRev2.'},'thicknessReceivingMm':.3,'staticScope':'Outsideassumed connector engagement only, material s5..195.6; fullmaterialmesh separate.','expectedObstacles':len(keys),'completedObstacles':0,'checks':[],'sourceHashes':n['hashes'],'remaining':['selfcheck','connectorengagement/latch','assemblysequenceandclosure','physicalbendacceptance']}
def save():(O/'spacer2-negative-edge2-static.json').write_text(json.dumps(r,indent=2)+'\n')
solid=build(5,L-4.4);r['outsideMesh']=export(solid,'spacer2-negative-edge2-ribbon-outside');save()
for key in keys:
 if key=='openrb':
  em=json.loads(read(H/'usb-access/usb-repair/openrb-component-enclosures/manifest.json'));bb=np.array(solid.bounding_box()).reshape(2,3);rows=[]
  for z in em['components']:
   obb=np.array(z['bounds']);gap=float(np.linalg.norm(np.maximum(np.maximum(bb[0]-obb[1],obb[0]-bb[1]),0)))
   if gap>0:rows.append({'component':z['index'],'overlapMm3':0,'gapLowerBoundMm':gap});continue
   ob=load(Path(z['mesh']));v,b=n['volume'](solid,ob);rows.append({'component':z['index'],'overlapMm3':v,'boundsMm':b});del ob;gc.collect()
  row={'obstacle':key,'components':rows,'overlapMm3':sum(z['overlapMm3'] for z in rows)}
 else:
  ob=load(H/files[key]) if key in files else n['source'](key)
  if key in shiftKeys:ob=ob.translate(delta)
  v,b=n['volume'](solid,ob);row={'obstacle':key,'overlapMm3':v,'boundsMm':b};del ob;gc.collect()
 r['checks'].append(row);r['completedObstacles']+=1;save()
 if row['overlapMm3']>1e-5:print(key,row['overlapMm3'],flush=True)
del solid;gc.collect();full=build(0,L);r['fullMesh']=export(full,'spacer2-negative-edge2-ribbon');save();print('complete',r['completedObstacles'],flush=True)
