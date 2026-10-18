exec(__import__('pathlib').Path('hip_core.py').read_text().split('top=json')[0])
rows=[]
for side in [-1,1]:
 a=mf.Manifold.cylinder(27,5.3,5.3,64).translate([-14.8,side*17.,-31]);q=a.to_mesh64();m=trimesh.Trimesh(q.vert_properties,q.tri_verts);checks=[]
 for p in O.glob('*.json'):
  ob=json.loads(p.read_text());bb=np.array(ob['expectedFinalBoundsMm'])
  if np.any(m.bounds[1]<bb[0])or np.any(bb[1]<m.bounds[0]):continue
  mm=trimesh.load_mesh(ob['file']);mm.apply_translation(ob.get('importTranslationMm',[0,0,0]));cut=a^solid(mm);v=cut.volume();checks.append({'key':ob['key'],'overlapMm3':v,'bounds':list(cut.bounding_box()) if v>1e-7 else None})
 rows.append({'side':side,'checks':checks});print(side,checks)
(D/'hip-coil-cavity.json').write_text(json.dumps(rows,indent=2))
