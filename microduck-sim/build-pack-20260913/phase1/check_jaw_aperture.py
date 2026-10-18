"""Measure geometric mouth opening at the proposed small foam gripping patch."""
from pathlib import Path
import json
import sys
import numpy as np
from scipy.spatial.transform import Rotation

P=Path(__file__).resolve().parent
OLD=P.parents[1]/'hardware-design-20260912/whole-robot-20260912'
sys.path.insert(0,str(OLD/'assembly'))
from assembly_fk import fk,raw
meshes={g['mesh']:raw(g['mesh']).apply_transform(g['local']) for g in fk()[1]
    if g['body']=='jaw_soft' and g['mesh'] in ['jaw_soft','soft_mouth_top']}
rows=[]
for degrees in [0,10,20]:
    lower=meshes['jaw_soft'].copy()
    pivot=np.array([3.,0,-18.])
    r=Rotation.from_euler('y',degrees,degrees=True).as_matrix()
    transform=np.eye(4);transform[:3,:3]=r;transform[:3,3]=pivot-r@pivot
    lower.apply_transform(transform)
    gaps=[]
    for y in [-10,0,10]:
        for z in [-55,-60,-65]:
            lower_hits=lower.ray.intersects_location([[-100,y,z]],[[1,0,0]],multiple_hits=True)[0]
            upper_hits=meshes['soft_mouth_top'].ray.intersects_location([[-100,y,z]],[[1,0,0]],multiple_hits=True)[0]
            assert len(lower_hits)>=2 and len(upper_hits)>=2, (degrees,y,z)
            gaps.append({'y_mm':y,'z_mm':z,'gap_mm':float(upper_hits[:,0].min()-lower_hits[:,0].max())})
    rows.append({'opening_degrees':degrees,'samples':gaps,'minimum_gap_mm':min(x['gap_mm'] for x in gaps)})
report={'method':'Ray intersections with both exact transformed lip meshes along local X; sampled 20mm-wide by10mm-deep central lip patch. Opening is measured between facing surfaces.',
    'target_candidate':{'grip_thickness_mm':8,'grip_width_mm':20,'grip_depth_mm':10,'maximum_mass_g':2,'material':'soft foam, actual mass and compression to be measured'},
    'rows':rows,'opening20_clears_8mm_candidate_at_all9_samples':rows[-1]['minimum_gap_mm']>8,
    'scope':'Geometric aperture only. Does not validate insertion swept volume, attachment, friction, clamping force, physical printing or robot reaching.'}
(P/'jaw-aperture.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'minimum_gap_mm_by_degrees':{r['opening_degrees']:r['minimum_gap_mm'] for r in rows},'passed':report['opening20_clears_8mm_candidate_at_all9_samples']}))
