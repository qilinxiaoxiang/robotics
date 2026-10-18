from pathlib import Path
D=Path(__file__).resolve().parent
exec((D/'check_joint_up_down_pair.py').read_text().split('pi_parts=')[0])
pts=[]
for z,width,height in [(12,13,6),(20,6,5)]:
 for x in [-height/2,height/2]:
  for y in [-width/2,width/2]:pts.append([x,y,z])
mesh=tm.convex.convex_hull(np.array(pts));fr=mf.Manifold(mf.Mesh64(np.asarray(mesh.vertices,np.float64),np.asarray(mesh.faces,np.uint64)))
sc0=(mf.Manifold.cube([6,13,12]).translate([-3,-6.5,0])+fr+mf.Manifold.cube([5,6,5]).translate([-2.5,-3,20])).translate([66.01,8.9,146.0496]).transform(piT[:3])
actual={str(q['index']):load(q['mesh']).transform(Tr[:3])for q in json.loads((D/'actual-openrb-components/micro-contact-proof.json').read_text())['records']if 'mesh'in q};ports=json.loads((W/'enclosed-wiring-repair/motor-wires/two-openrb-ports.json').read_text())
for i,p in enumerate(ports['ports']):
 b=np.array(p['housingLocalBounds']);actual['plug'+str(i+1)]=mf.Manifold.cube(b[1]-b[0]).translate(b[0]).transform(np.array(p['transform'])[:3]).transform(Tr[:3])
results=[]
for deg,dy in [(0,0),(-5,2),(-10,3)]:
 a=np.radians(deg);Z=np.array([[np.cos(a),-np.sin(a),0],[np.sin(a),np.cos(a),0],[0,0,1]]);Q=np.eye(4);Q[:3,:3]=Z;Q[:3,3]=np.array([59,-1+dy,131])-Z@np.array([59,-1,131]);T=Q@Tp;s=sc0.transform(T[:3]);hits=[]
 for k,o in actual.items():
  q=s^o
  if q.volume()>1e-6:hits.append({'part':k,'volume':q.volume(),'bounds':list(q.bounding_box())})
 results.append({'piYawDelta':deg,'piYDelta':dy,'hits':hits,'overlapSum':sum(h['volume']for h in hits),'currentPiDelta':T.tolist()})
r={'integrationReady':False,'sourceBasedLimits':'SC0727 photo supports a taper and ribbed strain relief, but axial breakpoints12/20/25 are sensitivity assumptions, NOT measured/manufacturer dimensions. Keep original rectangular negative.','results':results,'sourceHashes':hashes};(D/'micro-taper-local.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(results,indent=2))
