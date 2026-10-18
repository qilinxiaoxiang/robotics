from check_routes import *
# Recover exact current cap except *only* two amp mounting columns; preserve original
# curved shell wherever a removal cylinder overlaps it. No exterior edits.
cap=obs['head_cap'];native=man(load(H/'curved-head/community-curved-head-world.stl'));holes=[[26.6500006104,-17.287000885],[39.3500006104,-17.287000885]]
old_columns=mf.Manifold.batch_boolean([mf.Manifold.cylinder(28,2.01,circular_segments=64).translate([x,y,133.5849994]) for x,y in holes],mf.OpType.Add)
base=cap-(old_columns-native);rows=[]
for angle in [90,-90,180]:
 T=trimesh.transformations.rotation_matrix(np.deg2rad(angle),[0,0,1],[33,-24,138]);m=meshes['amplifier'].copy().apply_transform(T);s=man(m)
 hh=check(s,['amplifier','head_cap','curved_cap_hardware']);hh['capWithoutAmpColumns']=hits(s,base);hh={k:v for k,v in hh.items() if v>1e-5}
 # Fixed initial cable receiving stems6mm along transformed outward terminal Y.
 exits=np.array([[31.2,-14.203,138.5],[34.7,-14.203,138.5]]);exits=trimesh.transform_points(exits,T);axis=T[:3,:3]@np.array([0,1,0]);stems=[]
 for p in exits:
  t=tube([p,p+axis*6],.75);h=check(t,['amplifier','head_cap','curved_cap_hardware']);v=hits(t,base)
  if v>1e-5:h['capWithoutAmpColumns']=v
  stems.append(h)
 rows.append({'angleDegrees':angle,'transform':T.tolist(),'amplifierIntersectionsMm3':hh,'terminalStemIntersectionsMm3':stems,'terminalExits':exits.tolist(),'outwardAxis':axis.tolist()})
 if not hh and not any(stems):m.export(D/f'amplifier-rotated-{angle}-candidate-world.stl')
report={'changesPublished':False,'rows':rows,'sourceHashes':hashes};(D/'amp-reorientation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(rows,indent=2))
