#!/usr/bin/env python3
"""Read frozen CAD; compare six print directions; export rigid STL copies.
No CAD edits, native slicing, printer communication or physical acceptance.
The cheek export is explicitly an orientation trial, not a settled recommendation.
"""
from pathlib import Path
import ast,base64,hashlib,json
import numpy as np
import trimesh
O=Path(__file__).resolve().parent
ROTATIONS={
 'local_positive_Z_down':np.diag([1,-1,-1]),'local_negative_Z_down':np.eye(3),
 'local_positive_X_down':np.array([[0,0,1],[0,1,0],[-1,0,0]]),
 'local_negative_X_down':np.array([[0,0,-1],[0,1,0],[1,0,0]]),
 'local_positive_Y_down':np.array([[1,0,0],[0,0,1],[0,-1,0]]),
 'local_negative_Y_down':np.array([[1,0,0],[0,0,-1],[0,1,0]])}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):return json.loads(Path(p).read_text())
def read_stl(path):
 raw=trimesh.load(path,force='mesh',process=False)
 vertices,inverse=np.unique(np.asarray(raw.vertices,dtype='<f4'),axis=0,return_inverse=True)
 return trimesh.Trimesh(vertices,inverse[raw.faces],process=False)
def canonical_triangles(m):
 a=np.asarray(m.triangles,dtype='<f4');idx=np.lexsort((a[:,:,2],a[:,:,1],a[:,:,0]),axis=1)
 a=np.take_along_axis(a,idx[:,:,None],axis=1).reshape(-1,9);idx=np.lexsort(tuple(a[:,i]for i in range(8,-1,-1)))
 return hashlib.sha256(np.ascontiguousarray(a[idx]).tobytes()).hexdigest()
def pose_metrics(mesh,rotation):
 v=mesh.vertices@rotation.T;v[:,2]-=v[:,2].min();n=mesh.face_normals@rotation.T;tri=v[mesh.faces]
 onbed=tri[:,:,2].max(axis=1)<.0001;down=(n[:,2]<-np.sqrt(.5))&(tri[:,:,2].min(axis=1)>.4)
 q={'rotation3x3':rotation.tolist(),'contact_flat_triangles_area_mm2':float(mesh.area_faces[onbed].sum()),'down_45_above_0p4mm_area_mm2':float(mesh.area_faces[down].sum()),'max_build_height_mm':float(v[:,2].max())}
 posed=trimesh.Trimesh(v,mesh.faces,process=False)
 for z in [.05,.2]:
  s=posed.section(plane_origin=[0,0,z],plane_normal=[0,0,1]);ps=s.to_2D()[0].polygons_full if s else[]
  q[f'model_section_area_at_{z}_mm2']=float(sum(p.area for p in ps));q[f'model_section_islands_at_{z}']=len(ps)
 return q

def run():
 report=load(O/'print-review.json');manifest=load(O/'preview-data.json');D=load(O.parent/'leg-guide-20261006/full-build-data.json');params={}
 for node in ast.walk(ast.parse((O/'generate_candidate.py').read_text())):
  if isinstance(node,ast.Assign):
   for t in node.targets:
    if isinstance(t,ast.Name)and t.id in ['SPLIT','LUGS','PEGS']:params[t.id]=ast.literal_eval(node.value)
 assert params['PEGS']==[], 'This review is for compact transverse-bolt/open-slot v6; round-peg versions need separate review.'
 paths=[Path(p[k])for s in manifest['sides'].values()for p in s['parts']if 'localStl'in p for k in ['localStl','stl']];frozen={str(p):sha(p)for p in paths};out=[]
 (O/'PRINT-STL').mkdir(exist_ok=True)
 for side in ['left','right']:
  T=np.asarray(manifest['sides'][side]['frameWorld'])
  for part in manifest['sides'][side]['parts']:
   if 'localStl'not in part:continue
   path=Path(part['localStl']);m=read_stl(path);kind=part['key'].split('_')[-1];wm=read_stl(part['stl']);mapped=m.copy().apply_transform(T)
   assert m.is_watertight and len(m.split(only_watertight=False))==1 and m.volume>0
   assert abs(m.volume-wm.volume)<.003 and np.max(np.abs(mapped.bounds-wm.bounds))<.00002
   r={'key':part['key'],'file':str(path),'sha256':frozen[str(path)],'world_file':part['stl'],'world_sha256':frozen[part['stl']],'color':part['color'],'watertight':True,'components':1,'volume_mm3':float(m.volume),'bounds':m.bounds.tolist(),'overall_dimensions_mm':m.extents.tolist(),'print_orientation_candidates':[],'functional_surfaces':[]}
   for name,rotation in ROTATIONS.items():
    q=pose_metrics(m,rotation);q['orientation']=name
    q['output_or_lip_normal_z']=float((rotation@[0,0,-1])[2]);q['transverse_cap_head_normal_z']=float((rotation@[0,1,0])[2])
    r['print_orientation_candidates'].append(q)
   if kind=='base':
    selected='local_positive_X_down'if side=='left'else'local_negative_X_down'
    r['recommended_orientation']=selected;r['orientation_status']='Geometry-supported starting orientation; native horizontal-hole/support checks pending'
    r['orientation_reason']='Actual broad side facet lands as one first-layer model island. Original output seats and large motor-contact plane are vertical, rather than support-facing. The passive full ring pocket belongs to the separate cheek; remaining horizontal bores need native checks.'
   elif kind=='cheek':
    selected='local_positive_Z_down';r['recommended_orientation']=None;r['orientation_status']='Orientation trial only; no settled recommended print orientation'
    r['orientation_reason']='Trial keeps the capture lip upward and full ring pocket vertical, but starts on two tab pads with the main exterior plane4.1mm or more above bed. Side-X alternatives have one small contact pad and horizontal14/15mm pocket ceilings. Native paths and physical finish must select the tradeoff.'
   else:
    selected='local_negative_Z_down';r['recommended_orientation']=selected;r['orientation_status']='Axial starting orientation supported by geometry; native and physical fit unverified';r['orientation_reason']='Broad annular bed face, vertical bore, no downward45-degree region above0.4mm.'
   r['selected_geometry_orientation']=selected;rotation=ROTATIONS[selected]
   if kind=='base':
    prefix='S06-horn'if side=='left'else'S01-horn';probes=[]
    for c in D['screws']:
     if c['id'].startswith(prefix):
      p=(np.linalg.inv(T)@[*c['world_center_mm'],1])[:3]
      probes.extend([p+[1.6*np.cos(a),1.6*np.sin(a),-.02]for a in np.linspace(0,2*np.pi,8,endpoint=False)])
    a=np.asarray(probes);hits,ri,fi=m.ray.intersects_location(a,np.tile([0,0,1],(32,1)),multiple_hits=False)
    assert len(ri)==32 and np.max(np.abs(hits[:,2]-a[ri,2]-.02))<.001 and np.max(m.face_normals[fi,2])<-.99
    r['functional_surfaces'].append({'category':'original_four_output_screw_seats','verified_stl_samples':32,'local_normal':[0,0,-1],'selected_print_normal':(rotation@[0,0,-1]).tolist(),'support_facing':False})
    z=-30.70007 if side=='left'else -30.69907;mask=(np.abs(m.triangles_center[:,2]-z)<.002)&(m.face_normals[:,2]>.99999)
    r['functional_surfaces'].append({'category':'motor_case_contact_face','actual_planar_area_mm2':float(m.area_faces[mask].sum()),'local_normal':[0,0,1],'selected_print_normal':(rotation@[0,0,1]).tolist(),'support_facing':False,'note':'Was downward in+Z pose; now vertical. This is a mesh-normal finding, not native print quality.'})
    # Exact central aperture: rays in the active plate section, independent of names.
    dirs=np.array([[np.cos(a),np.sin(a),0]for a in np.linspace(0,2*np.pi,64,endpoint=False)]);orig=np.tile([0,0,-31.5],(64,1))
    hit,ri,fi=m.ray.intersects_location(orig,dirs,multiple_hits=False);assert len(ri)==64
    rr=np.linalg.norm(hit[:,:2],axis=1);r['active_plate_central_aperture_diameter_range_mm']=[float(2*rr.min()),float(2*rr.max())]
    r['native_bore_checks_required']=['Original output/horn bores and measured central aperture now horizontal','NewØ1.6mm transverse blind TAP pilot ceiling','Open-slot guide: actual bead dimensions and access']
   if kind=='cheek':
    z=1.49993 if side=='left'else 1.50093;mask=(np.abs(m.triangles_center[:,2]-z)<.002)&(m.face_normals[:,2]<-.99999)
    r['functional_surfaces'].append({'category':'inside_axial_capture_lip','actual_planar_area_mm2':float(m.area_faces[mask].sum()),'local_normal':[0,0,-1],'selected_print_normal':(rotation@[0,0,-1]).tolist(),'support_facing':False})
    origins=np.array([[x+1.6*np.cos(a),6.02,4.5+1.6*np.sin(a)]for x,_ in params['LUGS']for a in np.linspace(0,2*np.pi,8,endpoint=False)])
    hit,ri,fi=m.ray.intersects_location(origins,np.tile([0,-1,0],(16,1)),multiple_hits=False)
    assert len(ri)==16 and np.max(np.abs(hit[:,1]-6))<1e-5 and np.min(m.face_normals[fi,1])>.99
    r['functional_surfaces'].append({'category':'new_transverse_cap_screw_head_seats','verified_stl_samples':16,'local_y_mm':6,'local_normal':[0,1,0],'selected_print_normal':(rotation@[0,1,0]).tolist(),'support_facing':False,'on_bed':False,'note':'Vertical bearing face in trial+Z print; the horizontalØ2.3mm clearance bore has a separate downward ceiling.'})
    r['round_pegs_present']=False;r['native_bore_checks_required']=['Ø2.3mm transverse clearance-hole ceilings','Side-X trials: full14/15mm ring-pocket ceiling and bearing-wall finish','+Z trial: main exterior face above supports and two separated first-layer pads']
    r['main_exterior_plane_height_above_bed_in_trial_mm']=float(m.bounds[1,2]-3.)
   if kind=='sleeve':
    dirs=np.array([[np.cos(a),np.sin(a),0]for a in np.linspace(0,2*np.pi,64,endpoint=False)]);hit,ri,fi=m.ray.intersects_location(np.zeros((64,3)),dirs,multiple_hits=True);rays={i:sorted(np.linalg.norm(hit[ri==i,:2],axis=1))for i in range(64)};assert all(len(v)==2 for v in rays.values())
    r['dimensions_measured']={'bore_diameter_mm':[float(2*min(v[0]for v in rays.values())),float(2*max(v[0]for v in rays.values()))],'outer_diameter_mm':[float(2*min(v[1]for v in rays.values())),float(2*max(v[1]for v in rays.values()))],'radial_wall_at_midplane_mm':[float(min(v[1]-v[0]for v in rays.values())),float(max(v[1]-v[0]for v in rays.values()))],'width_mm':float(m.extents[2]),'end_flat_inner_radius_mm':5.4,'end_flat_outer_radius_mm':7.1,'axial_chamfer_mm':.2}
   transform=np.eye(4);transform[:3,:3]=rotation;posed=m.copy().apply_transform(transform);transform[:2,3]=-posed.bounds[:,:2].mean(axis=0);transform[2,3]=-posed.bounds[0,2];posed=m.copy().apply_transform(transform)
   dest=O/'PRINT-STL'/f'{side}-{kind}-PRINT.stl';posed.export(dest);rb=read_stl(dest);th=canonical_triangles(posed)
   assert rb.is_watertight and len(rb.split(only_watertight=False))==1 and abs(rb.volume-m.volume)<.003 and abs(rb.bounds[0,2])<1e-5 and np.max(np.abs(rb.bounds[:,:2].mean(axis=0)))<1e-5 and th==canonical_triangles(rb)
   r['print_export']={'file':str(dest),'sha256':sha(dest),'sourceLocalToPrint4x4':transform.tolist(),'bounds':rb.bounds.tolist(),'volume_mm3':float(rb.volume),'bed_min_z_mm':float(rb.bounds[0,2]),'xy_bbox_center_mm':rb.bounds[:,:2].mean(axis=0).tolist(),'rigid_only':True,'exact_float32_triangle_identity_sha256':th,'orientation_trial_only':kind=='cheek','native_slice_verified':False};out.append(r)
 assert frozen=={str(p):sha(p)for p in paths},'Source changed during measurement'
 previous=report.get('candidate_reviews',[])
 if previous and any(a['sha256']!=b['sha256']for a,b in zip(previous,out)):report.setdefault('historical_candidate_reviews',[]).extend(previous)
 report.update(candidate_reviews=out,review_state='Compact v6 source/export geometry PASS; base/sleeve starting poses, cheek orientation trials only',print_geometry_review_passed=False,source_geometry_readback_passed=True,rigid_print_export_passed=True,recommended_orientations_settled=False,print_ready=False,native_slice_verified=False,source_stl_hashes=frozen,source_parameter_snapshot=params,candidate_generator_sha256=sha(O/'generate_candidate.py'),candidate_manifest_sha256_at_review=sha(O/'preview-data.json'),print_preparation_script_sha256=sha(__file__),full_build_data_sha256=sha(O.parent/'leg-guide-20261006/full-build-data.json'))
 report.pop('known_support_facing_functional_surface',None)
 report['fit_coupon']={'decision':'No separate generic coupon produced; actual small sleeve is the proposed future local fit sample','printed_sample_verified':False,'orientation':'Actual selected sleeve axial orientation; guide/cheek need separate physical fit checks'}
 report['coupon_decision']='Geometry frozen; no generic coupon CAD added. A future physical trial can use the actual sleeve, followed by the actual open guide/cheek; no printing performed.'
 report['prototype_limits']={'mechanism':'Compact transverseY screws, open tongue/slot guides; no round pegs','guide_tongue_width_x_mm':2.,'guide_slot_width_x_mm':2.2,'nominal_guide_side_clearance_x_mm':.1,'guide_width_physical_fit_verified':False,'pilot_post_width_x_mm':4.,'nominal_pilot_diameter_mm':1.6,'nominal_X_wall_each_side_mm':1.2,'estimated_X_wall_after_nominal_M2_external_thread_mm':1.,'thread_geometry_modeled':False,'two_sliding_radial_clearances_can_sum_mm':.4,'axial_lip_flat_ring_end_overlap_radial_mm':.1,'no_load_or_torque_rating':True}
 report['measurement_method']={'rotation_candidates':6,'bed_contact_triangle_tolerance_mm':.0001,'geometric_section_heights_above_bed_mm':[.05,.2],'downward_proxy_normal_z_threshold':-float(np.sqrt(.5)),'downward_proxy_exclude_bottom_height_mm':.4,'output_headseat_probe_count_per_ankle':32,'cap_headseat_probe_count_per_ankle':16,'sleeve_radial_ray_directions':64,'section_is_native_extrusion':False,'support_proxy_is_native_support':False}
 report['envelope_comparison']={}
 for side,key in [('left','ankle'),('right','right_ankle')]:
  T=np.asarray(manifest['sides'][side]['frameWorld']);p=next(p for p in D['parts']if p['key']==key);v=np.frombuffer(base64.b64decode(p['positionB64']),dtype='<f4').reshape(-1,3);v=(v-T[:3,3])@T[:3,:3];a=np.array([v.min(axis=0),v.max(axis=0)]);items=[r for r in out if r['key'].startswith(side+'_')and not r['key'].endswith('sleeve')];b=np.array([np.min([r['bounds'][0]for r in items],axis=0),np.max([r['bounds'][1]for r in items],axis=0)])
  report['envelope_comparison'][side]={'original_whole_ankle_dimensions_mm':(a[1]-a[0]).tolist(),'candidate_base_cheek_dimensions_mm':(b[1]-b[0]).tolist(),'dimension_change_mm':((b[1]-b[0])-(a[1]-a[0])).tolist(),'local_axis_world_directions':T[:3,:3].tolist(),'motor_axis_edited_by_exporter':False}
 report['required_native_checks']=['Base side-X: horizontal output/screw/central aperture bores, transverse pilot ceilings, first layer and support access','Cheek+Z trial: two bed islands, main exterior plane4.1mm abovebed, real support/finish; all transverse clearance ceilings','Cheek side-X alternatives: bearing-pocket ceiling/support removal/finish; not accepted from lower global overhang area','Guide dimensions, actual bead envelopes, full footprint/spacing and native real thumbnails before any printer-file handoff']
 (O/'print-review.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');write_markdown(report)
 print('ANKLE_PRINT_STL_EXPORT_CHECK_PASS: six exact rigid oriented copies; no native slice or physical claim')
 print('ANKLE_PRINT_ORIENTATION_TRIALS_REMAIN: cheeks have no settled recommended print orientation')
 for r in out:
  q=next(p for p in r['print_orientation_candidates']if p['orientation']==r['selected_geometry_orientation']);print(r['key'],r['selected_geometry_orientation'],round(q['contact_flat_triangles_area_mm2'],3),q['model_section_islands_at_0.2'],r['print_export']['sha256'])
 return report

def write_markdown(report):
 text=['# Ankle redesign: print-facing review','','Problems P5/P6. All six source solids and six rigid-oriented exports pass geometry/hash readback. **The cheeks have no settled recommended print orientation.** Their exported+Z pose is a trial only. No native sliced plate, printed fit, load rating or commissioning is accepted. No slicer or printer was operated.','','## Source identity and orientation','','The files in `PRINT-STL/` contain proper rigid rotation/translation only, with bottomZ0 and XY bounding-box centre0. Exact matrices, source/output hashes and float32 triangle identity are in [print-review.json](print-review.json). Local/world files remain assembly/evidence CAD. Orange base/cheek and black sleeve are retained.','']
 for r in report['candidate_reviews']:
  q=next(p for p in r['print_orientation_candidates']if p['orientation']==r['selected_geometry_orientation']);tag='TRIAL ONLY'if r['recommended_orientation']is None else'geometric starting pose'
  text.append(f"- **{r['key']} — {tag}**: {r['selected_geometry_orientation']}; flat contact{q['contact_flat_triangles_area_mm2']:.2f}mm², model-only section0.2mm abovebed{q['model_section_area_at_0.2_mm2']:.2f}mm²/{q['model_section_islands_at_0.2']}island(s). [{Path(r['print_export']['file']).name}]({r['print_export']['file']})")
 text.extend(['','Those areas are mesh sections, not actual extruded first layers or adhesion evidence. Six cardinal directions were compared on both real side meshes. There is no universal minimum bed-contact area.','','## Why these starting poses, and why the cheek remains a trial','','The left base+X and right base−X poses land an actual81.14mm² side facet as a single island. The four output seats and399.17mm² inner motor-contact plane become vertical;32 native-schedule output-seat probes per side verify the preserved surfaces. This avoids placing the large motor face above support. It creates horizontal original output/central bores and the newØ1.6mm transverse pilots, which need actual native roof/bridge and clear-bore checks. A vertical face finding is not a native quality result.','','A base+Z pose would begin on only49.8mm²/two post pads with the original split face8.7mm above bed. That is not the old broad split-face contact, and is not selected. ±Y directions have tiny or nonplanar first contact; the oppositeX direction lacks the designed planar facet.','','Cheek+Z keeps its22.75mm² inside capture lip upward and ring pocket vertical, while both new transverse screw head seats are vertical (16 STL probes per side). But it starts on57.6mm²/two tab pads, with the old main exterior plane4.1mm abovebed and other surfaces above support. Cheek±X has only21.8mm²/one pad and introduces horizontal14/15mm bearing-pocket ceilings. Cheek−Z gives a better contact island but turns the capture lip downward. The lower global overhang area of a side pose cannot accept a rough sliding bore. **No cheek pose is declared a settled print recommendation:** native support/bridge paths and an actual sample must select this tradeoff.','','The black sleeve has a broad66.76mm² annular bed face with its bore vertical; the geometric0.2mm section is82.47mm²/one island and no downward45°region lies above0.4mm. This axial starting pose avoids a sideways sliding bore.',''])
 for side,e in report['envelope_comparison'].items():
  a=e['original_whole_ankle_dimensions_mm'];b=e['candidate_base_cheek_dimensions_mm'];delta=e['dimension_change_mm']
  text.append(f"- **{side} bracket envelope, local axes**: source{a[0]:.2f}×{a[1]:.2f}×{a[2]:.2f}mm → candidate{b[0]:.2f}×{b[1]:.2f}×{b[2]:.2f}mm; axis changes{delta[0]:+.2f}/{delta[1]:+.2f}/{delta[2]:+.2f}mm. Coordinate directions are recorded explicitly; this is not a load or gait-clearance rating.")
 text.extend(['','## Fit, existing hardware and process limits','','The actual sleeve is ID10.39987–10.40000mm, OD14.59982–14.60000mm, width2.8mm, with approximately2.10mm radial wall. It is a plain floating bushing: both inner and outer interfaces can slide. Roughly0.2mm radial clearance on each can combine to approximately0.4mm radial play; stiffness, wear and installed fit remain physical questions. Its end chamfer leaves the flat end at radius7.1mm against a lip beginning near radius7mm, only about0.1mm flat radial overlap. The larger middle diameter still gives geometric capture, not a contact-pressure rating.','','The final mechanism has transverseY M2×8TAP screws and open tongue/slot guides, **no round pegs**. TongueX width2mm in a2.2mm channel has only0.1mm nominal clearance per side and still needs its own printed fit check. The pilot post has4mm X width around a1.6mm pilot:1.2mm nominal radialX wall, roughly1mm after forming a nominalM2 external thread. That last value is an engineering estimate because real threads are not modeled. The retained4-wall setting cannot establish four complete lines in every thin rail or a verified tightening torque. Use the final mechanical report for actual screw heads, engagement, tip margin and access; ordinary machine screws do not become TAP screws by diameter alone. No missing-stock or purchasing need is inferred.','','Keep the known orange/black ordinary PLA context. The earlier0.4mm-nozzle/0.2mm-layer profile with4walls and30%infill is only a source starting point. [Prusa design guidance](https://help.prusa3d.com/article/modeling-with-3d-printing-in-mind_164135) supports choosing layer/face direction deliberately and testing actual fits, with no universal tolerance. [PLA guidance](https://help.prusa3d.com/article/pla_2062) does not certify this joint’s clamp load, fatigue, temperature resistance or wear.','','No generic coupon was produced. If a later print trial is requested, the actual small sleeve in its final orientation is the useful local fit sample; test inner and outer fits independently, then the open guide/cap before using screw force to close the assembly. Do not infer guide fit from the sleeve’s larger clearance. Native layer coverage, support extraction, hole/guide bead envelopes, full plate footprint and real thumbnails are still required by [the printing workflow](../printing/WORKFLOW.md). The old photograph’s rough downward screw seats remain a regression; surface quality has not been proven by this new CAD or its animation.'])
 (O/'print-review.md').write_text('\n'.join(text)+'\n')

if __name__=='__main__':run()
