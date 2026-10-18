from pathlib import Path
D=Path(__file__).resolve().parent
exec((D/'pack_populated_boards.py').read_text().split('pikeys=')[0])
pikeys=[k for k in rows if k=='pi' or k.startswith(('zero_w_','gpio_pin_','component_'))]
retired=['openrb','openrb_usb_receiving','curved_cap_hardware','camera_ribbon_200']+[k for k in rows if k.startswith('E-pi-')]
jp=json.loads((D/'packing-photo/pi-cardinal-screen.json').read_text());jr=json.loads((D/'packing-amp-free/openrb-tilt-screen.json').read_text());p=next(r for r in jp['results'] if r['orientationId']==20)['candidates'][0];r=next(r for r in jr['results'] if r['orientationId']==218)['candidates'][0];j={'pi':p,'openrb':r};Tp=np.array(p['currentWorldDelta']);Tr=np.array(r['currentWorldDelta']);piT=np.array(json.loads((H/'camera-ribbon-repair/fixed-pose-local-bend/pi-spacer2-pose.json').read_text())['worldTransform'])
coupler=mf.Manifold.cube([20,54,10]).translate([53,-32,118]);hits=[];clears=0
for k in rows:
 if k in pikeys+retired:continue
 if k=='head_cap':ob=load(D/'native-cap-registered-world.stl')
 elif k=='face_panel':ob=load(H/'camera-ribbon-repair/positive-x225/face_three_screw_camera-world.stl')
 else:ob=source(k)
 q=ob^coupler
 if q.volume()>1e-6:hits.append({'key':k,'volume':q.volume(),'bounds':list(q.bounding_box())})
 else:clears+=1
r={'integrationReady':False,'receivingBounds':[53,-32,118,73,22,128],'purpose':'Independent allocation of USB-A coupling zone; receiving dimensions are engineering allocation, not manufacturer coupled body dimensions.','hits':hits,'clearFixedParts':clears,'sourceHashes':hashes};(D/'coupler-zone.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r['hits']))
