from pathlib import Path
D=Path(__file__).resolve().parent
exec((D/'check_joint_up_down_pair.py').read_text().split('for k in rows:')[0])
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
p=H/'curved-head/openrb-curved-layout-world.stl';m=tm.load(p,force='mesh');v=m.vertices;f=m.faces
rv=f[:,[0,1,2]].ravel();cv=f[:,[1,2,0]].ravel();graph=coo_matrix((np.ones(len(rv),np.int8),(rv,cv)),shape=(len(v),len(v))).tocsr();count,labels=connected_components(graph,directed=False);fl=labels[f[:,0]];del graph,rv,cv
out=D/'actual-openrb-components';out.mkdir(exist_ok=True);records=[]
for i in [60,66,69,74,82,105,110,114,141]:
 sub=m.submesh([np.where(fl==i)[0]],append=True);rec={'index':i,'watertight':bool(sub.is_watertight),'volumePositive':bool(sub.is_volume),'sourceFaces':int(len(sub.faces))}
 s=mf.Manifold(mf.Mesh64(np.asarray(sub.vertices,np.float64),np.asarray(sub.faces,np.uint64)));rec['manifoldStatus']=str(s.status());rec['hullOverlap']=(rb_parts[str(i)]^sc).volume()
 if sub.is_volume and s.status()==mf.Error.NoError:
  q=s.transform(Tr[:3])^sc;rec['actualOverlap']=q.volume();rec['actualBounds']=list(q.bounding_box()) if q.volume()>0 else None
  dest=out/f'component-{i:04d}.stl';pm.export(ctx,s,dest);rec['mesh']=str(dest);rec['meshSha256']=sha(dest)
 records.append(rec)
r={'source':str(p),'sourceSha256':sha(p),'candidate':'joint-up-down-pair','records':records,'sourceComponentsUnmodified':True}
(out/'micro-contact-proof.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(records,indent=2))
