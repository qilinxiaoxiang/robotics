from pathlib import Path
import json,gc
import unify_amp_cap as u
u.require_classification();u.core.guarded_import();c=u.core
native=u.load(u.NATIVE);base=u.load(u.BASE);old,speaker=u.old_amp_features(native);raw=base-old;rows=[]
for mode in ['original-simplify','tolerance-simplify']:
 s=raw.as_original().simplify(.00003) if mode=='original-simplify' else raw.set_tolerance(.00003).simplify(.00003)
 q=s.to_mesh();mesh=c.tm.Trimesh(q.vert_properties[:,:3],q.tri_verts,process=True);row={'mode':mode,'watertight':mesh.is_watertight,'triangles':len(mesh.faces),'degenerateFaces':int((~mesh.nondegenerate_faces()).sum())}
 if mesh.is_watertight:
  out=u.OUT/f'retire-{mode}-candidate.stl';mesh.export(out);m=u.load(out);removed=base-m;row.update(nativeSkinRemovedMm3=u.vol(removed^native),speakerRemovedMm3=u.vol(removed^speaker),unexpectedRemovedMm3=u.vol(removed-old),addedMm3=u.vol(m-base),readbackStatus=str(m.status()))
 rows.append(row);del s,q,mesh;gc.collect()
c.atomic_json(u.OUT/'retire-serialization2-diagnostic.json',{'rows':rows,'sourceHashes':u.inputs([Path(__file__)]),'integrationReady':False});print(json.dumps(rows))
