from pathlib import Path
import json,hashlib
import cadquery as cq
from OCP.BRepAdaptor import BRepAdaptor_Surface
O=Path(__file__).resolve().parent; S=O/'sources';out={}
for name in ['X330_3d.stp','fpx330-s101.stp']:
 shape=cq.importers.importStep(str(S/name)).val(); cylinders=[]
 for f in shape.Faces():
  if f.geomType()!='CYLINDER':continue
  c=BRepAdaptor_Surface(f.wrapped).Cylinder();p=c.Location();d=c.Axis().Direction();bb=f.BoundingBox()
  if name=='X330_3d.stp': keep=abs(abs(p.X())-8)<1e-5 and min(abs(p.Y()-7.5),abs(p.Y()+22.5))<1e-5 and c.Radius()<1.01 and abs(d.Z())>.99
  else:keep=abs(abs(p.X())-15)<1e-5 and abs(p.Y()+2)<1e-5 and c.Radius()<1.03 and abs(d.Z())>.99
  if keep:cylinders.append(dict(radius_mm=round(c.Radius(),5),axis_point_mm=[p.X(),p.Y(),p.Z()],z_range_mm=[round(bb.zmin,5),round(bb.zmax,5)]))
 out[name]={'sha256':hashlib.sha256((S/name).read_bytes()).hexdigest(),'solid_count':len(shape.Solids()),'cylinders':cylinders}
rows=out['X330_3d.stp']['cylinders'];assert any(r['radius_mm']==.8 and r['z_range_mm']==[-15.,0.] for r in rows)
assert any(r['radius_mm']==1 and r['z_range_mm']==[0.,3.5] for r in rows)
assert any(r['radius_mm']==1 and r['z_range_mm']==[-19.5,-15.] for r in rows)
f=out['fpx330-s101.stp']['cylinders'];assert all(abs(abs(r['z_range_mm'][1]-r['z_range_mm'][0])-1.3)<1e-4 for r in f)
out.update(passed=True,case_width_mm=23,front_clearance_collar_mm=3.5,rear_clearance_collar_mm=4.5,case_pilot_diameter_mm=1.6,case_pilot_length_mm=15,official_frame_case_screw='M2 x 8 TAP',official_frame_effective_web_mm=1.3,official_frame_insertion_mm=6.7,official_frame_thread_engagement_mm={'front':3.2,'rear':2.2},horn_max_insertion_mm=3.0,source_to_reference_motor_transform=[[0.,0.,-1.,-8.],[-1.,0.,0.,0.],[0.,1.,0.,0.],[0.,0.,0.,1.]],scope='Geometrical dimensions and manufacturer example, not a joint strength or physical fit test.')
(O/'manufacturer-geometry.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
