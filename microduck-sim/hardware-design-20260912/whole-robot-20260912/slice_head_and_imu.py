from pathlib import Path
import json,subprocess
P=Path(__file__).resolve().parent;profiles=P.parent/'slicing';out=P/'printing/head';out.mkdir(parents=True,exist_ok=True)
parts=[P/'electrical/head-layout/final'/f'{name}_print.stl' for name in ['head_cap','audio_carrier']]
parts += [P.parent/'camera'/f'{name}.stl' for name in ['camera_pitch_foot','camera_cradle']]
parts += [P/'assembly/trunk-imu'/f'{name}_print.stl' for name in ['imu_clamp_holder','imu_rear_cover']]
cmd=['/Applications/BambuStudio.app/Contents/MacOS/BambuStudio','--load-settings',f'{profiles}/machine.json;{profiles}/head-process.json','--load-filaments',str(profiles/'filament.json'),'--arrange','1','--orient','0','--slice','0','--export-3mf','head-and-imu-raw.3mf','--outputdir',str(out)]+[str(p) for p in parts]
with (out/'slice.log').open('w') as log:r=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT)
r.check_returncode();data=json.loads((out/'result.json').read_text())
assert data['return_code']==0 and data.get('sliced_plates'),data
(out/'slice-result.json').write_text(json.dumps(data,indent=2))
subprocess.run(['python3',str(profiles/'embed_presets.py'),str(out/'head-and-imu-raw.3mf'),str(out/'MicroDuck-head-camera-IMU-X1C-CoolPlate.3mf')],check=True)
print(json.dumps(data,indent=2))
