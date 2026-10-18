"""Export current final plate views; absolute paths avoid Bambu's working-directory shift."""
from pathlib import Path
import subprocess,hashlib,json,shutil
H=Path(__file__).resolve().parent;P=H/'printing-full';O=P/'final-preview';O.mkdir(exist_ok=True)
f=P/'MicroDuck-complete-89-instances-X1C-CoolPlate.3mf'
with (P/'preview-export.log').open('w') as log:
 subprocess.run(['/Applications/BambuStudio.app/Contents/MacOS/BambuStudio','--export-png','0','--outputdir',str(O),str(f)],stdout=log,stderr=subprocess.STDOUT,check=True)
images=sorted(O.glob('plate_*_0.png'));assert len(images)==len(json.loads((P/'slice-verification.json').read_text())['result']['sliced_plates'])
for p in images:shutil.copy2(p,P/p.name)
(P/'preview-verification.json').write_text(json.dumps({'input_file':str(f),'input_sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'tool':'BambuStudio --export-png 0; absolute input and output paths','output_images':[p.name for p in images],'return_code':0,'scope':'Fresh plate previews exported from the final 3MF; no physical print.'},indent=2))
