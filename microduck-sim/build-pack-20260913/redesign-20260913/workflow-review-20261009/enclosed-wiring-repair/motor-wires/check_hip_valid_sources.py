exec(__import__('pathlib').Path('hip_core.py').read_text().split('top=json')[0])
NM=D.parent/'ankle-wires/native-motors/manifest.json';nm=json.loads(NM.read_text());native=[r for r in nm['parts']if r['motor']==2]
gp=D.parents[2]/'leg-guide-20261006/full-build-data.json';gd=json.loads(gp.read_text());parts={p['key']:{'sourceTransformWorld':p.get('sourceTransformWorld')} for p in gd['parts']};del gd;import gc;gc.collect()
top=json.loads((D/'active-topology.json').read_text());reports=[]
for side in ['right','left']:
 route=json.loads((D/f'hip-coiled-{side}.json').read_text());entities=[]
 for w in route['strands']:
  m=trimesh.load_mesh(w['file']);entities.append((f'wire{w["id"]}',m,solid(m),None))
 rr=next(x for x in top['routes']if x['id']==route['routeId'])
 for label,key in [('fromHousing',rr['fromPort']),('toHousing',rr['toPort'])]:
  p=top['ports'][key];bb=np.array(p['housingLocalBounds']);m=trimesh.creation.box(bb[1]-bb[0]);m.apply_translation(bb.mean(axis=0));m.apply_transform(np.array(p['transform']));f=D/f'hip-{side}-{label}.stl';m.export(f);entities.append((label,m,solid(m),p['motor']))
 checked=[];invalid=[];culled=[]
 for f in O.glob('*.json'):
  ob=json.loads(f.read_text());key=ob['key'];bb=np.array(ob['expectedFinalBoundsMm'])
  near=[e for e in entities if not(np.any(e[1].bounds[1]<bb[0])or np.any(bb[1]<e[1].bounds[0]))]
  if not near:culled.append(key);continue
  if key.startswith('motor') and key[5:].isdigit():
   mid=int(key[5:]);T=np.array(parts[key]['sourceTransformWorld']);
   def motor_meshes():
    for n in native:
     p=Path(n['file']);assert sha(p)==n['sha256'];m=trimesh.load_mesh(p);m.apply_transform(T@np.linalg.inv(n['worldTransform']));assert m.is_volume,(key,n['solid']);yield(f'{key}-solid{n["solid"]}',m,n['sha256'])
   meshes=motor_meshes()
  else:
   p=Path(ob['file']);assert sha(p)==ob['sha256'];m=trimesh.load_mesh(p);m.apply_translation(ob.get('importTranslationMm',[0,0,0]));meshes=[(key,m,ob['sha256'])]
  for label,m,hashval in meshes:
   if not m.is_volume:invalid.append({'key':label,'watertight':m.is_watertight,'winding':m.is_winding_consistent,'volume':m.volume});continue
   b=solid(m)
   for en,em,a,own in near:
    if own is not None and key==f'motor{own}':continue # own socket is a mating interface; box is not detailed latch geometry
    if np.any(em.bounds[1]<m.bounds[0])or np.any(m.bounds[1]<em.bounds[0]):continue
    cut=a^b;v=cut.volume();checked.append({'entity':en,'obstacle':label,'sourceSha256':hashval,'overlapMm3':v,'gapMmCappedAt1':a.min_gap(b,1.) if en.startswith('wire') else None,'bounds':list(cut.bounding_box())if v>1e-7 else None})
 out={'side':side,'routeId':route['routeId'],'inputSha256':sha(D/f'hip-coiled-{side}.json'),'strictSources':not invalid,'invalidSources':invalid,'wholeObstacleAabbSeparated':culled,'checked':checked,'passed':not invalid and all(r['overlapMm3']<1e-7 for r in checked)};reports.append(out);print(side,'invalid',invalid,'hits',[r for r in checked if r['overlapMm3']>1e-7],flush=True)
(D/'hip-valid-source-static.json').write_text(json.dumps({'passed':all(r['passed']for r in reports),'nativeSourceManifestSha256':sha(NM),'guideSha256':sha(gp),'scope':'All near original obstacles, closed manufacturer motor solids substituted for invalid aggregate motor meshes. Full mated receiving boxes checked against other parts; own socket mating geometry not certified by envelope.','routes':reports},indent=2))
