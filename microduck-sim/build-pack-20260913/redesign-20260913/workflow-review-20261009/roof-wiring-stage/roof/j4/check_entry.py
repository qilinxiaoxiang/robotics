import os,json,sys,types,hashlib
from pathlib import Path
assert os.environ.get('MICRODUCK_BOUNDED_CAD')=='1'
import numpy as np,trimesh as tm,manifold3d as mf
D=Path(__file__).resolve().parent;R=D.parents[3];H=R/'head-redesign-20261008';sys.path.insert(0,str(H/'gpio-audio-repair'));import precision_mesh as pm
c=types.SimpleNamespace(np=np,tm=tm,mf=mf);q=pm.load(c,D/'j4-native.stl');e=json.loads((D/'extraction.json').read_text());T=np.array(e['nativeToWorld']);rows=[]
for name,x in [('negative-native-X',-1.71),('positive-native-X',1.79),('center-divider-negative-control',.04)]:
 axis=np.array([0,1,0]);Rr=np.array([[1,0,0],[0,0,1],[0,-1,0.]])
 probe=mf.Manifold.cylinder(2.6,.8,.8,64).transform(np.column_stack([Rr,[x,-34.49,4.215]]));v=max(0,(probe^q).volume());row={'id':name,'nativeEntranceMm':[x,-33.89,4.215],'worldEntranceMm':(T@np.array([x,-33.89,4.215,1]))[:3].tolist(),'insertionAxisWorld':(T[:3,:3]@axis).tolist(),'outwardAxisWorld':(T[:3,:3]@-axis).tolist(),'cavityRectNativeMm':{'width':2.6,'height':3.96},'testWireDiameterMm':1.6,'testAxisIntervalNativeYmm':[-34.49,-31.89],'intersectionMm3':v,'electricalAssignment':None};rows.append(row)
assert rows[0]['intersectionMm3']<1e-6 and rows[1]['intersectionMm3']<1e-6 and rows[2]['intersectionMm3']>1
report={'status':'GEOMETRIC_PORTS_REGISTERED_POLARITY_MAPPING_PENDING','rows':rows,'source':e,'method':'Extract native connected terminal geometry from existing STL; invert registered rigid transform; section at nativeY=-33.3; cavity rectangle centers and outward lip reference. Positive insertion shaft clears each cavity; center divider is retained negative control. Not inferred from board bounding-box center.','polarity':'Official schematic J4 pin1 VIN and pin2 GND known; physical pin1 mapping to nativeX sign not yet established. Do not energize from unsigned registration.','sourceHashes':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [D/'j4-native.stl',D/'extraction.json',D/'sections.json',Path(__file__)]},'physicalValidated':False}
(D/'terminal-registration.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(rows))
