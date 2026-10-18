"""Combine frozen head CAD with trunk CAD and preserve all replacement accounting."""
from pathlib import Path
import copy,json
import numpy as np,trimesh
P=Path(__file__).resolve().parent;W=P.parent

def from_mesh(path,mass,body,ident):
    mesh=trimesh.load(path,force='mesh');mesh.apply_scale(.001)
    assert mesh.volume>0,(ident,mesh.volume)
    return dict(id=ident,body=body,mass_kg=mass,position_m=mesh.center_mass.tolist(),
      inertia_about_com_kg_m2=(mesh.moment_inertia*(mass/mesh.volume)).tolist(),
      inertia_basis='Uniform mesh density approximation with specified total mass; electronic mass distribution is not a measured inertia.')

if __name__=='__main__':
    h=json.loads((W/'electrical/head-layout/final/head-mesh-mass-manifest.json').read_text())
    geom=json.loads((P/'new-geometry.json').read_text());geom['remove_meshes']+=h['remove_original_geoms']
    mass=copy.deepcopy(json.loads((W/'assembly/compact-battery/component-body-masses.json').read_text())['parts'])
    colors={'head_cap':[.91,.73,.28,1],'audio_carrier':[.3,.38,.45,1],
      'openrb':[.12,.38,.2,1],'camera_module3_wide':[.15,.26,.21,1],
      'camera_cradle':[.2,.27,.35,1],'camera_pitch_foot':[.2,.27,.35,1],
      'amp':[.12,.42,.28,1],'speaker':[.17,.17,.2,1]}
    for part in h['pieces']:
        if part['id'] in ['pi_retained','head_fasteners']:continue
        visual=part['mesh_file']
        if part['id']=='openrb':
            # MuJoCo's binary STL decoder caps one file at 200,000 triangles.
            # OBJ preserves every triangle without simplifying the manufacturer CAD.
            visual=str(P/'openrb-visual.obj');trimesh.load(part['mesh_file'],force='mesh').export(visual)
        geom['parts'].append(dict(body='jaw_soft',mesh=visual,rgba=colors[part['id']]))
        mass.append(from_mesh(part['mesh_file'],part['mass_g']/1000,'jaw_soft',part['id']))
    old=next(x for x in h['removed_original_references'] if x['id']=='top_head_shell')
    mass.append(from_mesh(old['mesh_file'],-old['mass_g']/1000,'jaw_soft','old-head-shell-remove'))
    mass += [dict(id='head-fasteners',body='jaw_soft',mass_kg=.0118,position_m=[.03,0,-.025],dimensions_m=[.04,.06,.06]),
             dict(id='head-wires',body='jaw_soft',mass_kg=.004,position_m=[.02,0,-.025],dimensions_m=[.04,.06,.06]),
             dict(id='trunk-wires-hardware',body='trunk_base',mass_kg=.025,position_m=[-.02,0,0],dimensions_m=[.04,.04,.07]),
             dict(id='imu-and-holder',body='trunk_base',mass_kg=.0075,position_m=[-.057,0,.015],dimensions_m=[.013,.036,.031])]
    for name,color in [('imu_clamp_holder_body',[.4,.45,.5,1]),('imu_rear_cover_body',[.4,.45,.5,1]),('imu_28x25x8_envelope_body',[.08,.3,.4,1])]:
        geom['parts'].append(dict(body='trunk_base',mesh=str(W/f'assembly/trunk-imu/{name}.stl'),rgba=color))
    # The four original electronics are included in lumped inertia. Remove 0/15/30g,
    # explicitly distributing that unknown mass as an assumption, never as a measurement.
    old_shares={'lens':.25,'elec_rpi_robot_hat_pcb':.45,'m12_lens_holder':.15,'speaker':.15}
    (P/'full-geometry.json').write_text(json.dumps(geom,indent=2))
    (P/'full-mass-base.json').write_text(json.dumps({'parts':mass,'unknown_old_electronics_mass_shares':old_shares},indent=2))
    base=json.loads((P/'compact-prototype.config.json').read_text())
    base.update(duration=30,heading_hold=True,geometry_manifest=str(P/'full-geometry.json'),mass_manifest=str(P/'full-mass-base.json'),mass_parts=[])
    jobs=[]
    for battery_removed in [0,60,120]:
        for electronics_removed in [0,15,30]:
            c=copy.deepcopy(base);c.update(name=f'full-oldbattery{battery_removed}-oldelectronics{electronics_removed}',remove_old_battery_kg=battery_removed/1000)
            for old in h['removed_original_references']:
                if old['id'] in old_shares and electronics_removed:
                    c['mass_parts'].append(from_mesh(old['mesh_file'],-electronics_removed/1000*old_shares[old['id']],'jaw_soft','remove-'+old['id']))
            jobs.append(c)
    import concurrent.futures
    from run_compact_suite import execute
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(execute,jobs))
    (P/'full-assembly-summary.json').write_text(json.dumps({'cases':results},indent=2))
    print(json.dumps([{'name':r.get('config',{}).get('name',r.get('name')),**{k:r.get(k) for k in ['error','mass_kg','fell','walking_gate_pass','mean_forward_velocity_m_s','max_abs_heading_deviation_deg']}} for r in results],indent=2))
