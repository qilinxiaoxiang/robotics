"""Continuous-Z entry by exhaustive spatial partition, exact seat-column bounds."""
import json,gc
from pathlib import Path
import bounded_amp_check as c
import precision_mesh as pm
D=Path(__file__).resolve().parent;O=D/'speaker-rewire';A=D/'cap-amp16z2';c.guarded_import();cf=A/'cap-current-audio-usb-world.stl';af=D/'amp16z2-closed-receiving-world.stl';pfs=[A/f'amp-new-post-{i}-world.stl' for i in [0,1]];cap=pm.load(c,cf);amp=pm.load(c,af);columns=[];seatrows=[]
for i,f in enumerate(pfs):
 post=pm.load(c,f);b=list(post.bounding_box());seat=b[2];column=c.mf.Manifold.cube([b[3]-b[0]+.02,b[4]-b[1]+.02,100]).translate([b[0]-.01,b[1]-.01,100]);columns.append(column);part=amp^column;ab=list(part.bounding_box());assert ab[5]-seat<.00001
 capcol=cap^column;lower=c.mf.Manifold.cube([100,100,seat-100-.00001]).translate([0,-50,100]);below=capcol^lower;v=max(0,float(below.volume()));assert v<1e-8
 seatrows.append({'post':i,'columnBoundsMm':list(column.bounding_box()),'ampInsideColumnBoundsMm':ab,'seatZmm':seat,'finalSurfaceOffsetMm':ab[5]-seat,'completeCapBelowSeatMinus10nmMm3':v,'allowedBelowSeatVolumeCapMm3':1e-8,'proof':'Entire amplifier within this XY column is below the cap seat for all translations up to the final10nm numerical interval. Complete cap material below seat is bounded by1e-8mm3, not ignored by identity. At the final endpoint, contact is separately bounded to original post seats by source-fingerprint receipt.'})
remaining=cap-columns[0]-columns[1];rows=[];r={'integrationReady':False,'passed':False,'inputHashes':c.fingerprint([Path(__file__),cf,af,*pfs,O/'prewire-entry-amplifier.json']),'seatColumnProof':seatrows,'partition':'The full cap is partitioned into two post-AABB columns enlarged0.01mm inXY and their complement; no cap volume omitted. Entire columns tested by vertical support/complete below-seat volume bound, complement by continuous-distance bound.','translationWorldMm':[[0,0,-40],[0,0,0]],'stepMm':.25,'rows':rows};out=O/'amplifier-continuous-entry.json'
for i in range(161):
 z=-40+i*.25;target=amp.translate([0,0,z]);gap=float(target.min_gap(remaining,2));v=max(0,float((target^remaining).volume()));rows.append({'offsetMm':z,'minimumGapMm':gap,'volumeMm3':v});c.atomic_json(out,r)
 if gap<=.125 or v>1e-6:break
 del target;gc.collect()
r['minimumComplementGapMm']=min(x['minimumGapMm'] for x in rows);r['continuousComplementGapLowerBoundMm']=r['minimumComplementGapMm']-.125;r['passed']=len(rows)==161 and r['continuousComplementGapLowerBoundMm']>0 and all(x['volumeMm3']<=1e-6 for x in rows) and json.loads((O/'prewire-entry-amplifier.json').read_text())['passed'];r['finalContactReceipt']='prewire-entry-amplifier.json';c.atomic_json(out,r);print(json.dumps({k:v for k,v in r.items() if k not in ['rows','inputHashes']}));raise SystemExit(0 if r['passed'] else 2)
