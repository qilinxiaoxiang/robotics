from pathlib import Path
import json,gc
import unify_amp_cap as u
u.require_classification();u.core.guarded_import();c=u.core
native=u.load(u.NATIVE);base=u.load(u.BASE);old,speaker=u.old_amp_features(native);after=base-old;rows=[]
for precision in ['64','32']:
 q=after.to_mesh64() if precision=='64' else after.to_mesh()
 mesh=c.tm.Trimesh(q.vert_properties[:,:3],q.tri_verts,process=True)
 row={'precision':precision,'vertices':len(mesh.vertices),'faces':len(mesh.faces),'watertight':mesh.is_watertight,'windingConsistent':mesh.is_winding_consistent,'degenerateFaces':int((~mesh.nondegenerate_faces()).sum()),'duplicateFaces':len(mesh.faces)-len(mesh.unique_faces())}
 # Remove only geometrically degenerate or exact duplicate triangles created
 # when representable STL float32 coordinates coincide. Never fill a hole.
 mesh.update_faces(mesh.nondegenerate_faces());mesh.update_faces(mesh.unique_faces());mesh.remove_unreferenced_vertices()
 row['afterDroppingZeroAreaDuplicateFacesWatertight']=mesh.is_watertight
 if mesh.is_watertight:
  out=u.OUT/f'retire-serialization-{precision}-candidate.stl';mesh.export(out);read=c.tm.load(out,force='mesh');row['stlReadbackWatertight']=read.is_watertight
  m=c.mf.Manifold(c.mf.Mesh(c.np.asarray(read.vertices,c.np.float32),c.np.asarray(read.faces,c.np.uint32)));row['status']=str(m.status())
  if m.status()==c.mf.Error.NoError:
   removed=base-m;row['nativeSkinRemovedMm3']=u.vol(removed^native);row['speakerRemovedMm3']=u.vol(removed^speaker);row['unexpectedRemovedMm3']=u.vol(removed-old);row['addedMm3']=u.vol(m-base)
 rows.append(row);del q,mesh;gc.collect()
u.core.atomic_json(u.OUT/'retire-serialization-diagnostic.json',{'rows':rows,'sourceHashes':u.inputs([Path(__file__)]),'integrationReady':False});print(json.dumps(rows))
