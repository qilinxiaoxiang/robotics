from pathlib import Path
import subprocess, json
P=Path(__file__).resolve().parent; root=P.parent
parts=[root/'battery'/f'{x}.stl' for x in ['battery_tray','frame_riser','battery_lid','electronics_deck','audio_enclosure','audio_grille']]+[root/'head'/f'{x}.stl' for x in ['camera-conformal-saddle','camera-inner-backing']]+[root/'camera'/f'{x}.stl' for x in ['camera_pitch_foot','camera_cradle']]
cmd=['/Applications/BambuStudio.app/Contents/MacOS/BambuStudio','--load-settings',f'{P}/machine.json;{P}/process.json','--load-filaments',str(P/'filament.json'),'--arrange','1','--orient','0','--slice','0','--export-3mf','fit-parts.3mf','--outputdir',str(P)]+[str(p) for p in parts]
with (P/'fit-slice.log').open('w') as log:
 r=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT)
print((P/'fit-slice.log').read_text()[-2500:]);print('exit',r.returncode)
if (P/'result.json').exists():
 d=json.loads((P/'result.json').read_text());print('result:',d['return_code'],d['error_string']);print([(x.get('total_predication'),x.get('warning_message'),x.get('filaments')) for x in d.get('sliced_plates',[])])
 r.check_returncode()
 assert d['return_code']==0 and d.get('sliced_plates'),d
 (P/'slice-result.json').write_text(json.dumps(d,indent=2))
