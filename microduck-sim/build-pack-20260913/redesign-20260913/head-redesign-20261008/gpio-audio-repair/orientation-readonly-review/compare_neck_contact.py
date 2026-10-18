"""Read-only planar supporting-face area comparison, current vs all mesh face normals."""
from pathlib import Path
import json,os,hashlib,gc
assert os.environ.get('MICRODUCK_BOUNDED_CAD')=='1'
import numpy as np,trimesh as tm
D=Path(__file__).resolve().parent;H=D.parents[1];R=H.parent;P=R/'printing/11-ASSEMBLY-REPAIR-20261008';source=P/'orientation-preparation.json';data=json.loads(source.read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();seen=set();rows=[]
for part in data['parts']:
 if part['key']!='neck_pitch':continue
 p=(R/part['source']).resolve()
 if str(p)in seen:continue
 seen.add(str(p));m=tm.load(p,force='mesh');T=np.array(part['printTransform']);v=np.asarray(m.vertices);f=np.asarray(m.faces);area=m.area_faces
 normals=np.asarray(m.face_normals);_,ids=np.unique(np.round(normals,5),axis=0,return_index=True);ns=normals[ids];ns=ns[np.linalg.norm(ns,axis=1)>.5]
 # Area at any supporting plane: outward n faces down onto bed; maxdot is its supporting offset.
 current=-T[2,:3];cp=v@current;mx=float(cp.max());currentarea=float(area[np.min(cp[f],axis=1)>=mx-.01].sum());strict=float(area[np.min(cp[f],axis=1)>=mx-.0001].sum())
 best=(-1,None,None);beststrict=(-1,None,None)
 for i in range(0,len(ns),32):
  dirs=ns[i:i+32];pr=v@dirs.T;maxima=pr.max(axis=0);mins=np.minimum(np.minimum(pr[f[:,0]],pr[f[:,1]]),pr[f[:,2]])
  vals=(area[:,None]*(mins>=maxima-.01)).sum(axis=0);valstrict=(area[:,None]*(mins>=maxima-.0001)).sum(axis=0)
  j=int(np.argmax(vals));k=int(np.argmax(valstrict))
  if vals[j]>best[0]:best=(float(vals[j]),dirs[j].tolist(),float(maxima[j]))
  if valstrict[k]>beststrict[0]:beststrict=(float(valstrict[k]),dirs[k].tolist(),float(maxima[k]))
 ratio=currentarea/best[0]if best[0]>0 else None
 row={'key':part['key'],'color':part['color'],'source':str(p),'sourceSha256':sha(p),'testedFaceNormals':len(ns),'contactToleranceMm':.01,'currentAreaMm2':currentarea,'currentStrict1e4AreaMm2':strict,'maximumTestedAreaMm2':best[0],'maximumStrict1e4AreaMm2':beststrict[0],'maximumDownwardOutwardNormalWorld':best[1],'currentDownwardOutwardNormalWorld':current.tolist(),'ratioToMaximum':ratio,'maximizedWithin1Percent':currentarea>=best[0]*.99,'currentAreaInOriginalReport':part['planarBedContactAreaMm2'],'sourceReportUnchanged':True};rows.append(row);(D/'neck-contact-comparison.json').write_text(json.dumps({'readOnly':True,'sourceReportSha256':sha(source),'sourceScriptSha256':sha(Path(__file__)),'scope':'Planar contact area from all distinct mesh facet normals, support planes determined from all vertices. Tolerance1e-2; strict1e-4 also reported. Not printability/support/cosmetic optimization. No geometry/plate/profile modification.','rows':rows},indent=2)+'\n');print(json.dumps(row),flush=True);del m;gc.collect()
