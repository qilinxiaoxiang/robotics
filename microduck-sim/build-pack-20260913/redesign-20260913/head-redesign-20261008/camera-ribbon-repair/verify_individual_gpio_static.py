from pathlib import Path
import os,json,gc
assert os.environ.get('MICRODUCK_BOUNDED_CAD')=='1'
D=Path(__file__).resolve().parent;H=D.parent;p=D/'check_saved_pose.py';n={'__file__':str(p)};exec(p.read_text().split('resume=')[0],n);np=n['np'];mf=n['mf'];tm=n['trimesh'];read=n['read'];read(Path(__file__))
def load(p,broad=False):
 read(p);m=tm.load(p,force='mesh')
 if broad and all(np.any(np.array(g.bounding_box()).reshape(2,3)[0]>=m.bounds[1]) or np.any(m.bounds[0]>=np.array(g.bounding_box()).reshape(2,3)[1]) for g in parts.values()):return None
 assert m.is_watertight,str(p);s=mf.Manifold(mf.Mesh64(np.array(m.vertices,np.float64),np.array(m.faces,np.uint64)));assert s.status()==mf.Error.NoError;return s
m=json.loads(read(D/'local-candidate-manifest.json'));gpio=json.loads(read(D/'gpio-individual-receiving-manifest.json'));parts={q['key']:load(H/q['mesh']) for q in gpio['additionalParts']};files=m['replacementMeshes']|{q['key']:q['mesh'] for q in m['additionalParts']};files['amplifier']='gpio-audio-repair/amp16z2-placement-world.stl'
keys=sorted(set(n['P'])|set(n['files'])|set(files));skip=set(m['removedParts'])|set(parts)|{'pi','zero_w_components','zero_w_gpio_solder_tails','csi_free_straight_receiving'}
keys=[k for k in keys if k not in skip];rows=[];r={'acceptedStaticOnly':False,'wholeAssemblyAccepted':False,'expectedObstacles':len(keys),'expectedPairs':len(keys)*13,'completedPairs':0,'checks':rows,'sourceHashes':n['hashes']}
for key in keys:
 s=load(H/files[key],True) if key in files else n['source'](key)
 if s is None:
  rows.append({'obstacle':key,'method':'Exact vertex AABB separation from all13 receiving solids; no mesh Boolean required','hits':[]});r['completedPairs']+=13;continue
 assert s.status()==mf.Error.NoError and s.volume()>0,key
 hits=[]
 for k,g in parts.items():
  v,bb=n['volume'](g,s);r['completedPairs']+=1
  if v>1e-5:hits.append({'gpio':k,'volumeMm3':v,'boundsMm':bb})
 rows.append({'obstacle':key,'hits':hits});r['sourceHashes']=n['hashes'];(D/'gpio-individual-static-verification.json').write_text(json.dumps(r,indent=2)+'\n');del s;gc.collect()
r['acceptedStaticOnly']=r['completedPairs']==r['expectedPairs'] and not any(q['hits'] for q in rows);(D/'gpio-individual-static-verification.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({'passed':r['acceptedStaticOnly'],'completed':r['completedPairs'],'expected':r['expectedPairs'],'failures':[q for q in rows if q['hits']]},indent=2))
