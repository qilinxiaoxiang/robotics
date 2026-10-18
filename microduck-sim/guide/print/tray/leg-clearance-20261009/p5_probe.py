"""Fixed-grid probe (0.1 rad hip pitch from home to the problem-side limit) with part labels.
Usage: p5_probe.py <walk|full>. Writes p5-probe-<mode>.json."""
import sys, json, itertools, time, numpy as np; sys.argv = [sys.argv[0], sys.argv[1]] + sys.argv[2:]
mode = sys.argv[1]
import importlib.util
spec = importlib.util.spec_from_file_location('S', 'p5_sweep_lib.py'); S = importlib.util.module_from_spec(spec); spec.loader.exec_module(S)
W = S.W; HOME = S.HOME; out = {}; t0 = time.time()
for side in ('left', 'right'):
    J = S.L.SIDE[side]['joints']; y, r, pj, kj, aj = J; sgn = 1.0 if side == 'left' else -1.0
    if mode == 'walk': Y = (W[y]['min'], W[y]['max']); R = (W[r]['min'], W[r]['max']); K = {'straight': 0.0, 'walkMin': W[kj]['min'], 'walkMax': W[kj]['max']}
    else: Y = S.rng(y); R = S.rng(r); K = {'straight': 0.0, 'home': HOME[kj]}
    lim = S.rng(pj)[1] if side == 'left' else S.rng(pj)[0]
    P = list(np.arange(HOME[pj], lim, sgn * 0.1)) + [lim]
    rows = []
    for yy, rr in itertools.product(Y, R):
        for kn, kv in K.items():
            for p in P:
                res, _ = S.evaluate(side, {y: yy, r: rr, pj: float(p), kj: kv, aj: HOME[aj]})
                rows.append(dict(yaw=round(yy, 3), roll=round(rr, 3), knee=kn, pitch=round(float(p), 3), **{k: [round(d, 2), S.LABEL.get(pt, pt)] for k, (d, pt) in res.items()}))
            first = {k: next(((x['pitch'], x[k][1]) for x in rows if x['yaw'] == round(yy, 3) and x['roll'] == round(rr, 3) and x['knee'] == kn and x[k][0] < 2.0), None) for k in S.TREE}
            print(side, mode, round(yy, 3), round(rr, 3), kn, 'first<2mm', first, round(time.time() - t0), 's', flush=True)
    out[side] = rows
json.dump(out, open(f'p5-probe-{mode}.json', 'w'), indent=1)
