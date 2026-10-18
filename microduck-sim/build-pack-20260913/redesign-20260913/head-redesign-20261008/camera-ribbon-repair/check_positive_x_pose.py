from pathlib import Path
import os,json,sys,gc
assert os.environ.get('MICRODUCK_BOUNDED_CAD')=='1'
D=Path(__file__).resolve().parent;H=D.parent;p=D/'check_saved_pose.py';n={'__file__':str(p)};exec(p.read_text().split('resume=')[0],n);np=n['np'];mf=n['mf'];tm=n['trimesh'];read=n['read'];read(Path(__file__));dx=float(sys.argv[1]);assert dx in [1.5,2]
m=json.loads(read(D/'local-candidate-manifest.json'));files=m['replacementMeshes']|{q['key']:q['mesh'] for q in m['additionalParts']}
def load(p):
 read(p);q=tm.load(p,force='mesh');assert q.is_watertight,str(p);s=mf.Manifold(mf.Mesh64(np.array(q.vertices,np.float64),np.array(q.faces,np.uint64)));assert s.status()==mf.Error.NoError and s.volume()>0;return s
moving=['pi','zero_w_components','zero_w_gpio_solder_tails']+[q['key'] for q in json.loads(read(D/'gpio-individual-receiving-manifest.json'))['additionalParts']];parts={k:load(H/files[k]).translate([dx,0,0]) for k in moving}
fixed=['native_cap','head_cap','curved_cap_hardware','bare_face_without_pi_mounts','face_panel','camera_board','camera_retainer','eye_trim','head_bottom','upper_pad','jaw_support','motor15']+[q['key'] for q in m['additionalParts'] if q['key'].endswith('_revision_screw') and not q['key'].startswith('E-pi')]
rows=[];report={'integrationReady':False,'deltaFromLoweredMm':[dx,0,0],'sourceManifestSha256':__import__('hashlib').sha256((D/'local-candidate-manifest.json').read_bytes()).hexdigest(),'expectedPairs':len(fixed)*len(parts),'completedPairs':0,'checks':rows,'scope':'Boundary diagnostic only. Native face and existing Pi mounts reported separately; all printed Pi mounts andUSB shoulder would require regeneration if adopted.','sourceHashes':n['hashes']}
for k in fixed:
 if k=='native_cap':s=load(H/'curved-head/community-curved-head-world.stl')
 elif k=='bare_face_without_pi_mounts':
  script=D/'build_face_mounts124.py';read(script);nn={'__file__':str(script)};exec(script.read_text().split('hardware=[]')[0],nn);s=nn['face'];n['hashes'].update(nn['n']['hashes']);del nn
 elif k in files:s=load(H/files[k])
 else:s=n['source'](k)
 assert s.status()==mf.Error.NoError and s.volume()>0,k
 hits=[]
 for name,q in parts.items():
  v,bb=n['volume'](q,s);report['completedPairs']+=1
  if v>1e-5:hits.append({'part':name,'volumeMm3':v,'boundsMm':bb})
 rows.append({'obstacle':k,'hits':hits});report['sourceHashes']=n['hashes'];(D/f'positive-x-{dx:g}-boundary.json').write_text(json.dumps(report,indent=2)+'\n');print(k,sum(q['volumeMm3'] for q in hits),flush=True);del s;gc.collect()
print('complete',report['completedPairs'])
