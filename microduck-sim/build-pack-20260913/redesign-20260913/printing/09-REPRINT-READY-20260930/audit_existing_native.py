from pathlib import Path
import json
from native_tools import first_layer_summary,parse,sha
D=Path(__file__).resolve().parent;P=D.parent;C=P/'04-FOUR-COLOR-20260929';K=C/'07-COMPACT-CENTER-20260929'
files={'old-orange-plate1':P/'03-PRINT/Elegoo/MicroDuck_Elegoo_plate_1.gcode','old-black-plate5':P/'03-PRINT/Elegoo/MicroDuck_Elegoo_plate_5.gcode','orange':P/'08-ORANGE-BOTTOM-AUDIT-20260930/MicroDuck_Elegoo_orange_FLAT.gcode','yellow':K/'ALTERNATE-ELEGOO/MicroDuck_Elegoo_yellow_COMPACT.gcode','WHITE':K/'ALTERNATE-ELEGOO/MicroDuck_Elegoo_WHITE_COMPACT.gcode','black':C/'USB-PRINT/MicroDuck_black.gcode'}
out=[]
for g,p in files.items():
 print(g,flush=True);first=first_layer_summary(p.read_text());spacing=parse(p)[0];b=spacing['actual_extrusion_bounds_conservative_mm'];out.append({'group':g,'path':str(p),'sha256':sha(p),'first_layer':first,'spacing':spacing,'footprint_center_translation_mm':[128-(b[0]+b[2])/2,128-(b[1]+b[3])/2]});(D/'existing-native-evidence.json').write_text(json.dumps({'groups':out},indent=2)+'\n')
