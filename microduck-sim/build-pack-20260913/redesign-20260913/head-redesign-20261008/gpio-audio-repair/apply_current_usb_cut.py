"""Apply root-owned USB specification to current audio cap using exact Mesh64 IO."""
import json,os
from pathlib import Path
import unify_amp_cap as u
u.core.guarded_import();c=u.core;S=u.U/'lowered-usb-service-opening-spec.json';spec=json.loads(S.read_text());posefile=Path(spec['poseFile']);assert c.sha(posefile)==spec['poseSha256'];pose=json.loads(posefile.read_text());capfile=u.OUT/'cap-new-amp-before-final-openings-world.stl';r=u.current_receipt(u.OUT/'cap-new-amp-before-final-openings.json');assert c.sha(capfile)==r['outputSha256']
R=c.np.column_stack([spec['widthAxis'],spec['heightAxis'],spec['axis']]);assert c.np.allclose(R.T@R,c.np.eye(3)) and c.np.linalg.det(R)>.999

def placed(start,length,width,height):
 T=c.np.eye(4);T[:3,:3]=R;T[:3,3]=c.np.array(start)+R[:,2]*length/2
 return c.mf.Manifold.cube([width,height,length],True).transform(T[:3])
cap=u.load(capfile);cut=placed(spec['cutStartMm'],spec['cutLengthMm'],spec['cutWidthMm'],spec['cutHeightMm']);new=cap-cut;assert len(new.decompose())==1
out=u.OUT/'cap-current-audio-usb-world.stl';io=u.export(new,out);new=u.load(out);added=u.vol(new-cap);assert added<1e-4
plug=placed(pose['usbShoulderWorldMm'],25,8,18);rows=[];trace=u.OUT/'current-usb-entry.jsonl'
with trace.open('w') as f:
 for i in range(121):
  offset=30-i*.25;current=plug.translate(R[:,2]*offset);before=u.vol(current^cap);after=u.vol(current^new);row={'offsetMm':offset,'beforeMm3':before,'afterMm3':after};rows.append(row);f.write(json.dumps(row)+'\n');f.flush();os.fsync(f.fileno())
passed=all(r['afterMm3']<1e-5 for r in rows);report={'integrationReady':False,'localEntryClear':passed,'entrySamples':121,'negativeControlReproduced':any(r['beforeMm3']>1e-5 for r in rows),'addedMm3':added,'removedMm3':u.vol(cap^cut),'io':io,'outputSha256':c.sha(out),'inputHashes':u.inputs([Path(__file__),u.U/'apply_usb_service_opening.py',S,posefile,capfile,u.OUT/'cap-new-amp-before-final-openings.json']),'entryTraceSha256':c.sha(trace),'boundary':'Same root USB cut parameters and121 translation samples. Precision-only IO change. No neck portal added; final static and articulated checks separate.'};c.atomic_json(u.OUT/'current-usb-cut-report.json',report);print(json.dumps({k:v for k,v in report.items() if k!='inputHashes'}));assert passed
