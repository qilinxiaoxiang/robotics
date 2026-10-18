"""FK in mm, raw STL meshes; transformations never use MuJoCo recentered mesh vertices."""
from pathlib import Path
import xml.etree.ElementTree as ET
import numpy as np, trimesh
from scipy.spatial.transform import Rotation
ROOT=Path(__file__).resolve().parents[3]
ROBOT=ROOT/'microduck_rl/src/mjlab_microduck/robot/microduck'
XML=ROBOT/'robot_allcollisions.xml'
TREE=ET.parse(XML).getroot()
def transform(e):
 t=np.eye(4);q=np.fromstring(e.get('quat','1 0 0 0'),sep=' ')
 t[:3,:3]=Rotation.from_quat(q[[1,2,3,0]]).as_matrix();t[:3,3]=np.fromstring(e.get('pos','0 0 0'),sep=' ')*1000
 return t
def fk(q=None,root_world=False):
 q=q or {};bodies={};geoms=[]
 def walk(b,P):
  B=P@transform(b)
  if b.get('name')=='trunk_base' and not root_world:B=np.eye(4)
  for j in b.findall('joint'):
   angle=q.get(j.get('name'),0.);axis=np.fromstring(j.get('axis','0 0 1'),sep=' ')
   p=np.fromstring(j.get('pos','0 0 0'),sep=' ')*1000;J=np.eye(4)
   J[:3,:3]=Rotation.from_rotvec(axis*angle).as_matrix();J[:3,3]=p-J[:3,:3]@p;B=B@J
  bodies[b.get('name')]=B
  for i,g in enumerate(b.findall('geom')):
   if g.get('class')=='visual' and g.get('mesh'):geoms.append(dict(body=b.get('name'),mesh=g.get('mesh'),index=i,local=transform(g),world=B@transform(g)))
  for child in b.findall('body'):walk(child,B)
 for b in TREE.find('worldbody').findall('body'):walk(b,np.eye(4))
 return bodies,geoms
_meshes={}
def raw(name):
 if name not in _meshes:
  m=trimesh.load(ROBOT/'assets'/f'{name}.stl',force='mesh');m.apply_scale(1000);_meshes[name]=m
 return _meshes[name].copy()
def world_meshes(q=None):
 return [(g,raw(g['mesh']).apply_transform(g['world'])) for g in fk(q)[1]]
if __name__=='__main__':
 import json
 out=Path(__file__).parent;matches=json.loads((out/'verified-rigid-matches.json').read_text());b,gs=fk();result={'units':'mm','convention':'column vector: p_body = T_4x4 @ [x,y,z,1]; root trunk_base frame. Rotation applies before translation.','source_xml':str(XML),'community_to_named_body':{},'zero_joint_body_transforms':{k:v.tolist() for k,v in b.items()},'original_battery_to_trunk_base':None}
 for k,v in matches.items():
  if 'surface_residuals' not in v:continue
  candidate=v['top_candidates'][0];T=np.eye(4);T[:3,:3]=candidate['rotation'];T[:3,3]=candidate['translation_mm'];g=next(g for g in gs if g['mesh']==Path(v['asset']).stem);M=g['local']@T
  result['community_to_named_body'][k]={'body':g['body'],'mesh':g['mesh'],'matrix_mm':M.tolist(),'matrix_m':(M*np.array([[1,1,1,.001],[1,1,1,.001],[1,1,1,.001],[1,1,1,1]])).tolist(),'surface_residuals':v.get('surface_residuals')}
 for g in gs:
  if g['mesh']=='np_f970':result['original_battery_to_trunk_base']=g['local'].tolist()
 (out/'body-transforms.json').write_text(json.dumps(result,indent=2))
 print(json.dumps({k:v for k,v in result['community_to_named_body'].items() if k in ['6','12']},indent=2))
