"""Build per-part digital functional-interface criteria from actual source geometry."""
from pathlib import Path
import hashlib,json,sys
import numpy as np
import audit_surfaces as a
from source_core_slab import source_slab_boundary_radius

G=Path(__file__).resolve().parent
audit=json.loads((G/'surface-audit.json').read_text())
cache={};slab_cache={};rows=[]

def closed_bore(mesh,center,axis):
    axis=np.array(axis,float);axis/=np.linalg.norm(axis)
    basis=a.trimesh.geometry.align_vectors([0,0,1],axis)[:3,:3]
    radii=[]
    for angle in np.linspace(0,2*np.pi,16,endpoint=False):
        d=basis@np.array([np.cos(angle),np.sin(angle),0]);hit=a.ray_first(mesh,center,d)
        if hit is None or np.dot(hit[1],d)>-.5:return None
        radius=np.linalg.norm(hit[0]-center)
        if radius>12:return None
        radii.append(radius)
    if max(radii)-min(radii)>.025:return None
    return float(min(radii))

for row in audit['instances']:
    name=row['name']
    if row['source_id'] is not None:mesh=a.namespace['mesh']('3D/3dmodel.model',str(row['source_id']))
    else:mesh=a.trimesh.load(row['source_stl'],force='mesh')
    core=[];seats=[];invalid_core_windows=[]
    for f in row['critical_surface_probes_bed_mm']:
        seats.append(dict(id=f['id'],category=f['category'],spec=f['spec'],baseline_valid_samples=len(f['points']),
                          source_point_mm=f['source_point_mm'],source_axis=f['source_outward_axis'],
                          actual_probe_points_in_old_primary_bed_mm=f['points'],actual_normals_in_old_primary_bed=f['normals'],
                          requirement='If the actual new pose leaves these real triangles facing downward, query model beads and support-interface footprints at the corresponding model underside Z. A global support-present flag is insufficient.',
                          physical_finish_verified=False))
        axis=np.array(f['source_outward_axis'],float);center=np.array(f['source_point_mm'],float)
        if f['category'] in ['horn','case','rear_center']:
            levels=[(-depth,center-axis*depth) for depth in [.25,.75,1.25]]
        elif f['category'] in ['sliding_bore','sliding_pocket']:
            extent=np.ptp(mesh.vertices@axis);levels=[(offset,center+axis*offset) for offset in [-min(.5,extent*.15),0,min(.5,extent*.15)]]
        else:continue
        for distance,point in levels:
            key=(row['family_key'],tuple(np.round(point,5)),tuple(np.round(axis,5)))
            if key not in cache:cache[key]=closed_bore(mesh,point,axis)
            radius=cache[key]
            if radius is None or radius<.4:continue
            if key not in slab_cache:slab_cache[key]=source_slab_boundary_radius(mesh,point,axis,.18)
            slab=slab_cache[key]
            if slab['minimum_source_boundary_radius_mm']<.4:
                invalid_core_windows.append(dict(feature_id=f['id'],source_center_mm=point.tolist(),centre_section_radius_mm=radius,
                                                 source_finite_slab=slab,reason='The full proposed cylinder crosses an original source solid boundary such as a blind-hole bottom. A2D cavity centre alone is not a known-empty volume.'))
                continue
            center_radius=radius;radius=min(radius,slab['minimum_source_boundary_radius_mm'])
            # Preserve the measured source bore with 0.10mm radial discretization allowance,
            # not a nominal motor/screw major diameter (TAP pilots are deliberately smaller).
            core.append(dict(feature_id=f['id'],category=f['category'],source_center_mm=point.tolist(),source_axis=axis.tolist(),
                             measured_native_minor_radius_mm=radius,centre_section_minor_radius_mm=center_radius,source_finite_slab=slab,radial_discretization_allowance_mm=.10,
                             required_clear_core_radius_mm=radius-.10,axial_half_window_mm=.18,
                             requirement='Reject model bead-envelope overlap with this known empty native core. Report support beads separately with a proven extraction route; a centreline-only clear result is insufficient.'))
    access=row.get('channel_access')
    if not access:
        access=dict(named_extraction_check=row['support_access_check'],digital_model_opening_check='Check actual supported native ROI against the named opening; no claim that a tree branch is removable from normal/area alone.')
    rows.append(dict(group=row['group'],object_id=row['object_id'],manifest_instance_index=row['manifest_instance_index'],name=name,
                     family_key=row['family_key'],source_stl=row['source_stl'],source_sha256=row['source_sha256'],
                     source_id=row['source_id'],raw_source_to_old_primary_bed4x4=row['raw_source_to_bed4x4'],
                     functional_probe_requirements=seats,known_empty_source_bore_cores=core,invalid_full_core_windows=invalid_core_windows,extraction_access=access,
                     current_pose_decision=row['decision'],physical_quality_not_part_of_digital_file_gate=True))
    print(row['manifest_instance_index'],name,'measured-bore-levels',len(core),flush=True)

result=dict(scope='Per-part digital native interface, source-preservation and accessible-support requirements; physical fit/finish unverified',
            source_audit_sha256=hashlib.sha256((G/'surface-audit.json').read_bytes()).hexdigest(),
            finite_slab_checker_sha256=hashlib.sha256((G/'source_core_slab.py').read_bytes()).hexdigest(),
            instance_count=len(rows),unique_indices=len({r['manifest_instance_index'] for r in rows}),
            acceptance_rules=[
                'Nomination pose must actually remove its sampled bearing/sliding support exposure; old66 four bearing annuli must fail.',
                'All model bead widths and layer heights must be included in known-empty-core tests; centres alone do not clear a bore.',
                'Supported retained interfaces require localized real model/support-interface comparison, not the existence of support somewhere on a part.',
                'Intentional short hole bridges are checked by core preservation and path span/speed, not blanket 100% underside support coverage.',
                'Native supports in a cavity require an opening/path that exists in the preserved source geometry. Actual hand removal and finish remain later measurements.',
            ],instances=rows)
(G/'native-feature-requirements.json').write_text(json.dumps(result,indent=2)+'\n')
assert len(rows)==89 and len({r['manifest_instance_index'] for r in rows})==89
