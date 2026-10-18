"""Actual native model/support bead-envelope readback in measured empty source bores.

This checks segment capsules using the G-code's actual width and height. It does
not infer full hole clearance from empty extrusion centreline samples.
Usage: python audit_native_bore_envelopes.py --project P --gcode G --group GROUP
       --printer Elegoo|Bambu --output OUTPUT
"""
from pathlib import Path
import argparse, hashlib, json, re, sys, zipfile, xml.etree.ElementTree as E
import numpy as np
from scipy.optimize import minimize_scalar, minimize
import audit_surfaces as a
from native_material_frame import material_frame_paths

G=Path(__file__).resolve().parent;S=G.parent/'slicing'
sys.path.insert(0,str(S))
from audit_surface_paths import read_code,parse
N=a.N

def identify_ids(project):
    # Emitted `_id_N_copy_0` is the native ModelObject ordinal, not the persisted
    # model_settings identify_id. Bind ordinal to actual build sequence; the
    # exact printed name is separately mandatory in both native audits.
    with zipfile.ZipFile(project) as z:root=E.fromstring(z.read('3D/3dmodel.model'))
    return {item.get('objectid'):str(index) for index,item in enumerate(root.find(a.N+'build'))}

def segments(layers, include_arc_error=False):
    starts=[];ends=[];widths=[];heights=[];kinds=[];arc_errors=[]
    for z,paths in layers.items():
        for p in paths:
            if any(word in p['kind'].lower() for word in ['brim','skirt']):continue
            zz=z-p['height']/2
            points=np.array(p['points']);arc_radius=None;fit_residual=0.0
            if len(points)>2:
                xy=points[:,:2]-points[:,:2].mean(axis=0)
                coefficients=np.linalg.lstsq(np.c_[2*xy,np.ones(len(xy))],np.sum(xy*xy,axis=1),rcond=None)[0]
                rr=coefficients[2]+sum(coefficients[:2]**2)
                if rr>0:
                    radius=float(np.sqrt(rr));residual=np.max(abs(np.linalg.norm(xy-coefficients[:2],axis=1)-radius))
                    if residual<.002:arc_radius=radius;fit_residual=float(residual)
            for first,last in zip(p['points'],p['points'][1:]):
                chord=np.linalg.norm(np.array(first[:2])-np.array(last[:2]))
                arc_errors.append(0.0 if len(points)==2 else (.025 if arc_radius is None else arc_radius-np.sqrt(max(0,arc_radius**2-chord**2/4))+fit_residual+1e-6))
                starts.append([first[0],first[1],zz]);ends.append([last[0],last[1],zz]);widths.append(p['width']);heights.append(p['height']);kinds.append(p['kind'])
    result=(np.array(starts),np.array(ends),np.array(widths),np.array(heights),np.array(kinds))
    return result+(np.array(arc_errors),) if include_arc_error else result

def envelope_intersections(p0,p1,width,height,axis,center,radius,window,arc_error=None,kinds=None):
    """Conservative cylinder overlap, with exact segment closest projection.

    XY capsule radius=w/2, layer slab half-height=h/2. Projection support functions
    provide a lower radial-distance bound. Extra .025mm accounts for G2/G3
    polyline discretization, never a substitute for actual bead width.
    """
    tolerance=np.full(len(width),.025) if arc_error is None else arc_error
    rounded=(width>=height) if kinds is not None else np.zeros(len(width),dtype=bool)
    if kinds is not None:rounded &= np.array(['bridge' not in k.lower() for k in kinds])
    def padding(unit,ww,hh,tol,rr):
        box=ww/2*np.linalg.norm(unit[...,:2],axis=-1)+hh/2*np.abs(unit[...,2])+tol
        stadium=np.maximum(0,ww-hh)/2*np.linalg.norm(unit[...,:2],axis=-1)+hh/2+tol
        return np.where(rr,stadium,box)
    d0=p0-center;step=p1-p0;ax0=d0@axis;axstep=step@axis
    axpad=padding(axis,width,height,tolerance,rounded)
    low=-window-axpad;high=window+axpad
    feasible=(np.minimum(ax0,ax0+axstep)<=high)&(np.maximum(ax0,ax0+axstep)>=low)
    idx=np.flatnonzero(feasible)
    if not len(idx):return idx,np.empty(0),np.empty((0,3))
    dd0=d0[idx];ss=step[idx];ax=ax0[idx];ad=axstep[idx]
    tlo=np.zeros(len(idx));thi=np.ones(len(idx));moving=abs(ad)>1e-10
    aa=np.zeros(len(idx));bb=np.zeros(len(idx));aa[moving]=(low[idx][moving]-ax[moving])/ad[moving];bb[moving]=(high[idx][moving]-ax[moving])/ad[moving]
    tlo[moving]=np.maximum(0,np.minimum(aa[moving],bb[moving]));thi[moving]=np.minimum(1,np.maximum(aa[moving],bb[moving]))
    radial0=dd0-ax[:,None]*axis;radstep=ss-ad[:,None]*axis
    denom=np.einsum('ij,ij->i',radstep,radstep);t=np.zeros(len(idx));nz=denom>1e-15
    t[nz]=-np.einsum('ij,ij->i',radial0[nz],radstep[nz])/denom[nz];t=np.clip(t,tlo,thi)
    vector=radial0+t[:,None]*radstep;rho=np.linalg.norm(vector,axis=1);unit=np.zeros_like(vector);valid=rho>1e-10;unit[valid]=vector[valid]/rho[valid,None]
    radial_pad=padding(unit,width[idx],height[idx],tolerance[idx],rounded[idx])
    radial_pad[~valid]=width[idx][~valid]/2+height[idx][~valid]/2+tolerance[idx][~valid]
    margin=rho-radial_pad-radius
    # Any unit plane normal perpendicular to the core axis supplies a rigorous
    # separating lower bound for the full projected convex bead+segment body.
    # Optimize only model candidates; a positive plane bound certifies clearance
    # even when subtracting the radial support at the centreline closest point
    # was too pessimistic. The finite axial window is deliberately omitted here:
    # separation from the infinite cylinder also separates its finite section.
    if kinds is not None:
        basis0=np.cross(axis,[1,0,0] if abs(axis[0])<.8 else [0,1,0]);basis0/=np.linalg.norm(basis0)
        basis1=np.cross(axis,basis0)
        for ii in np.flatnonzero(margin<.001):
            segment_index=idx[ii]
            if 'support' in kinds[segment_index].lower():continue
            def plane(theta):
                u=basis0*np.cos(theta)+basis1*np.sin(theta)
                return min(float(u@d0[segment_index]),float(u@(d0[segment_index]+step[segment_index])))-float(padding(u,width[segment_index],height[segment_index],tolerance[segment_index],rounded[segment_index]))
            angles=np.arange(64)*2*np.pi/64;scores=np.array([plane(x) for x in angles]);best=int(np.argmax(scores));theta=angles[best]
            optimized=minimize_scalar(lambda t:-plane(t),bounds=(theta-2*np.pi/64,theta+2*np.pi/64),method='bounded',options={'xatol':1e-12})
            # Recompute the selected separating plane's support directly; this
            # acceptance is a certified inequality, not optimizer convergence.
            certificate=plane(float(optimized.x))-radius
            margin[ii]=max(margin[ii],certificate)
            if margin[ii]<.001:
                def finite_plane(parameters):
                    theta,phi=parameters
                    u=(basis0*np.cos(theta)+basis1*np.sin(theta))*np.cos(phi)+axis*np.sin(phi)
                    native_lower=min(float(u@d0[segment_index]),float(u@(d0[segment_index]+step[segment_index])))-float(padding(u,width[segment_index],height[segment_index],tolerance[segment_index],rounded[segment_index]))
                    cylinder_upper=radius*np.linalg.norm(u-axis*float(u@axis))+window*abs(float(u@axis))
                    return native_lower-cylinder_upper
                finite=minimize(lambda params:-finite_plane(params),np.array([optimized.x,0.]),method='Powell',bounds=[(optimized.x-.8,optimized.x+.8),(-1.45,1.45)],options={'xtol':1e-10,'ftol':1e-12,'maxiter':100})
                margin[ii]=max(margin[ii],finite_plane(finite.x))
    overlap=margin<-.001
    return idx[overlap],margin,p0[idx]+t[:,None]*ss

def audit(project,gcode,group,printer,selected_object_ids=None):
    req=json.loads((G/'native-feature-requirements.json').read_text());requirements=[r for r in req['instances'] if r['group']==group]
    if selected_object_ids:requirements=[r for r in requirements if r['object_id'] in selected_object_ids]
    actual={m['object_id']:m for m in a.load_project(project)};ids=identify_ids(project)
    code,cfg,filehash,gchash=read_code(gcode,project,printer);paths,_,_=parse(code,collect_all=True)
    paths,material_offset=material_frame_paths(paths,cfg,code)
    job_support={}
    for material_layers in paths.values():
        for z,entries in material_layers.items():
            job_support.setdefault(z,[]).extend(p for p in entries if 'support' in p['kind'].lower())
    output=[];errors=[]
    for r in requirements:
        oid=r['object_id'];name=r['name']
        if oid not in actual:errors.append('Missing requested object '+oid+' '+name);continue
        item=actual[oid]
        labels=[k for k in paths if k.split('_id_')[0]==name]
        if len(labels)>1:labels=[k for k in labels if re.search('_id_'+re.escape(str(ids[oid]))+'(?:_|$)',k)]
        if len(labels)!=1:errors.append('Cannot resolve exact native instance '+oid+' '+name);continue
        model_layers={z:[p for p in entries if 'support' not in p['kind'].lower()]+job_support.get(z,[]) for z,entries in paths[labels[0]].items()}
        for z,entries in job_support.items():
            if z not in model_layers:model_layers[z]=entries
        p0,p1,width,height,kinds,arc_error=segments(model_layers,include_arc_error=True)
        if not len(p0):errors.append('No positive native extrusion for '+oid);continue
        local,W,_,_=item['components'][0];info=a.source_info(name,local);raw_child=np.eye(4)
        raw_child[:3,:3],raw_child[:3,3]=info['raw_to_child'];raw_bed=W@raw_child
        features=[]
        for core in r['known_empty_source_bore_cores']:
            axis=raw_bed[:3,:3]@np.array(core['source_axis']);axis/=np.linalg.norm(axis)
            center=(raw_bed@np.r_[core['source_center_mm'],1])[:3]
            overlap,margin,nearest=envelope_intersections(p0,p1,width,height,axis,center,core['required_clear_core_radius_mm'],core['axial_half_window_mm'],arc_error,kinds)
            found=kinds[overlap];model=[int(i) for i in overlap if 'support' not in kinds[i].lower()];support=[int(i) for i in overlap if 'support' in kinds[i].lower()]
            rawmesh=info['raw'];c=np.array(core['source_center_mm']);sourceaxis=np.array(core['source_axis']);escape=[]
            for sign in [-1,1]:
                hit=a.ray_first(rawmesh,c,sourceaxis*sign)
                escape.append(dict(direction=sign,unobstructed_axis_to_outside=hit is None,
                                   first_source_solid_distance_mm=None if hit is None else float(np.linalg.norm(hit[0]-c))))
            features.append(dict(feature_id=core['feature_id'],category=core['category'],source_center_mm=core['source_center_mm'],
                                 measured_native_minor_radius_mm=core['measured_native_minor_radius_mm'],tested_core_radius_mm=core['required_clear_core_radius_mm'],
                                 model_bead_overlap_segment_count=len(model),support_bead_overlap_segment_count=len(support),
                                 minimum_conservative_bead_margin_mm=float(margin.min()) if len(margin) else None,
                                 overlapping_model_features=sorted(set(kinds[model])) if model else [],
                                 overlapping_support_features=sorted(set(kinds[support])) if support else [],
                                 native_model_core_clear=not model,source_axial_escape=escape,
                                 support_has_open_axial_route=not support or any(e['unobstructed_axis_to_outside'] for e in escape),
                                 physical_bore_roundness_verified=False))
        model_clear=all(f['native_model_core_clear'] for f in features)
        open_support=all(f['support_has_open_axial_route'] for f in features)
        output.append(dict(object_id=oid,manifest_instance_index=r['manifest_instance_index'],name=name,native_label=labels[0],
                           known_empty_core_levels=len(features),model_bead_cores_clear=model_clear,support_in_core_has_open_axial_source_route=open_support,
                           features=features,source_raw_to_bed4x4=raw_bed.tolist()))
        print(printer,group,oid,name,'known levels',len(features),'model-clear',model_clear,'support-route',open_support,flush=True)
    return dict(passed=not errors and len(output)==len(requirements) and all(o['model_bead_cores_clear'] and o['support_in_core_has_open_axial_source_route'] for o in output),
                errors=errors,printer=printer,group=group,project=str(Path(project).resolve()),gcode=str(Path(gcode).resolve()),
                project_sha256=hashlib.sha256(Path(project).read_bytes()).hexdigest(),file_sha256=filehash,gcode_sha256=gchash,
                requirement_sha256=hashlib.sha256((G/'native-feature-requirements.json').read_bytes()).hexdigest(),
                commanded_xy_to_material_xy_offset_mm=material_offset,
                requested_object_ids=sorted(selected_object_ids) if selected_object_ids else None,requested_object_count=len(requirements),
                acceptance_scope='Explicit subset only; not full group/package acceptance' if selected_object_ids else 'Full named printer/group',
                bead_profile_primary_source='https://raw.githubusercontent.com/SoftFever/OrcaSlicer/v2.4.2/src/libslic3r/Flow.cpp#L219-L225',
                bead_profile_source_sha256=hashlib.sha256((G/'OrcaSlicer-v2.4.2-Flow.cpp').read_bytes()).hexdigest(),
                method='Exact closest projection of native extrusion segments onto measured source-core cylinders; actual G-code bead widths and layer heights, ordinary bead bounded by XY disk radius(w-h)/2 Minkowski sphere radius h/2, from native rounded-stadium profile; bridges or w<h keep XY capsule/Z slab bound. Actual fitted arc sagitta plus measured circle-fit residual and1e-6mm numerical tolerance; straight lines exact. Potential model overlaps additionally use a maximized exact support-function separating plane for the full segment+bead against the source-core cylinder, including its finite axial window for near-boundary cases. A positive separation is certified directly, independent of optimizer convergence. All emitted job-wide support beads are included regardless of object ownership scope. No centreline-only acceptance.',
                caveat='A conservative overlap is a digital hold requiring a closer slice/geometry check. A clear bound preserves only the measured core, not a physical full-diameter fit. An open axial source route does not prove intact tree-support removal.',
                physical_fit_verified=False,physical_surface_finish_verified=False,objects=output)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--project',required=True);p.add_argument('--gcode',required=True);p.add_argument('--group',required=True)
    p.add_argument('--printer',choices=['Elegoo','Bambu'],default='Elegoo');p.add_argument('--output',type=Path,required=True)
    p.add_argument('--object-id',action='append',help='Explicit bounded experiment subset; never full group acceptance');args=p.parse_args()
    result=audit(args.project,args.gcode,args.group,args.printer,set(args.object_id) if args.object_id else None);args.output.write_text(json.dumps(result,indent=2)+'\n');print('NATIVE_BORE_ENVELOPE_PASS' if result['passed'] else 'NATIVE_BORE_ENVELOPE_HOLD');sys.exit(0 if result['passed'] else 1)
