"""Thin-wall allowances for the V1.22 rows: every wall-check region that is stock geometry, with its evidence.

    /tmp/microduck-cad-venv/bin/python thin_wall_allowances.py      -> thin-wall-allowances.json beside this file

For each V1.22 part with a stock counterpart (the two slip-fit feet: community-44/46; the two split-ankle bases: the
one-piece stock bracket in the 10/06 leg guide) it runs the release wall check (13-RELEASE-PIPELINE-20261009/
wall_check.py) on the part in its print frame and compares every failing region with the stock part in the same frame:
  stockMinusNewMm3 / newMinusStockMm3  boolean volume difference inside the region's box grown by 1 mm
  stockMinMm / stockMedianMm           the stock part's smoothed thickness at the same place
A region becomes an allowance only when V1.22 added no material there (newMinusStockMm3 = 0) and the stock part is itself
below the minimum wall at that place; anything else is printed as NEW and the script exits 1, because a thin wall that
V1.22 created must be thickened, not allowed. make_manifest.py copies the entries into the rows' thinWallAllowances.
"""
import base64, json, sys
from pathlib import Path
import numpy as np
import trimesh
import manifold3d as m3
from scipy.spatial import cKDTree

HERE = Path(__file__).resolve().parent
SIM = HERE.parents[3]
PIPE = SIM / 'build-pack-20260913/redesign-20260913/printing/13-RELEASE-PIPELINE-20261009'
sys.path.insert(0, str(PIPE))
import wall_check as W  # noqa: E402

STOCK_PARTS = SIM / 'build-pack-20260913/assembly/print-parts'
LEG_GUIDE = SIM / 'build-pack-20260913/redesign-20260913/leg-guide-20261006/full-build-data.json'
PAD_MM = 0.3            # allowance box = region box grown by this
MIN_MARGIN_MM = 0.03    # allowance minMm = region min minus this, rounded down to 0.01


def stock_bracket(key, sign):
    """The one-piece stock ankle bracket in the ankle-redesign local frame (generate_candidate.py: solid())."""
    p = {q['key']: q for q in json.loads(LEG_GUIDE.read_text())['parts']}[key]
    m = trimesh.Trimesh(np.frombuffer(base64.b64decode(p['positionB64']), dtype='<f4').reshape(-1, 3),
                        np.frombuffer(base64.b64decode(p['indexB64']), dtype='<u4').reshape(-1, 3), process=True)
    T = np.eye(4); T[:3, :3] = [[sign, 0, 0], [0, 0, -sign], [0, 1, 0]]; T[:3, 3] = [-31.7771, sign * 33.8, -81.5]
    return m.apply_transform(np.linalg.inv(T))


STOCK = {'foot_left_slipfit': (lambda: trimesh.load(STOCK_PARTS / 'community-44.stl'), 'community-44.stl (stock left foot)'),
         'foot_right_slipfit': (lambda: trimesh.load(STOCK_PARTS / 'community-46.stl'), 'community-46.stl (stock right foot)'),
         'ankle_base_left': (lambda: stock_bracket('ankle', 1), 'the stock one-piece left ankle bracket (community-66.stl)'),
         'ankle_base_right': (lambda: stock_bracket('right_ankle', -1), 'the stock one-piece right ankle bracket (community-64.stl)')}


def man(t):
    return m3.Manifold(m3.Mesh(np.asarray(t.vertices, np.float32), np.asarray(t.faces, np.uint32)))


def reason(key, stock_name, r):
    where = 'internal rib of the foot' if key.startswith('foot') else 'wall beside the gusset hole, below the split'
    if r['stockMinusNewMm3'] > 0:
        return (f'Stock geometry: {where} of {stock_name}, already {r["stockMinMm"]}-{r["stockMedianMm"]} mm thick at this place in the '
                f'stock part. V1.22 adds nothing here; the 0.2 mm slip-fit socket clearance shaves {r["stockMinusNewMm3"]} mm3 from it.')
    return (f'Stock geometry, unchanged: {where} of {stock_name} ({r["stockMinMm"]}-{r["stockMedianMm"]} mm there in the stock part; '
            'zero volume difference to it within 1 mm).')


def main():
    sys.path.insert(0, str(HERE))
    import make_manifest as MM
    rows = {r['key']: r for r in MM.build_parts()}
    out, new_regions = {}, []
    for key, (load, stock_name) in STOCK.items():
        row = rows[key]; T = np.array(row['sourceToPrint'], float)
        new = trimesh.load(row['path'], force='mesh').apply_transform(T); stock = load().apply_transform(T)
        mn, ms = W.measure(new), W.measure(stock); tree = cKDTree(ms['points'])
        nm, sm = man(new), man(stock); thin = np.flatnonzero(mn['smoothed'] < W.MIN_WALL_MM - W.MEASURE_TOL_MM)
        entries = []
        for reg in (r for r in W.regions(mn) if r['areaMm2'] >= W.MIN_REGION_MM2):
            lo, hi = np.array(reg['bbox'])
            box = m3.Manifold.cube(tuple(map(float, hi - lo + 2))).translate(tuple(map(float, lo - 1)))
            sel = thin[np.all((mn['points'][thin] >= lo - 1e-6) & (mn['points'][thin] <= hi + 1e-6), 1)]
            d, j = tree.query(mn['points'][sel], k=8, distance_upper_bound=1.0)
            st = ms['smoothed'][j[np.isfinite(d)]]
            r = dict(bbox=reg['bbox'], areaMm2=reg['areaMm2'], minMm=reg['minMm'], medianMm=reg['medianMm'],
                     stockMinMm=round(float(st.min()), 2) if len(st) else None, stockMedianMm=round(float(np.median(st)), 2) if len(st) else None,
                     stockMinusNewMm3=round(((sm - nm) ^ box).volume(), 2), newMinusStockMm3=round(((nm - sm) ^ box).volume(), 3))
            stock_thin = r['stockMinMm'] is not None and r['stockMinMm'] < W.MIN_WALL_MM
            if r['newMinusStockMm3'] > 1e-3 or not stock_thin:
                new_regions.append((key, r)); print('NEW', key, r); continue
            entries.append(dict(bbox=[(lo - PAD_MM).round(3).tolist(), (hi + PAD_MM).round(3).tolist()],
                                minMm=float(np.floor((reg['minMm'] - MIN_MARGIN_MM) * 100) / 100), reason=reason(key, stock_name, r), evidence=r))
            print('STOCK', key, reg['areaMm2'], 'min', reg['minMm'], 'stock', r['stockMinMm'], r['stockMedianMm'], 'shaved', r['stockMinusNewMm3'])
        out[key] = entries
    (HERE / 'thin-wall-allowances.json').write_text(json.dumps(out, indent=1) + '\n')
    sys.exit(1 if new_regions else 0)


if __name__ == '__main__':
    main()
