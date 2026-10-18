"""Finite first-bend screen with true connector exit planes; not full-wire acceptance."""
from pathlib import Path
import argparse,json,base64,hashlib,math,os
assert os.environ.get('MICRODUCK_BOUNDED_CAD')=='1'
import bounded_amp_check as c
c.guarded_import()
from tube_with_end_frame import tube_with_start_tangent
D=Path(__file__).resolve().parent;H=D.parent;U=H/'usb-access/usb-repair'
ap=argparse.ArgumentParser();ap.add_argument('--candidate',type=Path,required=True);ap.add_argument('--dy',type=float,default=0);ap.add_argument('--dx',type=float,default=0);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--pin',type=int);ap.add_argument('--retire-old-pi-mounts',action='store_true');a=ap.parse_args()
hashes={}
def read(p):
 p=Path(p);b=p.read_bytes();hashes[str(p.resolve())]=hashlib.sha256(b).hexdigest();return b
def solid(p):
 p=Path(p)
 if p.suffix=='.json':
  d=json.loads(read(p));m=c.tm.Trimesh(c.np.frombuffer(base64.b64decode(d['positionB64']),'<f4').reshape(-1,3),c.np.frombuffer(base64.b64decode(d['indexB64']),'<u4').reshape(-1,3),process=True)
 else:read(p);m=c.tm.load(p,force='mesh')
 s=c.mf.Manifold(c.mf.Mesh64(c.np.asarray(m.vertices,c.np.float64),c.np.asarray(m.faces,c.np.uint64)));assert s.status()==c.mf.Error.NoError,str(p)
 return s
candidate=json.loads(read(a.candidate));T=c.np.array(candidate['candidate']['worldTransform']);T[1,3]+=a.dy;T[0,3]+=a.dx
scene=json.loads(read(U/'positive-x225-obstacle-plan.json'))['obstacles']
for r in candidate['parts']:
 if r['key'] in ('USB_insertion_corridor','CSI_free4') or r['key'].endswith('_firstbend'):continue
 bb=c.np.array(r['boundsMm']).reshape(2,3);bb[:,1]+=a.dy;bb[:,0]+=a.dx
 scene[r['key']]={'source':str(H/r['mesh']),'bounds':bb.tolist(),'dy':a.dy,'dx':a.dx}
# Original native shell closes old diagnostic USB hole, stronger for this lower-face screen.
scene['head_cap']['source']=str(U/'robot-source-cache/head_cap.json')
if a.retire_old_pi_mounts:
 scene['face_panel']['source']=str(H/'camera-ribbon-repair/positive-x225/face_three_screw_camera-world.stl')
 for k in list(scene):
  if k.startswith('E-pi-') or 'pi_mount_screw' in k:scene.pop(k)
NETS={1:('imu-vin',1.5),2:('pi-5v-2',1.8),3:('imu-sda',1.5),4:('pi-5v-4',1.8),5:('imu-scl',1.5),6:('pi-gnd-6',1.8),9:('imu-gnd',1.5),12:('BCLK',.8),14:('pi-gnd-14',1.8),20:('audio-ground',.8),35:('LRCLK',.8),40:('DIN',.8)}
if a.pin:NETS={a.pin:NETS[a.pin]}
solids={};routes=[]
for pin,(net,diameter) in NETS.items():
 start=(T@c.np.array([49.31,-24.141+2.54*((pin-1)//2),118.2796+(2.54 if pin%2==0 else 0),1]))[:3];n=-T[:3,0]
 choices=[]
 for angle in range(0,360,30):
  beta=math.radians(angle);b=T[:3,1]*math.cos(beta)+T[:3,2]*math.sin(beta);R=3
  pts=[start+b*R*(1-math.cos(t))+n*R*math.sin(t) for t in c.np.linspace(0,math.pi/2,25)]
  wire=tube_with_start_tangent(pts,diameter/2,n);wb=c.np.array(wire.bounding_box()).reshape(2,3);hits=[];exact=0
  for key,item in scene.items():
   bb=c.np.array(item['bounds'])
   if not(c.np.all(wb[0]<bb[1]) and c.np.all(bb[0]<wb[1])):continue
   sources=sorted((U/'openrb-component-enclosures').glob('*.stl')) if key=='openrb' else [Path(item['source'])]
   for f in sources:
    cache=(str(f),item.get('dx',0),item.get('dy',0))
    if cache not in solids:solids[cache]=solid(f).translate([item.get('dx',0),item.get('dy',0),0])
    ob=solids[cache];obbox=c.np.array(ob.bounding_box()).reshape(2,3)
    if not(c.np.all(wb[0]<obbox[1]) and c.np.all(obbox[0]<wb[1])):continue
    exact+=1;inter=wire^ob;v=max(0,float(inter.volume()))
    # Matching receiving female housing: only numerical exit-plane overlap is allowed.
    if key==f'gpio_pin_{pin:02}_receiving' and v>0:
     ib=c.np.array(inter.bounding_box()).reshape(2,3);axial=(ib-start)@n
     if max(abs(axial))<.000002:v=0
    if v>1e-5:hits.append({'key':key,'volumeMm3':v})
  choices.append({'angleDeg':angle,'hits':hits,'exactPairs':exact,'centerlineMm':[x.tolist() for x in pts]})
 routes.append({'pin':pin,'net':net,'diameterMm':diameter,'bendRadiusMm':3,'startMm':start.tolist(),'outward':n.tolist(),'clearAnglesDeg':[x['angleDeg'] for x in choices if not x['hits']],'choices':choices})
read(Path(__file__));a.out.parent.mkdir(exist_ok=True)
a.out.write_text(json.dumps({'integrationReady':False,'scope':'Twelve GPIO first-quarter-circle screens only; current full cables and interwire clearance not accepted. Pi pose conditional.','dyMm':a.dy,'dxMm':a.dx,'worldTransform':T.tolist(),'routes':routes,'sourceHashes':hashes},indent=2)+'\n')
print(json.dumps([{'pin':r['pin'],'clearAngles':r['clearAnglesDeg'],'failedExample':r['choices'][0]['hits']} for r in routes]))
