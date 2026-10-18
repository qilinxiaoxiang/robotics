from pathlib import Path
import os;assert os.environ.get('MICRODUCK_BOUNDED_CAD')=='1'
import sys,json,zipfile,hashlib
D=Path(__file__).resolve().parent;R=D.parent.parent;P=R/'printing/11-ASSEMBLY-REPAIR-20261008';sys.path.insert(0,str(P.parent/'09-REPRINT-READY-20260930'));from native_tools import first_layer_summary
rows=[]
for c,printer in [('Yellow','Bambu'),('Black','Elegoo')]:
 p=P/f'{c.lower()}-neck-preflight/{c}_neck.3mf'
 with zipfile.ZipFile(p) as z:s=z.read('Metadata/plate_1.gcode').decode()
 rows.append({'archive':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'objects':first_layer_summary(s,printer,p)})
(D/'split-native-first-layer.json').write_text(json.dumps(rows,indent=2)+'\n');print(json.dumps(rows,indent=2))
