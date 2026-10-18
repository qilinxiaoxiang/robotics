import cadquery as cq,json
from pathlib import Path
P=Path(__file__).resolve();R=P.parents[3];S=R.parents[1]/'hardware-design-20260912/whole-robot-20260912/electrical/sources/openrb-official.step'
# Explicit canonical project root; no whole-robot scene import.
S=Path('/Users/xiangzheng/code/robotics/microduck-sim/hardware-design-20260912/whole-robot-20260912/electrical/sources/openrb-official.step')
solids=cq.importers.importStep(str(S)).solids().vals();out=[]
for i in [47]:
 for e in solids[i].Edges():
  if e.geomType()=='CIRCLE':
   try:out.append({'solid':i,'center':e.arcCenter().toTuple(),'radius':e.radius()})
   except Exception:pass
(P.parent/'terminal-source-circles.json').write_text(json.dumps({'source':str(S),'solidCount':len(solids),'circles':out},indent=2));print(json.dumps(out))
