"""Read existing failed local document; no reimport or wire/mesh replacement."""
import adsk.core,adsk.fusion,json,traceback
from pathlib import Path
D=Path('/Users/xiangzheng/code/robotics/microduck-sim/build-pack-20260913/redesign-20260913/workflow-review-20261009/enclosed-wiring-repair/motor-wires')
app=adsk.core.Application.get();design=adsk.fusion.Design.cast(app.activeProduct);root=design.rootComponent
occ=next(root.occurrences.item(i) for i in range(root.occurrences.count) if root.occurrences.item(i).component.name.startswith('Conductor 1 '));comp=occ.component
sk=next(comp.sketches.item(i)for i in range(comp.sketches.count)if comp.sketches.item(i).name.startswith('EDITABLE 3D'))
curves=[sk.sketchCurves.item(i)for i in range(sk.sketchCurves.count)]
curves.sort(key=lambda c:json.loads(c.attributes.itemByName('MicroDuck','primitive').value)['start'])
# Find original route first primitive, regardless of collection's line/arc ordering.
first=next(c for c in curves if json.loads(c.attributes.itemByName('MicroDuck','primitive').value)['start']==json.loads((D/'local-route.json').read_text())['strands'][0]['primitives'][0]['start'])
def collection(cs):
 out=adsk.core.ObjectCollection.create()
 for c in cs:out.add(c)
 return out
out={'document':design.parentDocument.name,'occurrence':occ.name,'sketch':sk.name,'curveCount':len(curves),'tests':[]}
def test(label,fn):
 try:
  p=fn();out['tests'].append({'test':label,'success':bool(p),'entityCount':p.count if p else None})
 except Exception:out['tests'].append({'test':label,'success':False,'error':traceback.format_exc()})
# Compare native-entity static path with component-owned creation and root-context proxies.
test('native static collection baseline',lambda:adsk.fusion.Path.create(collection(curves),adsk.fusion.ChainedCurveOptions.noChainedCurves))
test('component features native collection',lambda:comp.features.createPath(collection(curves),False))
test('component features first curve auto chain',lambda:comp.features.createPath(first,True))
test('root occurrence proxy collection',lambda:root.features.createPath(collection([c.createForAssemblyContext(occ)for c in curves]),False))
# Same curves, changing only active edit context is the discriminating test.
try:
 occ.activate();test('active occurrence static native collection',lambda:adsk.fusion.Path.create(collection(curves),adsk.fusion.ChainedCurveOptions.noChainedCurves));test('active occurrence component features collection',lambda:comp.features.createPath(collection(curves),False))
finally:
 design.activateRootComponent()
 (D/'fusion-path-probe.json').write_text(json.dumps(out,indent=2))
(D/'fusion-path-probe.json').write_text(json.dumps(out,indent=2))
