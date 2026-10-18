"""One side-wall Pi + opposite OpenRB + center-roof amp coarse architecture."""
from pathlib import Path
D=Path(__file__).resolve().parent
exec((D/'build_reverse_nut_camera.py').read_text().split('cam=load')[0]);read(Path(__file__));m=json.loads(read(O/'pi-geometry-manifest.json'));Told=np.array(json.loads(read(D/'positive-x225-pose.json'))['worldTransform']);rot=np.array([[0,1,0],[1,0,0],[0,0,-1]]);T=np.eye(4);T[:3,:3]=rot;T[:3,3]=np.array([36.,26.,126.])-rot@np.array([68.11,-.0113773,131.0496]);delta=T@np.linalg.inv(Told);O=D/'side-layout';O.mkdir(exist_ok=True);parts=[]
for row in m['parts']:
 q=load(H/row['mesh']).transform(delta[:3]);parts.append({'key':row['key'],'mesh':export(q,row['key']),'boundsMm':list(q.bounding_box())})
amp=load(H/'gpio-audio-repair/amp16z2-closed-receiving-world.stl').translate([-19,23.2,1]);parts.append({'key':'amp_proposed','mesh':export(amp,'amp_proposed'),'boundsMm':list(amp.bounding_box())});del amp
checks=[];observed=[];keys=['native_cap','motor13','motor14','motor15','jaw_support','jaw_frame','head_yaw_link','head_roll_ring_a','head_roll_ring_b','speaker','head_bottom','upper_pad','lower_pad']
for key in keys:
 if key=='native_cap':obs=load(H/'curved-head/community-curved-head-world.stl')
 elif key not in n['P'] and key not in n['files']:continue
 else:obs=n['source'](key)
 observed.append(key)
 for row in parts:
  q=load(H/row['mesh']);v,bb=n['volume'](q,obs);checks.append({'part':row['key'],'obstacle':key,'overlapMm3':v,'boundsMm':bb});del q
 del obs;gc.collect()
# Actual every OpenRB component, moved as one body. Never repair source thin triangles.
rbT=np.array([[1,0,0,10],[0,0,1,-161.7646],[0,-1,0,127],[0,0,0,1.]])
cfg=json.loads(read(H/'usb-access/usb-repair/openrb-component-enclosures/manifest.json'));rbrows=[];agg={}
for row in cfg['components']:
 q=load(Path(row['mesh'])).transform(rbT[:3]);bb=list(q.bounding_box());rbrows.append({'index':row['index'],'boundsMm':bb})
 for key in observed:
  if key=='native_cap':obs=load(H/'curved-head/community-curved-head-world.stl')
  else:obs=n['source'](key)
  v,b=n['volume'](q,obs);entry=agg.setdefault('OpenRB/'+key,{'part':'OpenRB','obstacle':key,'overlapMm3':0,'componentHits':[]});entry['overlapMm3']+=v
  if v>1e-5:entry['componentHits'].append({'index':row['index'],'volume':v,'bounds':b})
  del obs
 for p in parts:
  obs=load(H/p['mesh']);v,b=n['volume'](q,obs);entry=agg.setdefault('OpenRB/'+p['key'],{'part':'OpenRB','obstacle':p['key'],'overlapMm3':0,'componentHits':[]});entry['overlapMm3']+=v
  if v>1e-5:entry['componentHits'].append({'index':row['index'],'volume':v,'bounds':b})
  del obs
 del q;gc.collect()
checks+=list(agg.values())
amp=load(H/parts[-1]['mesh'])
for row in parts[:-1]:
 q=load(H/row['mesh']);v,bb=n['volume'](q,amp);checks.append({'part':row['key'],'obstacle':'amp_proposed','overlapMm3':v,'boundsMm':bb})
r={'integrationReady':False,'worldTransform':T.tolist(),'OpenRbTransform':rbT.tolist(),'ampTranslation':[-19,23.2,1],'parts':parts,'checks':checks,'OpenRbComponentsCompleted':len(rbrows),'sourceHashes':n['hashes'],'FFCChecked':False,'dynamicChecked':False,'externalConnectorsChecked':False};(O/'coarse-report.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({'PiT':T.tolist(),'rbT':rbT.tolist(),'hits':[r for r in checks if r['overlapMm3']>1e-5]},indent=2))
