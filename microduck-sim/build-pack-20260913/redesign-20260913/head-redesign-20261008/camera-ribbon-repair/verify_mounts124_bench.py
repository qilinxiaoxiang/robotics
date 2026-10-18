"""Independent local mount/FOV/driver acceptance, explicitly excluding unfinished FFC installation."""
from pathlib import Path
import os,json,gc
assert os.environ.get('MICRODUCK_BOUNDED_CAD')=='1'
import numpy as np,trimesh,manifold3d as mf
D=Path(__file__).resolve().parent;H=D.parent;p=D/'check_saved_pose.py';n={'__file__':str(p)};exec(p.read_text().split('resume=')[0],n);read=n['read'];load=n['loadfile'];volume=n['volume'];source=n['source'];read(Path(__file__))
manifest=json.loads(read(D/'local-candidate-manifest.json'));files=manifest['replacementMeshes']|{q['key']:q['mesh'] for q in manifest['additionalParts']}
files['face_panel']='camera-ribbon-repair/face-mounts124-cap-clearance-world.stl'
files['head_cap']='gpio-audio-repair/cap-amp16z2/cap-current-audio-usb-world.stl'
for sid in ['E-pi-01','E-pi-02','E-pi-04']:
 files[sid+'_revision_screw']='camera-ribbon-repair/'+sid+'-mounts124-screw-world.stl'
files.pop('E-pi-03_revision_screw',None)
def load(p):
 m=trimesh.load(p,force='mesh');assert m.is_watertight, str(p);s=mf.Manifold(mf.Mesh64(np.array(m.vertices,np.float64),np.array(m.faces,np.uint64)));assert s.status()==mf.Error.NoError;return s
def part(k):
 if k in files:p=H/files[k];read(p);return load(p)
 return source(k)
def cyl(a,d,L,r):
 d=np.array(d,float);d/=np.linalg.norm(d);u=np.cross(d,[0,0,1.]);u/=np.linalg.norm(u);v=np.cross(d,u);return mf.Manifold.cylinder(L,r,circular_segments=32).transform(np.column_stack([u,v,d,np.array(a)]))
camreport=json.loads(read(D/'local-camera-roll90-lowear4-pi-report.json'));pireport=json.loads(read(D/'face-mounts124-report.json'));camera=['camera_board','camera_retainer'];face=['face_panel','eye_trim'];pi=['pi','zero_w_components','zero_w_gpio_solder_tails']+[a['key'] for a in json.loads(read(D/'gpio-individual-receiving-manifest.json'))['additionalParts']];screws=[key for key in files if key.endswith('_revision_screw')];sol={k:part(k) for k in camera+face+pi+screws}
toolrows=[]
for sc in camreport['screws']+pireport['fasteners']:
 sid=sc['id'];a=np.array(sc['headSeatMm']);d=np.array(sc['outwardAxis']);scene=camera+[k for k in screws if k.startswith('camera-')]
 if sid.startswith('face-wing'):scene=camera+face+[k for k in screws if not k.startswith('E-pi')]
 if sid.startswith('E-pi'):scene=list(sol)
 tool=cyl(a+d*1.55,d,45,1.5);handle=cyl(a+d*(1.55+45),d,60,9);hits=[]
 for key in scene:
  v,bb=volume(tool,sol[key]);hv,hbb=volume(handle,sol[key]);
  if v>1e-5 or hv>1e-5:hits.append({'obstacle':key,'shaftMm3':v,'handleMm3':hv})
 neg=None
 if sid.startswith('camera-'):neg=sum(volume(tool,sol[k])[0] for k in face)
 elif sid.startswith('face-wing'):neg=sum(volume(tool,sol[k])[0] for k in pi)
 toolrows.append({'id':sid,'shaftDiameterMm':3,'shaftLengthMm':45,'handleDiameterMm':18,'handleLengthMm':60,'scene':scene,'hits':hits,'lateFasteningNegativeMm3':neg})
# Exact whole camera cartridge and populated-board translations on an isolated face bench.
cartridge=camera+[k for k in screws if k.startswith('camera-')];paths=[]
for name,moving,fixed,axis in [('camera_cartridge',cartridge,face,np.array([-1.,0,0])),('populated_pi_board_only',pi,face+camera+[k for k in screws if not k.startswith('E-pi')],np.array(manifest['piWorldTransform'])[:3,0]*-1)]:
 rows=[]
 for off in np.linspace(30,0,121):
  hits=[]
  for mk in moving:
   shifted=sol[mk].translate(axis*off)
   for fk in fixed:
    v,bb=volume(shifted,sol[fk])
    if v>1e-5:hits.append({'moving':mk,'fixed':fk,'volumeMm3':v})
  rows.append({'offsetMm':float(off),'hits':hits})
 paths.append({'name':name,'scope':'No ribbon/wires included; cannot certify populated harness installation','moving':moving,'fixed':fixed,'axis':axis.tolist(),'expectedSamples':121,'completedSamples':len(rows),'rows':rows,'passed':not any(q['hits'] for q in rows)})
fov=load(D/'camera-fov-roll90-lowear4-world.stl');read(D/'camera-fov-roll90-lowear4-world.stl');fovrows=[]
for k in ['face_panel','eye_trim','head_cap','camera_retainer']:
 o=part(k);v,bb=volume(fov,o);fovrows.append({'obstacle':k,'volumeMm3':v});del o;gc.collect()
anchors=np.array([q['headSeatMm'] for q in pireport['fasteners']]);area=float(np.linalg.norm(np.cross(anchors[1]-anchors[0],anchors[2]-anchors[0]))/2)
r={'acceptedLocalOnly':len(toolrows)==9 and all(not q['hits'] for q in toolrows) and all(q['passed'] for q in paths) and all(q['volumeMm3']<1e-5 for q in fovrows),'wholeAssemblyAccepted':False,'expectedTools':9,'completedTools':len(toolrows),'toolChecks':toolrows,'paths':paths,'cameraFOVDegreesWorldYThenZ':[67,102],'fovChecks':fovrows,'piMountingScrewCount':len(anchors),'piFastenerTriangleAreaMm2':area,'thirdCorner':'Passive bearing pad and inward rib; original fourth screw now used','remaining':['Ribbon preconnection/reform/insertion with full200mm material','Full final head assembly including movable jaw, cap and neck-domain obstacles','Populated plug/lead envelopes and physical stiffness'],'sourceHashes':n['hashes']}
(D/'mounts124-bench-verification.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({'acceptedLocalOnly':r['acceptedLocalOnly'],'toolFailures':[q for q in toolrows if q['hits']],'pathFailures':[{ 'name':q['name'],'first':next((s for s in q['rows'] if s['hits']),None)} for q in paths if not q['passed']],'FOV':fovrows,'triangleArea':area},indent=2))
