from pathlib import Path
OUT=Path(__file__).resolve().parent;D=OUT.parent
exec((D/'pack_populated_boards.py').read_text().split('pikeys=')[0].replace('D=Path(__file__).resolve().parent;R=', 'D=Path(__file__).resolve().parent.parent;R='))
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
reportfile=OUT/'report.json';report=json.loads(reportfile.read_text());delta=np.array(report['currentOpenRBWorldToCandidate']);ob=source('torso_base');p=H/'curved-head/openrb-curved-layout-world.stl';m=tm.load(p,force='mesh');v=m.vertices;f=m.faces
rv=f[:,[0,1,2]].ravel();cv=f[:,[1,2,0]].ravel();graph=coo_matrix((np.ones(len(rv),np.int8),(rv,cv)),shape=(len(v),len(v))).tocsr();count,labels=connected_components(graph,directed=False);fl=labels[f[:,0]];del graph,rv,cv
records=[]
for i in [14,90]:
 sub=m.submesh([np.where(fl==i)[0]],append=True);s=mf.Manifold(mf.Mesh64(np.asarray(sub.vertices,np.float64),np.asarray(sub.faces,np.uint64)));r={'component':i,'sourceFaces':len(sub.faces),'watertight':bool(sub.is_watertight),'volumePositive':bool(sub.is_volume),'status':str(s.status())}
 if s.status()==mf.Error.NoError and sub.is_volume:
  q=s.transform(delta[:3])^ob;r['actualIntersectionMm3']=q.volume();r['intersectionBounds']=list(q.bounding_box()) if q.volume()>0 else None
 records.append(r)
out={'source':str(p),'sourceSha256':sha(p),'reportSha256':sha(reportfile),'records':records,'sourceUnmodified':True};(OUT/'actual-header-to-torso.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
