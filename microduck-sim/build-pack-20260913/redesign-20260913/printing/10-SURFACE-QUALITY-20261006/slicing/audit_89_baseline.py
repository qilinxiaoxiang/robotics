from pathlib import Path
import json,subprocess,sys
D=Path(__file__).resolve().parent;B=D.parents[1];index=json.loads((B/'09-REPRINT-READY-20260930/packaging.json').read_text());rows=[]
for v in index['variants']:
 if not v.get('primary'):continue
 dst=D/('baseline-'+v['printer']+'-'+v['group']+'-paths.json');cmd=[sys.executable,str(D/'audit_surface_paths.py'),'--gcode',v['archive'],'--project',v['project'],'--printer',v['printer'],'--output',str(dst)];r=subprocess.run(cmd,capture_output=True,text=True);print(v['printer'],v['group'],r.returncode,r.stdout,r.stderr,flush=True);assert r.returncode==0
 out=json.loads(dst.read_text());rows.append({'printer':v['printer'],'group':v['group'],'count':out['object_count'],'path':str(dst),'settings':out['settings']})
assert sum(r['count'] for r in rows)==89
(D/'baseline89-path-index.json').write_text(json.dumps({'count':89,'groups':rows,'physical_quality_verified':False},indent=2)+'\n')
