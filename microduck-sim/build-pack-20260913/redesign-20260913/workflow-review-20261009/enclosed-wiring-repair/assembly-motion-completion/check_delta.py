"""Small station checks: retained screw heads and specified tool handles.
No flexible cable motion is inferred. One operation per process.
"""
import argparse,base64,hashlib,importlib.util,json,sys
from pathlib import Path
D=Path(__file__).resolve().parent;R=D.parents[2];G=R/'leg-guide-20261006'
sys.path.insert(0,str(G))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def data():
 import bundle_guide
 base=json.loads((G/'full-build-data.json').read_text());rp=R/'fastener-review-20261008/fastener-patch-proposal.json'
 effective=bundle_guide.apply_fastener_revision(base,json.loads(rp.read_text()),rp)
 service=json.loads((G/'non-head-review/torso-service-steps.json').read_text())
 bundle_guide.validate_torso_service(base,service,G/'non-head-review/torso-service-steps.json')
 return base,effective,service

def inventory():
 base,effective,service=data();parts={p['key']:p for p in effective['parts']};screws={s['id']:s for s in effective['screws']}
 modules=[service['module'] if m['id']=='torso' else m for m in effective['modules'] if m['id'] in ['left-leg','right-leg','torso','power','imu','neck']]
 plan=json.loads((D/'candidate-plan.json').read_text()) if (D/'candidate-plan.json').exists() else {}
 for mod in modules:
  if mod['id'] in plan.get('moduleOrders',{}):
   byid={o['id']:o for o in mod['operations']};mod['operations']=[byid[k] for k in plan['moduleOrders'][mod['id']]]
  for op in mod['operations']:op.update(plan.get('operationPatches',{}).get(op['id'],{}))
 seen=set();installed=set();out=[]
 for mod in modules:
  leg='leg' in mod['id'];local=set()
  for op in mod['operations']:
   seen.update(op['add']);local.update(op['add']);present=(local if leg else seen)
   scene=set(op.get('visiblePartKeys',op.get('isolatedPartKeys',present)))
   if 'isolatedPartKeys' in op:scene &= set(op['isolatedPartKeys'])
   moving=list(op.get('moveKeys',[]));active=op.get('screwIds',[])
   prior=[s for s in sorted(installed) if screws[s]['partKey'] in scene]
   carry=[s for s in prior if screws[s]['partKey'] in moving]
   out.append({'moduleId':mod['id'],'operation':op,'scene':sorted(scene),'priorScrewIds':prior,'movingScrewIds':carry,'fixedParts':sorted(scene-set(moving))})
   if op.get('screwAction')=='remove':installed.difference_update(active)
   else:installed.update(active)
 return effective,out

def run(opid,kind):
 import numpy as np,trimesh,manifold3d as mf
 packet=json.loads((D/'station-inputs'/f'{opid}.json').read_text());row=packet['station'];op=row['operation'];parts={p['key']:p for p in packet['parts']};screws={s['id']:s for s in packet['screws']};cache={};bounds={k:np.array(p['bounds'],float) for k,p in parts.items()}
 def solid(k):
  if k not in cache:
   p=parts[k];v=np.frombuffer(base64.b64decode(p['positionB64']),'<f4').reshape(-1,3);f=np.frombuffer(base64.b64decode(p['indexB64']),'<u4').reshape(-1,3)
   m=trimesh.Trimesh(v,f,process=True);a=mf.Manifold(mf.Mesh(np.array(m.vertices,dtype=np.float32),np.array(m.faces,dtype=np.uint32)))
   assert a.status()==mf.Error.NoError and a.volume()>0,(k,a.status());cache[k]=a;bounds[k]=np.array(a.bounding_box()).reshape(2,3)
  return cache[k]
 def cyl(o,a,start,end,r):
  a=np.array(a,float);a/=np.linalg.norm(a);T=trimesh.geometry.align_vectors([0,0,1],a);T[:3,3]=np.array(o)+a*(start+end)/2
  # Circumscribed polygon encloses the intended circular tool/head.
  m=trimesh.creation.cylinder(radius=r/np.cos(np.pi/48),height=end-start,sections=48).apply_transform(T)
  return mf.Manifold(mf.Mesh(np.array(m.vertices,np.float32),np.array(m.faces,np.uint32)))
 def head(s):return cyl(s['world_center_mm'],s['world_axis'],s.get('washer_mm',0),s.get('washer_mm',0)+1.5,2.5)
 def intersect(a,k):
  ab=np.array(a.bounding_box()).reshape(2,3);bb=bounds[k]
  if np.any(ab[1]<bb[0]) or np.any(bb[1]<ab[0]):return 0.
  return max(0,float((a^solid(k)).volume()))
 rows=[];hits=[]
 if kind=='tool':
  for sid in op['screwIds']:
   s=screws[sid];a=np.array(s['world_axis']);o=np.array(s['world_center_mm']);w=s.get('washer_mm',0)
   model=op.get('toolAccessModels',{}).get(sid);bent=sid.startswith('S14-horn-') or bool(model)
   # Existing 18 mm right-angle bit/side handle is retained; a 45 mm straight driver is not substituted into the fork.
   handle=cyl(o+a*17,model['handleAxis'] if model else [0,-1,0],0,model.get('handleLengthMm',50) if model else 50,3) if bent else cyl(o,a,w+45.5,w+105.5,9)
   shaft=cyl(o,a,w+2,w+(18 if bent else 45.5),1.5)
   contacts=[{'part':k,'volumeMm3':v} for k in row['scene'] if (v:=intersect(handle,k))>1e-5]
   hardware=[]
   for other in list(dict.fromkeys(row['priorScrewIds']+op['screwIds'][:op['screwIds'].index(sid)])):
    if other==sid:continue
    v=max(0,float(((shaft+handle)^head(screws[other])).volume()))
    if v>1e-5:hardware.append({'screw':other,'volumeMm3':v})
   rr={'screw':sid,'tool':'right-angle Ø3 bit/Ø6 side handle' if bent else 'Ø3 shaft45/Ø18×60 handle','handlePartIntersections':contacts,'priorHeadIntersections':hardware,'receivingModel':model or {'straightShaftLengthMm':45,'handleDiameterMm':18,'handleLengthMm':60}};rows.append(rr)
   if contacts or hardware:hits.append(rr)
 elif kind=='carry':
  vec=np.array(op['approachVector'],float);n=int(np.ceil(np.linalg.norm(vec)/.25))+1
  for sid in row['movingScrewIds']:
   h=head(screws[sid]);rr={'screw':sid,'samples':n,'intersections':[]}
   for k in row['fixedParts']:
    vals=[intersect(h.translate(vec*t),k) for t in np.linspace(1,0,n)]
    if max(vals)>1e-5:rr['intersections'].append({'part':k,'maxMm3':max(vals),'finalMm3':vals[-1],'samplesPositive':sum(v>1e-5 for v in vals)})
   rows.append(rr)
   if rr['intersections']:hits.append(rr)
  # Added physical foot is carried with the ankle, not left at its destination.
  for key in op.get('addedMotionDeltaKeys',[]):
   body=solid(key);rr={'part':key,'samples':n,'intersections':[]}
   for k in row['fixedParts']:
    vals=[intersect(body.translate(vec*t),k) for t in np.linspace(1,0,n)]
    if max(vals)>1e-5:rr['intersections'].append({'part':k,'maxMm3':max(vals),'finalMm3':vals[-1]})
   rows.append(rr)
   if rr['intersections']:hits.append(rr)
 else:raise ValueError(kind)
 out={'operationId':opid,'kind':kind,'passed':not hits,'sourceDataSha256':sha(G/'full-build-data.json'),'currentStockAdapterSha256':sha(G/'current_stock_fasteners.py'),'scriptSha256':sha(Path(__file__)),'scene':row['scene'],'movingScrewIds':row['movingScrewIds'],'priorScrewIds':row['priorScrewIds'],'rows':rows,'failures':hits,'scope':'New rigid head-envelope and stated handle delta only. Actual tool availability, grip/torque and flexible cable dressing are not certified.'}
 (D/f'{opid}-{kind}.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({'operation':opid,'kind':kind,'passed':not hits,'rows':len(rows),'failures':hits}))
 return not hits
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--operation');ap.add_argument('--kind',choices=['tool','carry']);ap.add_argument('--inventory',action='store_true');args=ap.parse_args()
 if args.inventory:
  effective,rows=inventory();(D/'station-inventory.json').write_text(json.dumps(rows,indent=2)+'\n');(D/'station-inputs').mkdir(exist_ok=True)
  for row in rows:
   keys=set(row['scene']);ids=set(row['priorScrewIds']+row['operation']['screwIds']);packet={'station':row,'parts':[p for p in effective['parts'] if p['key'] in keys],'screws':[s for s in effective['screws'] if s['id'] in ids]}
   (D/'station-inputs'/f"{row['operation']['id']}.json").write_text(json.dumps(packet,separators=(',',':'))+'\n')
  print(len(rows))
 else:sys.exit(0 if run(args.operation,args.kind) else 1)
