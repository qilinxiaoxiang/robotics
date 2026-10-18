"""Read actual Chrome receipts against source data. Never controls the browser."""
from pathlib import Path
import json,hashlib,collections,sys
import numpy as np
D=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
array=lambda s,k:json.loads(s.get(k,'[]'))
def main():
    ui=json.loads((D/'ui-acceptance-20261007.json').read_text());data=json.loads((D/'full-build-data.json').read_text());w=json.loads((D/'wiring-guide-data.json').read_text());paths=json.loads((D/'assembly-path-investigation.json').read_text())
    errors=[];results={};mods={m['id']:m for m in data['modules']};parts={p['key']:p for p in data['parts']};screws={c['id']:c for c in data['screws']}
    def ck(value,msg):
        if not value:errors.append(msg)
    hashes=[]
    for name,want in ui['artifactHashes'].items():
        got=sha(D/name);hashes.append({'file':name,'expected':want,'actual':got,'matched':want==got});ck(got==want,'UI receipt artifact changed: '+name)
    results['artifactBindings']=hashes
    seen=[];ops=[]
    for r in ui['operations']:
        m=mods[r['module']];i=int(r['state']['operation']);op=m['operations'][i];seen.append(op['id']);context=set(m['partKeys'])-set(m['ownedPartKeys']);expected=context|{k for o in m['operations'][:i+1] for k in o['add']}
        if op.get('isolatedPartKeys'):expected&=set(op['isolatedPartKeys'])
        actual=set(array(r['state'],'visibleParts'));want_screws=set(op['screwIds']) if op['kind']=='fasten' else set();actual_screws=set(array(r['state'],'visibleScrews'))
        ck(actual==expected,'Visible part mismatch: '+op['id']);ck(actual_screws==want_screws,'Visible screw mismatch: '+op['id']);ck(r['title']==op['title'],'Operation title mismatch: '+op['id'])
        if op.get('animationBlockedReason'):ck(r['blocked'] and not r['hasPlay'],'Blocked physical fit incorrectly animated: '+op['id'])
        ops.append({'operation':op['id'],'parts_equal':actual==expected,'screws_equal':actual_screws==want_screws,'blocked_as_required':not op.get('animationBlockedReason') or r['blocked'] and not r['hasPlay']})
    allops={op['id'] for m in mods.values() for op in m['operations']};ck(set(seen)==allops and len(seen)==len(set(seen)),'UI operations are not all76 exactly once');results['operations']=ops
    station_sets=[]
    for r in ui['washers']:
        start,end=r['start']['state'],r['end']['state'];visible=set(array(end,'visibleParts'));hardware=visible&{p['key'] for p in data['parts'] if p['key'].startswith('washer')};ck(bool(hardware),'Washer inspection has no washer: '+r['name']);station_sets.append(hardware)
        ck(start.get('motionProgress')=='0.000' and end.get('motionProgress')=='1.000','Washer endpoints not visited: '+r['name']);ck(not array(start,'visibleScrews') and not array(end,'visibleScrews'),'Inspection marker dataset not cleared: '+r['name'])
        moves=array(end,'motionParts');ck(bool(moves) and all(np.linalg.norm(q['offset'])<1e-9 for q in moves),'Washer/nut not seated at end: '+r['name'])
        ck(any(np.linalg.norm(q['offset'])>1 for q in array(start,'motionParts')),'Washer stack was not visibly separated: '+r['name'])
    expectedwashers={p['key'] for p in data['parts'] if p['key'].startswith('washer')};actualwashers=set().union(*station_sets);ck(actualwashers==expectedwashers,'Washer inspection misses a specified washer');results['washerStations']={'count':len(station_sets),'all8washers_covered':actualwashers==expectedwashers}
    pby={p['id']:p for p in paths['paths']};preports=[]
    for r in ui['paths']:
        a,b=r['start']['state'],r['end']['state'];pid=b['pathId'];p=pby[pid];anim=p['animation'];ck(a['pathId']==pid,'Inspection path changed between endpoints');ck(not array(a,'visibleScrews') and not array(b,'visibleScrews'),'Path marker dataset not cleared: '+pid)
        want=set(anim['fixedKeys'])|set(anim['movingKeys']);ck(set(array(b,'visibleParts'))==want,'Path shows wrong source parts: '+pid)
        stop=anim.get('stopAtT',1);ck(abs(float(b['pathFraction'])-stop)<1e-6,'Path did not stop at bound: '+pid)
        isblocked=p['result']=='rigid_blocked';ck((b['contactStopped']=='true')==isblocked,'Contact stop flag wrong: '+pid)
        if isblocked:ck(any(np.linalg.norm(q['offset'])>1 for q in array(b,'motionParts')),'Blocked path falsely reaches seated pose')
        else:ck(all(np.linalg.norm(q['offset'])<1e-9 for q in array(b,'motionParts')),'Partial path end not seated')
        preports.append({'id':pid,'fraction':float(b['pathFraction']),'contactStopped':b['contactStopped'],'source_result':p['result']})
    ck({p['id'] for p in preports}==set(pby),'Three path inspections not covered');results['partialPaths']=preports
    group=[]
    for tag in ['groupStart','groupScrub','playing','paused']:
        r=ui[tag];m=mods[r['module']];op=m['operations'][int(r['state']['operation'])];moves=array(r['state'],'motionParts');wanted=set(op['moveKeys']);ck({r['key'] for r in moves}==wanted,'Grouped animation loses a part: '+tag);ck(all(np.allclose(r['offset'],moves[0]['offset'],atol=1e-9) for r in moves),'Grouped assembly deforms or strands washer: '+tag);group.append({'receipt':tag,'part_count':len(moves),'same_vector':True})
    ck(ui['playing']['state']['playing']=='true' and ui['paused']['state']['playing']=='false','Play/pause states wrong');ck(ui['highlight']['state']['highlighted']=='lower','Selectable part highlight missing');results['groupedMotion']=group
    st=ui['screwsStart']['state'];en=ui['screwsEnd']['state'];moves=array(st,'motionParts');ck(moves and all(np.linalg.norm(r['offset'])>1 for r in moves),'Screw start not separated');ck(all(np.linalg.norm(r['offset'])<1e-9 for r in array(en,'motionParts')),'Screw end not seated')
    wiringby={r['id']:r for r in w['connections']};observed=set();stages=set()
    for r in ui['wiring']:
        state=r['state'];stage=state['wiringStep'];stages.add(stage);id=state.get('connection')
        if not id:continue
        ck(id in wiringby,'Unexpected wiring connection: '+id)
        if id in wiringby:
            q=wiringby[id];observed.add(id);ck(q['from'] in r['text'] and q['to'] in r['text'],'Rendered wiring endpoints differ: '+id)
    ck(observed==set(wiringby),'UI wiring misses a named connection');ck(stages=={r['id'] for r in w['steps']},'UI wiring misses a stage');results['wiring']={'stages':len(stages),'connections':len(observed),'all_endpoints_matched':True}
    pins={int(r['pin']):r for r in ui['header']};ck(set(pins)==set(range(1,41)),'Header does not contain40distinctphysicalpins')
    for p in w['pi_header_pins']:
        r=pins[p['physical_pin']];ck(r['used']==p['used'] and p['role'] in r['label'],'Physical pin role mismatch: '+str(p['physical_pin']))
    ck(ui['headerSelected']=='Physical pin 40 · GPIO 21 → amp DIN','Pin selection readback differs');ck(sum(r['used'] for r in pins.values())==12,'Used header pins not12')
    before=ui['idleBefore']['state'];after=ui['idleAfter']['state'];ck(before['renderedFrames']==after['renderedFrames'] and ui['idleImageBytesEqual'],'Idle renderer not stable');ck(ui['logs']==[],'Chrome errors remain');results['idle']={'rendered_before':before['renderedFrames'],'rendered_after':after['renderedFrames'],'image_bytes_equal':ui['idleImageBytesEqual'],'chrome_errors':ui['logs']}
    report={'passed':not errors,'errors':errors,'checks':results,'receipt_sha256':sha(D/'ui-acceptance-20261007.json'),'receipt':str(D/'ui-acceptance-20261007.json'),'scope':'Independent source comparison of actual Chrome receipts. No browser control, no CAD mutation and no hardware operation. Sampled paths remain limited to their reported scope; no complete rigid lower-link closure is certified.','physical_fit_verified':False}
    (D/'ui-acceptance-review.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'passed':report['passed'],'errors':errors,'operations':len(ops),'washer_stations':len(station_sets),'paths':len(preports),'connections':len(observed)}));return 0 if report['passed'] else 1
if __name__=='__main__':sys.exit(main())
