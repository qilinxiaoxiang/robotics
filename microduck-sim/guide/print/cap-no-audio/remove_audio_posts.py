"""Remove the four audio roof posts from the V1.8 head cap.

Shawn deferred the speaker and amplifier on 2026-10-12: they come back later as a loose add-on held by tape or a clip,
so the two speaker-cage bosses (ears at [5, -21.5] and [45, -21.5]) and the two amplifier posts ([19.65, 17.3] and
[32.35, 17.3]) have no purpose. Each post hangs below a plain 1.7-2.0 mm roof; its pilot hole ends inside the post,
so the roof above it is intact. The post is cut away below the roof underside of the original source shell
(head-layout/native-cap-registered-world.stl, the cap before any internal mounts were added), lowered by SKIN so the
cut never shares a surface with the roof (a shared surface leaves zero-width slivers in the boolean).
Acceptance: one closed body, nothing changed outside the four boxes, and no post material left more than SKIN below
the original roof underside.
Reads candidates/head-cap-v18-with-audio-posts/head_cap-world.stl, writes ../world/head_cap.stl and remove_audio_posts.json.

    /tmp/microduck-cad-venv/bin/python remove_audio_posts.py
"""
import hashlib, json
from pathlib import Path
import numpy as np
import manifold3d as m3
import trimesh

HERE = Path(__file__).resolve().parent
SIM = HERE.parents[2]
OLD = HERE.parent / 'candidates/head-cap-v18-with-audio-posts/head_cap-world.stl'
REF = SIM / 'build-pack-20260913/redesign-20260913/workflow-review-20261009/enclosed-wiring-repair/head-layout/native-cap-registered-world.stl'
OUT = HERE.parent / 'world/head_cap.stl'
# Post footprints found by comparing the cap with the source shell (faces deviating > 0.3 mm), plus a margin.
POSTS = {'speaker_post_front': ([42.4, -24.1], [47.6, -18.9]), 'speaker_post_rear': ([2.4, -24.1], [7.6, -18.9]),
         'amp_post_front': ([30.4, 15.3], [34.3, 19.3]), 'amp_post_rear': ([17.7, 15.3], [21.6, 19.3])}
MARGIN, ZLOW, SKIN = 0.8, 125.0, 0.02


def man(t):
    return m3.Manifold(m3.Mesh(vert_properties=np.asarray(t.vertices, np.float32), tri_verts=np.asarray(t.faces, np.uint32)))


def roof(rt, lo, hi):
    """Underside and top of the source-shell roof on a 0.25 mm grid over the box footprint."""
    xs, ys = np.arange(lo[0], hi[0] + 1e-9, 0.25), np.arange(lo[1], hi[1] + 1e-9, 0.25)
    g = np.array([[x, y, 100.0] for x in xs for y in ys])
    loc, ray, _ = rt.ray.intersects_location(g, np.tile([0, 0, 1.0], (len(g), 1)), multiple_hits=True)
    under, top = np.full(len(g), np.inf), np.full(len(g), -np.inf)
    np.minimum.at(under, ray, loc[:, 2]); np.maximum.at(top, ray, loc[:, 2])
    assert np.isfinite(under).all() and (np.bincount(ray, minlength=len(g)) == 2).all(), 'roof is not a single plain layer here'
    return float(under.max()), float(top.min()), float(under.min()), float(top.max())


def main():
    ot, rt = trimesh.load(OLD), trimesh.load(REF)
    old, ref_low = man(ot), man(rt).translate([0, 0, -SKIN])
    boxes, cuts, rep = [], [], {}
    for name, (lo, hi) in POSTS.items():
        lo2, hi2 = [lo[0] - MARGIN, lo[1] - MARGIN], [hi[0] + MARGIN, hi[1] + MARGIN]
        u_max, t_min, u_min, t_max = roof(rt, lo2, hi2)
        b = m3.Manifold.cube([hi2[0] - lo2[0], hi2[1] - lo2[1], t_max + 2 - ZLOW]).translate([lo2[0], lo2[1], ZLOW])
        # The box minus the lowered roof falls into two pieces: the space under the roof (holding the post) and the
        # space over it. Only the lower piece is cut.
        parts = sorted((b - ref_low).decompose(), key=lambda m: m.bounding_box()[2])
        assert len(parts) == 2, (name, len(parts))
        cut = parts[0]
        boxes.append(b)
        cuts.append(cut)
        rep[name] = dict(boxLo=lo2 + [ZLOW], boxHi=hi2 + [round(t_max + 2, 3)], roofUndersideMm=[round(u_min, 3), round(u_max, 3)],
                         roofTopMm=[round(t_min, 3), round(t_max, 3)], removedMm3=round((old ^ cut).volume(), 3))
    cut_all = m3.Manifold.batch_boolean(cuts, m3.OpType.Add)
    new = old - cut_all
    pieces = new.decompose()
    assert len(pieces) == 1, [p.volume() for p in pieces]
    allb = m3.Manifold.batch_boolean(boxes, m3.OpType.Add)
    outside = ((new - allb) - (old - allb)).volume() + ((old - allb) - (new - allb)).volume()
    leftover = ((new ^ allb) - man(rt)).volume()  # material in the boxes that the source shell does not have
    mm = new.to_mesh()
    trimesh.Trimesh(mm.vert_properties[:, :3].astype(np.float64), mm.tri_verts.astype(np.int64), process=False).export(OUT)
    r = trimesh.load(OUT)
    res = dict(out=str(OUT), source=str(OLD), sourceSha256=hashlib.sha256(OLD.read_bytes()).hexdigest(), shell=str(REF),
               skinMm=SKIN, posts=rep, volumeBeforeMm3=round(old.volume(), 3), volumeAfterMm3=round(new.volume(), 3),
               changeOutsideBoxesMm3=round(outside, 5), leftoverBelowRoofMm3=round(leftover, 4),
               genusBefore=int(old.genus()), genusAfter=int(new.genus()),
               readback=dict(watertight=bool(r.is_watertight), bodies=int(len(r.split(only_watertight=False))),
                             bounds=np.round(r.bounds, 3).tolist(), faces=int(len(r.faces))),
               sha256=hashlib.sha256(OUT.read_bytes()).hexdigest(), bytes=OUT.stat().st_size)
    (HERE / 'remove_audio_posts.json').write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1))
    assert res['readback']['watertight'] and res['readback']['bodies'] == 1 and outside < 1e-3
    assert res['readback']['bounds'] == np.round(ot.bounds, 3).tolist()


if __name__ == '__main__':
    main()
