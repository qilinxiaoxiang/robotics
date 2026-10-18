"""Create the 89-instance editable Bambu project; preserve all purchasing/print sources."""
from pathlib import Path
import copy,hashlib,json,subprocess,zipfile,xml.etree.ElementTree as ET
import trimesh
O=Path(__file__).resolve().parent;P=O.parent;S=P.parent/'hardware-design-20260912/slicing';W=O/'printing';W.mkdir(exist_ok=True)
base=json.loads((P/'phase1/print-manifest.json').read_text());rows=copy.deepcopy(base['instances']);assert len(rows)==85
for r in rows:
    p=Path(r['file']);assert hashlib.sha256(p.read_bytes()).hexdigest()==r['sha256']
old_head=[r for r in rows if Path(r['file']).name=='head-cap-mouth-clearance-print.stl'];assert len(old_head)==1
old_head[0].update(name='Jaw-clearance head cap with USB service window',file=str(O/'head-cap-usb-service-print.stl'),revision_basis='Local service-window revision; replaces one existing cap')
adds=[('Open regulator insert',O/'regulator-open-insert-print.stl'),('Camera tilt foot',P/'assembly/print-parts/current/camera_pitch_foot.stl'),('Camera cradle',P/'assembly/print-parts/current/camera_cradle.stl'),('Audio carrier',P/'assembly/print-parts/current/audio_carrier_print.stl')]
for name,path in adds:rows.append({'name':name,'quantity':1,'file':str(path),'material':'PLA','count_basis':'current integration design','orientation':'Provided STL orientation retained'})
for r in rows:
    p=Path(r['file']);m=trimesh.load(p,force='mesh');r.update(sha256=hashlib.sha256(p.read_bytes()).hexdigest(),extent_mm=m.extents.tolist())
assert len(rows)==89 and sum(r['quantity'] for r in rows)==89
assert not any('voltage-alarm' in r['file'] for r in rows)
man={'revision':'redesign-20260913-89','problem_ids':['P5','P6'],'source_manifest':str(P/'phase1/print-manifest.json'),'source_manifest_sha256':hashlib.sha256((P/'phase1/print-manifest.json').read_bytes()).hexdigest(),'queue_count':89,'basis':'Retain all 85 previous print-stock instances; replace cap once; add regulator insert and three camera/audio parts. No battery-alarm carrier.','instances':rows,'physical_print_completed':False}
(O/'print-manifest.json').write_text(json.dumps(man,indent=2)+'\n')
raw=W/'current-head-queue-raw.3mf'
cmd=['/Applications/BambuStudio.app/Contents/MacOS/BambuStudio','--load-settings',str(S/'machine.json')+';'+str(S/'head-process.json'),'--load-filaments',str(S/'filament.json'),'--arrange','1','--orient','0','--export-3mf',raw.name,'--outputdir',str(W)]+[r['file'] for r in rows]
with (W/'arrange.log').open('w') as log:result=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT)
result.check_returncode()
subprocess.run(['python3',str(S/'embed_presets.py'),str(raw),str(O/'current-print-queue.3mf')],check=True)
with zipfile.ZipFile(O/'current-print-queue.3mf') as z:
    names=z.namelist();assert not any(n.endswith('.gcode') for n in names)
    settings=ET.fromstring(z.read('Metadata/model_settings.config'));plates=settings.findall('plate')
    ids=[i.find("metadata[@key='object_id']").get('value') for p in plates for i in p.findall('model_instance')]
    assert len(ids)==89 and len(set(ids))==89
print(json.dumps({'manifest':str(O/'print-manifest.json'),'editable_project':str(O/'current-print-queue.3mf'),'plates':len(plates),'assigned_print_instances':len(ids),'gcode_entries':0}))
