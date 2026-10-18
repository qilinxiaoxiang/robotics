"""Pose-wise grid (no path assumption): backward hip pitch 0..1.571 step 0.025 x inward hip yaw 0..MJCF limit step 0.04 x roll
{walk min, home, walk max, MJCF min, MJCF max} x knee {straight, walk min, walk max}; ankle home. Unsigned 1 mm EDT fields; a leg
part penetrating an existing body necessarily has surface samples within ~1 mm of it, so d<2 covers penetration.
Left fully; right mirrored with knee straight. Writes p5-grid.json."""
import sys, json, time, itertools, numpy as np; sys.path.insert(0, '.')
import p5_field as P
for s in P.PTS:
    Pl, lab = P.PTS[s]; newP = []; newlab = []; off = 0
    for b, p in Pl:
        l = lab[off:off + len(p)]; off += len(p)
        _, i = np.unique(np.round(p / 1.2).astype(np.int64), axis=0, return_index=True); newP.append((b, p[i])); newlab.append(l[i])
    P.PTS[s] = (newP, np.concatenate(newlab))
W = P.W; H = P.HOME; rows = []; t0 = time.time()
for side in ('left', 'right'):
    y, r, pj, kj, aj = P.L.SIDE[side]['joints']; sg = 1.0 if side == 'left' else -1.0
    ylim = P.rng(y)[0] if side == 'left' else P.rng(y)[1]
    Yv = [-sg * v for v in np.arange(0.0, abs(ylim) + 1e-6, 0.04)] + [ylim]
    Rv = sorted({W[r]['min'], H[r], W[r]['max'], *P.rng(r)})
    K = {'straight': 0.0, 'walkMin': W[kj]['min'], 'walkMax': W[kj]['max']} if side == 'left' else {'straight': 0.0}
    for (kn, kv), rr, yy in itertools.product(K.items(), Rv, Yv):
        for pb in np.arange(0.0, 1.5708, 0.025):
            res, _ = P.evaluate(side, {y: float(yy), r: float(rr), pj: float(sg * pb), kj: kv, aj: H[aj]})
            rows.append([side, kn, round(float(yy), 3), round(float(rr), 3), round(float(pb), 3)] + [round(res[k][0], 2) for k in P.F] + [res['tray'][1], res['board'][1], res['power_support'][1]])
        print(side, kn, round(float(rr), 3), 'done', len(rows), round(time.time() - t0), 's', flush=True)
    json.dump(dict(cols=['side', 'knee', 'yaw', 'roll', 'pitchBackwardAbs'] + list(P.F) + ['trayPart', 'boardPart', 'psPart'], rows=rows), open('p5-grid.json', 'w'))
