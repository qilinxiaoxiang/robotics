"""Replace one editable 3MF mesh; preserve its native arrangement and all88 others.
This updates source geometry only. Bambu Studio must regenerate machine toolpaths.
"""
from pathlib import Path
import copy,re,json,hashlib,zipfile,xml.etree.ElementTree as E
import numpy as np,trimesh
O=Path(__file__).resolve().parent;R=O.parent
BASE=R/'printing-20260926/superseded-before-fastener-review/current-print-queue.3mf'
TARGET=R/'current-print-queue.3mf';STL=R/'head-cap-usb-service-print.stl';MAN=R/'print-manifest.json'
NS={'m':'http://schemas.microsoft.com/3dmanufacturing/core/2015/02'};PROD='{http://schemas.microsoft.com/3dmanufacturing/production/2015/06}'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def T(text):
 t=np.eye(4)
 if text:t[:3,:]=np.array([float(x) for x in text.split()]).reshape(4,3).T
 return t
z=zipfile.ZipFile(BASE);settings=E.fromstring(z.read('Metadata/model_settings.config'))
obj=next(o for o in settings.findall('object') if o.find("metadata[@key='name']").get('value')==STL.name);oid=obj.get('id');part=obj.find('part');pid=part.get('id')
model=E.fromstring(z.read('3D/3dmodel.model'));container=model.find(f"m:resources/m:object[@id='{oid}']",NS);components=container.findall('m:components/m:component',NS);assert len(components)==1
comp=components[0];member=comp.get(PROD+'path').lstrip('/');assert comp.get('objectid')==pid
component_T=T(comp.get('transform'));build=model.find(f"m:build/m:item[@objectid='{oid}']",NS);build_T=T(build.get('transform'))
# The stored component transform maps local vertices into the STL print frame.
oldmesh=E.fromstring(z.read(member)).find(f"m:resources/m:object[@id='{pid}']/m:mesh",NS)
oldv=np.array([[float(v.get(a)) for a in 'xyz'] for v in oldmesh.find('m:vertices',NS)])
oldstl=trimesh.load(O/'before-third-boss-repair-head-cap-usb-service-print.stl',force='mesh')
from scipy.spatial import cKDTree
oldframe=oldv@component_T[:3,:3].T+component_T[:3,3]
old_frame_error=max(cKDTree(oldstl.vertices).query(oldframe)[0].max(),cKDTree(oldframe).query(oldstl.vertices)[0].max());assert old_frame_error<.00002,old_frame_error
mesh=trimesh.load(STL,force='mesh');assert mesh.is_watertight and len(mesh.split())==1
# Invert native component placement instead of recentering/reorienting the object.
local=trimesh.transform_points(mesh.vertices,np.linalg.inv(component_T));faces=mesh.faces
lines=['<mesh>','<vertices>']+[f'<vertex x="{v[0]:.17g}" y="{v[1]:.17g}" z="{v[2]:.17g}"/>' for v in local]+['</vertices>','<triangles>']+[f'<triangle v1="{a}" v2="{b}" v3="{c}"/>' for a,b,c in faces]+['</triangles>','</mesh>']
oldtext=z.read(member).decode();newtext,n=re.subn(r'<mesh>.*?</mesh>','\n'.join(lines),oldtext,flags=re.S);assert n==1
config=z.read('Metadata/model_settings.config').decode();pattern=rf'<object id="{oid}">.*?</object>';oldblock=re.search(pattern,config,re.S).group();newblock=re.sub(r'face_count="\d+"',f'face_count="{len(faces)}"',oldblock);newconfig=config.replace(oldblock,newblock,1)
changes={member:newtext.encode(),'Metadata/model_settings.config':newconfig.encode()}
# Refuse to overwrite unrelated source-project edits made after the archived base.
if TARGET.exists() and sha(TARGET)!=sha(BASE):
 current=zipfile.ZipFile(TARGET)
 for name in z.namelist():
  if name not in changes:assert current.read(name)==z.read(name),'Unrelated project edit: '+name
current_before=sha(TARGET)
tmp=TARGET.with_suffix('.repair-tmp.3mf')
with zipfile.ZipFile(tmp,'w') as out:
 for info in z.infolist():out.writestr(copy.copy(info),changes.get(info.filename,z.read(info.filename)))
check=zipfile.ZipFile(tmp);assert check.namelist()==z.namelist()
unchanged=[n for n in z.namelist() if check.read(n)==z.read(n)];different=[n for n in z.namelist() if check.read(n)!=z.read(n)];assert set(different)==set(changes)
newsettings=E.fromstring(check.read('Metadata/model_settings.config'))
for a,b in zip(settings.findall('object'),newsettings.findall('object')):
 if a.get('id')!=oid:assert E.tostring(a)==E.tostring(b)
assert [E.tostring(p) for p in settings.findall('plate')]==[E.tostring(p) for p in newsettings.findall('plate')]
newmesh=E.fromstring(check.read(member)).find(f"m:resources/m:object[@id='{pid}']/m:mesh",NS);v=np.array([[float(v.get(a)) for a in 'xyz'] for v in newmesh.find('m:vertices',NS)]);f=np.array([[int(t.get(a)) for a in ['v1','v2','v3']] for t in newmesh.find('m:triangles',NS)])
embedded_print_frame=trimesh.transform_points(v,component_T);expected_world=trimesh.transform_points(mesh.vertices,build_T);embedded_world=trimesh.transform_points(embedded_print_frame,build_T);error=float(np.max(np.abs(expected_world-embedded_world)));assert error<1e-10 and np.array_equal(f,faces)
assert len(model.findall('m:build/m:item',NS))==89;assert len(settings.findall('plate'))==6
assert not any(n.endswith('.gcode') for n in check.namelist())
check.close();tmp.replace(TARGET)
manifest=json.loads(MAN.read_text());rows=[r for r in manifest['instances'] if Path(r['file']).name==STL.name];assert len(rows)==1
oldrow=dict(rows[0]);rows[0].update(sha256=sha(STL),extent_mm=mesh.extents.tolist(),revision_basis='USB service window retained; original third cap attachment axis restored with4.6mm boss/2.1mm pilot; arrangement unchanged')
MAN.write_text(json.dumps(manifest,indent=2)+'\n')
report={'scope':'Editable source3MF geometry replacement only; requires native Bambu reslicing','baseline':str(BASE),'baseline_sha256':sha(BASE),'previous_target_sha256':current_before,'target':str(TARGET),'target_sha256':sha(TARGET),'stl':str(STL),'stl_sha256':sha(STL),'object_id':oid,'mesh_object_id':pid,'mesh_member':member,'plate':1,'instances':89,'plates':6,'unchanged_other_instances':88,'changed_archive_members':different,'unchanged_archive_members':len(unchanged),'component_transform_unchanged':comp.get('transform'),'build_transform_unchanged':build.get('transform'),'old_stl_frame_match_error_mm':float(old_frame_error),'new_world_vertex_max_abs_error_mm':error,'triangle_indices_exact_match':bool(np.array_equal(f,faces)),'new_faces':len(faces),'unchanged_presets':True,'unchanged_plate_assignments':True,'manifest_before_cap':oldrow,'manifest_after_cap':rows[0],'preview_images':'Preserved original source previews; native Bambu slice/export regenerates machine previews','embedded_gcode_count':0,'passed':True}
(O/'repaired-cap-3mf-update-verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
