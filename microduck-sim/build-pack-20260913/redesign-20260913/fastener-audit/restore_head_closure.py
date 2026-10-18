"""Restore the original upper cap screw boss lost during cowl hollowing.
Reconstructs a bounded annular boss on the measured original top screw axis.
Called by check_usb_service_window.py before its existing USB cut. No Pi shift.
"""
from pathlib import Path
import sys,json,hashlib
import numpy as np,trimesh
O=Path(__file__).resolve().parent;R=O.parent;S=R.parent.parent
H=S/'hardware-design-20260912/whole-robot-20260912/electrical/head-layout';sys.path.insert(0,str(H))
from geometry import man,tri,obstacles

def restore_upper_boss(current):
 original=next(m for n,m,solid in obstacles() if n=='top_head_shell')
 t=np.eye(4);t[:3,:3]=[[0,0,1],[0,1,0],[-1,0,0]];t[:3,3]=[4.85,0,31.5]
 roi=trimesh.creation.cylinder(radius=2.3,height=12.3,sections=96,transform=t)
 # Parametric reconstruction uses measured original pilot diameter2.1mm and
 # boss outer radius2.3mm. Avoid re-union of coplanar triangulated source slivers.
 bore=trimesh.creation.cylinder(radius=1.05,height=13.3,sections=96,transform=t)
 original_boss=man(roi)-man(bore)
 before=man(current);restored=(before+original_boss)-man(bore);added=restored-before
 restored=restored.simplify(0.00001)
 new=tri(restored)
 report={'problem_ids':['P5','P6'],'repair':'Restore original top mounting boss, removed by cowl inner-box subtraction','frame':'jaw_soft_mm','axis':[1,0,0],'hole_yz':[0,31.5],'roi_x':[-1.3,11.0],'roi_radius_mm':2.3,'original_boss_volume_mm3':float(original_boss.volume()),'added_volume_mm3':float(added.volume()),'added_mesh':'head-closure-restored-material.stl','watertight':bool(new.is_watertight),'solids':len(new.split()),'source_geometry':'original top_head_shell section measured pilot radius1.05 atY0Z31.5; reconstructed continuous annular boss, x-1.3..11 outerradius2.3; no thread geometry','source_caps_unchanged':True}
 tri(added).export(O/'head-closure-restored-material.stl')
 (O/'electronics-head-closure-restoration.json').write_text(json.dumps(report,indent=2)+'\n')
 if not new.is_watertight or len(new.split())!=1:raise ValueError('Restored boss must connect to existing cap as single solid')
 return new
