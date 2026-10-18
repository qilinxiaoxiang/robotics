"""Bind the prototype handoff to exact files and real browser observations."""
from pathlib import Path
import json,hashlib,zipfile,urllib.request
P=Path(__file__).resolve().parent;G=P.parent/'leg-guide-20261006'
def read(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def need(c,m):
    if not c:raise AssertionError(m)
def main():
    regression=read(P.parent/'current-build-verification.json')
    need(regression['passed'] and regression['scope']=='design' and regression['physical_tests']==0,'baseline design entry did not pass')
    proto=read(P/'preview-data.json');bundle=read(P/'review-bundle.json');receipt=read(P/'redesign-ui.json')
    need(sha(P/'ANKLE-REDESIGN.html')==sha(G/'ANKLE-REDESIGN.html')==bundle['htmlSha256']==receipt['htmlSha256'],'final reviewed HTML mismatch')
    need(sha(P/'preview-data.json')==bundle['prototypeSha256'],'stale candidate bundle')
    for f,h in bundle['sourceHashes'].items():need(sha(f)==h,'stale viewer/source '+f)
    need(receipt['url']=='http://127.0.0.1:8766/ANKLE-REDESIGN.html','wrong original service destination')
    need(receipt['errors']==[],'browser errors')
    need(set(receipt['sides'])=={'left','right'},'both sides not tested')
    for side,captures in receipt['sides'].items():
        steps=proto['sides'][side]['steps'];need(len(captures['steps'])==len(steps),'step coverage '+side)
        for i,(st,cap) in enumerate(zip(steps,captures['steps'])):
            for name,t in [('start',0),('middle',.5),('end',1)]:
                d=cap[name]['dataset'];need(d['side']==side and d['mode']=='assembly' and int(d['step'])==i,'wrong scene')
                need(abs(float(d['progress'])-t)<.001,'wrong slider time')
                need(set(json.loads(d['visibleParts']))==set(st['visibleKeys']),'visible part coverage')
                poses={v['key']:v for v in json.loads(d['partPoses'])}
                for k in st['movingKeys']:
                    expected=[a+(b-a)*t for a,b in zip(st['from'],st['to'])]
                    need(max(abs(a-b) for a,b in zip(expected,poses[k]['offset']))<1e-5,'rendered motion differs from checked path')
        need(captures['parts']['dataset']['mode']=='parts' and captures['baseline']['dataset']['mode']=='baseline','parts/comparison missing')
        need(len(captures['parts']['cards'])==3 and all(x['loaded'] for x in captures['parts']['cards']),'replacement thumbnails absent or hardware shown as prints')
        need(captures['highlight']['dataset']['selected']==side+'_cheek','replacement highlight failed')
        for row in captures['rotation']:
            d=row['dataset'];need(d['mode']=='rotation' and d['side']==side and float(d['angle']) in [-90,0,90],'joint inspection state incorrect')
        w=captures['washer']['dataset'];need(w['isolated']=='true' and json.loads(w['visibleParts'])==['washer6' if side=='left' else 'washer1'],'washer not independently visible')
    play=receipt['play'];need(play['paused']['dataset']['playing']=='false' and play['paused']['dataset']['progress']==play['pausedLater']['dataset']['progress'],'pause drift')
    need(play['finished']['dataset']['progress']=='1.000' and play['finished']['dataset']['playing']=='false','playback did not finish')
    idle=receipt['idle'];need(idle['before']['dataset']['renderedFrames']==idle['after']['dataset']['renderedFrames'] and idle['shaBefore']==idle['shaAfter'],'idle instability')
    for v in receipt['screenshots']:need(sha(v['path'])==v['sha256'],'screenshot changed')
    need(receipt['originalGuide']['operation']=='6' and receipt['originalGuide']['play']=='Play approach','original guide entry regressed')
    print_review=read(P/'print-review.json');need(not print_review['printing_performed'] and not print_review['native_slice_verified'],'unexpected print claim/action')
    need(len(print_review['candidate_reviews'])>=6,'print-facing coverage incomplete')
    for v in print_review['candidate_reviews']:
        need(sha(v['file'])==v['sha256'] and v['watertight'],'stale or invalid print-facing mesh')
        e=v['print_export'];need(sha(e['file'])==e['sha256'] and e['rigid_only'] and abs(e['bed_min_z_mm'])<1e-5,'invalid bed-oriented STL')
    server=read(P/'server-regression.json');need(server['passed'] and sha(G/'serve_guide.py')==server['script_sha256'],'server regression stale')
    cad=read(P/'cad-export.json');need(cad['passed'] and len(cad['exports'])==6,'current CAD export incomplete')
    for e in cad['exports']:need(e['valid'] and sha(e['stl'])==e['sourceStlSha256'] and sha(e['cad'])==e['stepSha256'],'stale/invalid STEP export')
    package=read(P/'package-manifest.json');need(sha(G/'ANKLE-REDESIGN.zip')==package['zipSha256'],'download changed')
    with zipfile.ZipFile(G/'ANKLE-REDESIGN.zip') as z:
        need(set(z.namelist())==set(package['files']),'package coverage mismatch')
        for name,h in package['files'].items():need(hashlib.sha256(z.read(name)).hexdigest()==h,'package member changed')
    for route,f in [('ANKLE-REDESIGN.html',G/'ANKLE-REDESIGN.html'),('ANKLE-REDESIGN.zip',G/'ANKLE-REDESIGN.zip')]:
        body=urllib.request.urlopen('http://127.0.0.1:8766/'+route,timeout=5).read();need(hashlib.sha256(body).hexdigest()==sha(f),'live served file mismatch')
    print('CURRENT_DESIGN_REGRESSION_PASS',len(regression['steps']))
    print('ANKLE_REDESIGN_DELIVERY_PASS',json.dumps({'sides':2,'steps':sum(len(v['steps']) for v in proto['sides'].values()),'printJobSent':False,'htmlSha256':bundle['htmlSha256']}))
if __name__=='__main__':main()
