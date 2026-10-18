from pathlib import Path
D=Path(__file__).resolve().parent
exec((D/'pack_populated_boards.py').read_text().split('pikeys=')[0])
import argparse
ap=argparse.ArgumentParser();ap.add_argument('--pose',default='native-lanes-pose.json');ap.add_argument('--output',default='pi-in-lanes-piecewise.json');ap.add_argument('--include-microb',action='store_true');ap.add_argument('--cap');args=ap.parse_args()
posefile=D/args.pose;pose=json.loads(posefile.read_text());hashes[str(posefile)]=sha(posefile);Tp=np.array(pose['piCurrentWorldDelta'])
pifile=H/'camera-ribbon-repair/fixed-pose-local-bend/pi-spacer2-pose.json';piT=np.array(json.loads(pifile.read_text())['worldTransform']);hashes[str(pifile)]=sha(pifile)
keys=[k for k in rows if k=='pi' or k.startswith(('zero_w_','gpio_pin_','component_'))]
fixedkeys=['head_cap','jaw_support','jaw_frame','upper_pad','lower_pad','head_bottom','motor13','motor14','motor15','head_yaw_link','face_panel','camera_retainer','camera_board','eye_trim']
fixed={}
for k in fixedkeys:
 if k=='head_cap':fixed[k]=load(Path(args.cap) if args.cap else D/'native-cap-registered-world.stl')
 elif k=='face_panel':fixed[k]=load(H/'camera-ribbon-repair/positive-x225/face_three_screw_camera-world.stl')
 else:fixed[k]=source(k)
checks=[];parts=[]
for k in keys:
 original=source(k);variants=[('source',original)]
 if k.startswith('gpio_pin_'):
  native=original.transform(np.linalg.inv(piT)[:3]);body=native^mf.Manifold.cube([200,400,400]).translate([50.52,-200,-100]);body=body.transform(piT[:3]);variants=[('18mm_assembly_receiving',original),('16.79mm_class_hardware_upper_bound',body)]
 for role,s in variants:
  s=s.transform(Tp[:3]);parts.append({'key':k,'role':role,'boundsMm':list(s.bounding_box()),'volumeMm3':s.volume()})
  for fk,obs in fixed.items():
   a=np.array(s.bounding_box()).reshape(2,3);b=np.array(obs.bounding_box()).reshape(2,3)
   if np.any(a[1]<b[0])or np.any(b[1]<a[0]):checks.append({'moving':k,'role':role,'fixed':fk,'volumeMm3':0,'method':'aabb-separated'});continue
   q=s^obs;v=max(0,q.volume());checks.append({'moving':k,'role':role,'fixed':fk,'volumeMm3':v,'method':'individual-solid-intersection','intersectionBounds':list(q.bounding_box())if v>1e-6 else None})
 del original;gc.collect()
if args.include_microb:
 s=mf.Manifold.cube([6,13,25]).translate([63.01,2.4,146.0496]).transform(piT[:3]).transform(Tp[:3]);parts.append({'key':'microB_photo_receiving','role':'13x6photo bound,25 axial assumed;EDAC1.30 datum','boundsMm':list(s.bounding_box()),'volumeMm3':s.volume()})
 for fk,obs in fixed.items():
  q=s^obs;v=max(0,q.volume());checks.append({'moving':'microB_photo_receiving','role':'13x6photo bound,25 axial assumed;EDAC1.30 datum','fixed':fk,'volumeMm3':v,'method':'individual-solid-intersection','intersectionBounds':list(q.bounding_box())if v>1e-6 else None})
p=D/args.output;report={'integrationReady':False,'pose':pose,'sourceHashes':hashes,'sourcePartCount':len(keys),'parts':parts,'checks':checks,'hits':[q for q in checks if q['volumeMm3']>1e-6],'scope':'68 independent current Pi geometry parts against14 fixed original cap/jaw/camera/motor parts. No union. Board-to-board/native OpenRB and connector egress checked by other branch.','gpioDimensions':'12 used individual housings only;16.79mm class upper bound =14.25 female+2.54 male base, measured from native component PCB planeX67.31 toX50.52.18mm source includes1.21mm assembly margin. Same-class housing evidence, not measured user unit.40 actual male pins unchanged.'};p.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'file':str(p),'count':len(checks),'hits':report['hits']},indent=2))
