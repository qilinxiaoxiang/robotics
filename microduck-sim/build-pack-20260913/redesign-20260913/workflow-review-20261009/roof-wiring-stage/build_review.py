"""Build the review only after current repair acceptance; diagnostics are local-only."""
from pathlib import Path
import argparse,base64,json,html,hashlib
P=Path(__file__).resolve().parent
REQUIRED_SCOPES=('static-routing','connector-installation','cable-self-contact','closure','joint-motion-slack','enclosure-and-topology')
def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def validate_repair(root=P):
    """Consume native evidence; do not infer geometry acceptance from Fusion readback."""
    errors=[]
    def read(relative):
        try:return json.loads((root/relative).read_text())
        except (OSError,ValueError) as e:errors.append(f'{relative}: missing or invalid ({e})');return {}
    manifest=read('fusion/fusion-import-manifest.json');manifest_path=root/'fusion/fusion-import-manifest.json'
    manifest_hash=sha(manifest_path) if manifest_path.is_file() else None
    receipt=read('fusion/fusion-receipt.json')
    if receipt.get('status')!='COMPLETE' or receipt.get('readbackPassed') is not True:errors.append('Fusion archive readback incomplete')
    if receipt.get('manifestSha256')!=manifest_hash:errors.append('Fusion receipt does not bind the current assembly manifest')
    for part in manifest.get('parts',[]):
        f=Path(part.get('file',''))
        if not f.is_file() or sha(f)!=part.get('sha256'):errors.append('Stale/missing adopted part: '+str(part.get('key')))
    if not manifest.get('parts'):errors.append('Adopted assembly inventory is empty')
    motor=read('fusion/motor-wires-stage-summary.json');head=read('fusion/head-wires-stage-summary.json')
    routes=motor.get('routes',[])
    if not routes or motor.get('routeCount')!=len(routes) or len({r.get('id') for r in routes})!=len(routes):errors.append('Motor route inventory incomplete/duplicated')
    if motor.get('failedOrUnresolvedCount')!=0 or motor.get('neutralStaticClearCount')!=len(routes):errors.append('Known failed/unresolved motor routes')
    if any(r.get('neutralStaticCollisionFree') is not True or r.get('sourceMeshInterferences') for r in routes):errors.append('Motor collision records reject repair acceptance')
    if head.get('integrationReady') is not True or head.get('remainingFailures') or head.get('unclosedChecks'):errors.append('Known failed/incomplete head wiring')
    # One revision-specific conjunction, not a replacement collision engine.
    acceptance=read('repair-acceptance.json')
    if acceptance.get('assemblyManifestSha256')!=manifest_hash:errors.append('Repair evidence does not bind the adopted assembly')
    if acceptance.get('topology')!='pi-usb-to-openrb-internal':errors.append('Required internal Pi-to-OpenRB topology not accepted')
    if acceptance.get('exteriorEnclosed') is not True or acceptance.get('unresolvedOpenings')!=[]:errors.append('Required enclosure still open or unverified')
    expected={'motor':sorted(r.get('id','') for r in routes),'head':sorted(p.get('key','') for p in read('fusion/head-wires-manifest.json').get('parts',[]))}
    if not expected['head'] or acceptance.get('routeInventory')!=expected:errors.append('Repair evidence omits/changes required wire inventory')
    bindings=acceptance.get('inputHashes',{})
    for rel in ('fusion/motor-wires-stage-summary.json','fusion/head-wires-stage-summary.json','fusion/head-wires-manifest.json'):
        f=root/rel
        if not f.is_file() or bindings.get(rel)!=sha(f):errors.append('Repair evidence stale: '+rel)
    evidence=acceptance.get('scopeEvidence',{})
    for scope in REQUIRED_SCOPES:
        ref=evidence.get(scope,{})
        f=root/ref.get('file','__missing__')
        if not f.is_file() or ref.get('sha256')!=sha(f):errors.append('Missing/stale required scope: '+scope);continue
        try:d=json.loads(f.read_text())
        except (ValueError,OSError):errors.append('Invalid scope report: '+scope);continue
        if d.get('assemblyManifestSha256')!=manifest_hash or d.get('scope')!=scope:errors.append('Scope source/revision mismatch: '+scope)
        if d.get('passed') is not True or d.get('coverageComplete') is not True or d.get('unresolved')!=[]:errors.append('Failed, skipped or incomplete required scope: '+scope)
        # A standalone passed boolean is not native evidence. Reconcile the
        # checker's concrete expected and completed result records.
        expected_ids=d.get('expectedCheckIds',[]);records=d.get('checks',[])
        actual_ids=[c.get('id') for c in records]
        if not expected_ids or len(set(expected_ids))!=len(expected_ids) or sorted(actual_ids)!=sorted(expected_ids):errors.append('Empty or incomplete native check inventory: '+scope)
        if d.get('testedValidBodyCount',0)<=0:errors.append('Empty valid geometry inventory: '+scope)
        for c in records:
            if c.get('status')!='complete' or c.get('validInputs') is not True or c.get('validResult') is not True or c.get('result') not in ('clear','accepted-contact'):errors.append('Native failure/invalid result: '+scope+'/'+str(c.get('id')))
            if c.get('result')=='accepted-contact' and not c.get('contactEvidence'):errors.append('Unbound contact exception: '+scope+'/'+str(c.get('id')))

    return errors

def main(argv=None, root=None):
    global P
    if root is not None:P=Path(root)
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--diagnostic-output',type=Path,help='Explicit internal diagnostic file, restricted to this stage diagnostics directory; never DESIGN-REVIEW.html')
    args=parser.parse_args(argv);diagnostic=args.diagnostic_output is not None
    out=P.parent/'DESIGN-REVIEW.html'
    if diagnostic:
        out=args.diagnostic_output.resolve();allowed=(P/'diagnostics').resolve()
        if not out.is_relative_to(allowed) or out.name.upper()=='DESIGN-REVIEW.HTML':raise SystemExit('Diagnostic output must stay under roof-wiring-stage/diagnostics and cannot be DESIGN-REVIEW.html')
    errors=validate_repair(P)
    if errors and not diagnostic:raise SystemExit('Repair not accepted; previous page preserved:\n- '+'\n- '.join(errors))
    receipt=json.loads((P/'fusion/fusion-receipt.json').read_text())
    assert receipt['status']=='COMPLETE' and receipt['readbackPassed']
    roof=json.loads((P/'roof/patch-static-check.json').read_text());assert roof['passed']
    def img(f):return 'data:image/png;base64,'+base64.b64encode((P/'fusion'/f).read_bytes()).decode()
    views=[('Closed head','head-closed-readback.png','The original curved crown is restored. Internal mounts and the rear OpenRB port are retained.'),('Head wiring','head-wires.png','The cap is hidden to inspect head-local wires; cross-neck wires are shown in the whole-harness view. Other receiving geometry is translucent. These display controls do not remove obstacles from geometry checks.'),('Whole harness','whole-wiring.png','Connector-to-connector routes in the original body proportions. A route drawn here is not automatically accepted for motion or stock cable slack.'),('Closed robot','whole-closed-readback.png','Original body and leg spacing, with the converter in the original battery location.')]
    buttons=''.join(f'<button onclick="show({i})" id="b{i}" class="'+('active' if i==0 else '')+f'">{t}</button>' for i,(t,f,c) in enumerate(views))
    figures=''.join(f'<figure id="v{i}" '+('' if i==0 else 'hidden')+f'><img src="{img(f)}" alt="{html.escape(c)}"><figcaption>{html.escape(c)}</figcaption></figure>' for i,(t,f,c) in enumerate(views))
    motor=json.loads((P/'fusion/motor-wires-stage-summary.json').read_text())
    issues='<h2>Wire routing findings</h2><p><strong>'+str(motor['neutralStaticClearCount'])+' of '+str(motor['routeCount'])+' motor routes clear the checked neutral pose; '+str(motor['failedOrUnresolvedCount'])+' still have interference and are shown in red.</strong> Neutral clearance is not motion/slack acceptance. Power and IMU paths are also routing studies with remaining conflicts.</p><details><summary>Show the exact remaining motor routes</summary><ul>'
    for r in motor['routes']:
     if r['neutralStaticCollisionFree']:continue
     obstacles=sorted(set(i['obstacle'] for i in r['sourceMeshInterferences']))
     issues+='<li><strong>'+html.escape(r['id'].replace('ttl-','').replace('-',' → '))+'</strong>: '+html.escape(', '.join(obstacles))+'</li>'
    issues+='</ul></details>'
    head=json.loads((P/'fusion/head-wires-stage-summary.json').read_text())
    issues+='<p>The four audio-signal routes now avoid the camera ribbon. Remaining head findings include a small roof contact on pin 40, speaker-keeper contact, and power/IMU routes crossing existing structures. These stay unresolved in this stage.</p><details><summary>Show the head-wire findings</summary><ul>'+''.join('<li>'+html.escape(t)+'</li>' for t in head['remainingFailures'])+'</ul></details>'
    if not diagnostic:
        issues='<h2>Accepted repair scope</h2><p>The source-bound required route inventory has passed its recorded digital checks. No known in-scope routing failure remains. Physical fit and commissioning are separate.</p>'
    body='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>MicroDuck · Restored crown and wiring review</title><style>*{box-sizing:border-box}body{margin:0;background:#f2f5f1;color:#24372e;font:17px/1.6 system-ui}main{max-width:1280px;margin:auto;padding:26px 28px 65px}h1{font-size:40px;line-height:1.15;margin:16px 0}h2{font-size:25px}nav{display:flex;gap:24px;flex-wrap:wrap}a{color:#256647}.label{font-size:13px;letter-spacing:1.5px;color:#61796a}.note{padding:15px 20px;background:#dfecdF;border-left:4px solid #51865d}.views{background:white;border:1px solid #d1ded2;border-radius:14px;padding:15px;margin:24px 0}.tabs{display:flex;gap:8px;flex-wrap:wrap}button{border:1px solid #b7c8ba;border-radius:7px;background:#f2f6f1;padding:10px 16px;font:inherit;cursor:pointer}button.active{background:#2b6046;color:white}figure{margin:12px 0 0}figure[hidden]{display:none}img{width:100%;display:block;max-height:780px;object-fit:contain}figcaption{font-size:14px;color:#5a6e5e;margin-top:8px}.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:16px}.card{background:white;border:1px solid #d1ded2;border-radius:12px;padding:20px}.card h3{margin:0;font-size:20px}footer{font-size:13px;color:#64796a;margin-top:28px}li{margin:9px 0}@media(max-width:800px){main{padding:20px 15px}.grid{grid-template-columns:1fr}h1{font-size:32px}}</style><main><nav><a href="LEFT-LEG.html">Assembly guide</a><a href="HEAD-EYE-REVIEW.html">Earlier head guide</a><a href="#connections">Connection changes</a></nav><p class="label">MICRODUCK · NATIVE CAD REVIEW · 09 OCTOBER 2026</p><h1>Curved crown restored.<br>Wires added to the assembly.</h1><p>The unnecessary crown opening is closed in this configuration. The body keeps its original proportions and the converter stays in the original battery location.</p><div class="note"><strong>This stage is saved and reopened in Fusion.</strong> The repaired roof and named harness geometry share the same assembly coordinates. Wiring still has explicit review items; this page is not a claim that the complete robot is commissioned.</div><section class="views"><div class="tabs">'''+buttons+'''</div>'''+figures+'''</section>'''+issues+'''<div class="grid"><article class="card"><h3>Original surface</h3><p>The repair reconstructs the missing curved-shell material. It is not a flat cover or a cap placed over the old hole.</p><p>Internal posts, speaker mounts and the rear USB opening remain. The added roof material clears all other existing components in the checked closed pose.</p></article><article class="card"><h3>Visible connections</h3><p>The model includes the camera ribbon, speaker leads, signal/power routing and motor-cable candidates with separate connector bodies. Routes have named endpoints and retained source records.</p><p>The inspection views expose the wires without pretending the shells are physically absent.</p></article><article class="card"><h3>Assembly order</h3><p>Preconnect buried motor sockets before their covers close access. Route the loose wires, retain the joint loops, then close the covers.</p><p>The prior left-knee insertion finding is retained: the orange wall obstructs a late straight insertion.</p></article></div><h2 id="connections">Why the top USB opening is no longer needed</h2><p>The earlier opening was cut around an unverified SC0727 plug envelope. It was not part of the community crown. In this review the <strong>Mac connects to the OpenRB through its rear USB port</strong>, and the Pi keeps the camera, audio and sensor role. Its upward-facing USB/data socket is unused, so no plug has to project through the crown.</p><p>This follows the specified Mac-control/Pi-sensor division. The existing combined Pi runtime has <strong>not yet been migrated or commissioned</strong> for it; moving that USB connection in CAD does not change software ownership automatically. USB does not provide motor-load power.</p><h2>What this stage establishes</h2><ul><li>Roof restoration preserves current mounts and original outer curvature; the reconstructed patch has a clear static pose against the existing assembly.</li><li>All displayed parts are bound to their source geometry and read back after reopening the saved Fusion archive.</li><li>Wire geometry is now reviewable at actual component interfaces. Remaining connector registration, interference, motion/slack and electrical termination items are retained in the harness records.</li></ul><p>The earlier 1.4 print package is unchanged. This is the requested intermediate design review, before any affected parts receive a new print release.</p><p><a href="https://www.raspberrypi.com/products/micro-usb-male-to-usb-a-female-cable/">Official SC0727 specification</a> · <a href="https://emanual.robotis.com/docs/en/parts/controller/openrb-150/">OpenRB USB bridge documentation</a></p><footer>Fusion geometry count: '''+str(receipt['meshBodies'])+''' · source-bound wire/connector bodies: '''+str(receipt['wireBodies'])+''' · saved archive readback passed. Existing shell references and routed mesh geometry remain explicitly identified as such; importing them does not recreate the original solid feature history.</footer></main><script>function show(i){document.querySelectorAll('figure').forEach((n,j)=>n.hidden=i!==j);document.querySelectorAll('.tabs button').forEach((n,j)=>n.classList.toggle('active',i===j))}</script></html>'''
    if diagnostic:
        body=body.replace('<title>MicroDuck · Restored crown and wiring review</title>', '<title>INTERNAL DIAGNOSTIC — unresolved wiring</title>').replace('<h1>Curved crown restored.<br>Wires added to the assembly.</h1>', '<h1>Internal diagnostic — repair incomplete</h1>')
        body=body.replace('<main>', '<main><p style=\"background:#ffe0e0;padding:20px\"><strong>INTERNAL DIAGNOSTIC ONLY.</strong> Required repair checks have not passed. This is not the repaired user handoff.</p>',1)
        body=body.replace('Closed head','Cap shown — enclosure not accepted').replace('Closed robot','Shells shown — assembly not accepted')
    if not diagnostic:
        body=body.replace('The original curved crown is restored. Internal mounts and the rear OpenRB port are retained.', 'The required crown and rear enclosure are closed; internal wiring is covered by the bound acceptance reports.')
        body=body.replace('Internal posts, speaker mounts and the rear USB opening remain.', 'Internal posts and speaker mounts remain; the required rear opening is closed.')
        start=body.index('<h2 id="connections">');end=body.index('<h2>What this stage establishes</h2>',start)
        body=body[:start]+'<h2 id="connections">Internal USB and enclosure</h2><p>The Pi connects internally to OpenRB. The required crown and rear openings are closed. Connector bodies, the complete cable and installation sequence are covered by this assembly revision’s accepted scope reports. An unverified plug envelope is not treated as a manufacturer dimension.</p>'+body[end:]
        body=body.replace('The four audio-signal routes now avoid the camera ribbon. Remaining head findings include a small roof contact on pin 40, speaker-keeper contact, and power/IMU routes crossing existing structures. These stay unresolved in this stage.', 'The required head wiring checks are complete for this source-bound revision. Physical commissioning remains separate.')
        body=body.replace('Power and IMU paths are also routing studies with remaining conflicts.', 'Power and IMU routes are covered by the required repair scope reports.')
        body=body.replace('Wiring still has explicit review items; this page is not a claim that the complete robot is commissioned.', 'Required digital repair checks have passed for this revision; physical commissioning remains separate.')
        body=body.replace('Remaining connector registration, interference, motion/slack and electrical termination items are retained in the harness records.', 'Connector registration, interference, motion/slack and electrical termination checks are bound to the adopted revision and complete required scope.')
        body=body.replace('motor-cable candidates', 'motor cables')
    out.parent.mkdir(parents=True,exist_ok=True)
    tmp=out.with_suffix(out.suffix+'.tmp');tmp.write_text(body);tmp.replace(out)
    print(json.dumps({'file':str(out),'bytes':out.stat().st_size,'sha256':hashlib.sha256(out.read_bytes()).hexdigest()}))

if __name__=='__main__':main()
