from pathlib import Path
import json,zipfile,hashlib,xml.etree.ElementTree as E,sys,copy
import numpy as np,trimesh as tm
D=Path(__file__).resolve().parent;H=D.parent.parents[1]/'head-redesign-20261008';color=sys.argv[1];manifest=Path(sys.argv[2]);rows=json.loads(manifest.read_text())['parts'];prep=json.loads((D/'preparation.json').read_text());pose=next(p for p in json.loads((H/'gpio-audio-repair/orientation-readonly-review/flat-base-pose-candidates.json').read_text())['parts']if p['color']==color)
T=np.linalg.inv(pose['relativeToExistingObjectMesh'])@pose['worldToPrintTransform'];Q='{http://schemas.microsoft.com/3dmanufacturing/core/2015/02}';E.register_namespace('',Q[1:-1]);evidence=[]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
for row in prep['rows']:
 if row['color']!=color or (len(sys.argv)>3 and row['machine']!=sys.argv[3]):continue
 file=Path(row['project']);backup=D/(file.stem+'-before-hole-blockers.3mf')
 if not backup.exists():backup.write_bytes(file.read_bytes())
 with zipfile.ZipFile(backup)as z:data={n:z.read(n)for n in z.namelist()}
 root=E.fromstring(data['3D/3dmodel.model']);resources=root.find(Q+'resources');owner=next(o for o in resources if o.get('id')=='1');settings=E.fromstring(data['Metadata/model_settings.config']);so=next(o for o in settings.findall('object')if o.get('id')=='1');mesh=owner.find(Q+'mesh')
 if mesh is not None:
  owner.remove(mesh);normal=E.SubElement(resources,Q+'object',{'id':'10100','type':'model','name':'head_bottom'});normal.append(mesh);components=E.SubElement(owner,Q+'components');E.SubElement(components,Q+'component',{'objectid':'10100','transform':'1 0 0 0 1 0 0 0 1 0 0 0'});so.find('part').set('id','10100')
 else:components=owner.find(Q+'components')
 for i,r in enumerate(rows):
  src=Path(r['mesh']);assert sha(src)==r['sha256'];m=tm.load(src,force='mesh',process=False);m.apply_transform(T);v,inv=np.unique(m.vertices,axis=0,return_inverse=True);f=inv[m.faces];m=tm.Trimesh(v,f,process=False);assert m.is_watertight
  ident=str(10200+i);obj=E.SubElement(resources,Q+'object',{'id':ident,'type':'model','name':r['key']});mesh=E.SubElement(obj,Q+'mesh');verts=E.SubElement(mesh,Q+'vertices');faces=E.SubElement(mesh,Q+'triangles')
  for vv in v:E.SubElement(verts,Q+'vertex',dict(zip(['x','y','z'],[format(float(x),'.15g')for x in vv])))
  for ff in f:E.SubElement(faces,Q+'triangle',dict(zip(['v1','v2','v3'],map(str,ff))))
  E.SubElement(components,Q+'component',{'objectid':ident,'transform':'1 0 0 0 1 0 0 0 1 0 0 0'});sp=E.SubElement(so,'part',{'id':ident,'subtype':'support_blocker'});E.SubElement(sp,'metadata',{'key':'name','value':r['key']});E.SubElement(sp,'mesh_stat',{'face_count':str(len(f)),'edges_fixed':'0','degenerate_facets':'0','facets_removed':'0','facets_reversed':'0','backwards_edges':'0'})
 data['3D/3dmodel.model']=E.tostring(root,encoding='utf-8',xml_declaration=True);data['Metadata/model_settings.config']=E.tostring(settings,encoding='utf-8',xml_declaration=True)
 with zipfile.ZipFile(file,'w',zipfile.ZIP_DEFLATED)as z:
  for n,b in data.items():z.writestr(n,b)
 row['projectSha256']=sha(file);row['supportBlockerManifest']=str(manifest);row['supportBlockerManifestSha256']=sha(manifest);row['addedSupportBlockers']=len(rows);evidence.append({'project':str(file),'sha256':sha(file),'before':str(backup),'beforeSha256':sha(backup),'addedSupportBlockers':len(rows),'worldToObject':T.tolist(),'printedGeometryAndBuildPoseUnchanged':True})
(D/'preparation.json').write_text(json.dumps(prep,indent=2)+'\n');(D/f'{color}-hole-blockers-application.json').write_text(json.dumps(evidence,indent=2)+'\n');print(color,len(rows),'blockers installed')
