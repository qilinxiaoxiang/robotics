"""Package native primary files only after all ten native exports exist."""
from pathlib import Path
import json,zipfile,hashlib
D=Path(__file__).resolve().parent
LABELS={'old-orange-plate1':'Orange-10-Original-Plate1','old-black-plate5':'Black-18-Original-Plate5','orange':'Orange-4','yellow':'Yellow-4','WHITE':'White-3','black':'Black-50'}
def sha(data):return hashlib.sha256(data).hexdigest()
def main():
 manifest=json.loads((D/'packaging.json').read_text());rows=[];payloads=[]
 for v in manifest['variants']:
  archive=Path(v['archive']);project=Path(v['project']);assert archive.is_file() and project.is_file(),v
  with zipfile.ZipFile(archive) as z:
   members=[n for n in z.namelist() if n.endswith('.gcode')];assert len(members)==1;data=z.read(members[0])
  if v['printer']=='Elegoo':assert Path(v['gcode']).read_bytes()==data,'Native extracted bytes differ'
  if not v['primary']:continue
  extension='.gcode' if v['printer']=='Elegoo' else '.gcode.3mf';name=f"MicroDuck_{v['printer']}_{LABELS[v['group']]}{extension}";dest=D/'READY-TO-PRINT'/name;payload=data if v['printer']=='Elegoo' else archive.read_bytes();payloads.append((dest,payload));rows.append({'printer':v['printer'],'group':v['group'],'count':v['expected_count'],'copy':str(dest),'sha256':sha(payload),'archive':str(archive),'archive_sha256':sha(archive.read_bytes()),'project':str(project),'project_sha256':sha(project.read_bytes()),'archive_member':members[0] if v['printer']=='Elegoo' else None})
 assert len(rows)==6 and sum(r['count'] for r in rows)==89
 for dest,payload in payloads:dest.parent.mkdir(exist_ok=True);dest.write_bytes(payload);assert dest.read_bytes()==payload
 (D/'handoff-index.json').write_text(json.dumps({'packaging_sha256':sha((D/'packaging.json').read_bytes()),'primary_files':rows,'count':89,'instruction':'Optional replacements only. Never print both a primary and its alternative; do not reprint sound completed parts automatically.'},indent=2)+'\n');print('HANDOFF_COPIES_CREATED',len(rows))
if __name__=='__main__':main()
