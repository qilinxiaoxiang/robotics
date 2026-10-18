"""Local cap opening for one moulded USB data plug. Envelope is a design limit."""
from pathlib import Path
import sys,json,hashlib
import numpy as np,trimesh
O=Path(__file__).resolve().parent;P=O.parent;D=P.parent/'hardware-design-20260912/whole-robot-20260912/electrical/head-layout';F=D/'final'
sys.path.insert(0,str(D))
from geometry import man,box,add_pi,obstacles,hits
source=P/'assembly/mouth-clearance/head-cap-mouth-clearance-assembly.stl'
old=trimesh.load(source,force='mesh')
window=box([42.5,8.9,-56.1],[9,20,10])
import importlib.util
_spec=importlib.util.spec_from_file_location('restore_head_closure',O/'fastener-audit/restore_head_closure.py')
_restore=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(_restore)
cap=trimesh.boolean.difference([_restore.restore_upper_boss(old),window],engine='manifold')
cap.export(O/'head-cap-usb-service-body.stl')
# Retain the existing cap's assembly-to-print orientation, then ground the new part.
ref=json.loads((P/'assembly/print-manifest.json').read_text())
T=np.asarray(json.loads((F/'validation.json').read_text())['print_transforms_assembly_to_print_mm']['head_cap'])
pr=cap.copy().apply_transform(T);pr.apply_translation(-pr.bounds[0]);pr.export(O/'head-cap-usb-service-print.stl')
obs=add_pi(obstacles(True))
for name in ['audio_carrier_assembly','head_fastener_reference_assembly','camera_pitch_foot_assembly','camera_cradle_assembly','openrb_actual_box_proxy_assembly','amp_reservation_assembly','speaker_reservation_assembly']:
    m=trimesh.load(F/(name+'.stl'),force='mesh');obs.append((name,m,man(m)))
obs.append(('revised_head_cap',cap,man(cap)))
# Entire chosen bounding box starts at the same external connector datum as old checker.
plug=box([42.935,8.9,-56.1],[25,18,8]);plug.export(O/'usb-data-plug-acceptance-envelope.stl')
new_hits=hits(man(plug),obs)
negative_tall_hits=hits(man(box([42.935,8.9,-56.1],[25,18,9])),obs)
old_hits=hits(man(plug),[('old_head_cap',old,man(old))])
removed=trimesh.boolean.difference([old,cap],engine='manifold')
fast=trimesh.load(F/'head_fastener_reference_assembly.stl',force='mesh')
fv=max(0.,float((man(removed)^man(fast)).volume()))
report={'scope':'One MicroB data plug; Pi receives power through GPIO so adjacent PWR port stays empty','source_cap':str(source),'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'updated_cap':str(O/'head-cap-usb-service-print.stl'),'updated_sha256':hashlib.sha256((O/'head-cap-usb-service-print.stl').read_bytes()).hexdigest(),'supplier':'SC0727 publishes overall cable length, not complete moulded-plug dimensions','declared_receiving_envelope_xyz_mm':[25,18,8],'envelope_meaning':'Acceptable external plug bounding box for this printed opening; not a measured or manufacturer-warranted SC0727 size','window_yz_mm':[20,10],'window_center_jaw_soft_mm':[42.5,8.9,-56.1],'old_cap_hits':old_hits,'new_envelope_hits':new_hits,'negative_9mm_tall_hits':negative_tall_hits,'removed_volume_mm3':removed.volume,'removed_volume_vs_fasteners_mm3':fv,'watertight':bool(cap.is_watertight),'solids':len(cap.split()),'print_bounds_mm':pr.bounds.tolist(),'physical_tests':0,'passed':not new_hits and bool(negative_tall_hits) and bool(old_hits) and fv<.005 and cap.is_watertight and len(cap.split())==1,'received_part_check':'Before final cap closure, confirm the actual SC0727 moulding plus insulation lies inside the declared 25 x 18 x 8 mm envelope; use a smooth service loop outside the cap. If only wider or longer, revise the local window from measured dimensions. A plug taller than 8 mm requires reviewing the internal Pi/controller spacing; enlarging the plastic window alone cannot resolve an internal collision.'}
(O/'usb-service-window-verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2));sys.exit(0 if report['passed'] else 1)
