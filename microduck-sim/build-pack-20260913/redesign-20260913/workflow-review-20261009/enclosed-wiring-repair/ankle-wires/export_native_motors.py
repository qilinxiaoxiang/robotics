from pathlib import Path
import json,hashlib,cadquery as cq
from OCP.gp import gp_Trsf
D=Path(__file__).resolve().parent;M=D.parent/'motor-wires';W=D.parents[1];source=W/'leg-ports/xl330-registered-motor-local.step';top=json.loads((M/'active-topology.json').read_text());native=cq.importers.importStep(str(source)).val().Solids();assert len(native)==12
out=[];folder=D/'native-motors';folder.mkdir(exist_ok=True)
for motor in [1,2,6,7]:
 p=next(v for v in top['ports'].values()if v['motor']==motor);T=p['transform'];tr=gp_Trsf();tr.SetValues(*[v for r in T[:3]for v in r]);loc=cq.Location(tr)
 for i,s in enumerate(native):
  q=s.moved(loc);assert q.isValid() and q.Volume()>0;f=folder/f'motor{motor}-solid{i:02d}.stl';cq.exporters.export(q,str(f),tolerance=.008,angularTolerance=.12);out.append({'motor':motor,'solid':i,'file':str(f),'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'volumeMm3':q.Volume(),'worldTransform':T,'sourceBody':i if i<10 else i+3})
(folder/'manifest.json').write_text(json.dumps({'sourceFile':str(source),'sourceSha256':hashlib.sha256(source.read_bytes()).hexdigest(),'parts':out},indent=2));print(len(out))
