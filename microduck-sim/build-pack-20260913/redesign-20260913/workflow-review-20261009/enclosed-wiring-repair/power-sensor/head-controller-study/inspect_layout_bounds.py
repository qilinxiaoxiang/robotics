from pathlib import Path
import json,trimesh,numpy as np
D=Path(__file__).resolve().parent;HD=D.parents[2]/'enclosed-wiring-repair/head-layout';j=json.loads((HD/'audio-relocation/positive-y13-native/current-rigid-inventory.json').read_text());groups={}
for q in j['parts']:
 n=q['id'];m=trimesh.load_mesh(q['file']);m.apply_transform(q['worldTransform']);b=m.bounds
 if n=='REFERENCE Pi current pi' or n in ['REFERENCE current speaker','REFERENCE current speaker_keeper','REFERENCE MicroB photo receiving','current_amp','REFERENCE fixed head camera_board','REFERENCE fixed head camera_retainer','REFERENCE fixed head jaw_frame'] or 'gpio_pin_02' in n or 'gpio_pin_40' in n:print(n,b.tolist())
 if 'REFERENCE Pi current' in n:groups[n]=b.tolist()
(D/'pi-current-parts-bounds.json').write_text(json.dumps(groups,indent=2)+'\n')
