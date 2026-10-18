from pathlib import Path
import json, numpy as np,trimesh,manifold3d as mf,hashlib
D=Path('/Users/xiangzheng/code/robotics/microduck-sim/build-pack-20260913/redesign-20260913/workflow-review-20261009/enclosed-wiring-repair/power-sensor/head-controller-study');F=D/'final-integration-20261009';HD=D.parents[1]/'head-layout';H=D.parents[3]/'head-redesign-20261008'
p=H/'curved-head/community-curved-head-world.stl';m=trimesh.load_mesh(p);assert m.is_volume;s=mf.Manifold(mf.Mesh64(m.vertices,m.faces.astype(np.uint64)));assert s.status()==mf.Error.NoError
T=np.array(json.loads((HD/'native-fusion-repair-inputs.json').read_text())['openrb']['nativeToCurrentWorld']);p0=json.loads((HD/'openrb-usbc-native-port.json').read_text())['correctedAssumedMouldShoulderMm'];out=[]
for w,t in [(12,7),(4,2),(2,1)]:
 a=mf.Manifold.cube([w,22,t]).translate([p0[0]-w/2,p0[1],p0[2]-t/2]).transform(T[:3]);c=a^s;out.append({'crossSectionMm':[w,t],'volumeMm3':c.volume(),'intersectionBoundsMm':list(c.bounding_box())})
r={'source':str(p),'sourceSha256':hashlib.sha256(p.read_bytes()).hexdigest(),'assumedShoulderNativeMm':p0,'measurements':out,'scope':'Sensitivity to overmould rectangular corners only. Small central axial prisms are diagnostic probes, not manufacturer connector solids. Does not independently establish actual minimum body cross-section.'};(F/'original-c-axis-sensitivity.json').write_text(json.dumps(r,indent=2));print(json.dumps(r,indent=2))
