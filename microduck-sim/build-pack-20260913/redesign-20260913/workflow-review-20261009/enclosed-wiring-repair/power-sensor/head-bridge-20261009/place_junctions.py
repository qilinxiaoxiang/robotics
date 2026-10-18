from context import *
rows,hashes=inventory();obs=load_obstacles(rows);out=[]
# Fixed head distributor joints; two separate insulated same-net splices, not a new board.
for net,y in [('5v',-5),('gnd',5)]:
 m=trimesh.creation.cylinder(radius=3/np.cos(np.pi/48),height=12,sections=48);m.apply_transform(trimesh.transformations.rotation_matrix(np.pi/2,[0,1,0]));m.apply_translation([51.8,y,132.5]);checks=check(m,obs);hits=[c for c in checks if c['volumeMm3']>1e-6];print(net,hits,flush=True);p=D/f'head-{net}-splice.stl';m.export(p);out.append({'key':'head_'+net+'_splice','file':str(p),'sha256':sha(p),'centerMm':[51.8,y,132.5],'axis':[1,0,0],'diameterMm':6,'lengthMm':12,'checks':checks,'hits':hits})
(D/'head-splice-placement.json').write_text(json.dumps({'sourceHashes':hashes|{str(Path(__file__)):sha(__file__)},'parts':out,'passed':all(not p['hits']for p in out),'scope':'Two proposed head insulation receiving spaces only, not head circuit completion'},indent=2))
