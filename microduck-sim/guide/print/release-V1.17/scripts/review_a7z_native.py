"""V1.17: support toolpaths at the changed A7Z features, before against after, from the native slices (read-only on all inputs).

    /tmp/microduck-cad-venv/bin/python scripts/review_a7z_native.py <Bambu|Elegoo>

Cap: the V1.16 White slice (V1.9 cap, same pose) against the V1.17 White slice (A7Z cap). Every extruding support move
('support' in the feature name) is split at 0.4 mm, mapped back to the robot frame through the cap's placement in that run,
and counted in two boxes: the whole cap (its print-frame bounding box plus 6 mm) and the changed rail region (robot x 50..64,
|y| <= 37, z 114..160: the rails, both end slots and the roof column above them, where support for the new down-facing faces
stands). The crown, posts and pilots are the same in both caps, so the difference is the change.
Clip: the V1.9 Orange slice (release-V1.9/run-r2, clip_cap_v19) against the V1.17 Orange slice (clip_cap_a7z): support within the
clip's print box plus 3 mm, and the first-layer model area of the clip (release_pipeline_v2.first_layer).
Writes review/a7z-native-<Machine>.json.
"""
import json, sys
from pathlib import Path
import numpy as np
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent; REL = HERE.parent; PRINT = REL.parent
sys.path.insert(0, str(HERE))
import review_v117 as rv  # noqa: E402  (segments(), r2)
r2 = rv.r2
CHANGED = dict(lo=[50.0, -37.0, 114.0], hi=[64.0, 37.0, 160.0])


def payload(run, color, machine):
    prep = r2.read(run / 'preparation.json'); res = r2.read(run / f'native/{color}_{machine}/result.json')
    arch = Path(res['archive']['path']); g, cfg, _ = r2.native_payload(arch); assert r2.digest(g) == res['gcodeSha256']
    row = next(x for x in prep['rows'] if x['color'] == color and x['machine'] == machine)
    off = list(map(float, cfg.get('extruder_offset', ['0x0'])[0].split('x'))) if machine == 'Bambu' else [0.0, 0.0]
    return prep, row, g, rv.segments(g, off), dict(path=str(arch), sha256=res['archive']['sha256']), res['gcodeSha256']


def placed(prep, row, key):
    part = next(p for p in prep['parts'] if p['key'] == key); pl = next(p for p in row['placements'] if p['key'] == key)
    T = np.array(part['sourceToPrint'], float); T[2, 3] += part.get('dropToBedMm', 0.0); T[:3, 3] += np.array(pl['translation'], float)
    b = np.array(part['bounds'], float) + np.array(pl['translation'], float)
    return T, b


def support_points(segs, step=0.4):
    pts, lens = [], []
    for a, b, c, d, z, kind in segs:
        if 'support' not in kind.lower(): continue
        L = float(np.hypot(c - a, d - b)); n = max(1, int(L / step)); t = (np.arange(n) + 0.5) / n
        pts.append(np.c_[a + (c - a) * t, b + (d - b) * t, np.full(n, z)]); lens.append(np.full(n, L / n))
    return (np.vstack(pts), np.concatenate(lens)) if pts else (np.zeros((0, 3)), np.zeros(0))


def cap_side(run, machine, key):
    prep, row, g, segs, arch, gsha = payload(run, 'White', machine); T, b = placed(prep, row, key)
    P, L = support_points(segs)
    inbox = (P[:, 0] >= b[0, 0] - 6) & (P[:, 0] <= b[1, 0] + 6) & (P[:, 1] >= b[0, 1] - 6) & (P[:, 1] <= b[1, 1] + 6)
    W = (np.c_[P, np.ones(len(P))] @ np.linalg.inv(T).T)[:, :3]
    ch = inbox & np.all(W >= CHANGED['lo'], axis=1) & np.all(W <= CHANGED['hi'], axis=1)
    kinds = {}
    for a_, b_, c_, d_, z_, k in segs:
        if 'support' in k.lower():
            mx, my = (a_ + c_) / 2, (b_ + d_) / 2
            if b[0, 0] - 6 <= mx <= b[1, 0] + 6 and b[0, 1] - 6 <= my <= b[1, 1] + 6: kinds[k] = kinds.get(k, 0.0) + float(np.hypot(c_ - a_, d_ - b_))
    return dict(run=str(run), archive=arch, gcodeSha256=gsha, capKey=key, supportNearCapMm=round(float(L[inbox].sum()), 1),
                supportNearCapByKindMm={k: round(v, 1) for k, v in sorted(kinds.items())},
                supportInChangedRailRegionMm=round(float(L[ch].sum()), 1),
                changedRegionSupportPrintZ=[round(float(P[ch, 2].min()), 2), round(float(P[ch, 2].max()), 2)] if ch.any() else None,
                plateSupportTotalMm=round(float(L.sum()), 1), estimatedSeconds=r2.time_seconds(g, machine))


def clip_side(run, machine, key):
    prep, row, g, segs, arch, gsha = payload(run, 'Orange', machine); T, b = placed(prep, row, key)
    P, L = support_points(segs)
    inbox = (P[:, 0] >= b[0, 0] - 3) & (P[:, 0] <= b[1, 0] + 3) & (P[:, 1] >= b[0, 1] - 3) & (P[:, 1] <= b[1, 1] + 3)
    out = dict(run=str(run), archive=arch, clipKey=key, clipPrintBox=np.round(b, 2).tolist(), supportNearClipMm=round(float(L[inbox].sum()), 1),
               supportNearClipPrintZ=[round(float(P[inbox, 2].min()), 2), round(float(P[inbox, 2].max()), 2)] if inbox.any() else None)
    try:
        rows, _ = r2.first_layer(g, Path(row['project']['path']), machine)
        fl = next((x for x in rows if x['name'] == f'{key}_1'), None)
        if fl: out.update(firstLayerModelMm2=round(fl['model_area_mm2'], 2), firstLayerIslands=fl['modelIslands'], firstLayerSupportMm2=round(fl['support_area_mm2'], 2))
    except Exception as e:  # noqa: BLE001  (the V1.9 run is pipeline v1; its project layout may differ)
        out['firstLayerError'] = str(e)[:200]
    return out


def main():
    machine = sys.argv[1]
    before = cap_side(PRINT / 'release-V1.16/run', machine, 'head_cap_v19_white'); after = cap_side(REL / 'run', machine, 'head_cap_a7z')
    cb = clip_side(PRINT / 'release-V1.9/run-r2', machine, 'clip_cap_v19'); ca = clip_side(REL / 'run', machine, 'clip_cap_a7z')
    out = dict(machine=machine, changedRailRegionRobotBox=CHANGED, cap=dict(before=before, after=after,
               deltaSupportNearCapMm=round(after['supportNearCapMm'] - before['supportNearCapMm'], 1),
               deltaSupportInChangedRailRegionMm=round(after['supportInChangedRailRegionMm'] - before['supportInChangedRailRegionMm'], 1)),
               clip=dict(before=cb, after=ca, deltaSupportNearClipMm=round(ca['supportNearClipMm'] - cb['supportNearClipMm'], 1)))
    r2.write(REL / f'review/a7z-native-{machine}.json', out)
    print(json.dumps(dict(machine=machine, cap={k: v for k, v in out['cap'].items() if k.startswith('delta')},
                          capBefore={k: before[k] for k in ('supportNearCapMm', 'supportInChangedRailRegionMm', 'supportNearCapByKindMm')},
                          capAfter={k: after[k] for k in ('supportNearCapMm', 'supportInChangedRailRegionMm', 'changedRegionSupportPrintZ', 'supportNearCapByKindMm')},
                          clipBefore={k: v for k, v in cb.items() if k not in ('run', 'archive')}, clipAfter={k: v for k, v in ca.items() if k not in ('run', 'archive')}), indent=1))


if __name__ == '__main__':
    main()
