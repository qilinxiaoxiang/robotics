"""Close the 2 x 30 mm strip the V1.8 window fill left open in the lower head shell roof.

V1.8 filled the V1.6 beak-roof window with the original shell material inside the box x 57.9..71.4, y -35.8..-5.0, but
the V1.6 window reached x 73.6, so a strip x 71.4..73.6 stayed open: a slot with no purpose. This script adds the
original shell (camera-ribbon-repair/head-source-cache) inside x 71.0..74.5, y -36.5..-4.5 back onto the current
V1.8 shell. A direct union with the source leaves pinched edges, because the source and V1.8 roof surfaces differ by
microns; so the fill is the V1.8 roof's own solid slab x 68.9..71.4 shifted +2.5 mm in x, which covers the strip and
overlaps 0.3 mm into the roof on each side. Acceptance: one closed body, no roof column in the strip that is open while
the source has roof, and top/bottom faces within 0.05 mm of the source. Writes ../world/head_bottom.stl and
close_strip.json.

    /tmp/microduck-cad-venv/bin/python close_strip.py
"""
import base64, hashlib, json
from pathlib import Path
import numpy as np
import manifold3d as m3
import trimesh

HERE = Path(__file__).resolve().parent
SIM = HERE.parents[2]
CACHE = SIM / 'build-pack-20260913/redesign-20260913/head-redesign-20261008/camera-ribbon-repair/head-source-cache'
BEFORE = HERE / 'head_bottom-before-strip.stl'
OUT = HERE.parent / 'world/head_bottom.stl'
STRIP = ([71.0, -36.5, 100.0], [74.5, -4.5, 118.0])
SLAB = ([68.9, -36.0, 105.0], [71.4, -4.6, 115.0])   # filled V1.8 roof next to the strip, inside the window rim
SHIFT = 2.5


def man(v, f):
    return m3.Manifold(m3.Mesh(vert_properties=np.asarray(v, np.float32), tri_verts=np.asarray(f, np.uint32)))


def box(lo, hi):
    lo, hi = np.array(lo, float), np.array(hi, float)
    return m3.Manifold.cube((hi - lo).tolist()).translate(lo.tolist())


def main():
    idx = json.loads((CACHE / 'index.json').read_text())
    p = json.loads((CACHE / idx['parts']['head_bottom']).read_text())
    v = np.frombuffer(base64.b64decode(p['positionB64']), '<f4').reshape(-1, 3).astype(np.float64)
    f = np.frombuffer(base64.b64decode(p['indexB64']), '<u4').reshape(-1, 3).astype(np.int64)
    s = trimesh.Trimesh(v, f, process=True)   # merges the duplicated vertices of the guide encoding
    src = man(s.vertices, s.faces)
    assert src.status() == m3.Error.NoError, src.status()
    old = trimesh.load(BEFORE)
    cur = man(old.vertices, old.faces)
    slab = cur ^ box(SLAB[0], SLAB[1])
    fill = slab.translate([SHIFT, 0, 0])
    pieces = (cur + fill).decompose()
    assert len(pieces) == 1, [m.volume() for m in pieces]
    new = pieces[0]
    mm = new.to_mesh()
    t = trimesh.Trimesh(mm.vert_properties[:, :3].astype(np.float64), mm.tri_verts.astype(np.int64), process=False)
    t.export(OUT)
    r = trimesh.load(OUT)
    xs, ys = np.arange(70.0, 75.01, 0.25), np.arange(-37.0, -3.99, 0.25)
    O = np.array([[x, y, 100.0] for x in xs for y in ys]); D = np.tile([0, 0, 1.0], (len(O), 1))

    def roof(m):
        loc, ri, _ = m.ray.intersects_location(O, D); out = []
        for i in range(len(O)):
            z = np.sort(loc[ri == i, 2]); z = z[(z >= 108) & (z <= 114)]
            out.append((z.min(), z.max()) if len(z) else None)
        return out
    a, b = roof(r), roof(s)
    dev = [max(abs(a[i][0] - b[i][0]), abs(a[i][1] - b[i][1])) for i in range(len(O)) if a[i] and b[i]]
    rays = dict(columns=len(O), spacingMm=0.25, openWhereSourceHasRoof=sum(1 for i in range(len(O)) if a[i] is None and b[i] is not None),
                roofWhereSourceHasNone=sum(1 for i in range(len(O)) if a[i] and not b[i]), maxFaceDeviationMm=round(float(max(dev)), 4))
    res = dict(before=str(BEFORE), out=str(OUT), strip=STRIP, slab=SLAB, shiftMm=SHIFT, stripRays=rays,
               addedVolumeMm3=round(float(new.volume() - cur.volume()), 3), beforeVolumeMm3=round(float(cur.volume()), 3),
               newVolumeMm3=round(float(new.volume()), 3), status=str(new.status()), genusBefore=int(cur.genus()), genusAfter=int(new.genus()),
               remainingOriginalMaterialMissingInStripMm3=round(float(((src ^ box(*STRIP)) - new).volume()), 4),
               readback=dict(watertight=bool(r.is_watertight), windingConsistent=bool(r.is_winding_consistent), volume=round(float(r.volume), 3),
                             bodies=int(len(r.split(only_watertight=False))), faces=int(len(r.faces)), bounds=np.round(r.bounds, 3).tolist()),
               sha256=hashlib.sha256(OUT.read_bytes()).hexdigest(), bytes=OUT.stat().st_size)
    assert res['readback']['watertight'] and res['readback']['bodies'] == 1 and rays['openWhereSourceHasRoof'] == 0 and rays['maxFaceDeviationMm'] < 0.05, res
    (HERE / 'close_strip.json').write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1))


if __name__ == '__main__':
    main()
