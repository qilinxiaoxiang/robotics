from pathlib import Path
import json,hashlib,struct,base64,array
D=Path(__file__).resolve().parent;m=json.loads((D/'fusion-import-manifest.json').read_text());rows=[];maximum=0
for p in m['parts']:
 a=json.loads(Path(p['sourcePartJson']).read_text());v=array.array('f');v.frombytes(base64.b64decode(a['positionB64']));ix=array.array('I');ix.frombytes(base64.b64decode(a['indexB64']));dy=p['translationFromBaselineMm'][1];path=Path(p['file']);assert hashlib.sha256(path.read_bytes()).hexdigest()==p['sha256'];err=0
 with path.open('rb')as f:
  f.read(80);assert struct.unpack('<I',f.read(4))[0]==len(ix)//3
  for k in range(0,len(ix),3):
   values=struct.unpack('<12fH',f.read(50))[3:12]
   for j,value in enumerate(values):
    expected=v[3*ix[k+j//3]+j%3]+(dy if j%3==1 else 0);err=max(err,abs(value-expected))
  assert not f.read(1)
 assert err<1e-5,(p['key'],err);maximum=max(maximum,err);rows.append({'key':p['key'],'triangles':len(ix)//3,'maxVertexDifferenceMm':err,'expectedTranslationMm':p['translationFromBaselineMm']})
r={'passed':True,'partCount':len(rows),'maxRoundoffMm':maximum,'claim':'Every exported triangle corner equals the source registered mesh corner plus only the declared whole-leg Y translation, to binary STL float32 precision. No component scaled or relative leg geometry changed.','rows':rows,'manifestSha256':hashlib.sha256((D/'fusion-import-manifest.json').read_bytes()).hexdigest()};(D/'mesh-export-readback.json').write_text(json.dumps(r,indent=2)+'\n');print(len(rows),maximum)
