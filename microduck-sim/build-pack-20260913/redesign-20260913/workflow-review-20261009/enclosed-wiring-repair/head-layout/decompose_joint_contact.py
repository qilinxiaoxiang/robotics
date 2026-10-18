from pathlib import Path
D=Path(__file__).resolve().parent
exec((D/'pack_populated_boards.py').read_text().split('pikeys=')[0])
pikeys=[k for k in rows if k=='pi' or k.startswith(('zero_w_','gpio_pin_','component_'))]
retired=['openrb','openrb_usb_receiving','curved_cap_hardware','camera_ribbon_200']+[k for k in rows if k.startswith('E-pi-')]
j=json.loads((D/'joint-first/report.json').read_text())['candidate'];Tp=np.array(j['pi']['currentWorldDelta']);Tr=np.array(j['openrb']['currentWorldDelta']);piT=np.array(json.loads((H/'camera-ribbon-repair/fixed-pose-local-bend/pi-spacer2-pose.json').read_text())['worldTransform'])
Tp[:3,3]+=np.array([0.,0.,-1.]);Tr[:3,3]+=np.array([0.,0.,0.]);j['localAdjustment']={'pi':[0,0,-1],'openrb':[0,0,0]};
pi_parts={k:source(k).transform(Tp[:3])for k in pikeys};pi=mf.Manifold.batch_boolean(list(pi_parts.values()),mf.OpType.Add)
sc=mf.Manifold.cube([6,13,25]).translate([63.01,2.4,146.0496]).transform(piT[:3]).transform(Tp[:3])
ep=H/'usb-access/usb-repair/openrb-component-enclosures/manifest.json';rb_parts={str(i):load(r['mesh']).transform(Tr[:3])for i,r in enumerate(json.loads(ep.read_text())['components'])};rb=mf.Manifold.batch_boolean(list(rb_parts.values()),mf.OpType.Add)
cplug=load(H/'usb-access/full-harness/openrb-usb-c-published-envelope-world.stl').transform(Tr[:3]);moving={'pi_populated':pi,'microB_photo_receiving':sc,'openrb_populated':rb,'C_plug':cplug};hits=[];clear=0;tested=0
ports=json.loads((W/'enclosed-wiring-repair/motor-wires/two-openrb-ports.json').read_text());
for i,port in enumerate(ports['ports']):
 b=np.array(port['housingLocalBounds']);moving['EH_'+str(i+1)]=mf.Manifold.cube(b[1]-b[0]).translate(b[0]).transform(np.array(port['transform'])[:3]).transform(Tr[:3])
result=[]
for rk,rs in rb_parts.items():
 for pk,ps in pi_parts.items():
  q=rs^ps
  if q.volume()>1e-6:result.append({'rbComponent':rk,'pi':pk,'volume':q.volume(),'intersection':list(q.bounding_box()),'rbBounds':list(rs.bounding_box()),'piBounds':list(ps.bounding_box())})
(D/'joint-datum-down1/pair-decomposition.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
