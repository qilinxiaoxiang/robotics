from pathlib import Path
import cadquery as cq,json,hashlib
from OCP.gp import gp_Trsf
D=Path(__file__).resolve().parent;R=D.parents[1];P=R/'fastener-audit/sources/X330_3d.stp'
s=cq.importers.importStep(str(P)).val();solids=s.Solids();rows=[]
rows=[None]*12
# Native relative motor frame already established by the source generator/idler registration.
S=[[0,0,-1,-8],[-1,0,0,0],[0,1,0,0],[0,0,0,1]]
tr=gp_Trsf();tr.SetValues(*[q for row in S[:3] for q in row]);loc=cq.Location(tr)
compound=cq.Compound.makeCompound([solids[i] for i in list(range(10))+[13,14]]).moved(loc)
cq.exporters.export(compound,str(D/'xl330-registered-motor-local.step'))
for i in [13,14]:cq.exporters.export(solids[i].moved(loc),str(D/f'header-{i}-motor-local.step'))
print(json.dumps({'exportedComponents':len(rows),'nativeLocalStep':str(D/'xl330-registered-motor-local.step')},indent=2))
