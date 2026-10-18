"""Read frozen/current source geometry; write this assembly pack only."""
from pathlib import Path
import xml.etree.ElementTree as ET
import zipfile,json,hashlib,sys,itertools,collections
import numpy as np,trimesh
from scipy.spatial import cKDTree

OUT=Path(__file__).resolve().parent
SIM=OUT.parents[1]
OLD=SIM/'hardware-design-20260912/whole-robot-20260912'
sys.path.insert(0,str(OLD/'assembly'))
from assembly_fk import fk,raw,world_meshes,ROBOT,XML
SOURCE=SIM/'Microduck-build-tutorial/microduck3D打印.3mf'
NS={'m':'http://schemas.microsoft.com/3dmanufacturing/core/2015/02','p':'http://schemas.microsoft.com/3dmanufacturing/production/2015/06'}
z=zipfile.ZipFile(SOURCE)
trees={}
def tree(p):
 if p not in trees:trees[p]=ET.fromstring(z.read(p))
 return trees[p]
def trans(s):
 T=np.eye(4)
 if s:T[:3,:]=np.array([float(x) for x in s.split()]).reshape(4,3).T
 return T
def mesh(p,id):
 obj=next(o for o in tree(p).findall('m:resources/m:object',NS) if o.get('id')==id)
 node=obj.find('m:mesh',NS)
 if node is not None:
  v=[[float(x.get(k)) for k in ('x','y','z')] for x in node.findall('m:vertices/m:vertex',NS)]
  f=[[int(x.get(k)) for k in ('v1','v2','v3')] for x in node.findall('m:triangles/m:triangle',NS)]
  return trimesh.Trimesh(v,f,process=True)
 return trimesh.util.concatenate([mesh(c.get('{'+NS['p']+'}path',p).lstrip('/'),c.get('objectid')).apply_transform(trans(c.get('transform'))) for c in obj.findall('m:components/m:component',NS)])
settings=ET.fromstring(z.read('Metadata/model_settings.config'))
meta=lambda o:{x.get('key'):x.get('value') for x in o.findall('metadata') if x.get('key')}
names={o.get('id'):meta(o)['name'] for o in settings.findall('object')}
plate={}
for p in settings.findall('plate'):
 for i in p.findall('model_instance'):plate[meta(i)['object_id']]=int(meta(p)['plater_id'])
build={i.get('objectid'):trans(i.get('transform')) for i in tree('3D/3dmodel.model').findall('m:build/m:item',NS)}
rot=[]
for perm in itertools.permutations(range(3)):
 for signs in itertools.product([-1,1],repeat=3):
  R=np.eye(3)[list(perm)]*np.array(signs)[:,None]
  if np.linalg.det(R)>.5:rot.append(R)
refs={g['mesh']:raw(g['mesh']) for g in fk()[1]}
rows=[]
for id in sorted(names,key=int):
 m=mesh('3D/3dmodel.model',id)
 if not len(m.faces):continue
 candidates=[]
 for name,ref in refs.items():
  err=np.linalg.norm(np.sort(m.extents)-np.sort(ref.extents))
  if err>.12:continue
  best=None
  for R in rot:
   v=m.vertices@R.T;t=ref.bounds.mean(axis=0)-(v.min(0)+v.max(0))/2
   d=cKDTree(ref.vertices).query(v+t)[0]
   score=np.percentile(d,95)
   if best is None or score<best[0]:best=(score,R,t)
  candidates.append((best[0],name,best[1],best[2]))
 candidates.sort(key=lambda x:x[0]);match=candidates[0] if candidates else None
 record={'id':int(id),'source_name':names[id],'plate':plate.get(id),'source_extent_mm':m.extents.tolist(),'source_volume_mm3':float(m.volume),'watertight':bool(m.is_watertight),'connected_solids':len(m.split()),'source_sha256':hashlib.sha256(m.export(file_type='stl')).hexdigest()}
 if match:
  record.update(reference_mesh=match[1],vertex_p95_mm=float(match[0]),source_to_reference_rotation=match[2].tolist(),source_to_reference_translation_mm=match[3].tolist())
 # Keep the original plate's orientation but centre and ground the individual object.
 pm=m.copy().apply_transform(build.get(id,np.eye(4)))
 shift=np.r_[-pm.bounds.mean(axis=0)[:2],-pm.bounds[0,2]];pm.apply_translation(shift)
 path=OUT/'print-parts'/f'community-{id}.stl';pm.export(path)
 record.update(print_file=str(path),print_extent_mm=pm.extents.tolist(),original_plate_rotation=build.get(id,np.eye(4))[:3,:3].tolist())
 rows.append(record)
(OUT/'community-print-inventory.json').write_text(json.dumps({'source':str(SOURCE),'source_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),'objects':rows},ensure_ascii=False,indent=2))
manifest=json.loads((OLD/'final-delivery-verification.json').read_text());checks=[]
for name,expected in manifest['part_sha256'].items():
 p=SIM/'hardware-design-20260912'/name
 got=hashlib.sha256(p.read_bytes()).hexdigest();checks.append({'file':str(p),'expected':expected,'actual':got,'pass':got==expected})
if not all(x['pass'] for x in checks):raise RuntimeError('Frozen print geometry mismatch')
(OUT/'source-verification.json').write_text(json.dumps({'frozen_eight_parts':checks,'source_xml':str(XML),'source_xml_sha256':hashlib.sha256(XML.read_bytes()).hexdigest(),'geometry_counts':dict(collections.Counter(g['mesh'] for g in fk()[1])),'scope':'Disk and topology readback only; no physical printing or assembly.'},indent=2))
for row in rows:print(row['id'],row['source_name'],row.get('reference_mesh','UNMATCHED'),round(row.get('vertex_p95_mm',999),4),flush=True)
