from pathlib import Path
import json,sys,subprocess
D=Path(__file__).resolve().parents[1];q=json.loads((D/'projects/project-preparation.json').read_text())
for row in q['variants']:
 if row['group'] not in ['WHITE','old-black-plate5']:continue
 out=D/'intermediate'/row['printer']/row['group']/'reused-native';out.mkdir(parents=True,exist_ok=True);cmd=[sys.executable,str(D/'scripts/audit_surface_spacing.py'),'--archive',row['source_archive'],'--printer',row['printer'],'--expected',str(row['expected_count']),'--output',str(out/'spacing-acceptance.json')];r=subprocess.run(cmd,capture_output=True,text=True);(out/'spacing.log').write_text(r.stdout+r.stderr);print(row['printer'],row['group'],r.returncode,r.stdout,flush=True);assert r.returncode==0,(row,r.stderr)
