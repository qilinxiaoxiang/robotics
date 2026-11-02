"""What the camera loop did during each pick: frames used, frames gated, projected positions. argv: seepick trace files."""
import json, sys
for f in sys.argv[1:]:
    rows = [json.loads(l) for l in open(f)]
    t0 = None; ep = []
    for r in rows:
        if r.get('phase') == 'pick': ep.append(r)
    print(f.split('/')[-1], 'rows in pick', len(ep), 'kinds', {k: sum(k in r for r in rows) for k in ('meas', 'gated')})
    for r in ep[:40]:
        if 'gated' in r: print('  %.2f GATED x %.3f y %.3f u %.0f v %.0f bbox %s neck %.2f hp %.2f' % (r['t'] % 1000, *r['gated'], r['u'], r['v'], r['bbox'], r['q'].get('neck_pitch', 0), r['q'].get('head_pitch', 0)))
        elif 'meas' in r:
            m = r['meas']; print('  %.2f meas x %.3f y %.3f size %.3f u %s v %s w %s' % (r['t'] % 1000, m['x'], m['y'], m['size'], m.get('u'), m.get('v'), m.get('w')))
