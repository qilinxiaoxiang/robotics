from pathlib import Path
D=Path(__file__).resolve().parent
exec((D/'build_reverse_nut_camera.py').read_text().split('cam=load')[0]);read(Path(__file__))
import sys
name=sys.argv[1];idx=int(sys.argv[2]);screen=json.loads(read(D/'occupancy-layout/screen-with-ports.json'));candidate=next(r for r in screen['results'] if r['orientation']==name)['best'][idx];T=np.array(candidate['worldTransform']);T[0,3]-=.75;candidate['worldTransform']=T.tolist();candidate['centerWorldMm'][0]-=.75;Told=np.array(json.loads(read(D/'positive-x225-pose.json'))['worldTransform']);delta=T@np.linalg.inv(Told);pieces=json.loads(read(O/'pi-geometry-manifest.json'))['parts'];moving={r['key']:load(H/r['mesh']).transform(delta[:3]) for r in pieces};O=D/'occupancy-layout'/'back-dual-U';O.mkdir(exist_ok=True);checks=[];rows=[]
moving['USB_body']=mf.Manifold.cube([8,18,25]).translate([60.2,-.1,146.0496]).transform(T[:3]);moving['USB_insertion_corridor']=mf.Manifold.cube([8,18,55]).translate([60.2,-.1,146.0496]).transform(T[:3]);moving['CSI_free4']=mf.Manifold.cube([.6,4,16]).translate([65.5,32.4886208,123.0496]).transform(T[:3])
for k,s in moving.items():rows.append({'key':k,'mesh':export(s,k),'boundsMm':list(s.bounding_box())})
obstacles=[('native_cap',H/'curved-head/community-curved-head-world.stl'),('camera',D/'positive-x225/camera_board_clamped-world.stl'),('amp',H/'gpio-audio-repair/amp16z2-closed-receiving-world.stl')]
for k in ['motor13','motor14','motor15','jaw_support','jaw_frame','head_yaw_link','head_roll_ring_a','head_roll_ring_b','speaker','head_bottom','upper_pad','lower_pad']:
 if k in n['P'] or k in n['files']:obstacles.append((k,None))
rb=json.loads(read(H/'usb-access/usb-repair/openrb-component-enclosures/manifest.json'));obstacles += [('OpenRB_'+str(r['index']),Path(r['mesh'])) for r in rb['components']]
def save():
 r={'integrationReady':False,'stage':'coarse rigid candidate only','candidate':candidate,'parts':rows,'expectedPairs':len(obstacles)*len(moving),'completedPairs':len(checks),'checks':checks,'sourceHashes':n['hashes']};(O/'report.json').write_text(json.dumps(r,indent=2)+'\n')
for key,p in obstacles:
 fixed=load(p) if p else n['source'](key)
 for k,s in moving.items():
  v,bb=n['volume'](s,fixed);checks.append({'part':k,'obstacle':key,'overlapMm3':v,'boundsMm':bb,'gapCapped2':float(s.min_gap(fixed,2)),'futureServiceOpeningRequired': bool(key=='native_cap' and k.startswith('USB'))})
 del fixed;save();gc.collect()
print(json.dumps({'candidate':candidate,'hits':[r for r in checks if r['overlapMm3']>1e-5]},indent=2))
