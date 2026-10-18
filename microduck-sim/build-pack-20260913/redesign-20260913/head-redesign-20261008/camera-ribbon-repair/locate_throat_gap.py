from pathlib import Path
D=Path(__file__).resolve().parent
exec((D/'build_reverse_nut_camera.py').read_text().split('cam=load')[0]);read(D/'build_reverse_nut_camera.py');m=json.loads(read(O/'candidate-manifest.json'));files=m['replacementMeshes']|{q['key']:q['mesh'] for q in m['additionalParts']};cam=load(H/files['camera_board']);housing=cam^box([79.05,-50,100],[95,50,160]);verts=np.array(housing.to_mesh64().vert_properties[:,:3]);rows=[]
for k in ['face_panel','eye_trim']:
 mesh=tm.load(H/files[k],force='mesh');closest,dist,_=tm.proximity.closest_point(mesh,verts);order=np.argsort(dist)[:8];rows.append({'key':k,'points':[{'camera':verts[i].tolist(),'fixed':closest[i].tolist(),'gap':float(dist[i])} for i in order]})
(O/'throat-gap-location.json').write_text(json.dumps(rows,indent=2)+'\n');print(json.dumps(rows,indent=2))
