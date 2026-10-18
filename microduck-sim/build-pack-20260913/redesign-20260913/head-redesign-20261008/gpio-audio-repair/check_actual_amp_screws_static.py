"""New cap/amp mounting features vs frozen model parts, one solid at a time."""
import argparse,json,os,gc
from pathlib import Path
import unify_amp_cap as u
import bounded_amp_static as b
p=argparse.ArgumentParser();p.add_argument('--target',choices=['screw0','screw1'],required=True);a=p.parse_args();u.core.guarded_import();c=u.core
files={'cap':'cap-current-audio-usb-world.stl','post0':'amp-new-post-0-world.stl','post1':'amp-new-post-1-world.stl','screws':'amp-new-two-screws-world.stl'};targetfile=u.OUT/files['screws'];pieces=sorted(u.load(targetfile).decompose(),key=lambda p:p.bounding_box()[1]);assert len(pieces)==2;target=pieces[int(a.target[-1])];index=b.rows()
for key in ['fullFFC','pi_csi_end','csi_free_straight_receiving']:index.pop(key,None)
index['amplifier']={'key':'amplifier','path':u.D/'amp16z2-placement-world.stl'};index['head_cap']={'key':'head_cap','path':u.OUT/files['cap']};index['curved_cap_hardware']={'key':'curved_cap_hardware','path':u.OUT/'hardware-current-amp-world.stl'}
inputs=[Path(__file__),u.D/'bounded_amp_static.py',u.D/'amp16_aabb_precheck.py',c.SOURCE,c.CONFIG,b.C/'local-candidate-manifest.json',targetfile];inputs.extend(r['path'] for r in index.values() if r.get('path'))
bindings=u.inputs(inputs);tb=[list(target.bounding_box())[:3],list(target.bounding_box())[3:]];rows=[];trace=u.OUT/f'static-{a.target}.jsonl';reportpath=trace.with_suffix('.json');paired=None
for i in range(2):
 r=json.loads((u.OUT/f'amp-new-post-{i}.json').read_text());xyz=r['holeBottomMm'];s=c.mf.Manifold.cylinder(6.43+2e-5,1.25+1e-5,circular_segments=48).translate([xyz[0],xyz[1],xyz[2]-1e-5]);paired=s if paired is None else paired+s
with trace.open('w') as f:
 for key,row in index.items():
  self_reason=None
  if a.target in ['cap','post0','post1'] and key=='head_cap':self_reason='same unified cap solid; added post is a named subset'
  if a.target.startswith('screw') and key=='curved_cap_hardware':self_reason='same two screw subset in complete hardware aggregate'
  if self_reason:
   rows.append({'key':key,'selfRepresentation':self_reason});continue
  bb=b.rowbounds(row);gap=b.compare(tb,bb)
  if not gap['aabbOverlap']:result={'key':key,'aabbDisjoint':True,'outsideInterfaceMm3':0}
  else:
   obstacle=u.load(row['path']) if row.get('path') else c.solid(row)
   intersection=target^obstacle;nominal=u.vol(intersection);allowed=(a.target in ['cap','post0','post1'] and key=='curved_cap_hardware') or (a.target.startswith('screw') and key=='head_cap');outside=u.vol(intersection-paired) if allowed else nominal
   result={'key':key,'aabbDisjoint':False,'nominalOverlapMm3':nominal,'outsideInterfaceMm3':outside,'allowedInterface':'Only two nominal Ø2.5 tap shafts within6.43mm post engagement' if allowed else None};del obstacle,intersection;gc.collect()
  result['failed']=result['outsideInterfaceMm3']>1e-4;rows.append(result);f.write(json.dumps(result)+'\n');f.flush();os.fsync(f.fileno())
  if result['failed']:break
complete=len(rows)==len(index);report={'target':a.target,'completed':complete,'passed':complete and not any(r.get('failed') for r in rows),'rows':rows,'inputHashes':bindings,'integrationReady':False,'excludedUnreleasedCableGeometry':['fullFFC','pi_csi_end','csi_free_straight_receiving','old speaker wires','old PiUSB proxy'],'boundary':'Static modeled-part check. Exact mating shaft contact only; no blanket part-contact waivers. Full FFC/USB/wires, source screws not represented as meshes, full229 motion and closure remain separate.'};c.atomic_json(reportpath,report);print(json.dumps({'target':a.target,'complete':complete,'passed':report['passed'],'pairs':len(rows),'failures':[r for r in rows if r.get('failed')]}));raise SystemExit(0 if report['passed'] else 2)
