from pathlib import Path
import sys,json,zipfile,hashlib,xml.etree.ElementTree as ET
import numpy as np
D=Path(__file__).resolve().parent;P=D.parent
sys.path.insert(0,str(P/'08-ORANGE-BOTTOM-AUDIT-20260930'))
import analyze_bottom as a
C=P/'04-FOUR-COLOR-20260929';K=C/'07-COMPACT-CENTER-20260929'
records=json.loads((P/'copy-manifest.json').read_text())['copy_records'];ids={str(r['object_id']):r for r in records if 'object_id'in r}
groups=[('old-orange-plate1',P/'02-PROJECTS/Elegoo/MicroDuck-Centauri-Carbon-Orca.3mf',{k for k,v in ids.items() if v['plate']==1}),('old-black-plate5',P/'02-PROJECTS/Elegoo/MicroDuck-Centauri-Carbon-Orca.3mf',{k for k,v in ids.items() if v['plate']==5}),('orange',P/'08-ORANGE-BOTTOM-AUDIT-20260930/MicroDuck_Elegoo_orange_FLAT_editable.3mf',None),('yellow',K/'Elegoo/yellow/MicroDuck_Elegoo_yellow_COMPACT_editable.3mf',None),('WHITE',K/'Elegoo/WHITE/MicroDuck_Elegoo_WHITE_COMPACT_editable.3mf',None),('black',C/'black/MicroDuck-black-editable.3mf',None)]
def assess(m):
    floor=m.bounds[0,2]; nf=m.face_normals; ar=m.area_faces
    candidates=[]
    for inds in m.facets:
        area=float(ar[inds].sum()); normal=np.average(nf[inds],axis=0,weights=ar[inds]);normal/=np.linalg.norm(normal)
        vv=m.triangles[inds].reshape(-1,3)
        if normal[2]<-.85 and vv[:,2].min()<floor+1.5 and area>2:
            candidates.append((area,normal,vv,inds))
    if not candidates:return {'decision':'keep-no-broad-near-horizontal-planar-facet','sections':{str(h):a.section_shape(m,floor+h).area for h in [.05,.1,.2]},'bounds':m.bounds.tolist()}
    candidates.sort(key=lambda x:-x[0]); area,n,v,inds=candidates[0]
    # Aggregate separated coplanar patches in same intended face.
    selected=[x for x in candidates if np.dot(x[1],n)>.999999 and abs(np.mean(x[2]@n)-np.mean(v@n))<.01]
    v=np.concatenate([x[2] for x in selected]);area=sum(x[0] for x in selected)
    angle=float(np.degrees(np.arccos(np.clip(-n[2],-1,1))));b=np.array([0.,0.,-1.]);cross=np.cross(n,b);s=np.linalg.norm(cross);c=np.dot(n,b);V=np.array([[0,-cross[2],cross[1]],[cross[2],0,-cross[0]],[-cross[1],cross[0],0]])
    R=np.eye(3) if s<1e-12 else np.eye(3)+V+V@V*((1-c)/s**2)
    center=m.bounds.mean(0);T=np.eye(4);T[:3,:3]=R;T[:3,3]=center-R@center
    fixed=m.copy();fixed.apply_transform(T);T[2,3]-=fixed.bounds[0,2];fixed=m.copy();fixed.apply_transform(T)
    before={str(h):float(a.section_shape(m,floor+h).area) for h in [.01,.05,.1,.2]};after={str(h):float(a.section_shape(fixed,h).area) for h in [.01,.05,.1,.2]}
    decision='rotate' if angle>.1 and after['0.1']>before['0.1']*1.1 and after['0.1']-before['0.1']>3 else 'keep'
    return {'decision':decision,'angle_degrees':angle,'plane_area_mm2':area,'plane_intrinsic_spread_mm':float(np.ptp(v@n)),'plane_z_spread_mm':float(np.ptp(v[:,2])),'normal':n.tolist(),'sections_before':before,'sections_after':after,'candidate_delta4x4':T.tolist(),'applied_delta4x4':T.tolist() if decision=='rotate' else np.eye(4).tolist(),'volume_before':float(m.volume),'volume_after':float(fixed.volume),'bounds_before':m.bounds.tolist(),'bounds_after':fixed.bounds.tolist()}
rows=[]
for group,path,subset in groups:
    a.PROJECT=path
    for oid,name,m in a.load_meshes():
        if subset is not None and oid not in subset:continue
        row={'group':group,'object_id':oid,'name':name,'manifest_instance_index':ids[oid]['manifest_instance_index'],'source_project':str(path),'source_sha256':a.sha(path),**assess(m)};rows.append(row)
        print(group,oid,name,row['decision'],round(row.get('angle_degrees',0),4),flush=True)
    (D/'orientation-audit.json').write_text(json.dumps({'parts':rows},indent=2)+'\n')
assert len(rows)==89 and len({r['manifest_instance_index'] for r in rows})==89
print('COVERAGE89')
