exec(__import__('pathlib').Path('hip_core.py').read_text().split('top=json')[0])
top=json.loads((D/'active-topology.json').read_text());rows=[]
for side,rid in [('right','ttl-05-04'),('left','ttl-10-09')]:
 rr=next(r for r in top['routes']if r['id']==rid)
 for label,key in [('fromHousing',rr['fromPort']),('toHousing',rr['toPort'])]:
  port=top['ports'][key];m=trimesh.load_mesh(D/f'hip-{side}-{label}.stl');a=solid(m);v=np.array(port['outward']);end=m.bounds+v*15;bb=np.array([np.minimum(m.bounds[0],end[0]),np.maximum(m.bounds[1],end[1])]);checks=[]
  for f in O.glob('*.json'):
   ob=json.loads(f.read_text());obb=np.array(ob['expectedFinalBoundsMm'])
   if ob['key'].startswith('motor'):continue
   if np.any(bb[1]<obb[0])or np.any(obb[1]<bb[0]):continue
   p=Path(ob['file']);assert sha(p)==ob['sha256'];om=trimesh.load_mesh(p);om.apply_translation(ob.get('importTranslationMm',[0,0,0]));assert om.is_volume,ob['key'];b=solid(om)
   samples=[]
   for t in np.linspace(0,15,31):
    cut=a.translate(v*t)^b;vol=cut.volume()
    if vol>1e-7:samples.append({'withdrawalMm':float(t),'overlapMm3':vol,'bounds':list(cut.bounding_box())})
   checks.append({'key':ob['key'],'sourceSha256':ob['sha256'],'collisionSamples':samples})
  out={'route':rid,'port':key,'axis':v.tolist(),'housingFile':str(D/f'hip-{side}-{label}.stl'),'housingSha256':sha(D/f'hip-{side}-{label}.stl'),'checks':checks,'blockedBy':[x['key']for x in checks if x['collisionSamples']]};rows.append(out);print(key,out['blockedBy'],flush=True)
(D/'hip-plug-access.json').write_text(json.dumps({'scope':'0..15mm axial full-housing translation, .5mm samples, against every swept-AABB-near original printed/structural object. Motor socket mating and hand access not certified. Reports specific closure blockers to establish pre-insertion order; this is not full cable-group insertion certification.','topologySha256':sha(D/'active-topology.json'),'ports':rows},indent=2))
