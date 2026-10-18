"""Bound regression: clear bead, invading bead, nozzle coordinate frame."""
from pathlib import Path
import json
import numpy as np
from audit_native_bore_envelopes import envelope_intersections
from native_material_frame import material_frame_paths
G=Path(__file__).resolve().parent
results=[]
for axis in ([0,0,1],[0,1,0]):
    # A0.4x0.2 rounded bead parallel to Y (vertical bore) or Z's horizontal
    # projection (horizontal bore); deliberately deep intrusion/clear separation.
    p0=np.array([[.95,-1,0.0],[1.25,-1,0.0]])
    p1=np.array([[.95,1,0.0],[1.25,1,0.0]])
    overlap,margin,_=envelope_intersections(p0,p1,np.array([.4,.4]),np.array([.2,.2]),np.array(axis,dtype=float),np.zeros(3),1.0,.2,np.zeros(2),np.array(['Outer wall','Outer wall']))
    assert 0 in overlap and 1 not in overlap,(axis,overlap,margin)
    results.append(dict(axis=axis,known_invading_segment_rejected=True,known_clear_segment_passed=True,margins_mm=margin.tolist()))
# The real native Bambu command frame differs from deposited material by+2Y.
paths={'part':{.2:[dict(points=[[10.,20.],[11.,20.]])]}}
shifted,offset=material_frame_paths(paths,{'extruder_offset':['0x2']},'G90\n; start printing object part id:0 copy 0\nG1 X10 Y20 E1\n; stop printing object part id:0 copy 0\n')
assert np.allclose(shifted['part'][.2][0]['points'][0],[10.,22.])
results.append(dict(native_frame_offset_mm=offset,material_coordinate_readback_correct=True))
report=dict(passed=True,tests=results,physical_fit_verified=False)
(G/'native-envelope-regression.json').write_text(json.dumps(report,indent=2)+'\n')
print('NATIVE_ENVELOPE_REGRESSION_PASS')
