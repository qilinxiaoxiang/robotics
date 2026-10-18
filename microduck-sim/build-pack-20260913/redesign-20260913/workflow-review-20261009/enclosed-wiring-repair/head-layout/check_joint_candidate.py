from pathlib import Path
D=Path(__file__).resolve().parent
exec((D/'pack_populated_boards.py').read_text().split('pikeys=')[0])
pikeys=[k for k in rows if k=='pi' or k.startswith(('zero_w_','gpio_pin_','component_'))]
retired=['openrb','openrb_usb_receiving','curved_cap_hardware','camera_ribbon_200']+[k for k in rows if k.startswith('E-pi-')]
j=json.loads((D/'packing/joint-screen.json').read_text())['best'][0];Tp=np.array(j['pi']['currentWorldDelta']);Tr=np.array(j['openrb']['currentWorldDelta']);piT=np.array(json.loads((H/'camera-ribbon-repair/fixed-pose-local-bend/pi-spacer2-pose.json').read_text())['worldTransform'])
pi_parts={k:source(k).transform(Tp[:3])for k in pikeys};pi=mf.Manifold.batch_boolean(list(pi_parts.values()),mf.OpType.Add)
sc=mf.Manifold.cube([8,18,25]).translate([60.2,-.1,146.0496]).transform(piT[:3]).transform(Tp[:3])
ep=H/'usb-access/usb-repair/openrb-component-enclosures/manifest.json';rb_parts={str(i):load(r['mesh']).transform(Tr[:3])for i,r in enumerate(json.loads(ep.read_text())['components'])};rb=mf.Manifold.batch_boolean(list(rb_parts.values()),mf.OpType.Add)
cplug=load(H/'usb-access/full-harness/openrb-usb-c-published-envelope-world.stl').transform(Tr[:3]);moving={'pi_populated':pi,'microB_assumed':sc,'openrb_populated':rb,'C_plug':cplug};hits=[];clear=0;tested=0
for k in rows:
 if k in pikeys+retired:continue
 if k=='head_cap':obs=load(W/'enclosed-wiring-repair/enclosure-shell/cap-crown-and-rear-restored-world.stl')
 elif k=='face_panel':obs=load(H/'camera-ribbon-repair/positive-x225/face_three_screw_camera-world.stl')
 else:obs=source(k)
 for key,s in moving.items():
  tested+=1;b=np.array(s.bounding_box()).reshape(2,3);b2=np.array(obs.bounding_box()).reshape(2,3)
  if np.any(b[1]<b2[0])or np.any(b2[1]<b[0]):clear+=1;continue
  q=s^obs;v=max(0,q.volume())
  if v>1e-6:
   entry={'moving':key,'fixed':k,'volume':v,'bounds':list(q.bounding_box())}
   if key=='pi_populated':entry['individual']=[{'key':pk,'volume':(ps^obs).volume()}for pk,ps in pi_parts.items()if (ps^obs).volume()>1e-6]
   if key=='openrb_populated':entry['componentIds']=[pk for pk,ps in rb_parts.items()if (ps^obs).volume()>1e-6]
   hits.append(entry)
  else:clear+=1
 del obs;gc.collect()
for a,b in [('pi_populated','openrb_populated'),('pi_populated','C_plug'),('microB_assumed','openrb_populated'),('microB_assumed','C_plug')]:
 q=moving[a]^moving[b];v=max(0,q.volume());tested+=1
 if v>1e-6:
  entry={'moving':a,'fixed':b,'volume':v,'bounds':list(q.bounding_box())}
  if a=='pi_populated':entry['individual']=[{'key':pk,'volume':(ps^moving[b]).volume()}for pk,ps in pi_parts.items()if (ps^moving[b]).volume()>1e-6]
  hits.append(entry)
 else:clear+=1
out=D/'joint-current-cap';out.mkdir(exist_ok=True)
# Keep compound solids internal; output independent part geometry after collision report.
r={'integrationReady':False,'candidate':j,'testedPairs':tested,'clearPairs':clear,'hits':hits,'sourceHashes':hashes,'limits':'Coarse pairing followed by real solids; SC0727 25x18x8 receiving is assumed, C body thickness7 assumed; retired board mount/flexible shapes must be rebuilt, not hidden in final model.'}
(out/'report.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(hits,indent=2))
