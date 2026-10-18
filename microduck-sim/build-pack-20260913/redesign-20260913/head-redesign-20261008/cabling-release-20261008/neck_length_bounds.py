from check_routes import *
import sys,itertools
SIM=H.parent.parents[1];sys.path.insert(0,str(SIM/'hardware-design-20260912/whole-robot-20260912/assembly'));from assembly_fk import fk,TREE
B,_=fk();inv=np.linalg.inv(B['jaw_soft']);spatial=json.loads(read(G/'wiring-spatial-data.json'));nodes={p['id']:p for p in spatial['nodes']}
js=['neck_pitch','head_pitch','head_yaw','head_roll'];limits={j:np.rad2deg(np.fromstring(next(x for x in TREE.iter('joint') if x.get('name')==j).get('range'),sep=' ')).tolist() for j in js};cases=[]
for j,(lo,hi) in limits.items():
 for a in np.linspace(lo,hi,int(np.ceil((hi-lo)/5))+1):cases.append({j:float(a)})
for a in itertools.product([-20,0,20],[-30,0,30],[-90,0,90],[-20,0,20]):cases.append(dict(zip(js,a)))
rows=[]
for start,end,L in [('imu','pi',250),('F10','amp',250),('F9','pi',None)]:
 if start not in nodes:
  print('missing',start);continue
 targetkey={'pi':'pi','amp':'amplifier'}[end];target=meshes[targetkey].bounds.mean(0);origin=np.array(nodes[start]['position']);vals=[]
 for deg in cases:
  poses,_=fk({k:np.deg2rad(v) for k,v in deg.items()});q=(poses['jaw_soft']@inv@np.r_[target,1])[:3];vals.append({'jointDegrees':deg,'componentCenterDistanceMm':float(np.linalg.norm(q-origin))})
 rows.append({'from':start,'to':end,'specifiedWireLengthMm':L,'neutralCenterDistanceMm':float(np.linalg.norm(target-origin)),'minimumSampleMm':min(x['componentCenterDistanceMm'] for x in vals),'maximumSample':max(vals,key=lambda x:x['componentCenterDistanceMm']),'scope':'Component-center chord diagnostic ONLY: not connector coordinates, not cable routed length, not a clearance/slack pass. Existing rigid collision poses not filtered.'})
out={'cases':len(cases),'jointRangesDeg':limits,'rows':rows,'routeAccepted':False,'sourceHashes':hashes};(D/'neck-length-bounds.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out['rows'],indent=2))
