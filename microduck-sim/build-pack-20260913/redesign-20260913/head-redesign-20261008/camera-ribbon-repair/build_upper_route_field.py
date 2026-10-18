from pathlib import Path
import ast
D=Path(__file__).resolve().parent
exec((D/'build_reverse_nut_camera.py').read_text().split('cam=load')[0]);read(Path(__file__))
from matplotlib.path import Path as MPath
from scipy.ndimage import distance_transform_edt
src=D/'coarse_voxel_full_ports_batch.py';read(src);node=next(a for a in ast.parse(src.read_text()).body if isinstance(a,ast.FunctionDef) and a.name=='raster');exec(ast.unparse(node))
lo=np.array([-35.,-48.,75.]);shape=(131,97,131);fixed=np.zeros(shape,np.uint8);cache=np.load(D/'occupancy-layout/fixed-full-ports-1mm.npz');outside=cache['outside'];del cache
old=D/'positive-x225';items=[('cap',H/'curved-head/community-curved-head-world.stl'),('current_audio_cap',H/'gpio-audio-repair/speaker-rewire/cap-audio-speaker-restraint-print-candidate-world.stl'),('face',old/'face_x225_complete-world.stl'),('eye',old/'eye_three_screw_camera-world.stl'),('bottom',old/'head_bottom_x225_receiver-world.stl'),('amp',H/'gpio-audio-repair/amp16z2-closed-receiving-world.stl'),('amp_hardware',H/'gpio-audio-repair/cap-amp16z2/hardware-current-amp-world.stl'),('camera',D/'camera-quarter-rolls/90/camera-world.stl')]
for k in ['motor13','motor14','motor15','jaw_support','jaw_frame','head_yaw_link','head_roll_ring_a','head_roll_ring_b','speaker','upper_pad','lower_pad']:
 if k in n['P'] or k in n['files']:items.append((k,None))
r=json.loads(read(old/'pi-geometry-manifest.json'));items.extend((q['key'],H/q['mesh']) for q in r['parts']);items.extend(('PiScrew'+str(i),old/('E-pi-0'+str(i)+'_x225-world.stl')) for i in [1,2,4])
r=json.loads(read(H/'usb-access/usb-repair/openrb-component-enclosures/manifest.json'));items.extend(('OpenRB'+str(q['index']),Path(q['mesh'])) for q in r['components'])
for pin in [12,20,35,40]:items.append(('i2s'+str(pin),H/'gpio-audio-repair/gpio-fanout/x225/actual4397'/('i2s-pin'+str(pin)+'-world.stl')))
rows=[]
for key,path in items:
 if path is not None and not path.exists():raise RuntimeError('Missing exact obstacle '+str(path))
 s=load(path) if path else n['source'](key)
 if key=='camera':s-=mf.Manifold.cube([.8,16.2,5.2],True).translate([75.63,-.0913766914184464,138.07659913253173])
 occ=raster(s,lo,shape);fixed|=occ;rows.append({'key':key,'mesh':str(path.resolve()) if path else 'source:'+key,'voxelCount':int(occ.sum())});del s,occ;gc.collect()
blocked=fixed.astype(bool)|outside.astype(bool);sdf=(distance_transform_edt(~blocked)-distance_transform_edt(blocked)).astype(np.float32);out=D/'camera-quarter-rolls/90/actual-fixed-field.npz';np.savez_compressed(out,sdf=sdf);(out.with_suffix('.json')).write_text(json.dumps({'screeningOnly':True,'integrationReady':False,'lo':lo.tolist(),'pitch':1,'expectedObstacles':len(items),'completedObstacles':len(rows),'obstacles':rows,'sourceHashes':n['hashes'],'exclusions':['retired old camera and clamp/three old clamp screws; replacements not yet designed','external USB harness above head not in this internal routing field; exact final inspection still required'],'connectorModel':'camera only receiving mating slot carved, .1mm bounded extra per dimension for 1mm occupancy; exact verifier retains .6x16x5 intended contact only'},indent=2)+'\n');print(len(rows),flush=True)
