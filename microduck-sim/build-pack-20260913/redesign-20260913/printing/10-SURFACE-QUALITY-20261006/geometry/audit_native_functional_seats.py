"""Localized actual model/support footprint readback at named functional mesh probes.

Support is queried below the actual first model bead bottom, rather than assuming
the configured gap is the manufactured gap or counting support anywhere on a part.
An explicit short-bridge exception is bounded by native segment span and speed.
"""
from pathlib import Path
import argparse,hashlib,json,re,sys
import numpy as np
import audit_surfaces as a
from native_material_frame import material_frame_paths
from native_anchor_paths import local_native_anchor
from audit_native_bore_envelopes import identify_ids

G=Path(__file__).resolve().parent;sys.path.insert(0,str(G.parent/'slicing'))
from audit_surface_paths import read_code,parse,number

def layer_segments(paths):
    starts=[];ends=[];width=[];height=[];kind=[];speed=[];length=[]
    for p in paths:
        if any(word in p['kind'].lower() for word in ['skirt','brim']):continue
        for u,v in zip(p['points'],p['points'][1:]):
            starts.append(u);ends.append(v);width.append(p['width']);height.append(p['height']);kind.append(p['kind']);speed.append(p['speed']);length.append(p['length'])
    return dict(p0=np.array(starts),p1=np.array(ends),w=np.array(width),h=np.array(height),kind=np.array(kind),speed=np.array(speed),length=np.array(length))

def footprint_hit(layer,point,mask,extra_allowance=0.0):
    if not len(layer['p0']):return []
    idx=np.flatnonzero(mask)
    if not len(idx):return []
    start=layer['p0'][idx];step=layer['p1'][idx]-start;denom=np.einsum('ij,ij->i',step,step)
    t=np.zeros(len(idx));nz=denom>1e-15;t[nz]=np.einsum('ij,ij->i',point-start[nz],step[nz])/denom[nz];t=np.clip(t,0,1)
    distance=np.linalg.norm(start+t[:,None]*step-point,axis=1)
    hit=distance<=layer['w'][idx]/2+.025+np.sqrt(2)*.0005+extra_allowance
    return [(int(i),float(d)) for i,d in zip(idx[hit],distance[hit])]

def measure(project,gcode,group,printer,selected_object_ids=None):
    geometry=json.loads((G/'surface-audit.json').read_text());rows=[r for r in geometry['instances'] if r['group']==group]
    if selected_object_ids:rows=[r for r in rows if r['object_id'] in selected_object_ids]
    selected_indices={r['manifest_instance_index'] for r in json.loads((G/'nominations.json').read_text())['pose_candidates']}
    actual={r['object_id']:r for r in a.load_project(project)};ids=identify_ids(project)
    code,cfg,fh,gh=read_code(gcode,project,printer);paths,_,_=parse(code,collect_all=True);output=[];errors=[]
    paths,material_offset=material_frame_paths(paths,cfg,code)
    configured_gap=number(cfg.get('support_top_z_distance'),.2);normal_layer=number(cfg.get('layer_height'),.2)
    first_height=number(cfg.get('initial_layer_print_height'),.2);bed_xy_compensation=number(cfg.get('elefant_foot_compensation'),0.)
    job_support={}
    for material_layers in paths.values():
        for z,material_paths in material_layers.items():
            job_support.setdefault(z,[]).extend(p for p in material_paths if 'support' in p['kind'].lower())
    for row in rows:
        oid=row['object_id'];name=row['name']
        if oid not in actual:errors.append('Missing requested object '+oid);continue
        labels=[k for k in paths if k.split('_id_')[0]==name]
        if len(labels)>1:labels=[k for k in labels if re.search('_id_'+re.escape(str(ids[oid]))+'(?:_|$)',k)]
        if len(labels)!=1:errors.append('Unresolved native identity '+oid);continue
        item=actual[oid];local,W,_,_=item['components'][0];info=a.source_info(name,local)
        rawchild=np.eye(4);rawchild[:3,:3],rawchild[:3,3]=info['raw_to_child'];currentraw=W@rawchild
        delta=currentraw@np.linalg.inv(np.array(row['raw_source_to_bed4x4']))
        features=a.transformed_features(row['critical_surface_probes_bed_mm'],delta)
        local_model={z:[p for p in entries if 'support' not in p['kind'].lower()] for z,entries in paths[labels[0]].items()}
        layers={z:layer_segments(local_model.get(z,[])+job_support.get(z,[])) for z in set(local_model)|set(job_support)};measured=[]
        for feature in features:
            points=np.array(feature['points']);normals=np.array(feature['normals']);probes=[]
            for point,normal in zip(points,normals):
                downward=bool(normal[2]<-.70710678);candidates=[]
                for z,layer in layers.items():
                    if abs(z-point[2])>normal_layer+.35:continue
                    model=np.array(['support' not in kind.lower() for kind in layer['kind']])
                    first_layer_allowance=bed_xy_compensation if abs(point[2])<=.025 and z<=first_height+.025 else 0.0
                    for index,dist in footprint_hit(layer,point[:2],model,first_layer_allowance):
                        bottom=z-layer['h'][index]
                        if bottom-.10<=point[2]<=z+.10:
                            candidates.append(dict(z=z,bottom=float(bottom),height=float(layer['h'][index]),kind=str(layer['kind'][index]),
                                                   path_span_mm=float(layer['length'][index]),speed_mm_s=float(layer['speed'][index]),native_segment_index=int(index),
                                                   xy_centerline_distance_mm=dist,width=float(layer['w'][index]),first_layer_nominal_xy_compensation_mm=float(first_layer_allowance)))
                model=min(candidates,key=lambda p:p['bottom']) if candidates else None
                evidence=[];self_support=[]
                if model and downward:
                    for z,layer in layers.items():
                        gap=model['bottom']-z
                        if -.025<=gap<=configured_gap+normal_layer+.05:
                            mask=np.array(['support interface' in kind.lower() for kind in layer['kind']])
                            for index,dist in footprint_hit(layer,point[:2],mask):
                                evidence.append(dict(actual_support_top_z_mm=z,actual_gap_to_model_bottom_mm=float(gap),
                                                     interface_width_mm=float(layer['w'][index]),xy_distance_to_interface_centerline_mm=dist))
                        if -.025<=gap<=.075:
                            mask=np.array(['support' not in kind.lower() for kind in layer['kind']])
                            for index,dist in footprint_hit(layer,point[:2],mask):
                                self_support.append(dict(previous_model_top_z_mm=z,gap_mm=float(gap),xy_distance_to_model_centerline_mm=dist))
                # A short bridge across a screw clearance is intentional only at a
                # screw-bearing feature, bounded by whole native path span and speed.
                short_bridge=bool(model and feature['category'] in ['horn','case','rear_center','electronics_printed_mount','blind_pilot_mouth']
                                  and 'bridge' in model['kind'].lower() and model['path_span_mm']<=4.0 and model['speed_mm_s']<=30.01)
                bed_support=bool(model and abs(model['bottom'])<=.025)
                local_anchor=local_native_anchor(layers,model,point,configured_gap,normal_layer) if model and downward and not bed_support and not evidence and not self_support else None
                supported=bool(not downward or bed_support or evidence or self_support or short_bridge or (local_anchor and (local_anchor['direct_model_bead_overlap'] or local_anchor['two_sided_bounded_span'])))
                probes.append(dict(mesh_probe_mm=point.tolist(),mesh_normal=normal.tolist(),requires_underneath_support=downward,
                                   actual_model_bead=model,actual_support_interfaces=evidence,previous_model_support=self_support,
                                   bed_support=bed_support,local_native_anchor=local_anchor,bounded_short_hole_bridge=short_bridge,digital_support_explanation_present=supported))
            valid=sum(p['actual_model_bead'] is not None for p in probes);down=sum(p['requires_underneath_support'] for p in probes)
            selected_quality_target=row['manifest_instance_index'] in selected_indices
            support_contact_quality_risk=sum(p['requires_underneath_support'] and not p['bed_support'] for p in probes) if selected_quality_target else 0
            explained=sum(p['requires_underneath_support'] and p['actual_model_bead'] is not None and p['digital_support_explanation_present'] for p in probes)
            unexplained=[p for p in probes if p['requires_underneath_support'] and p['actual_model_bead'] is not None and not p['digital_support_explanation_present']]
            measured.append(dict(id=feature['id'],category=feature['category'],spec=feature['spec'],sample_count=len(probes),
                                 model_footprint_present_samples=valid,downward_samples=down,explained_downward_samples=explained,
                                 selected_pose_quality_target=selected_quality_target,selected_quality_target_downward_nonbed_samples=support_contact_quality_risk,
                                 unexplained_downward_samples=len(unexplained),probes=probes,
                                 no_direct_mesh_bearing_sample=not bool(probes),native_roi_evidence_complete=(not probes or valid>=max(1,len(probes)*.75)) and not unexplained and not support_contact_quality_risk))
        output.append(dict(object_id=oid,manifest_instance_index=row['manifest_instance_index'],name=name,native_label=labels[0],
                           functions=measured,digital_roi_evidence_complete=all(f['native_roi_evidence_complete'] for f in measured),
                           physical_flatness_and_finish_verified=False))
        print(printer,group,oid,name,'features',len(measured),'incomplete',[(f['id'],f['model_footprint_present_samples'],f['unexplained_downward_samples']) for f in measured if not f['native_roi_evidence_complete']],flush=True)
    return dict(passed=not errors and len(output)==len(rows) and all(r['digital_roi_evidence_complete'] for r in output),errors=errors,
                project=str(Path(project).resolve()),gcode=str(Path(gcode).resolve()),printer=printer,group=group,
                source_geometry_audit_sha256=hashlib.sha256((G/'surface-audit.json').read_bytes()).hexdigest(),
                project_sha256=hashlib.sha256(Path(project).read_bytes()).hexdigest(),file_sha256=fh,gcode_sha256=gh,
                commanded_xy_to_material_xy_offset_mm=material_offset,
                requested_object_ids=sorted(selected_object_ids) if selected_object_ids else None,objects=output,
                method='Actual width-aware 2D segment capsule footprints with0.025mm surface-discretization plus native0.001mm XY rounding bound at real model bead bottom Z; support top Z and gap measured from emitted model bead, direct bed and adjacent-model support distinguished; emitted job-wide support footprints checked regardless of ownership scope; nominal bed-face samples account only for the declared first-layer elephant-foot compensation; empty bearing records explicitly indicate no direct mesh seat, with bore checks separate; local >=0.10mm bead-overlap anchors are measured in emitted footprints; a connected <=4mm span at <=30mm/s requires real >=0.40mm native anchors at both ends. Exact point gaps between support stripes alone are not failures.',
                criterion='At least75% of sparse source-probe points require real nearby model footprint and no modeled downward probe may have unexplained support/bridge span. This is a finite digital ROI check, not full-area finish or physical acceptance.',
                physical_fit_verified=False,physical_surface_quality_verified=False)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--project',required=True);p.add_argument('--gcode',required=True);p.add_argument('--group',required=True)
    p.add_argument('--printer',choices=['Elegoo','Bambu'],default='Elegoo');p.add_argument('--object-id',action='append');p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    result=measure(args.project,args.gcode,args.group,args.printer,set(args.object_id) if args.object_id else None)
    args.output.write_text(json.dumps(result,indent=2)+'\n');print('FUNCTIONAL_ROI_PASS' if result['passed'] else 'FUNCTIONAL_ROI_HOLD');sys.exit(0 if result['passed'] else 1)
