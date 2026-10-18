from pathlib import Path
import os,json,hashlib,zipfile,xml.etree.ElementTree as E
assert os.environ.get('MICRODUCK_BOUNDED_CAD')=='1'
import numpy as np,trimesh as tm
from shapely.geometry import Polygon
from shapely.ops import unary_union
D=Path(__file__).resolve().parent;H=D.parents[1];R=H.parent;P=R/'printing/12-REPAIR-V1-20261008';ori=json.loads((P/'orientation-preparation.json').read_text());compare=json.loads((D/'contact-comparison.json').read_text());Q='{http://schemas.microsoft.com/3dmanufacturing/core/2015/02}';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();out=[]
for key,color in [('head_bottom','Yellow'),('head_cap','Orange')]:
 row=next(r for r in ori['parts']if r['key']==key);test=next(r for r in compare['rows']if r['key']==key);p=(R/row['source']).resolve();mesh=tm.load(p,force='mesh');old=np.array(row['printTransform']);n=np.array(test['maximumDownwardOutwardNormalWorld']);oldnormal=old[:3,:3]@n;delta=tm.geometry.align_vectors(oldnormal,[0,0,-1])[:3,:3];newrot=delta@old[:3,:3];verts=mesh.vertices@newrot.T;bb=np.array([verts.min(axis=0),verts.max(axis=0)]);new=np.eye(4);new[:3,:3]=newrot;new[:3,3]=[-bb[:,0].mean(),-bb[:,1].mean(),-bb[0,2]];pv=mesh.vertices@newrot.T+new[:3,3];atbed=np.all(pv[mesh.faces,:,][...,2]<=.01000001,axis=1);polys=[Polygon(v[:,:2])for v in pv[mesh.faces[atbed]]];union=unary_union(polys)
 project=P/'delivery-V1.3'/color/(color+'_V1.3_editable.3mf')
 with zipfile.ZipFile(project)as z:
  model=E.fromstring(z.read('3D/3dmodel.model'));obj=next(o for o in model.find(Q+'resources')if o.get('name')==key);item=next(i for i in model.find(Q+'build')if i.get('objectid')==obj.get('id'));a=np.array(list(map(float,item.get('transform').split()))).reshape(4,3).T;oldbuild=np.eye(4);oldbuild[:3]=a
 # Convert pretransformed mesh coordinates in delivered3MF into new local pose;
 # entire compound object's supportblockers share this same rigid transform.
 rel=new@np.linalg.inv(old);build=oldbuild@rel
 out.append({'key':key,'color':color,'sourceMesh':str(p),'sourceSha256':sha(p),'sourceProject':str(project),'sourceProjectSha256':sha(project),'objectId':obj.get('id'),'selectedOutwardNormalWorld':n.tolist(),'worldToPrintTransform':new.tolist(),'relativeToExistingObjectMesh':rel.tolist(),'candidateBuildTransform':' '.join(format(float(v),'.15g')for v in build[:3].T.reshape(-1)),'keepOtherInstancesInitially':True,'nativeFootprintPackingMustRecheck':True,'allChildSupportBlockersFollowSameTransform':True,'modelMaterialRemovedMm3':0,'contactToleranceMm':.01,'contactAreaMm2':float(union.area),'contactIslands':len(union.geoms)if hasattr(union,'geoms')else 1,'contactBoundsXYMm':list(union.bounds),'contactVertexZRangeMm':[float(pv[mesh.faces[atbed],2].min()),float(pv[mesh.faces[atbed],2].max())],'dimensionsMm':(bb[1]-bb[0]).tolist(),'next':'One native slice perprinter tocheckactualfirstlayer stablecontacts andholes/support; no furthernormal search.'})
(D/'flat-base-pose-candidates.json').write_text(json.dumps({'notAppliedByThisScript':True,'geometryUnchanged':True,'oneCandidatePerColor':True,'parts':out,'sourceScriptSha256':sha(Path(__file__))},indent=2)+'\n');print(json.dumps(out,indent=2))
