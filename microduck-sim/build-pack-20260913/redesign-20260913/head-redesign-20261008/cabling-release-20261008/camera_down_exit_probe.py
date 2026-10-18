from check_routes import *
# Test the one untested optical-equivalent orientation:180 around optical+X,
# lens stays fixed and H/V FOV unchanged; this is NOT a ready retainer design.
pivot=[0,-.0913782119751,131.1145957947];T=trimesh.transformations.rotation_matrix(np.pi,[1,0,0],pivot)
camera=meshes['camera_board'].copy().apply_transform(T);ribbon=trimesh.creation.box([.3,16,12]).apply_translation([74.73,-.0913782119751,115.65259552006405])
rows={}
for k,m in [('camera180',camera),('first12mmRibbon180',ribbon)]:
 s=man(m);rows[k]={'boundsMm':m.bounds.tolist(),'intersectionsMm3':check(s,['camera_board','camera_retainer','camera_mount_screws']),'retainerIntersectionsMm3':hits(s,obs['camera_retainer'])}
 m.export(D/(k+'-rejected-probe-world.stl'))
out={'status':'FINITE_OPTICAL_AXIS_180_DEG_PROBE','lensFixed':True,'fieldOfViewAxesUnchanged':True,'ribbonBoundary':'Camera-end16mm-wide by0.3mm-thick receiving strip,12mmstraight below movedmouth; thickness and12mmstraightlead are assumptions, not actual SC1892 stiffness specification.','transform':T.tolist(),'rows':rows,'accepted':False,'sourceHashes':hashes};(D/'camera-down-exit-probe.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(rows,indent=2))
