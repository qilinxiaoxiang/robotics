from pathlib import Path
import sys,json,trimesh
H=Path(__file__).resolve().parent;D=H.parents[1]/'hardware-design-20260912/whole-robot-20260912/electrical/head-layout';sys.path.insert(0,str(D))
from geometry import man,box,add_pi,obstacles,hits
F=D/'final';obs=add_pi(obstacles(True))
for name in ['head_cap_assembly','audio_carrier_assembly','head_fastener_reference_assembly','camera_pitch_foot_assembly','camera_cradle_assembly','openrb_actual_box_proxy_assembly','amp_reservation_assembly','speaker_reservation_assembly']:
 m=trimesh.load(F/(name+'.stl'),force='mesh');obs.append((name,m,man(m)))
res=[]
for use,y in [('data',8.9),('power',21.5)]:
 # Treat entire 14 mm manufacturer bare connector as external (do not assume insertion length).
 m=box([37.685,y,-56.1],[14.5,9.5,7]);m.export(H/'service-mounts'/f'pi-{use}-bare-plug-reservation.stl')
 res.append({'use':use,'reservation_mm':[14.5,9.5,7],'hits':hits(man(m),obs)})
(H/'usb-bare-plug-check.json').write_text(json.dumps({'manufacturer':'Adafruit 1826 bare plug 14 x 8.5 x 6 mm; assembled shell 26 x 10 x 7 NOT checked','full_length_treated_external':True,'checks':res,'passed':all(not x['hits'] for x in res),'limit':'No particular OTG 1099 or A-to-C 4472 moulded plug approved; solder tail bend/strain relief and physical fit require first article.'},indent=2));print(json.dumps(res,indent=2))
