from pathlib import Path
f=Path(__file__).parent/'check_spacer2_prefix_current.py';exec(compile(f.read_text().split("solid=load(O/")[0],str(f),'exec'));read(f)
solid=load(O/'spacer2-tilted-complete-ribbon-outside-world.stl');keys=sorted((set(n['P'])|set(files))-removed-{'zero_w_components'});r={'accepted':False,'componentRefinementPending':True,'scope':'Frozen outsidebody s5..195.6; terminal engagement excluded, physicalconnectorhandling not claimed','expectedObstacles':len(keys),'completedObstacles':0,'checks':[],'sourceHashes':n['hashes']}
for key in keys:
 if key=='openrb':
  em=json.loads(read(H/'usb-access/usb-repair/openrb-component-enclosures/manifest.json'));bb=np.array(solid.bounding_box()).reshape(2,3);gap=2.;v=0;complete=0
  for z in em['components']:
   zb=np.array(z['bounds']);lower=float(np.linalg.norm(np.maximum(np.maximum(bb[0]-zb[1],zb[0]-bb[1]),0)))
   if lower>=2:complete+=1;continue
   ob=load(Path(z['mesh']));gap=min(gap,float(solid.min_gap(ob,2)));v+=n['volume'](solid,ob)[0];complete+=1;del ob;gc.collect()
  row={'obstacle':key,'overlapMm3':v,'gapCapped2Mm':gap,'expectedComponents':len(em['components']),'completedComponents':complete}
 else:
  ob=load(H/files[key]) if key in files else n['source'](key)
  if key in shiftKeys:ob=ob.translate(delta)
  v,bb=n['volume'](solid,ob);gap=float(solid.min_gap(ob,2));row={'obstacle':key,'overlapMm3':v,'gapCapped2Mm':gap};del ob;gc.collect()
 r['checks'].append(row);r['completedObstacles']+=1;(O/'frozen-ribbon-clearance.json').write_text(json.dumps(r,indent=2)+'\n')
 if gap<.5:print(key,gap,v,flush=True)
print('complete',len(keys),flush=True)
