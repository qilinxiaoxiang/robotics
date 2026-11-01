"""Bring guide/content/fasteners.json to the V1.40 battery backpack (2026-11-01). Idempotent: records carrying 'v140' are
left alone. Reads the world STLs that to_guide_world.py wrote (Dual Lock pose) and ray-casts each screw axis.

- BP-cap-01..03 (cap to frame, three M2 x 8, unchanged positions in y and z): the redesign cap is 1.1 mm deeper, so the
  head seat (rear face of the 3.0 mm column floor) moves from the V1.20 cap's to the V1.40 cap's; the screw still ends
  inside the frame boss pilot.
- BP-bar-01..04 (new, step bp-bars): the two retainer bars, 2 x M2 x 6 each, heads on the bar front face, axis -x, into
  the four cap boss pilots at (y, z) = (+-18.6, -8) and (+-18.6, 24) (team README: 5.5 mm M2 pilots at the boss front).
- counts are recomputed from the records.
    /tmp/microduck-cad-venv/bin/python update_fasteners.py"""
import json
from pathlib import Path
import numpy as np, trimesh

HERE = Path(__file__).resolve().parent
WORLD = HERE.parents[1] / 'world'
FAST = HERE.parents[2] / 'content' / 'fasteners.json'
TAG = 'V1.40 battery backpack 2026-11-01 (print/back-plate/battery-backpack-v140/update_fasteners.py)'
CAP = trimesh.load(WORLD / 'battery_backpack_cap.stl', force='mesh')
FRAME = trimesh.load(WORLD / 'battery_backpack_frame.stl', force='mesh')
BARS = trimesh.load(WORLD / 'battery_backpack_bars.stl', force='mesh')


def spans(m, y, z, r):
    """Solid x-intervals of m along x at (y + r, z): r off the axis, so the hole itself does not hide the material."""
    loc, _, _ = m.ray.intersects_location(np.array([[-200.0, y + r, z]]), np.array([[1.0, 0, 0]]))
    xs = sorted(np.asarray(loc).reshape(-1, 3)[:, 0].tolist())
    return [(round(a, 2), round(b, 2)) for a, b in zip(xs[0::2], xs[1::2])]


def hole_r(m, y, z, x):
    """Smallest probed radius at which a +y ray from the axis at x meets material: the hole radius (to 0.05 mm)."""
    loc, _, _ = m.ray.intersects_location(np.array([[x, y, z]]), np.array([[0, 1.0, 0]]))
    d = np.asarray(loc).reshape(-1, 3)[:, 1] - y
    return round(float(d[d > 0].min()), 2) if (d > 0).any() else None


def cap_screw(r):
    y, z = r['center'][1], r['center'][2]
    cap = spans(CAP, y, z, 1.6)               # column floor ring round the clearance hole
    frame = spans(FRAME, y, z, 1.6)           # boss ring round the pilot
    seat = cap[0][0]                          # rear face of the column floor: the head seat
    tip = seat + 8.0
    boss0 = frame[0][0]
    pilot_end = spans(FRAME, y, z, 0.0)[0][0]   # closed end of the pilot on the axis
    eng = round(tip - boss0 - 0.3, 2)
    r.update(center=[round(seat, 3), y, z], engagementMm=eng, tipMarginMm=round(pilot_end - tip, 2), verified=False,
             evidence=(f'V1.40 world STLs ray cast 2026-11-01: cap column floor x {cap[0][0]}..{cap[0][1]} (head seat {seat}), '
                       f'frame boss x {frame[0][0]}..{frame[0][1]}, pilot closed from x {pilot_end}; M2 x 8 tip x {round(tip, 2)}: '
                       f'{round(tip - boss0, 2)} mm of thread less 0.3 mm lead-in, {round(pilot_end - tip, 2)} mm of pilot past the tip.'),
             source='print/battery-quickswap-20261101/build (V1.40 frame and cap; screw positions of the D-037 redesign, unchanged from V1.20)',
             v140=TAG)
    return r


def bar_screw(i, y, z):
    head = spans(BARS, y, z, 1.6)[0]          # bar x span beside the hole
    boss = spans(CAP, y, z, 1.6)              # cap boss column beside the pilot
    seat = head[1]                            # bar front face
    tip = seat - 6.0
    boss_front = boss[-1][1]
    pilot = spans(CAP, y, z, 0.0)             # material on the axis: the closed end behind the pilot
    pilot_end = pilot[-1][1] if pilot else None
    eng = round(boss_front - tip - 0.3, 2)
    return {'id': f'BP-bar-0{i}', 'step': 'bp-bars', 'spec': 'M2 × 6 TAP', 'kind': 'TAP', 'diameterMm': 2.0, 'lengthMm': 6.0,
            'headDiameterMm': 4.0, 'headHeightMm': 1.5, 'nut': None, 'washer': None, 'center': [round(seat, 3), y, z],
            'axis': [-1.0, 0.0, 0.0], 'throughPart': 'battery_backpack_bars', 'throughParts': ['battery_backpack_bars'],
            'intoPart': 'battery_backpack_cap', 'engagementMm': eng,
            'tipMarginMm': round(tip - pilot_end, 2) if pilot_end is not None else None, 'verified': False,
            'evidence': (f'V1.40 world STLs ray cast 2026-11-01: bar x {head[0]}..{head[1]} (hole radius {hole_r(BARS, y, z, (head[0] + head[1]) / 2)}), '
                         f'cap boss column to x {boss_front} (pilot radius {hole_r(CAP, y, z, boss_front - 1.0)}), pilot closed behind x {pilot_end}; '
                         f'M2 x 6 tip x {round(tip, 2)}: {round(boss_front - tip, 2)} mm of thread less 0.3 mm lead-in.'),
            'note': 'Battery retainer bar to its cap boss.', 'role': 'Battery retainer bar to cap',
            'source': 'qilinxiaoxiang/microduck_rl 8bce48af cmu/hardware/battery-redesign/README.md (bars: 2 x M2 x 6 each into the boss pilots)',
            'reuse': True, 'v140': TAG}


def main():
    F = json.loads(FAST.read_text())
    out = [r if r.get('v140') or not r['id'].startswith('BP-cap-') else cap_screw(r) for r in F['screws'] if not r['id'].startswith('BP-bar-')]
    old_bars = [r for r in F['screws'] if r['id'].startswith('BP-bar-')]
    out += old_bars or [bar_screw(i + 1, y, z) for i, (y, z) in enumerate([(18.6, 24.0), (-18.6, 24.0), (18.6, -8.0), (-18.6, -8.0)])]
    F['screws'] = out
    by_step, by_spec = {}, {}
    for r in out:
        by_step[r['step']] = by_step.get(r['step'], 0) + 1
        by_spec[r['spec']] = by_spec.get(r['spec'], 0) + 1
    c = F['counts']
    c.update(total=len(out), byStep=by_step, bySpec=by_spec, verified=sum(1 for r in out if r.get('verified')))
    F['updated'] = '2026-11-01'
    FAST.write_text(json.dumps(F, indent=1, ensure_ascii=False) + '\n')
    for r in out:
        if r['id'].startswith(('BP-cap-', 'BP-bar-')):
            print(r['id'], r['center'], r['engagementMm'], r.get('tipMarginMm'), r['evidence'])


if __name__ == '__main__':
    main()
