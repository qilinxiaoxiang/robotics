from pathlib import Path
import json,hashlib,struct,math,shutil
R=Path('/Users/xiangzheng/code/robotics/microduck-sim/build-pack-20260913/redesign-20260913');H=R/'head-redesign-20261008';D=R/'workflow-review-20261009/roof-wiring-stage/head-wires'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def bounds(p):
 b=p.read_bytes();n=struct.unpack_from('<I',b,80)[0]; pts=[]
 if 84+50*n != len(b):
  pts=[list(map(float,line.split()[1:])) for line in b.decode().splitlines() if line.strip().startswith('vertex ')]
  return [[min(q[k] for q in pts) for k in range(3)],[max(q[k] for q in pts) for k in range(3)]]
 for i in range(n):
  vals=struct.unpack_from('<12f',b,84+i*50);pts.extend([vals[3:6],vals[6:9],vals[9:12]])
 return [[min(q[k] for q in pts) for k in range(3)],[max(q[k] for q in pts) for k in range(3)]]
def stl(path,vs,fs):
 b=bytearray(80)+struct.pack('<I',len(fs))
 for f in fs:b.extend(struct.pack('<12fH',0,0,0,*vs[f[0]],*vs[f[1]],*vs[f[2]],0))
 path.write_bytes(b)
def straight_tube(path,p,a,length,r):
 u=[0,1,0];v=[-a[2],0,a[0]];vs=[]
 for t in [0,length]:
  for j in range(32):
   c=2*math.pi*j/32;vs.append([p[k]+a[k]*t+r*(u[k]*math.cos(c)+v[k]*math.sin(c)) for k in range(3)])
 fs=[]
 for j in range(32):k=(j+1)%32;fs.extend([(j,k,32+k),(j,32+k,32+j)])
 vs.extend([p,[p[k]+length*a[k] for k in range(3)]])
 for j in range(32):k=(j+1)%32;fs.extend([(64,k,j),(65,32+j,32+k)])
 stl(path,vs,fs)
parts=[]
def add(key,name,src,col,status,group='head-wiring',source=None):
 dest=D/(key+'-world.stl')
 if src.resolve()!=dest.resolve():shutil.copyfile(src,dest)
 parts.append(dict(key=key,name=name,file=str(dest),color=col,group=group,expectedFinalBoundsMm=bounds(dest),sha256=sha(dest),validationStatus=status,sourceFile=str(source or src),sourceSha256=sha(source or src)))
add('camera_ribbon_200','SC1892 camera ribbon: 200 mm placement example',H/'gpio-audio-repair/ffc-terminal-adjustment/dogleg-0.25-full200-world.stl','#dcb35a','Prior full-line static/self/closure geometric receipt; current roof patch check separate. Flexible placement example, not a prescribed physical bend radius.')
for i in range(2):add('speaker_wire_'+str(i),'Speaker VO'+('+' if i==0 else '-')+' wire',H/f'gpio-audio-repair/speaker-rewire/speaker-wire-{i}-world.stl',['#d84a43','#353535'][i],'Source route reused without moving amp or speaker; no new roof/current-scene clearance claim.')
u=json.loads((H/'usb-access/full-harness/published-usbc-verification.json').read_text())
add('mac_usb_c_plug','Mac motor-control link: OpenRB USB-C connector',H/'usb-access/full-harness/openrb-usb-c-published-envelope-world.stl','#555b68','Published 27 mm axial overmould; 7 mm cross dimension remains receiving assumption. Prior rear-port insertion evidence; current roof-specific check pending.')
p=D/'mac_usb_flex-world.stl';straight_tube(p,u['cableExitWorldMm'],u['outwardAxis'],102.5,2.25)
add('mac_usb_flex','Mac motor-control link: external USB cable',p,'#486cad','Illustrative straight external placement of nominal 102.5 mm flexible span; host adapter/socket outside model. Not a validated robot-motion cable route.',source=H/'usb-access/full-harness/published-usbc-verification.json')
route={'key':'mac_usb_flex','from':'OpenRB USB-C','to':'USB-A plug toward Mac host / adapter, off robot','centerlineMm':[u['cableExitWorldMm'],[u['cableExitWorldMm'][i]+102.5*u['outwardAxis'][i] for i in range(3)]],'diameterMm':4.5,'nominalFlexibleLengthMm':102.5,'lengthBasis':'4472 152.4 mm shoulder-to-shoulder minus 27 mm C overmould and 22.9 mm A overmould','plugShoulderWorldMm':u['seatedShoulderWorldMm'],'insertionAxis':[-x for x in u['outwardAxis']],'source':u['officialDrawingUrl'],'status':'CAD architecture alternative; split runtime migration not executed; Mac-side connector not seated in a modeled host.'}
(D/'mac-usb-route.json').write_text(json.dumps(route,indent=2)+'\n')
m={'schemaVersion':1,'units':'mm','coordinateFrame':'current robot world; no added translation','title':'Restored roof / split-host wiring study','problemIds':['P0','P5','P6'],'architecture':'Mac USB to OpenRB rear service port; Pi sensor capture via CSI/I2S/I2C. Pi OTG port unused in this CAD-stage alternative. Runtime migration unverified.','integrationReady':False,'parts':parts,'pending':['Update I2S Pi ends to current 2 mm spacer pose','DFR 5 V and return pairs to Pi/OpenRB/amplifier','BNO085 3.3 V/SDA/SCL/GND','Current roof and remaining local clearance checks'],'excluded':['11-fuse array','Pi SC0727 OTG route and its unverified 25 x 18 x 8 mm plug envelope'],'sourceHashes':{str(H/'gpio-audio-repair/ffc-terminal-adjustment/final-geometric-acceptance.json'):sha(H/'gpio-audio-repair/ffc-terminal-adjustment/final-geometric-acceptance.json')}}


# Pure Python centerline mesh: review geometry only, not a continuum clearance proof.
def sub(a,b):return [a[i]-b[i] for i in range(3)]
def norm(a):return math.sqrt(sum(x*x for x in a))
def unit(a):
 n=norm(a);return [x/n for x in a]
def cross(a,b):return [a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]
def tube(path,ps,r):
 vs=[];N=24
 for i,p in enumerate(ps):
  t=unit(sub(ps[min(i+1,len(ps)-1)],ps[max(i-1,0)]));u=unit(cross(t,[0,0,1] if abs(t[2])<.9 else [0,1,0]));v=cross(t,u)
  for j in range(N):
   a=2*math.pi*j/N;vs.append([p[k]+r*(u[k]*math.cos(a)+v[k]*math.sin(a)) for k in range(3)])
 fs=[]
 for i in range(len(ps)-1):
  for j in range(N):
   k=(j+1)%N;fs.extend([(i*N+j,i*N+k,(i+1)*N+k),(i*N+j,(i+1)*N+k,(i+1)*N+j)])
 c=len(vs);vs.extend([ps[0],ps[-1]])
 for j in range(N):
  k=(j+1)%N;fs.extend([(c,k,j),(c+1,(len(ps)-1)*N+j,(len(ps)-1)*N+k)])
 stl(path,vs,fs)
pose=H/'camera-ribbon-repair/fixed-pose-local-bend/pi-spacer2-pose.json';pd=json.loads(pose.read_text());T=pd['worldTransform'];delta=pd['translationFromPositiveX225Mm']
i2s=H/'gpio-audio-repair/gpio-fanout/x225/i2s-route-proposal.json';i2sd=json.loads(i2s.read_text())
routes=[route]
for r in i2sd['routes']:
 ps=r['centerlineMm'];length=0;new=[]
 for i,p in enumerate(ps):
  if i:length+=norm(sub(p,ps[i-1]))
  blendLength=6 if r['pin']==20 else 25
  a=max(0,1-length/blendLength);a=a*a*(3-2*a)
  new.append([p[k]+a*delta[k] for k in range(3)])
 key='i2s_pin_'+str(r['pin']);f=D/(key+'-world.stl');tube(f,new,.75)
 add(key,'I2S '+r['net']+' / Pi pin '+str(r['pin']),f,{12:'#ff9c3e',20:'#32353b',35:'#69bd6b',40:'#558ad7'}[r['pin']],'Pi end moved to actual 2 mm spacer; amp end unchanged. New local transition unverified; 1.5 mm receiving tube does not claim actual 4397 tail diameter or stock length.',source=i2s)
 routes.append({'key':key,'from':'Pi physical pin '+str(r['pin']),'to':'MAX98357A '+r['net'],'fromPoseSource':str(pose),'fromEndpointVerified':True,'toEndpointEvidence':'Existing registered solder pad coordinate retained','centerlineMm':new,'sourceRoute':str(i2s),'sourceRouteSha256':sha(i2s),'diameterReceivingMm':1.5,'actual4397TailDiameterMm':.8,'adjustment':f'Only first {blendLength} mm smoothly shifted; exact amplifier endpoint retained','sourceLengthMm':r['analyticLengthMm'],'candidatePolylineLengthMm':sum(norm(sub(new[i],new[i-1])) for i in range(1,len(new))),'validationStatus':'Current-pose candidate; collision/self/closure not yet checked'})
m['pending'].remove('Update I2S Pi ends to current 2 mm spacer pose');m['pending'].append('Validate new I2S local transitions against current roof/head and each other')
m['sourceHashes'].update({str(pose):sha(pose),str(i2s):sha(i2s)})
# Source-bound electrical nets; the converter and IMU are envelopes, so their
# connector-side drawing anchors remain explicitly provisional.
def point(q):return [sum(T[i][j]*q[j] for j in range(3))+T[i][3] for i in range(3)]
def pin_tail(pin):
 q=[58.81,-24.141+2.54*((pin-1)//2),118.2796+(2.54 if pin%2==0 else 0)]
 tip=point(q);return [tip[i]-T[i][0]*(14.25-5.96) for i in range(3)]
def round_polyline(w,r=3):
 # Exact planar circular fillets, sampled at <=0.25 mm. No pose-domain claim.
 def line(a,b):
  n=max(1,math.ceil(norm(sub(b,a))/.25));return [[a[k]+(b[k]-a[k])*j/n for k in range(3)] for j in range(1,n+1)]
 out=[w[0]];last=w[0]
 for i in range(1,len(w)-1):
  a=unit(sub(w[i],w[i-1]));b=unit(sub(w[i+1],w[i]));theta=math.acos(max(-1,min(1,sum(a[k]*b[k] for k in range(3)))))
  if theta<1e-7:continue
  d=r*math.tan(theta/2)
  if d>min(norm(sub(w[i],w[i-1])),norm(sub(w[i+1],w[i])))*.45:raise ValueError('fillet overlap; route must be revised')
  start=[w[i][k]-a[k]*d for k in range(3)];end=[w[i][k]+b[k]*d for k in range(3)];axis=unit(cross(a,b));normal=cross(axis,a);c=[start[k]+normal[k]*r for k in range(3)];rad=sub(start,c);perp=cross(axis,rad)
  out+=line(last,start);n=max(1,math.ceil(r*theta/.25))
  for j in range(1,n+1):
   t=theta*j/n;out.append([c[k]+rad[k]*math.cos(t)+perp[k]*math.sin(t) for k in range(3)])
  last=end
 out+=line(last,w[-1]);return out
power=[]
for j,pin in enumerate([2,4,6,14]):
 plus=pin in [2,4];end=pin_tail(pin);y=-40-2*j
 start=[-39.5,-10.7 if plus else 0,1];wps=[start,[-55,start[1],10],[-66,y,38],[-30,y,83],[35,y,105],[end[0]-8,end[1],end[2]],end]
 power.append(('pi_power_'+str(pin),'5 V' if plus else 'GND','DFR1202 VOUT' if plus else 'DFR1202 GND','Pi physical pin '+str(pin),wps,1.8,'#ed6545' if plus else '#30343e','DFR orientation is proposed from manufacturer pad photo; Pi endpoint is registered header wire exit.'))
for j,(net,yend) in enumerate([('VIN',-15.57999939),('GND',-18.11999939)]):
 start=[-39.5,-10.7 if j==0 else 0,1];end=[56.257000885,yend,135.5849994];y=-49-2*j
 wps=[start,[-56,start[1],12],[-67,y,39],[-28,y,87],[30,y,118],[56.257000885,yend,124],end]
 power.append(('amp_power_'+net.lower(),'5 V' if j==0 else 'GND','DFR1202 VOUT' if j==0 else 'DFR1202 GND','MAX98357A '+net,wps,1.5,'#e6a149' if j==0 else '#3f4149','Amp solder-pad locations inherited from existing registered I2S/GAIN source. VIN splice and restraint remain open; do not stuff multiple wires into one hole.'))
# J4 region is anchored to the actual terminal solid47 at the opposite end
# from USB. Pin sign assignment and mouth depth have not been registered.
# The line ends short of the terminal region rather than claiming fake seating.
for j in range(2):
 start=[-39.5,-10.7 if j==0 else 0,1];end=[62.5,-1.75+3.5*j,145]
 wps=[start,[-58,start[1],14],[-69,-54-2*j,42],[-25,-54-2*j,91],[42,-40,118],[64,-20,139],end]
 power.append(('openrb_power_'+str(j),'5 V' if j==0 else 'GND','DFR1202 VOUT' if j==0 else 'DFR1202 GND','OpenRB J4 pin1 VIN+' if j==0 else 'OpenRB J4 pin2 GND',wps,2.5,'#ce493c' if j==0 else '#25262b','J4 official schematic polarity known; mouth pose and handed pin mapping not registered. Loose end stops outside the terminal; not an inserted connector.'))
for j,(pin,net) in enumerate([(1,'3.3 V'),(3,'SDA'),(5,'SCL'),(9,'GND')]):
 start=pin_tail(pin);end=[-57,-3+2*j,29.5];y=-37+1.6*j
 wps=[start,[start[0]-8,start[1],start[2]],[35,y,104],[-25,y,78],[-65,y,40],[-65,end[1],29.5],end]
 power.append(('imu_'+net.lower().replace(' ','').replace('.','_'),net,'Pi physical pin '+str(pin),'BNO085 '+net,wps,.8,['#d3443b','#509d5b','#e3c843','#363b43'][j],'Pi endpoint registered. BNO085 board is an installation envelope; four loose ends stop above the board, not fictitious seated STEMMA sockets. 4397 nominal150 mm stock is not silently lengthened.'))
for key,net,fr,to,wps,diam,col,ev in power:
 pts=round_polyline(wps,2);f=D/(key+'-world.stl');tube(f,pts,diam/2)
 status='Illustrative current-pose route; terminal registration/clearance/articulation and cable stock not accepted. '+ev
 add(key,net+' / '+fr+' to '+to,f,col,status,group='torso-head-wiring-study',source=pose)
 routes.append({'key':key,'net':net,'from':fr,'to':to,'waypointsMm':wps,'centerlineMm':pts,'lengthMm':sum(norm(sub(pts[i],pts[i-1])) for i in range(1,len(pts))),'diameterReceivingMm':diam,'bendRadiusReceivingMm':2,'endpointEvidence':ev,'validationStatus':status,'physicalFitVerified':False})
m['pending']=['Register DFR installed pad orientation, OpenRB J4 mouth/polarity and BNO085 socket frame','Check new I2S/power/I2C routes and slack over the actual joint domain','Verify stock wire lengths, amp VIN splice and strain relief','Runtime split migration and physical electrical commissioning']
m['electricalBoundaries']=['Camera power and data both pass through CSI; no separate camera power branch','Pi pins2/4 share5V;6/14 are returns. Amp power return and I2S signal-reference GND are distinct physical conductors on the same net, not extra independent supplies','OpenRB power shown to J4 with official pin1 VIN+/pin2 GND; select appropriate VIN(DXL) source mode before commissioning','No fuse carrier or independent eleven-way fuse distribution is modeled','DFR output-pad image anchors are proposed installation orientation, not registered coordinates of the existing rectangular CAD envelope']
m['parts']=parts
(D/'routes.json').write_text(json.dumps({'units':'mm','routes':routes},indent=2)+'\n')
(D/'manifest.json').write_text(json.dumps(m,indent=2)+'\n');print(str(D/'manifest.json'));print(sha(D/'manifest.json'))
