from pathlib import Path
import json,hashlib,sys,gc
import numpy as np,trimesh,manifold3d as mf
D=Path(__file__).resolve().parent;N=D.parent;W=N.parents[1]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
manifest=W/'original-body-converter/fusion-import-manifest.json'
j=json.loads(manifest.read_text());
for p in j['parts']:assert sha(p['file'])==p['sha256'],p['key']
routes=json.loads((D/'head-trunk.json').read_text());obs={p['key']:p for p in j['parts']}
obs['imu_clamp']={'file':str(N/'imu-clamp-retained-world.stl'),'importTranslationMm':[0,0,0]}
obs['imu_cover']={'file':str(N/'imu-cover-retained-world.stl'),'importTranslationMm':[0,0,0]}
obs['imu_board']={'file':str(N/'bno085-valid-native-world.stl'),'importTranslationMm':[0,0,0]}
for part in json.loads((D/'distribution-feeds.json').read_text())['parts']:obs[part['key']]={'file':part['file'],'importTranslationMm':[0,0,0]}
for net in ['gnd','3v3','sda','scl']:obs['imu_wire_'+net]={'file':str(N/('imu_'+net+'-body-world.stl')),'importTranslationMm':[0,0,0]}
mixed=W/'enclosed-wiring-repair/motor-wires/slack-packaging/mixed-leg-manifest.json'
for part in json.loads((D/'zone-feeds.json').read_text())['parts']:obs[part['key']]={'file':part['file'],'importTranslationMm':[0,0,0]}
for part in json.loads(mixed.read_text())['parts']+json.loads(mixed.read_text())['retentionContexts']:obs['frozen_'+part['key']]={'file':part['file'],'importTranslationMm':[0,0,0],'expectedFinalBoundsMm':part['expectedFinalBoundsMm']}
rows=[];readback=[];hashes={str(manifest):sha(manifest),str(D/'head-trunk.json'):sha(D/'head-trunk.json'),str(Path(__file__)):sha(Path(__file__))}
selected=[r for r in routes['parts'] if r['key']==sys.argv[1]];assert len(selected)==1
for r in selected:
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
    if False:
     proof=json.loads((D/'zone-feed-own-motors.json').read_text());assert proof['passed'] and proof['complete'];assert proof['sourceHashes'][str(D/'head-trunk.json')]==sha(D/'head-trunk.json')
     if key==('motor5' if 'left' in r['key'] else 'motor10'):rec['status']='CONVEX_FALSE_POSITIVE_RESOLVED_BY_INDEPENDENT_MANUFACTURER_COMPONENTS';rec['componentReceipt']=str(D/'zone-feed-own-motors.json');rec['componentReceiptSha256']=sha(D/'zone-feed-own-motors.json')
    if rec['status']=='INTERSECTION' and (key=='distribution_'+('5v' if r['net']=='5V' else 'gnd')+'_insulated' or (key.startswith('zone_') and key.endswith('_'+('5v' if r['net']=='5V' else 'gnd')))):
     envelope=trimesh.load(D/('distribution_'+('5v' if r['net']=='5V' else 'gnd')+'-receiving-world.stl'),force='mesh');outside=trimesh.boolean.difference([c,envelope],engine='manifold');rec['intersectionOutsideOwnSpliceMm3']=float(outside.volume) if len(outside.faces) else 0
     if rec['intersectionOutsideOwnSpliceMm3']<=1e-7:rec['status']='NAMED_SAME_NET_SOLDER_JOIN_INSIDE_OWN_INSULATED_SPLICE';rec['scope']='Only same-net merging material inside the explicitly registered insulated solder junction; no opposite-net exemption.'
    if r['key'].startswith('distribution_') and key in ['power_support','shell_left','shell_right','regulator_insert'] and not len(c.faces):
     ma=mf.Manifold(mf.Mesh(np.asarray(a.vertices,dtype=np.float32),np.asarray(a.faces,dtype=np.uint32)));mb=mf.Manifold(mf.Mesh(np.asarray(mesh.vertices,dtype=np.float32),np.asarray(mesh.faces,dtype=np.uint32)))
     assert ma.status()==mb.status()==mf.Error.NoError
     rec['minimumMeshGapWithin1mm']=float(ma.min_gap(mb,1.0));rec['gapClippedAt1mm']=rec['minimumMeshGapWithin1mm']>=1.0
   del mesh
   gc.collect()
  rows.append(rec)
 # wire-wire pairs are distinct conductors, no blanket own-harness exemption.
 for q in routes['parts']:
  if q['key']<=r['key']:continue
  b=trimesh.load(q['file'],force='mesh');assert b.is_volume;c=trimesh.boolean.intersection([a,b],engine='manifold');assert not len(c.faces) or c.is_volume
  rec={'route':r['key'],'obstacle':q['key'],'status':'CLEAR' if not len(c.faces) else 'INTERSECTION','volumeMm3':0 if not len(c.faces) else float(c.volume),'boundsMm':None if not len(c.faces) else c.bounds.tolist()}
  if False:
   # Two material sections of the SAME continuous wire deliberately share this one end plane.
   main=r if r['key'].endswith('_pad_connected') else q
   axis=np.array(main['splitAxis'])
   error=float(np.max(np.abs((c.vertices-np.array(main['splitPlane']))@axis)))
   rec['jointPlaneMaximumErrorMm']=error
   if error<=1e-4 and float(c.volume)<=1e-6:rec['status']='SAME_CONDUCTOR_JOIN_PLANE';rec['scope']='Only the named bare-to-insulated section end plane, not a distinct-wire collision exemption'
  rows.append(rec)
 (D/('head-trunk-check-'+sys.argv[1]+'.json')).write_text(json.dumps({'complete':False,'rows':rows},indent=2))
fail=[r for r in rows if r['status'] not in ['CLEAR','BOUNDS_SEPARATE','SAME_CONDUCTOR_JOIN_PLANE','CONVEX_FALSE_POSITIVE_RESOLVED_BY_INDEPENDENT_MANUFACTURER_COMPONENTS','NAMED_SAME_NET_SOLDER_JOIN_INSIDE_OWN_INSULATED_SPLICE']]
hashes[str(mixed)]=sha(mixed)
out={'scope':'Four zone feed conductors: registered motor5/10 incoming contacts to distribution solder joints, neutral pose only; eight frozen leg cables included; no moving-joint or full head acceptance','complete':len(rows)==len(obs)+sum(q['key']>selected[0]['key'] for q in routes['parts']),'expectedPairs':len(obs)+sum(q['key']>selected[0]['key'] for q in routes['parts']),'expectedObstacleKeys':list(obs),'readback':readback,'rows':rows,'failures':fail,'sourceHashes':hashes,'passedStatic':not fail,'physicalFitVerified':False}
(D/('head-trunk-check-'+sys.argv[1]+'.json')).write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({'pairs':len(rows),'failures':fail}))
