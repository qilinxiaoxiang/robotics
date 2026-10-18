"""Explicit populated-board receiving envelopes; distinguishes drawings from assumptions."""
from pathlib import Path
import json,base64,hashlib,numpy as np,trimesh,manifold3d as mf
D=Path(__file__).resolve().parent;data=json.loads((D.parent.parent/'leg-guide-20261006/full-build-data.json').read_text());P={p['key']:p for p in data['parts']}
def box(c,d):return trimesh.creation.box(d).apply_translation(c)
def man(m):return mf.Manifold(mf.Mesh(np.asarray(m.vertices,np.float32),np.asarray(m.faces,np.uint32)))
def decode(k):
 p=P[k];return trimesh.Trimesh(np.frombuffer(base64.b64decode(p['positionB64']),'<f4').reshape(-1,3),np.frombuffer(base64.b64decode(p['indexB64']),'<u4').reshape(-1,3),process=True)
B=np.array(P['pi']['sourceTransformWorld'])
# Same board pose as current Zero reference. World -X points into the head.
# Full populated board, installed GPIO housing/wire exit, and solder tails are
# independent clearance bodies, not a cosmetic slab. Heights are receiving
# limits pending measurement, not invented physical measurements.
rows=[('zero_w_components',[15.435,-.011,-57.31],[28,63,3.8],'Existing conservative component height4mm and board edge clearance; USB/HDMI ports modeled separately.'),('zero_w_header_and_housing',[3.935,-.011,-51.71],[7,52,15],'15mm complete mating housing plus lead exit; bounds standard8.5mm header but actual soldered header must be measured.'),('zero_w_gpio_solder_tails',[3.935,-.011,-61.81],[5.2,50.8,2.0],'2mm solder-tail receiving allowance behind PCB; actual protrusion unknown.'),('zero_w_usb_moulding',[42.935,8.9,-56.1],[25,18,8],'Existing25x18x8mm cable receiving envelope; not supplier-warranted moulding.'),('zero_w_csi_latch_exit',[15.435,35.49,-56.1],[12,6,6],'6mm latch/FFC initial exit receiving envelope; full bend route remains pending.')]
parts={};details={}
for k,c,d,meaning in rows:
 m=box(c,d).apply_transform(B);m.export(D/(k+'-world.stl'));parts[k]=m;details[k]={'bodyCenterMm':c,'bodySizeMm':d,'worldBoundsMm':m.bounds.tolist(),'evidenceBoundary':meaning}
fixed={k:decode(k) for k in ['head_bottom','jaw_support','motor14','motor15','jaw_frame','upper_pad','lower_pad']};fixed['head_cap']=trimesh.load(D/'community-curved-head-world.stl',force='mesh')
for k,f in [('camera_board','camera-in-eye-world.stl'),('face_panel','face-eye-camera-clearance-world.stl'),('eye_trim','eye-trim-camera-clearance-world.stl')]:fixed[k]=trimesh.load(D.parent/f,force='mesh')
hits={k:{q:float((man(m)^man(o)).volume()) for q,o in fixed.items() if float((man(m)^man(o)).volume())>1e-4} for k,m in parts.items()}
# Pi3 B v1.2 board itself, before USB/Ethernet/header heights, is a decisive
# negative control for reusing the present vertical Zero pose; not all poses.
pi=decode('pi');ctr=pi.bounds.mean(0);b3=box(ctr,[1.6,85,56]);b3.export(D/'pi3b-pcb-at-zero-pose-NEGATIVE-world.stl');b3hits={q:float((man(b3)^man(o)).volume()) for q,o in fixed.items() if float((man(b3)^man(o)).volume())>1e-4}
report={'boardIdentities':{'small':'First-generation Raspberry Pi Zero W with soldered40-pin header; possible factory WH','large':'Raspberry Pi3 ModelB v1.2'},'checked':'2026-10-08','officialSources':[{'url':'https://datasheets.raspberrypi.com/rpizero/raspberry-pi-zero-w-mechanical-drawing.pdf','facts':'65x30mm board;58x23mm mounting pattern; no header height dimension in drawing.'},{'url':'https://datasheets.raspberrypi.com/rpi3/raspberry-pi-3-b-mechanical-drawing.pdf','facts':'RPI-3B-V1_2 drawing:85x56mm board, USB connector height16mm, Ethernet13.5mm, GPIO8.5mm, HDMI6.5mm; CSI15pin. These populated components must be included in any Pi3 layout.'}],'zeroWReceivingEnvelopes':details,'zeroWExistingPoseIntersectionsMm3':hits,'zeroWPhysicalDimensionsVerified':False,'pi3BAtExistingZeroPose':{'pcbDimensionsMm':[85,56,1.6],'intersectionsBeforeComponentsMm3':b3hits,'fits':not bool(b3hits),'scope':'Rejects reusing the Zero pose only. Does not prove all rotated Pi3 layouts impossible.'},'zeroWFullCableRoutingVerified':False}
(D/'board-envelope-review.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'zeroWHits':hits,'pi3bSamePoseHits':b3hits}))
