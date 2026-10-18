from pathlib import Path
D=Path(__file__).resolve().parent
exec((D/'pack_populated_boards.py').read_text().split('pikeys=')[0])
pikeys=[k for k in rows if k=='pi' or k.startswith(('zero_w_','gpio_pin_','component_'))]
retired=['openrb','openrb_usb_receiving','curved_cap_hardware','camera_ribbon_200']+[k for k in rows if k.startswith('E-pi-')]
jp=json.loads((D/'packing-photo/pi-cardinal-screen.json').read_text());jr=json.loads((D/'packing-amp-free/openrb-tilt-screen.json').read_text());p=next(r for r in jp['results'] if r['orientationId']==20)['candidates'][0];r=next(r for r in jr['results'] if r['orientationId']==218)['candidates'][0];j={'pi':p,'openrb':r};Tp=np.array(p['currentWorldDelta']);Tr=np.array(r['currentWorldDelta']);piT=np.array(json.loads((H/'camera-ribbon-repair/fixed-pose-local-bend/pi-spacer2-pose.json').read_text())['worldTransform'])
pi_parts={k:source(k).transform(Tp[:3])for k in pikeys};pi=mf.Manifold.batch_boolean(list(pi_parts.values()),mf.OpType.Add)
sc=mf.Manifold.cube([6,13,25]).translate([63.01,2.4,146.0496]).transform(piT[:3]).transform(Tp[:3])
ep=H/'usb-access/usb-repair/openrb-component-enclosures/manifest.json';rb_parts={str(i):load(r['mesh']).transform(Tr[:3])for i,r in enumerate(json.loads(ep.read_text())['components'])};rb=mf.Manifold.batch_boolean(list(rb_parts.values()),mf.OpType.Add)
cplug=load(H/'usb-access/full-harness/openrb-usb-c-published-envelope-world.stl').transform(Tr[:3]);moving={'pi_populated':pi,'microB_photo_receiving':sc,'openrb_populated':rb,'C_plug':cplug};hits=[];clear=0;tested=0
ports=json.loads((W/'enclosed-wiring-repair/motor-wires/two-openrb-ports.json').read_text());
for i,port in enumerate(ports['ports']):
 b=np.array(port['housingLocalBounds']);moving['EH_'+str(i+1)]=mf.Manifold.cube(b[1]-b[0]).translate(b[0]).transform(np.array(port['transform'])[:3]).transform(Tr[:3])
result=[]
for rk,rs in rb_parts.items():
 q=rs^sc
 if q.volume()>1e-6:result.append({'component':rk,'v':q.volume(),'bounds':list(q.bounding_box()),'rbBounds':list(rs.bounding_box())})
print(json.dumps(result,indent=2));(D/'joint-up-down-pair/micro-contact.json').write_text(json.dumps(result,indent=2))
