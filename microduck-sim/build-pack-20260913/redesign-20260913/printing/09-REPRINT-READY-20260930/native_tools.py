"""Native toolpath measurements for reprint comparison, independent of source mesh audit."""
from pathlib import Path
import sys,zipfile,xml.etree.ElementTree as E,json,re,hashlib
import numpy as np
from shapely.ops import unary_union
D=Path(__file__).resolve().parent;P=D.parent
sys.path.insert(0,str(P/'08-ORANGE-BOTTOM-AUDIT-20260930'))
from analyze_bottom import first_layer_paths
sys.path.insert(0,str(P/'04-FOUR-COLOR-20260929'))
from audit_spacing import parse
N='{http://schemas.microsoft.com/3dmanufacturing/core/2015/02}'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def normalize_bambu(code,project):
 with zipfile.ZipFile(project) as z:
  st=E.fromstring(z.read('Metadata/model_settings.config'))
 names={o.get('id'):o.find("metadata[@key='name']").get('value') for o in st.findall('object')}
 labels={i.find("metadata[@key='identify_id']").get('value'):names[i.find("metadata[@key='object_id']").get('value')] for i in st.findall('plate/model_instance')}
 out=[f'EXCLUDE_OBJECT_DEFINE NAME={name}_id_{label}_copy_0' for label,name in labels.items()]
 for l in code.splitlines():
  if l.startswith('; start printing object, unique label id:'):
   label=l.rsplit(':',1)[1].strip();l=f'EXCLUDE_OBJECT_START NAME={labels[label]}_id_{label}_copy_0'
  elif l.startswith('; stop printing object, unique label id:'):l='EXCLUDE_OBJECT_END'
  elif l.startswith('; FEATURE:'):l=';TYPE:'+l.split(':',1)[1].strip()
  elif l.startswith('; LINE_WIDTH:'):l=';WIDTH:'+l.split(':',1)[1].strip()
  out.append(l)
 return '\n'.join(out)
def first_layer_summary(code,printer='Elegoo',project=None):
 if printer=='Bambu':code=normalize_bambu(code,project)
 paths=first_layer_paths(code);rows=[]
 for name,kinds in paths.items():
  model=unary_union([v for k,v in kinds.items() if not any(s in k.lower() for s in ['support','brim','skirt'])]);support=unary_union([v for k,v in kinds.items() if 'support' in k.lower()])
  rows.append({'name':name,'model_area_mm2':model.area,'support_area_mm2':support.area,'types_mm2':{k:v.area for k,v in kinds.items()}})
 return rows
