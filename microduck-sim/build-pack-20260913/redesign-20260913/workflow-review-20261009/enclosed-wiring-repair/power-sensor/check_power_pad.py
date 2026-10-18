from pathlib import Path
import json,hashlib
import numpy as np,trimesh,manifold3d as mf
D=Path(__file__).resolve().parent;W=D.parents[1]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
manifest=W/'original-body-converter/fusion-import-manifest.json'
j=json.loads(manifest.read_text());
for p in j['parts']:assert sha(p['file'])==p['sha256'],p['key']
routes=json.loads((D/'power-pad-routes.json').read_text());obs={p['key']:p for p in j['parts']}
obs['imu_clamp']={'file':str(D/'imu-clamp-retained-world.stl'),'importTranslationMm':[0,0,0]}
obs['imu_cover']={'file':str(D/'imu-cover-retained-world.stl'),'importTranslationMm':[0,0,0]}
obs['imu_board']={'file':str(D/'bno085-valid-native-world.stl'),'importTranslationMm':[0,0,0]}
rows=[];readback=[];hashes={str(manifest):sha(manifest),str(D/'power-pad-routes.json'):sha(D/'power-pad-routes.json'),str(Path(__file__)):sha(Path(__file__))}
for r in routes['parts']:
 a=trimesh.load(r['file'],force='mesh');assert a.is_volume
 readback.append({'key':r['key'],'validSolid':True,'boundsMm':a.bounds.tolist(),'volumeMm3':float(a.volume)})
 for key,p in obs.items():
  b=p.get('expectedFinalBoundsMm');rec={'route':r['key'],'obstacle':key}
  if b is not None and (np.any(a.bounds[1]<np.array(b)[0]) or np.any(np.array(b)[1]<a.bounds[0])):rec['status']='BOUNDS_SEPARATE'
  else:
   mesh=trimesh.load(p['file'],force='mesh');mesh.apply_translation(p.get('importTranslationMm',[0,0,0]));hashes[p['file']]=sha(p['file'])
   if np.any(a.bounds[1]<mesh.bounds[0]) or np.any(mesh.bounds[1]<a.bounds[0]):rec['status']='BOUNDS_SEPARATE'
   else:
    if not mesh.is_volume:
     raw=mesh;mesh=raw.convex_hull;assert mesh.is_volume
     # A valid enclosing convex body can prove clearance, never prove collision against holes.
     rec['inputRepair']='Conservative convex enclosure of every source vertex; no source geometry removed'
     rec['sourceWatertight']=bool(raw.is_watertight)
    c=trimesh.boolean.intersection([a,mesh],engine='manifold');assert len(c.faces)==0 or c.is_volume
    rec.update(status='CLEAR' if len(c.faces)==0 else 'INTERSECTION',volumeMm3=0 if len(c.faces)==0 else float(c.volume),boundsMm=None if len(c.faces)==0 else c.bounds.tolist())
    if r['key'].startswith('power_') and key in ['power_support','shell_left','shell_right','regulator_insert'] and not len(c.faces):
     ma=mf.Manifold(mf.Mesh(np.asarray(a.vertices,dtype=np.float32),np.asarray(a.faces,dtype=np.uint32)));mb=mf.Manifold(mf.Mesh(np.asarray(mesh.vertices,dtype=np.float32),np.asarray(mesh.faces,dtype=np.uint32)))
     assert ma.status()==mb.status()==mf.Error.NoError
     rec['minimumMeshGapWithin1mm']=float(ma.min_gap(mb,1.0));rec['gapClippedAt1mm']=rec['minimumMeshGapWithin1mm']>=1.0
   del mesh
  rows.append(rec)
 # wire-wire pairs are distinct conductors, no blanket own-harness exemption.
 for q in routes['parts']:
  if q['key']<=r['key']:continue
  b=trimesh.load(q['file'],force='mesh');assert b.is_volume;c=trimesh.boolean.intersection([a,b],engine='manifold');assert not len(c.faces) or c.is_volume
  rec={'route':r['key'],'obstacle':q['key'],'status':'CLEAR' if not len(c.faces) else 'INTERSECTION','volumeMm3':0 if not len(c.faces) else float(c.volume)}
  if len(c.faces) and r['net']==q['net'] and set([r['key'].endswith('_pad_lead'),q['key'].endswith('_pad_lead')])=={True,False}:
   # Two material sections of the SAME continuous wire deliberately share this one end plane.
   main=r if r['key'].endswith('_pad_connected') else q
   section=main['routeSections'][0];axis=np.array(section['end'])-np.array(section['start']);axis/=np.linalg.norm(axis)
   error=float(np.max(np.abs((c.vertices-np.array(main['pathSplitWorldMm']))@axis)))
   rec['jointPlaneMaximumErrorMm']=error
   if error<=1e-4 and float(c.volume)<=1e-6:rec['status']='SAME_CONDUCTOR_JOIN_PLANE';rec['scope']='Only the named bare-to-insulated section end plane, not a distinct-wire collision exemption'
  rows.append(rec)
 (D/'power-pad-check.json').write_text(json.dumps({'complete':False,'rows':rows},indent=2))
fail=[r for r in rows if r['status'] not in ['CLEAR','BOUNDS_SEPARATE','SAME_CONDUCTOR_JOIN_PLANE']]
out={'scope':'Static body-side segment only; no head endpoint, service-loop, wire length or whole-harness acceptance','complete':len(rows)==len(routes['parts'])*len(obs)+len(routes['parts'])*(len(routes['parts'])-1)//2,'expectedPairs':len(routes['parts'])*len(obs)+len(routes['parts'])*(len(routes['parts'])-1)//2,'expectedObstacleKeys':list(obs),'readback':readback,'rows':rows,'failures':fail,'sourceHashes':hashes,'passedStatic':not fail,'physicalFitVerified':False}
(D/'power-pad-check.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({'pairs':len(rows),'failures':fail}))
