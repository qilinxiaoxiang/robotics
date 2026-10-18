"""Re-evaluate the three retained cap closure screw sites against restored native shell."""
exec((__import__('pathlib').Path(__file__).parent/'finalize_cap.py').read_text().split('cap=load(')[0])
cap=load(D/'curved-cap-final-candidate-world.stl');mesh=trimesh.load(D/'curved-cap-final-candidate-world.stl');rows=[]
for s in data['screws']:
 if s.get('groupId')!='head_cap_closure':continue
 c=np.array(s['world_center_mm']);d=-np.array(s['world_axis']);t=trimesh.geometry.align_vectors([0,0,1],d);t[:3,3]=c+d*4
 shaft=man(trimesh.creation.cylinder(radius=1.25,height=8,sections=48).apply_transform(t));t[:3,3]=c-d*24
 tool=man(trimesh.creation.cylinder(radius=1.5,height=45,sections=48).apply_transform(t))
 negative={k:hits(tool,dec(k)) for k in P if P[k].get('partKind') not in ['nut','washer'] and k not in ['head_cap','camera_pitch_foot','camera_cradle','camera_board','camera_ribbon','openrb','speaker','amplifier','audio_carrier'] and hits(tool,dec(k))>1e-4}
 obs={k:dec(k) for k in P if k not in ['head_cap','upper_pad','camera_pitch_foot','camera_cradle','camera_board','camera_ribbon','openrb','speaker','amplifier','audio_carrier'] and P[k].get('partKind') not in ['nut','washer']}
 pivot=np.array([26.1,0,118.6146]);R=trimesh.transformations.rotation_matrix(np.deg2rad(30),[0,1,0],pivot)
 for k in ['jaw_frame','lower_pad']:obs[k]=obs[k].transform(R[:3,:])
 h={k:hits(tool,o) for k,o in obs.items() if hits(tool,o)>1e-4}
 loc,_,_=mesh.ray.intersects_location([c+d*.01],[d],multiple_hits=True);zs=sorted(np.dot(loc-c,d).tolist())
 rows.append({'id':s['id'],'axisIntersectionsFromSeatMm':zs,'tappingShaftCapIntersectionMm3':hits(shaft,cap),'closedJawNegativeControlMm3':negative,'requiredState':'jaw and lower pad opened30deg worldY about[26.1,0,118.6146]; upper pad installed after cap fastening','driverIntersectionsMm3':h})
print(json.dumps(rows,indent=2));(D/'cap-fastener-investigation.json').write_text(json.dumps(rows,indent=2)+'\n')
