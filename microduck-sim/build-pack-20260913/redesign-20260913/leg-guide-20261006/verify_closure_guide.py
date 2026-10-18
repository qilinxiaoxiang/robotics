#!/usr/bin/env python3
"""Independent source, contact-boundary and actual browser closure acceptance.

Read-only checks. Does not regenerate geometry, operate Chrome or access hardware.
"""
from pathlib import Path
import argparse
import base64
import gzip
import hashlib
import json
import math
import re

G = Path(__file__).resolve().parent
BASELINE = {
    'full-build-data.json':'fa087e05d48e6c5cce5f13fd62573a319eb4c8cf74c263268990954c7e6d9f60',
    'leg-data.json':'a3b834b65b570fe984fd29896ba5818f97363f50f4d2ba13faa91ee0df261f0e',
    'wiring-guide-data.json':'f56138c8696b37aebbc614f7c984a79e2061fbf1f23ac7ad9f6412e949512c59',
    'wiring-spatial-data.json':'04e588e5f46723e0b307952eac4aaf2ea1aa6a8932ac700163376d5a23cad0b4',
    'wiring3d.js':'4c7997cca4c7207f35aba38dcad203b3b0bba59c394f9bae2b415dd7f16eec0d',
    'assembly-path-investigation.json':'21dc8be9a147f2d2ee2eb77c5f63fdbb7d518f3ff24db49a28be1776e994fc64',
}
def read(path): return json.loads(Path(path).read_text())
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def require(ok,message):
    if not ok: raise AssertionError(message)
def close(a,b,tol=1e-5):
    return len(a)==len(b) and all(abs(float(x)-float(y))<=tol for x,y in zip(a,b))
def bundled(name,html):
    token='const '+name+'='
    require(token in html,'missing bundled '+name)
    value,_=json.JSONDecoder().raw_decode(html[html.index(token)+len(token):])
    return value

def preserved_source_check():
    for name,digest in BASELINE.items(): require(sha(G/name)==digest,'closure repair changed existing source '+name)
    html=(G/'LEFT-LEG.html').read_text()
    packed=re.search(r'const packed="([^"]+)";',html)
    require(packed is not None,'missing full geometry bundle')
    data=json.loads(gzip.decompress(base64.b64decode(packed.group(1))))
    require(data==read(G/'full-build-data.json'),'delivered full source geometry mismatch')
    require(len(data['parts'])==103 and len(data['screws'])==154,'full robot coverage changed')
    for name,var in [('wiring-guide-data.json','WIRING'),('wiring-spatial-data.json','SPATIAL'),('assembly-path-investigation.json','PATHS')]:
        require(bundled(var,html)==read(G/name),'stale delivered '+var)
    for name in ['viewer.js','wiring3d.js','closure3d.js']:
        require((G/name).read_text() in html,'stale delivered renderer '+name)
    for side in ['left-leg','right-leg']:
        mod=next(m for m in data['modules'] if m['id']==side)
        require(len(mod['operations'])==18,'leg operation coverage changed '+side)
        op=mod['operations'][6]
        require(op['requiresPhysicalFit'] is True and not op['screwIds'],'closure fit incorrectly treated as fastened '+side)
    from verify_wiring_3d import source_check
    wiring=source_check()
    return data,html,wiring

def contact_check(data,html):
    c=read(G/'closure-approach-investigation.json')
    require(bundled('CLOSURE',html)==c,'delivered closure report stale')
    require(c['passedAsBoundedApproachInvestigation'] and c['noCadOrPrintChanges'] and not c['physicalFitVerified'],'bounded investigation scope changed')
    require(c['scriptSha256']==sha(G/'closure-approach-investigation.py'),'measurement script changed after investigation')
    for path,digest in c['sourceHashes'].items(): require(sha(path)==digest,'stale native geometry input '+path)
    parts={p['key']:p for p in data['parts']}
    require(set(c['meshIdentities'])=={'lower','ankle','smallring','motor6','right_lower','right_ankle','right_smallring','motor1'},'closure source identity coverage')
    for key,identity in c['meshIdentities'].items():
        p=parts[key]
        require(identity['sourceId']==p['sourceId'] and identity['sourceTransformWorld']==p['sourceTransformWorld'],'source pose changed '+key)
        for payload,digest in [('positionB64','positionPayloadSha256'),('indexB64','indexPayloadSha256')]:
            require(hashlib.sha256(base64.b64decode(p[payload])).hexdigest()==identity[digest],'source mesh payload mismatch '+key)
        require(identity['triangles']==p['triangles'] and identity['manifoldStatus']=='Error.NoError','invalid mesh '+key)
        if p['sourceId'] is not None:
            require(identity['nativeReadback']['trianglesMatch'] and identity['nativeReadback']['bidirectionalVertexMaxErrorMm']<2e-5,'original print mesh altered '+key)
    for side,moving,fixed,sign in [('left-leg','lower',['ankle','smallring','motor6'],-1),('right-leg','right_lower',['right_ankle','right_smallring','motor1'],1)]:
        p=c['paths'][side]
        require(p['movingKeys']==[moving] and p['fixedKeys']==fixed,'wrong loose-bench moving/fixed parts '+side)
        require(p['contactPair']==moving+'--'+fixed[0],'wrong first obstruction pair '+side)
        require(p['physicalFitVerified'] is False and p['completeClosureValidated'] is False,'complete closure falsely accepted '+side)
        require(close(p['startTranslation'],[0,sign*12,0]),'wrong source-frame start '+side)
        require(close(p['lastClearTranslation'],p['stopTranslation']) and math.dist(p['stopTranslation'],[0,0,0])>6,'preview ends in assembled target '+side)
        require(p['collisionThresholdMm3']==.02 and p['sampleStepMmMaximum']==.25 and p['retreatFromThresholdBoundaryMm']==.5,'measurement thresholds widened '+side)
        require(0<p['contactBracketWidthMm']<.0001,'contact bracket too coarse '+side)
        require(abs(math.dist(p['thresholdLastSafeTranslation'],p['contactTranslation'])-p['contactBracketWidthMm'])<1e-8,'contact bracket inconsistent '+side)
        require(abs(math.dist(p['stopTranslation'],p['thresholdLastSafeTranslation'])-.5)<1e-8,'safe stop is not outward retreat '+side)
        require(p['stopGapMm']>.38 and all(v>=p['stopGapMm']-1e-9 for v in p['stopPairGapsMm'].values()),'no positive stopped surface gap '+side)
        require(max(p['stopPairOverlapMm3'].values())<1e-9 and p['contactPairOverlapMm3'][p['contactPair']]>.02,'clear/contact endpoints do not distinguish obstruction '+side)
        require(14<p['targetPairOverlapMm3'][moving+'--'+fixed[1]]<16,'source target interference erased '+side)
        samples=p['samples']
        require(len(samples)>=22 and close(samples[0]['translation'],p['startTranslation']) and close(samples[-1]['translation'],p['stopTranslation']),'checked preview extent mismatch '+side)
        for i,s in enumerate(samples):
            require(set(s['pairOverlapMm3'])=={moving+'--'+k for k in fixed} and max(s['pairOverlapMm3'].values())<1e-9,'native sampled preview crosses solids '+side)
            if i: require(math.dist(s['translation'],samples[i-1]['translation'])<=.25+1e-8,'unchecked sample gap '+side)
        a=p['animation']
        require(a['stopAtT']==1 and a['movingKeys']==[moving] and a['fixedKeys']==fixed,'animation no longer caps at measured stop '+side)
        for f in a['frames']:
            expected=[x+(y-x)*f['t'] for x,y in zip(p['startTranslation'],p['stopTranslation'])]
            require(close(f['translation'],expected) and f['quaternion']==[0,0,0,1],'unsupported rotation/path '+side)
    js=(G/'closure3d.js').read_text()
    for text in ['Play approach','Stop before contact','Black link + round post','Small black ring','Orange bracket','Do not use screws to pull it together','not a fully assembled joint','joint is still not seated','closureTargetReached=\'false\'']:
        require(text in js,'missing plain fitting/control boundary '+text)
    require('p.stopTranslation' in js and 'p.contactTranslation' not in js,'UI plays contact frame instead of stopped path')
    require('p.collisionThresholdMm3' in js and 'p.volumeThresholdMm3' not in js,'undefined threshold shown')
    require("document.querySelector('.tools').hidden=true" in js,'misleading reference/assembled controls remain active')
    return c

def ui_check(c):
    receipt=read(G/'closure-ui-20261007.json')
    require(receipt['url']=='http://127.0.0.1:8766/LEFT-LEG.html','wrong original user URL')
    require(receipt['htmlSha256']==sha(G/'LEFT-LEG.html'),'browser receipt does not bind current HTML')
    for name,digest in receipt['artifactHashes'].items(): require(sha(G/name)==digest,'stale browser-tested source '+name)
    require(receipt['passed'] is True and not receipt['errors'],'actual browser errors')
    require(receipt['baseline']['playButtons']==0 and 'Dry-fit the lower link and sleeve/boss closure' in receipt['baseline']['snapshot'],'original opaque/no-animation failure not observed')
    require(set(receipt['sides'])=={'left-leg','right-leg'},'both sides not tested')
    captures=0
    for side,rows in receipt['sides'].items():
        path=c['paths'][side]; moving=path['movingKeys'][0]; fixed=path['fixedKeys']; ring=fixed[1]
        required={'start','middle','stop','highlights','isolated','restored','restarted','playing','paused','pausedLater','resumed','finished'}
        require(required<=set(rows),'missing actual closure control readback '+side)
        for name,row in rows.items():
            if name=='highlights': continue
            ds=row['dataset']; progress=float(ds['motionProgress'])
            require(ds['closurePath']==side and ds['operation']=='6' and ds['closureTargetReached']=='false','wrong closure mode or target falsely reached '+side+'/'+name)
            require(0<=progress<=1 and row['toolbarHidden'] is True,'misleading reference/assembled controls visible '+side+'/'+name)
            require(json.loads(ds['visibleScrews'])==[],'closure path includes tightening screws '+side+'/'+name)
            require(json.loads(ds['closureContactPair'])==path['contactPair'] and close(json.loads(ds['closureStopTranslation']),path['stopTranslation']),'wrong native path bound to UI '+side+'/'+name)
            offsets=json.loads(ds['motionParts'])
            require(len(offsets)==1 and offsets[0]['key']==moving,'fixed parts animated as lower-only '+side+'/'+name)
            expected=[a+(b-a)*progress for a,b in zip(path['startTranslation'],path['stopTranslation'])]
            require(close(offsets[0]['offset'],expected,.006),'UI interpolation crosses measured stop '+side+'/'+name)
            require(abs(float(row['slider'])-progress*100)<=.56,'slider differs from actual animation '+side+'/'+name)
            expectedvisible=[moving,ring] if name=='isolated' else [moving]+fixed
            require(set(json.loads(ds['visibleParts']))==set(expectedvisible),'wrong actual closure mesh visibility '+side+'/'+name)
            require('joint is still not seated' in row['text'] if progress>=.995 else 'not a fully assembled joint' in row['text'],'missing fitting boundary '+side+'/'+name)
            captures+=1
        for name,value in [('start',0),('middle',.5),('stop',1),('restarted',0),('finished',1)]:
            require(abs(float(rows[name]['dataset']['motionProgress'])-value)<.001,'wrong actual preview endpoint '+side+'/'+name)
        require(rows['stop']['dataset']['contactStopped']=='true' and rows['finished']['dataset']['contactStopped']=='true','playback failed to stop '+side)
        require(rows['playing']['dataset']['playing']=='true' and 0<float(rows['playing']['dataset']['motionProgress'])<1,'Play did not move '+side)
        require(rows['paused']['dataset']['playing']==rows['pausedLater']['dataset']['playing']=='false','Pause did not stop '+side)
        require(rows['paused']['dataset']['motionParts']==rows['pausedLater']['dataset']['motionParts'],'paused geometry continued moving '+side)
        require(rows['resumed']['dataset']['playing']=='true' and float(rows['resumed']['dataset']['motionProgress'])>float(rows['paused']['dataset']['motionProgress']),'resume did not advance '+side)
        require(rows['finished']['dataset']['playing']=='false','finished animation still running '+side)
        require(len(rows['highlights'])==3,'three explanatory part picks required '+side)
        require([r['dataset']['highlighted'] for r in rows['highlights']]==[moving,ring,fixed[0]],'part buttons highlight wrong source meshes '+side)
        require(rows['isolated']['dataset']['closureIsolated']=='true' and rows['isolated']['dataset']['highlighted']==ring,'ring/post isolation lost part identity '+side)
        require(rows['restored']['dataset']['closureIsolated']=='false','ankle view did not restore '+side)
        for text in ['Black link + round post','Small black ring','Orange bracket','Play approach','Stop before contact','Do not use screws to pull it together','0.35 mm']:
            require(text in rows['start']['text'],'plain instruction/control missing '+side+'/'+text)
    require(receipt['afterStep']['dataset']['operation']=='7' and receipt['afterStep']['toolbarHidden'] is False,'normal operation8 toolbar not restored')
    require(receipt['returnedStep']['dataset']['operation']=='6' and float(receipt['returnedStep']['dataset']['motionProgress'])==0,'return to fitting did not reset start apart')
    for image in receipt['screenshots']: require(sha(image['path'])==image['sha256'],'actual screenshot stale '+image['path'])
    require(len(receipt['screenshots'])>=4,'both stopped/isolation views missing')
    images={Path(x['path']).name:x for x in receipt['screenshots']}
    for side in ['left-leg','right-leg']:
        for mode in ['stop','isolated']: require('closure-'+side+'-'+mode+'.png' in images,'side-specific actual screenshot missing')
    idle=receipt['idle']
    require(idle['before']['dataset']['renderedFrames']==idle['after']['dataset']['renderedFrames'],'static closure view keeps rendering')
    require(idle['before']['dataset']['motionParts']==idle['after']['dataset']['motionParts'] and idle['shaBefore']==idle['shaAfter'],'static geometry/pixels unstable')
    require(images['closure-idle-a.png']['sha256']==idle['shaBefore'] and images['closure-idle-b.png']['sha256']==idle['shaAfter'],'idle pixel evidence mismatch')
    wires=receipt['wiring']; spatial=read(G/'wiring-spatial-data.json')
    expected=next(x for x in spatial['connections'] if x['id']=='imu-sda')
    for mode in ['installed','connector']:
        row=wires[mode]; ds=row['dataset']
        require(row['canvas'] is True and ds['connection']=='imu-sda' and ds['wireMode']==mode,'fresh wiring route lost after closure')
        require(json.loads(ds['wireSegments'])==[{k:v[k] for k in ['from','to','signal','points']} for v in expected['segments']],'fresh wiring topology differs from preserved source')
        require(ds['wireTubeCount']=='1' and set(json.loads(ds['wireVisibleNodes']))=={'pi','imu'},'fresh wiring endpoints/tube missing')
        require(any(x['display']=='block' for x in row['labels']) and 'Pi physical pin 3' in row['detail'],'fresh wiring pin labels missing')
    require('Connector detail is schematic' in wires['connector']['detail'],'connector schematic falsely presented exact')
    header=wires['header']; ds=header['dataset']
    require(header['canvas'] is True and ds['wireMode']=='header' and ds['wirePinCount']=='40' and ds['wireTubeCount']=='0','header shows stale cable instead of contacts')
    pins=[x for x in header['labels'] if x['display']=='block' and re.match(r'^\d+(?: ·|$)',x['text'])]
    require([int(x['text'].split(' ·')[0]) for x in pins]==list(range(1,41)),'complete header numbering missing')
    require(header['detail']=='Click any pin to see its assigned role.Physical pins, not GPIO signal numbers.','stale connection explanation in header')
    require(wires['pin']['dataset']['selectedPin']=='12' and 'Physical pin 12 · GPIO 18 → amp BCLK' in wires['pin']['detail'],'fresh physical pin mapping incorrect')
    start=wires['traceStart']['dataset']; paused=wires['tracePaused']['dataset']
    require(start['wireTracing']=='true' and 0<float(start['wireTraceProgress'])<1,'fresh wire trace does not animate')
    require(paused['wireTracing']=='false' and float(paused['wireTraceProgress'])>=float(start['wireTraceProgress']),'fresh wire pause failed')
    final=receipt['finalVisible']
    require(final['dataset']['closurePath']=='left-leg' and final['dataset']['operation']=='6' and final['toolbarHidden'] is True,'original user step not restored')
    require('Play approach' in final['text'] and final['dataset']['closureTargetReached']=='false','final visible user step misleading')
    return {'sides':2,'controlCaptures':captures,'highlightTargets':6,'noTargetCrossing':True,'idleStable':True,'freshWiringAndHeaderRegression':True}

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--source-only',action='store_true')
    args=parser.parse_args()
    data,html,_=preserved_source_check()
    c=contact_check(data,html)
    if args.source_only:
        print('CLOSURE_PRESERVATION_SOURCE_PASS')
    else:
        ui=ui_check(c)
        print(json.dumps({'sourceGeometryPreserved':True,'ui':ui,'htmlSha256':sha(G/'LEFT-LEG.html')}))
        print('CLOSURE_GUIDE_CHECK_PASS')
