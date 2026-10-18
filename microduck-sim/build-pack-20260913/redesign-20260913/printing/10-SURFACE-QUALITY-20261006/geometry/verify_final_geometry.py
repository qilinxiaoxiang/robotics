"""Independent readback of package geometry; no project, source or manifest writes.

Usage: python verify_final_geometry.py PACKAGE_MANIFEST [--output JSON]
The manifest's claims of rigidity, coverage and preserved meshes are not trusted.
Native file readiness/physical print quality are separate acceptance scopes.
"""
from pathlib import Path
import argparse, hashlib, json, sys, zipfile, xml.etree.ElementTree as E
import numpy as np
from scipy.spatial import cKDTree
from itertools import permutations
import audit_surfaces as a

G=Path(__file__).resolve().parent
BASE=a.PREVIOUS
MACHINE_FIELDS=['printer_settings_id','printer_model','nozzle_diameter','curr_bed_type','filament_type','filament_settings_id','print_sequence','extruder_offset']
MATERIAL_VALUES=['filament_type','filament_vendor','filament_diameter','filament_density','filament_flow_ratio',
                 'filament_max_volumetric_speed','nozzle_temperature','nozzle_temperature_initial_layer',
                 'textured_plate_temp','textured_plate_temp_initial_layer','cool_plate_temp','cool_plate_temp_initial_layer',
                 'fan_max_speed','fan_min_speed','overhang_fan_speed','filament_retraction_length','filament_z_hop']
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()

def model(path):
    with zipfile.ZipFile(path) as z:
        rt=E.fromstring(z.read('3D/3dmodel.model'));cfg=json.loads(z.read('Metadata/project_settings.config'))
        members={n:z.read(n) for n in z.namelist() if n.startswith('3D/') and n!='3D/3dmodel.model'}
        st=E.fromstring(z.read('Metadata/model_settings.config'))
    objects={o.get('id'):o for o in rt.find(a.N+'resources')}
    items={o.get('objectid'):o for o in rt.find(a.N+'build')}
    names={o.get('id'):o.find("metadata[@key='name']").get('value') for o in st.findall('object')}
    return cfg,members,objects,items,names

def yaw_equivalent(actual,want):
    delta=actual@want.T
    rigid=bool(np.allclose(delta.T@delta,np.eye(3),atol=3e-6) and abs(np.linalg.det(delta)-1)<3e-6)
    zonly=bool(np.allclose(delta[2],[0,0,1],atol=3e-6) and np.allclose(delta[:,2],[0,0,1],atol=3e-6))
    return rigid and zonly,float(np.degrees(np.arctan2(delta[1,0],delta[0,0])))

def exact_import_preset_name(actual,expected,filename):
    """Orca GUI adds only `(this exact imported filename)` to a scoped preset."""
    if actual==expected:return True
    if not isinstance(actual,list) or not isinstance(expected,list) or len(actual)!=len(expected):return False
    suffix='('+filename+')'
    return all(got==want or got==want+suffix for got,want in zip(actual,expected))


def semantic_native_geometry(project,archive,tolerance=2e-5):
    expected=a.load_project(project);native=a.load_project(archive);reports=[];errors=[]
    if len(expected)!=len(native):return [],['Native semantic instance count differs']
    for ordinal,(before,after) in enumerate(zip(expected,native)):
        if before['name']!=after['name']:errors.append('Native build-order source identity differs at ordinal '+str(ordinal));continue
        lhs=before['mesh'];rhs=after['mesh'];same_counts=len(lhs.faces)==len(rhs.faces) and len(lhs.vertices)==len(rhs.vertices)
        if not same_counts:errors.append('Native semantic vertex/triangle count differs: '+before['name'])
        max_vertex=float(cKDTree(rhs.vertices).query(lhs.vertices)[0].max())
        reverse_vertex=float(cKDTree(lhs.vertices).query(rhs.vertices)[0].max())
        face_error=float('inf');bijective=False
        if len(lhs.faces)==len(rhs.faces):
            lt=lhs.triangles;rt=rhs.triangles;dist,index=cKDTree(rt.mean(axis=1)).query(lt.mean(axis=1))
            bijective=len(set(index.tolist()))==len(index)
            alternatives=[]
            for perm in permutations(range(3)):
                alternatives.append(np.linalg.norm(lt-rt[index][:,perm,:],axis=2).max(axis=1))
            face_error=float(np.min(alternatives,axis=0).max())
            if not bijective:errors.append('Native triangle centroid pairing is not bijective: '+before['name'])
        max_bounds=float(np.max(abs(lhs.bounds-rhs.bounds)))
        okay=same_counts and bijective and max(max_vertex,reverse_vertex,face_error,max_bounds)<=tolerance
        if not okay:errors.append('Native semantic world geometry differs beyond2e-5mm: '+before['name'])
        reports.append(dict(native_build_ordinal=ordinal,name=before['name'],editable_object_id=before['object_id'],native_object_id=after['object_id'],
                            source_shape_and_pose_preserved=okay,vertex_count=len(lhs.vertices),triangle_count=len(lhs.faces),
                            bidirectional_max_vertex_error_mm=max(max_vertex,reverse_vertex),bijective_triangle_correspondence=bijective,
                            max_corresponding_triangle_vertex_error_mm=face_error,max_world_bounds_error_mm=max_bounds,tolerance_mm=tolerance))
    return reports,errors

def verify(manifest):
    pack=json.loads(Path(manifest).read_text());variants=pack.get('variants',pack.get('files',[]))
    baseline=json.loads((BASE/'packaging.json').read_text());basevars={(v['printer'],v['group']):v for v in baseline.get('variants',baseline.get('files',[]))}
    audit=json.loads((G/'surface-audit.json').read_text());source_rows={(r['group'],r['object_id']):r for r in audit['instances']}
    noms=json.loads((G/'nominations.json').read_text());nominated={r['manifest_instance_index']:r for r in noms['pose_candidates']}
    results=[];primary_indices=[];errors=[]
    if len(variants)!=10:errors.append('Expected exactly ten printer variants')
    if len({(v['printer'],v['group']) for v in variants})!=len(variants):errors.append('Duplicate printer/group variants')
    for variant in variants:
        printer=variant['printer'];group=variant['group'];row=dict(printer=printer,group=group,errors=[],objects=[]);results.append(row)
        try:
            original=Path(basevars[(printer,group)]['project']);project=Path(variant['project'])
            oldcfg,oldmembers,oldobjects,olditems,oldnames=model(original)
            cfg,members,objects,items,names=model(project)
            row.update(source_project=str(original),source_project_sha256=sha(original),project=str(project),project_sha256=sha(project))
            if 'source_project_sha256' in variant and sha(original)!=variant['source_project_sha256']:row['errors'].append('Immutable baseline source hash changed')
            # Verify exact native mesh member bytes, including topology and source geometry.
            if not all(n in oldmembers and payload==oldmembers[n] for n,payload in members.items()):row['errors'].append('Mesh members changed')
            if set(items)!=set(olditems):row['errors'].append('Instance coverage changed')
            if len(items)!=variant.get('expected_count',variant.get('expectedcount',len(olditems))):row['errors'].append('Object count mismatch')
            for field in MACHINE_FIELDS:
                if cfg.get(field)!=oldcfg.get(field):row['errors'].append('Machine/material invariant changed: '+field)
            if cfg.get('print_sequence')!='by layer':row['errors'].append('Print sequence is not by layer')
            loaded={m['object_id']:m for m in a.load_project(project)}
            for oid,item in items.items():
                key=(group,oid);base=source_rows[key];index=base['manifest_instance_index']
                if names[oid]!=base['name'] or names[oid]!=oldnames[oid]:row['errors'].append('Source identity changed: '+oid)
                if E.tostring(objects[oid].find(a.N+'components'))!=E.tostring(oldobjects[oid].find(a.N+'components')):
                    row['errors'].append('Component/source transform changed: '+oid)
                old=a.matrix(olditems[oid].get('transform'));current=a.matrix(item.get('transform'));delta=current@np.linalg.inv(old)
                if not np.allclose(delta[:3,:3].T@delta[:3,:3],np.eye(3),atol=3e-6) or abs(np.linalg.det(delta[:3,:3])-1)>3e-6:
                    row['errors'].append('Non-rigid scale/shear: '+oid)
                # Account independently for each printer's baseline; geometry audit's raw frame is canonical.
                selected=nominated.get(index);desired=np.array(selected['delta4x4'])[:3,:3] if selected else np.eye(3)
                okay,yaw=yaw_equivalent(delta[:3,:3],desired)
                if not okay:row['errors'].append('Bottom orientation differs from selected candidate/source: '+oid)
                mesh=loaded[oid]['mesh'];floor=float(mesh.bounds[0,2])
                if abs(floor)>.015:row['errors'].append('Part not landed on bed: '+oid)
                # Exact current pose is measured; the manifest's nomination_selected flag is ignored.
                full_delta=current@np.linalg.inv(np.array(base['build_transform']))
                # Source rows came from a primary project whose baseline yaw may differ by printer.
                local,W,_,_=loaded[oid]['components'][0];info=a.source_info(base['name'],local)
                raw_child=np.eye(4);raw_child[:3,:3],raw_child[:3,3]=info['raw_to_child'];raw_current=W@raw_child
                oldraw=np.array(base['raw_source_to_bed4x4']);raw_delta=raw_current@np.linalg.inv(oldraw)
                features=a.transformed_features(base['critical_surface_probes_bed_mm'],raw_delta)
                functional=a.measure(mesh,features)
                if selected and functional['support_exposed_seat_count']!=0:
                    row['errors'].append('Selected pose still exposes sampled critical bearing/sliding surfaces: '+oid)
                if abs(functional['volume_mm3']-base['current']['volume_mm3'])>.01:row['errors'].append('Volume changed: '+oid)
                row['objects'].append(dict(object_id=oid,manifest_instance_index=index,name=names[oid],selected_rotation=selected is not None,
                                           orientation_matches_selected=okay,measured_packing_z_yaw_degrees=yaw,minimum_z_mm=floor,
                                           support_exposed_functional_count=functional['support_exposed_seat_count'],
                                           first_layer_geometry_section_mm2=functional['first_layer_01_section_mm2'],
                                           functional_seats=functional['functional_seats'],raw_source_to_bed4x4=raw_current.tolist()))
                if variant.get('primary'):primary_indices.append(index)
            # A supplied archive must contain the same geometry/project pose and machine values.
            archive=variant.get('archive')
            if archive and Path(archive).exists():
                preset_filename=project.name;reused_native_cfg=None
                if variant.get('native_reused'):
                    original_native=Path(basevars[(printer,group)]['archive'])
                    if Path(archive).read_bytes()!=original_native.read_bytes():row['errors'].append('Claimed reused native is not byte-identical to original native archive')
                    else:
                        preset_filename=original.name;reused_native_cfg=model(original_native)[0]
                        if variant.get('native_source_sha256') and sha(original_native)!=variant['native_source_sha256']:row['errors'].append('Reused native source archive hash differs from bound source')
                acfg,amembers,aobjects,aitems,anames=model(archive)
                if aitems or amembers:
                    semantic,semantic_errors=semantic_native_geometry(project,archive)
                    row['native_semantic_geometry']=semantic;row['errors'].extend(semantic_errors)
                    row['native_archive_format']='Native writer serialization verified semantically: names/build ordinals, bijective world triangles, vertex counts and world dimensions within2e-5mm; editable source mesh bytes remain exact.'
                else:
                    # Real native GUI .gcode.3mf has an empty resources/build document
                    # and G-code/thumbnail metadata only. Source geometry is verified
                    # in the editable file; emitted paths must be independently bound.
                    with zipfile.ZipFile(archive) as zz:gc=[n for n in zz.namelist() if n.endswith('.gcode')]
                    if len(gc)!=1:row['errors'].append('Print-only native archive must contain one G-code member')
                    row['native_archive_format']='Native print-file-only archive: geometry absent by format; actual G-code labels/footprints/functional paths require separate native audit.'
                for field in MACHINE_FIELDS:
                    equal=(acfg.get(field)==reused_native_cfg.get(field) if reused_native_cfg is not None else exact_import_preset_name(acfg.get(field),cfg.get(field),preset_filename)) if field=='filament_settings_id' else acfg.get(field)==cfg.get(field)
                    if not equal:row['errors'].append('Native archive machine/material differs: '+field)
                for field in MATERIAL_VALUES:
                    if acfg.get(field)!=cfg.get(field):row['errors'].append('Native archive underlying material value differs: '+field)
                row['native_archive_sha256']=sha(archive)
        except Exception as exc:row['errors'].append(str(exc))
        row['passed']=not row['errors'];print(printer,group,row['passed'],row['errors'],flush=True)
    coverage=len(primary_indices)==89 and len(set(primary_indices))==89 and set(primary_indices)==set(range(89))
    if not coverage:errors.append('Primary coverage must be all 89 distinct canonical instance indices')
    old=next(r for r in audit['instances'] if r['name']=='community-66.stl')
    oldcount=sum(f.get('support_exposed_samples',0) for f in old['current']['functional_seats'] if f['category']=='horn')
    if oldcount!=32:errors.append('Known old ankle bearing-seat failure no longer reproduced')
    return dict(passed=not errors and all(r['passed'] for r in results),errors=errors,variants=results,
                package_manifest=str(Path(manifest).resolve()),package_manifest_sha256=sha(manifest),
                primary_89_instance_coverage=coverage,primary_instance_count=len(primary_indices),variant_count=len(results),
                old_ankle_expected_quality_failure=True,old_ankle_exposed_annular_samples=oldcount,
                scope='Independent exact source geometry/pose/machine/coverage acceptance. Native functional toolpaths and export/thumbnail/spacing remain separate checks.',
                physical_surface_quality_verified=False,physical_fit_verified=False)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('manifest');parser.add_argument('--output',type=Path,default=G/'final-geometry-verification.json');args=parser.parse_args()
    result=verify(args.manifest);args.output.write_text(json.dumps(result,indent=2)+'\n');print('FINAL_GEOMETRY_PASS' if result['passed'] else 'FINAL_GEOMETRY_FAIL');sys.exit(0 if result['passed'] else 1)
