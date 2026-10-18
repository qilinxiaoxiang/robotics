"""Adafruit3006 official STEP plus explicit missing-terminal receiving envelope."""
from pathlib import Path
import json,hashlib,numpy as np,trimesh,manifold3d as mf,cadquery as cq
D=Path(__file__).resolve().parent
s=cq.importers.importStep(str(D/'sources/adafruit-3006.step')).val();v,f=s.tessellate(.06);m=trimesh.Trimesh([[q.x,q.y,q.z] for q in v],f,process=True)
sol=[]
for q in s.Solids():
 v,f=q.tessellate(.06);t=trimesh.Trimesh([[x.x,x.y,x.z] for x in v],f,process=True);sol.append(mf.Manifold(mf.Mesh(np.asarray(t.vertices,np.float32),np.asarray(t.faces,np.uint32))))
# Original official board CAD omits the terminal block. EagleX1 uses7x7mm
# footprint centered[8.79,15.594]. Reserve8x8mm incl. .5mm per side, height10.4mm
# above1.57mm PCB surface (total11.97mm, inside prior12mm receiving height).
terminal=mf.Manifold.cube([8,8,10.4],center=True).translate([8.79,15.594,6.77]);solid=mf.Manifold.batch_boolean(sol+[terminal],mf.OpType.Add);a=solid.to_mesh();m=trimesh.Trimesh(np.asarray(a.vert_properties)[:,:3],np.asarray(a.tri_verts),process=True);m.export(D/'adafruit3006-with-terminal-receiving-local.stl')
(D/'amp-model-evidence.json').write_text(json.dumps({'officialStepUrl':'https://github.com/adafruit/Adafruit_CAD_Parts/tree/main/3006%20MAX98357','officialBoardUrl':'https://github.com/adafruit/Adafruit-MAX98357-I2S-Amp-Breakout','sourceStepSha256':hashlib.sha256((D/'sources/adafruit-3006.step').read_bytes()).hexdigest(),'sourceBoardSha256':hashlib.sha256((D/'sources/adafruit-3006.brd').read_bytes()).hexdigest(),'nominalBoardMm':[17.78,19.05,1.57],'terminalFootprintFromEagleMm':[7,7],'terminalReceivingSizeMm':[8,8,10.4],'terminalReceivingCenterMm':[8.79,15.594,6.77],'terminalHeightMeasured':False,'scope':'Full official bare assembly CAD plus explicit12mm-total-height terminal receiving allowance. Optional7pin header absent: approved harness solders directly to amplifier pads. Physical terminal dimensions, wire exit and screwdriver access remain to verify.'},indent=2)+'\n')
