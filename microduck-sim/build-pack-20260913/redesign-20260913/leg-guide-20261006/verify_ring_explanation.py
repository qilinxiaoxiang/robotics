"""Read-only source/assembly check of the small ankle ring's two interfaces.

verify() returns a dictionary and writes nothing. CLI prints the evidence marker;
--output can save a caller-owned JSON report. No CAD changes or motion tests.
"""
from pathlib import Path
import argparse,hashlib,json,sys
import numpy as np
import trimesh
from shapely.geometry import Polygon,LineString
from shapely.ops import polygonize,unary_union

HERE=Path(__file__).resolve().parent;SIM=HERE.parents[2]
ASSEMBLY=SIM/'build-pack-20260913/assembly'
FKPATH=SIM/'hardware-design-20260912/whole-robot-20260912/assembly'
sys.path.insert(0,str(FKPATH))
from assembly_fk import fk,raw,XML

sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()

def source_loader():
    namespace={'__file__':str(ASSEMBLY/'prepare_geometry.py')}
    exec((ASSEMBLY/'prepare_geometry.py').read_text().split('rows=[]')[0],namespace)
    return namespace

def ray_first(mesh,origin,direction):
    triangle=mesh.triangles;e1=triangle[:,1]-triangle[:,0];e2=triangle[:,2]-triangle[:,0]
    h=np.cross(direction,e2);det=np.einsum('ij,ij->i',e1,h);okay=abs(det)>1e-9
    f=np.divide(1.,det,out=np.zeros(len(det)),where=okay);s=origin-triangle[:,0]
    u=f*np.einsum('ij,ij->i',s,h);q=np.cross(s,e1);v=f*np.einsum('j,ij->i',direction,q);t=f*np.einsum('ij,ij->i',e2,q)
    okay &= (u>=-1e-7)&(v>=-1e-7)&(u+v<=1+1e-7)&(t>1e-7)
    indices=np.flatnonzero(okay)
    if not len(indices):return None
    return origin+float(t[indices].min())*direction

def radial_profile(mesh,z,start_radius=None,count=64):
    result=[];origin=np.array([0.,0.,z])
    for angle in np.arange(count)*2*np.pi/count:
        direction=np.array([np.cos(angle),np.sin(angle),0.])
        point=ray_first(mesh,origin if start_radius is None else origin+start_radius*direction,
                        direction if start_radius is None else -direction)
        result.append(None if point is None else float((point-origin)@direction))
    known=[r for r in result if r is not None]
    return dict(axial_z_mm=z,radii_mm=result,min_radius_mm=min(known) if known else None,
                max_radius_mm=max(known) if known else None,mean_radius_mm=float(np.mean(known)) if known else None,
                complete_64_directions=len(known)==count)

def material_section(mesh,z):
    cut=mesh.section(plane_origin=[0,0,z],plane_normal=[0,0,1])
    if cut is None:return Polygon()
    lines=[LineString(np.array(line)[:,:2]) for line in cut.discrete]
    regions=list(polygonize(unary_union(lines)));material=[]
    for region in regions:
        point=region.representative_point()
        if mesh.contains(np.array([[point.x,point.y,z]]))[0]:material.append(region)
    return unary_union(material)

def verify():
    ns=source_loader();guide=json.loads((HERE/'leg-data.json').read_text());parts={p['key']:p for p in guide['parts']}
    errors=[]
    for key,expected in [('smallring',62),('ankle',66),('lower',30)]:
        if parts[key]['sourceId']!=expected:errors.append('Guide source identity changed: '+key)
    native={key:ns['mesh']('3D/3dmodel.model',str(parts[key]['sourceId'])) for key in ['smallring','ankle','lower']}
    ring=native['smallring'];world={key:mesh.copy().apply_transform(np.array(parts[key]['sourceTransformWorld'])) for key,mesh in native.items()}
    ring_frame=np.array(parts['smallring']['sourceTransformWorld']);local={k:m.copy().apply_transform(np.linalg.inv(ring_frame)) for k,m in world.items()}
    ring_center=world['smallring'].bounds.mean(axis=0)
    ring_axis=ring_frame[:3,:3]@np.array([0,0,1.]);ring_axis/=np.linalg.norm(ring_axis)
    profiles=dict(ring_inner=radial_profile(local['smallring'],0),ring_outer=radial_profile(local['smallring'],0,12),
                  link_boss_outer=radial_profile(local['lower'],1.,12),link_boss_hole=radial_profile(local['lower'],1.),
                  ankle_pocket_inner=radial_profile(local['ankle'],0),ankle_outer_side_lip=radial_profile(local['ankle'],1.75))
    axes_order=np.argsort(ring.extents);ring_od=float(ring.extents[axes_order[-1]]);ring_width=float(ring.extents[axes_order[0]])
    smallring_components=len(ring.split(only_watertight=False));sections=[]
    for z in [-1.4,0,1.2]:
        shapes={k:material_section(mesh,z) for k,mesh in local.items()}
        sections.append(dict(axial_z_mm=z,ring_area_mm2=float(shapes['smallring'].area),
                             ring_link_native_material_overlap_mm2=float(shapes['smallring'].intersection(shapes['lower']).area),
                             ring_ankle_native_material_overlap_mm2=float(shapes['smallring'].intersection(shapes['ankle']).area)))
    _,geoms=fk();original_ring=next(g for g in geoms if g['body']=='ankle_left' and g['mesh']=='seeed_bearing__configuration_default')
    reference_ring=raw(original_ring['mesh']).apply_transform(original_ring['world']);reference_local=reference_ring.copy().apply_transform(np.linalg.inv(ring_frame))
    original_center=reference_ring.bounds.mean(axis=0);center_error=float(np.linalg.norm(original_center-ring_center))
    reference_profiles=dict(middle_inner=radial_profile(reference_local,0),middle_outer=radial_profile(reference_local,0,12),
                            near_end_inner=radial_profile(reference_local,1.49),near_end_outer=radial_profile(reference_local,1.49,12))
    ri=profiles['ring_inner'];bo=profiles['link_boss_outer'];ro=profiles['ring_outer'];po=profiles['ankle_pocket_inner']
    inner_interference=[b-r for b,r in zip(bo['radii_mm'],ri['radii_mm'])]
    outer_gap=[p-r for p,r in zip(po['radii_mm'],ro['radii_mm'])]
    metrics=dict(ring_outer_diameter_mm=ring_od,ring_width_mm=ring_width,
                 ring_inner_effective_diameter_range_mm=[2*ri['min_radius_mm'],2*ri['max_radius_mm']],
                 link_boss_effective_diameter_range_mm=[2*bo['min_radius_mm'],2*bo['max_radius_mm']],
                 link_centre_hole_diameter_range_mm=[2*profiles['link_boss_hole']['min_radius_mm'],2*profiles['link_boss_hole']['max_radius_mm']],
                 ankle_pocket_effective_diameter_range_mm=[2*po['min_radius_mm'],2*po['max_radius_mm']],
                 native_ring_to_link_radial_interference_range_mm=[min(inner_interference),max(inner_interference)],
                 native_ring_to_ankle_radial_clearance_range_mm=[min(outer_gap),max(outer_gap)],
                 guide_original_fk_ring_centre_error_mm=center_error,plain_annular_solid_count=smallring_components,
                 ring_watertight=bool(ring.is_watertight),ring_euler_number=int(ring.euler_number),ring_volume_mm3=float(ring.volume))
    shoulder_point=ray_first(local['ankle'],np.array([7.2,0,0]),np.array([0,0,1.]))
    axial_contact=dict(ring_positive_end_z_mm=1.5,ankle_shoulder_at_radius7_2_mm=None if shoulder_point is None else shoulder_point.tolist(),
                       outer_side_lip_z_mm=1.75,lip_section_has_64_circular_hits=profiles['ankle_outer_side_lip']['complete_64_directions'])
    tests=[('ring outside diameter14.6',14.59<=ring_od<=14.61),('ring width3',2.99<=ring_width<=3.01),
           ('ring measured bore9.65',9.63<=2*ri['min_radius_mm'] and 2*ri['max_radius_mm']<=9.67),
           ('link actual circular boss10',9.97<=2*bo['min_radius_mm'] and 2*bo['max_radius_mm']<=10.03),
           ('ankle pocket15',14.96<=2*po['min_radius_mm'] and 2*po['max_radius_mm']<=15.03),
           ('ring has one plain annular solid',smallring_components==1 and ring.is_watertight and ring.euler_number==0),
           ('native inner ring/link interference is real',min(inner_interference)>.15),
           ('native outer ring/ankle clearance exists',min(outer_gap)>.17),
           ('guide registration matches original FK centre',center_error<.01),
           ('full material sections show inner interference, no outer overlap',all(s['ring_link_native_material_overlap_mm2']>5 and s['ring_ankle_native_material_overlap_mm2']<1e-6 for s in sections)),
           ('uniform full annular cross-section',max(s['ring_area_mm2'] for s in sections)-min(s['ring_area_mm2'] for s in sections)<1e-6)]
    errors.extend(name for name,passed in tests if not passed)
    files=[ns['SOURCE'],HERE/'leg-data.json',ASSEMBLY/'community-print-inventory.json',ASSEMBLY/'source-surface-refinement.json',XML,
           FKPATH/'assembly_fk.py',Path(__file__),SIM/'microduck_rl/src/mjlab_microduck/robot/microduck/assets/seeed_bearing__configuration_default.stl',
           SIM/'Microduck-build-tutorial/README.md']
    return dict(passed=not errors,errors=errors,problem='P5',checked='2026-10-06',metrics=metrics,
                checks=[dict(name=n,passed=bool(p)) for n,p in tests],profiles=profiles,material_cross_sections=sections,axial_contact=axial_contact,
                reference_ring_profiles=reference_profiles,ring_centre_world_mm=ring_center.tolist(),ring_axis_world=ring_axis.tolist(),
                reference_ring_centre_world_mm=original_center.tolist(),input_sha256={str(p):sha(p) for p in files},
                known_geometry='Printed source62 is a single full annular sleeve. Its inner diameter interferes with the fixed link boss; its outer circumference is clear of the orange ankle pocket before physical deformation.',
                engineering_inference='If the sleeve stays on the link, ankle motion must slide at the outer sleeve/pocket interface. A merged link+sleeve outer bearing surface could in principle provide the same relative rotation, but this is not an accepted redesign.',
                author_statement_boundary='No explicit reason for the separate printed sleeve was found in the checked FanGe README or upstream project README. XML body ownership and the bearing part name do not establish which material interface slides, or prove a rolling-bearing mechanism in the original hardware.',
                physical_fit_verified=False,installed_sleeve_expansion_verified=False,actual_relative_motion_verified=False)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path);args=parser.parse_args();report=verify()
    if args.output:args.output.write_text(json.dumps(report,indent=2)+'\n')
    print('RING_INTERFACE_CHECK_PASS' if report['passed'] else 'RING_INTERFACE_CHECK_FAIL')
    print(json.dumps(dict(passed=report['passed'],errors=report['errors'],metrics=report['metrics']),indent=2))
    sys.exit(0 if report['passed'] else 1)
