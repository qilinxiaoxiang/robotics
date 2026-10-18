from pathlib import Path
import json,shutil,subprocess,zipfile
import trimesh,numpy as np
P=Path(__file__).resolve().parent
profiles=P.parent/'slicing';out=P/'printing';out.mkdir(exist_ok=True)
parts=[]
for name in ['power-support-integrated','small-regulator-cover']:
    mesh=trimesh.load(P/f'assembly/compact-battery/{name}-body.stl',force='mesh')
    if name=='small-regulator-cover':
        T=np.eye(4);T[:3,:3]=[[1,0,0],[0,0,-1],[0,1,0]];mesh.apply_transform(T)
    mesh.apply_translation([0,0,-mesh.bounds[0,2]])
    path=out/f'{name}-print.stl';mesh.export(path);parts.append(path)
cmd=['/Applications/BambuStudio.app/Contents/MacOS/BambuStudio','--load-settings',f'{profiles}/machine.json;{profiles}/head-process.json','--load-filaments',str(profiles/'filament.json'),'--arrange','1','--orient','0','--slice','0','--export-3mf','compact-head-support-raw.3mf','--outputdir',str(out)]+[str(p) for p in parts]
with (out/'compact-slice.log').open('w') as log:
    r=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT)
r.check_returncode()
data=json.loads((out/'result.json').read_text())
assert data['return_code']==0 and data.get('sliced_plates'),data
(out/'compact-slice-result.json').write_text(json.dumps(data,indent=2))
subprocess.run(['python3',str(profiles/'embed_presets.py'),str(out/'compact-head-support-raw.3mf'),str(out/'MicroDuck-compact-power-X1C-CoolPlate.3mf')],check=True)
final=out/'MicroDuck-compact-power-X1C-CoolPlate.3mf'
# Bambu reuses an already-loaded preset with the same name, even if a second
# project's embedded preset has different support settings. Give this one its own ID.
with zipfile.ZipFile(final) as z:entries={n:z.read(n) for n in z.namelist()}
name='MicroDuck Compact 20260912 Tree Supports @BBL X1C'
for key in ['Metadata/project_settings.config','Metadata/process_settings_1.config']:
    v=json.loads(entries[key]);v['print_settings_id']=name
    if key.endswith('process_settings_1.config'):v['name']=name
    entries[key]=json.dumps(v,indent=2).encode()
with zipfile.ZipFile(final,'w',zipfile.ZIP_DEFLATED) as z:
    for key,value in entries.items():z.writestr(key,value)
print(json.dumps(data,indent=2))
