"""Optional shims for the neck pitch ring: 1 mm and 2 mm, same 16.4 / 22 mm bore and outside as the ring.

    /tmp/microduck-cad-venv/bin/python print/neck-ring/make_shims.py

They go over the 16 mm boss on top of the pitch bracket, under the ring, when the printed stack still leaves a gap under
the ID13 case. A washer around the 18 mm shoulder would not lift the ring (the shoulder is itself 1 mm high) and would
overhang the 18 mm wide bracket front and back. Each edge has the ring's 0.3 mm chamfer, so the bore clears the 0.2 mm
chamfer at the root of the boss. Output is in print frame (axis z, lower face on z 0).
"""
import hashlib, json
from pathlib import Path
import numpy as np, trimesh

HERE = Path(__file__).resolve().parent
RI, RO, C = 8.2, 11.0, 0.3


def shim(t):
    prof = np.array([(RI + C, 0), (RO - C, 0), (RO, C), (RO, t - C), (RO - C, t), (RI + C, t), (RI, t - C), (RI, C), (RI + C, 0)])
    m = trimesh.creation.revolve(prof, sections=180)
    if m.volume < 0:
        m.invert()
    assert m.is_watertight and m.is_volume, t
    return m


def main():
    rec = {}
    for t in (1.0, 2.0):
        m = shim(t)
        out = HERE / f'shim_{int(t)}mm.stl'
        m.export(out)
        rec[out.name] = dict(thicknessMm=round(float(m.extents[2]), 3), outerDiameterMm=round(float(m.extents[0]), 3),
                             boreMm=2 * RI, volumeMm3=round(float(m.volume), 2),
                             bedContactMm2=round(float(np.pi * ((RO - C) ** 2 - (RI + C) ** 2)), 1),
                             sha256=hashlib.sha256(out.read_bytes()).hexdigest())
    rec['use'] = ('Optional. Over the 16 mm boss, on the 18 mm shoulder, under the 4.9 mm ring. Add only if the ring still '
                  'rattles under ID13 after the four horn screws are tight; stop as soon as ID13 turns stiffly by hand.')
    rec['modelGapMm'] = 0.0
    rec['reason'] = ('The model leaves no gap with the 4.9 mm ring. Shawn judged the printed stack at least 2 mm short and '
                     'asked for 1 mm and 2 mm shims to add on the bench (2026-10-12).')
    (HERE / 'shims.json').write_text(json.dumps(rec, indent=1))
    print(json.dumps(rec, indent=1))


if __name__ == '__main__':
    main()
