from pathlib import Path
f=Path(__file__).parent/'check_spacer2_full_ribbon.py';exec(compile(f.read_text().split('keys=sorted(')[0],str(f),'exec'))
import hashlib
overlay=json.loads(read(H/'current-closure/restored-source-overlay.json'))
for rel,sha in overlay['sourceHashes'].items():assert hashlib.sha256(read(H/rel)).hexdigest()==sha
files.update(overlay['replacementMeshes']);files.update({z['key']:z['mesh'] for z in overlay['additionalParts']});removed.update(overlay['removedParts'])
solid=load(O/'spacer2-R1-return46.0-w16-world.stl');keys=sorted((set(n['P'])|set(files))-removed);r={'accepted':False,'localPrefixClear':False,'scope':'Only53.0716mm outsidecamera prefix, whole16mmwidth/.3receiver/R1, currentrestoredmouth; remaining200mm connection notaccepted','expectedObstacles':len(keys),'completedObstacles':0,'checks':[],'sourceHashes':n['hashes']}
for key in keys:
 if key=='openrb':
  em=json.loads(read(H/'usb-access/usb-repair/openrb-component-enclosures/manifest.json'));bb=np.array(solid.bounding_box()).reshape(2,3);rows=[]
  for z in em['components']:
   obb=np.array(z['bounds']);gap=float(np.linalg.norm(np.maximum(np.maximum(bb[0]-obb[1],obb[0]-bb[1]),0)))
   if gap>0:rows.append({'component':z['index'],'overlapMm3':0,'gapLowerBoundMm':gap});continue
   ob=load(Path(z['mesh']));v,b=n['volume'](solid,ob);rows.append({'component':z['index'],'overlapMm3':v,'boundsMm':b});del ob
  row={'obstacle':key,'components':rows,'overlapMm3':sum(z['overlapMm3'] for z in rows)}
 else:
  ob=load(H/files[key]) if key in files else n['source'](key)
  if key in shiftKeys:ob=ob.translate(delta)
  v,b=n['volume'](solid,ob);row={'obstacle':key,'overlapMm3':v,'boundsMm':b};del ob
 r['checks'].append(row);r['completedObstacles']+=1;gc.collect()
 if row['overlapMm3']>1e-6:print(key,row['overlapMm3'])
r['localPrefixClear']=r['completedObstacles']==r['expectedObstacles'] and not any(z['overlapMm3']>1e-6 for z in r['checks']);(O/'spacer2-prefix-current-static.json').write_text(json.dumps(r,indent=2)+'\n');print('local',r['localPrefixClear'],len(keys))
