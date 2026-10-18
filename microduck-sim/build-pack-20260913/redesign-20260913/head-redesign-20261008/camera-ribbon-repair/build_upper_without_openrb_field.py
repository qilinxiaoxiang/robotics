from pathlib import Path
import ast
D=Path(__file__).resolve().parent
exec((D/'build_reverse_nut_camera.py').read_text().split('cam=load')[0]);read(Path(__file__))
from matplotlib.path import Path as MPath
from scipy.ndimage import distance_transform_edt
src=D/'coarse_voxel_full_ports_batch.py';read(src);node=next(a for a in ast.parse(src.read_text()).body if isinstance(a,ast.FunctionDef) and a.name=='raster');exec(ast.unparse(node))
lo=np.array([-35.,-48.,75.]);shape=(131,97,131);fixed=np.zeros(shape,np.uint8);ablation=[];cache=np.load(D/'occupancy-layout/fixed-full-ports-1mm.npz');outside=cache['outside'];del cache
old=D/'positive-x225';items=[('cap',H/'curved-head/community-curved-head-world.stl'),('current_audio_cap',H/'gpio-audio-repair/speaker-rewire/cap-audio-speaker-restraint-print-candidate-world.stl'),('face',old/'face_x225_complete-world.stl'),('eye',old/'eye_three_screw_camera-world.stl'),('bottom',old/'head_bottom_x225_receiver-world.stl'),('amp',H/'gpio-audio-repair/amp16z2-closed-receiving-world.stl'),('amp_hardware',H/'gpio-audio-repair/cap-amp16z2/hardware-current-amp-world.stl'),('camera',D/'camera-quarter-rolls/90/camera-world.stl')]
for k in ['motor13','motor14','motor15','jaw_support','jaw_frame','head_yaw_link','head_roll_ring_a','head_roll_ring_b','speaker','upper_pad','lower_pad']:
 if k in n['P'] or k in n['files']:items.append((k,None))
r=json.loads(read(old/'pi-geometry-manifest.json'));items.extend((q['key'],H/q['mesh']) for q in r['parts']);items.extend(('PiScrew'+str(i),old/('E-pi-0'+str(i)+'_x225-world.stl')) for i in [1,2,4])
# Diagnostic removal of OpenRB entire 142-component board. No external USB harness was in this internal field.
postrows=json.loads(read(H/'curved-head/mounts-and-paths.json'))['posts'];native=load(H/'curved-head/community-curved-head-world.stl');postcut=mf.Manifold()
for q in postrows:
 c=np.array(q['pcbHoleCenterWorldMm']);a=np.array(q['axisWorld']);B=tm.geometry.align_vectors([0,0,1],a);B[:3,3]=c-a*3;postcut+=mf.Manifold.cylinder(q['postLengthMm']+6,3.2,circular_segments=48).transform(B[:3])
for pin in [12,20,35,40]:items.append(('i2s'+str(pin),H/'gpio-audio-repair/gpio-fanout/x225/actual4397'/('i2s-pin'+str(pin)+'-world.stl')))
rows=[]
for key,path in items:
 if path is not None and not path.exists():raise RuntimeError('Missing exact obstacle '+str(path))
 s=load(path) if path else n['source'](key)
 if key=='current_audio_cap':
  before=float(s.volume());removed=(s-native)^postcut;s-=removed;ablation.append({'key':key,'removedInternalPostMaterialMm3':float(removed.volume()),'removedNativeShellMm3':float((removed^native).volume())})
 if key=='amp_hardware':
  keep=[];removed=[]
  for component in s.decompose():
   b=np.array(component.bounding_box()).reshape(2,3);v=(b[0]+b[1])/2;matches=[]
   for q in postrows:
    c=np.array(q['pcbHoleCenterWorldMm']);a=np.array(q['axisWorld']);d=v-c;along=float(d@a);rad=float(np.linalg.norm(d-along*a))
    if rad<3.2 and -3<along<q['postLengthMm']+3:matches.append(q['screw'])
   (removed if matches else keep).append(component)
  ablation.append({'key':key,'removedHardwareComponents':len(removed),'retainedHardwareComponents':len(keep),'removedHardwareMm3':sum(float(c.volume()) for c in removed)});s=mf.Manifold.batch_boolean(keep,mf.OpType.Add)
 if key=='camera':s-=mf.Manifold.cube([.8,16.2,5.2],True).translate([75.63,-.0913766914184464,138.07659913253173])
 occ=raster(s,lo,shape);fixed|=occ;rows.append({'key':key,'mesh':str(path.resolve()) if path else 'source:'+key,'voxelCount':int(occ.sum())});del s,occ;gc.collect()
blocked=fixed.astype(bool)|outside.astype(bool);sdf=(distance_transform_edt(~blocked)-distance_transform_edt(blocked)).astype(np.float32);out=D/'camera-quarter-rolls/90/without-openrb-fixed-field.npz';np.savez_compressed(out,sdf=sdf);(out.with_suffix('.json')).write_text(json.dumps({'ablation':ablation,'scope':'OpenRB out of head diagnostic only; no new board installation or electrical release','screeningOnly':True,'integrationReady':False,'lo':lo.tolist(),'pitch':1,'expectedObstacles':len(items),'completedObstacles':len(rows),'obstacles':rows,'sourceHashes':n['hashes'],'exclusions':['retired old camera and clamp/three old clamp screws; replacements not yet designed','external USB harness above head not in this internal routing field; exact final inspection still required'],'connectorModel':'camera only receiving mating slot carved, .1mm bounded extra per dimension for 1mm occupancy; exact verifier retains .6x16x5 intended contact only'},indent=2)+'\n');print(len(rows),flush=True)
