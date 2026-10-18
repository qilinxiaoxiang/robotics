from pathlib import Path
import json,hashlib
D=Path(__file__).resolve().parent;p=D/'terminal-registration.json';r=json.loads(p.read_text())
r['status']='GEOMETRIC_PORTS_REGISTERED_AND_OFFICIAL_IMAGE_POLARITY_MAPPED'
r['rows'][0]['electricalAssignment']='GND';r['rows'][0]['schematicPin']=2
r['rows'][1]['electricalAssignment']='VIN+';r['rows'][1]['schematicPin']=1
r['polarity']={'sourceURL':'https://emanual.robotis.com/assets/images/parts/controller/openrb-150/openrb-150_power_terminal_vin.png','verifiedDate':'2026-10-09','visualVerification':'Parent/root directly viewed official image: with USB at image left and J4 at right, upper terminal is VIN+ and lower terminal is GND; the GND terminal is on the red VIN(DXL) jumper side.','registration':'The CAD jumper connected component 118 occupies native X=-6.93..+0.69, on the negative-native-X terminal side. Native X maps to world Y. Therefore nativeX=-1.71/worldY=-1.71 is GND; nativeX=+1.79/worldY=+1.79 is VIN+.','basis':'Official schematic J4 pin1 VIN and pin2 GND; physical side tied to the nearby jumper rather than arbitrary image up/down.','physicalValidation':False}
r['polarityAssignmentScriptSha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
p.write_text(json.dumps(r,indent=2)+'\n');print(hashlib.sha256(p.read_bytes()).hexdigest())
