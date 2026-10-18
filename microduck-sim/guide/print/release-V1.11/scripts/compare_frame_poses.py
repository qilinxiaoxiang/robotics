"""V1.11 note: copied from release-V1.10 as a template and not run for V1.11. The layout F poses were screened by bed
contact, height and overhang (back-plate/layout-F/checks.json 7_printability) and confirmed by orientation_check.py and
the native slices (review/). The face groups below are the C2 frame's.

Bounded comparison of the rear_frame print poses (PRINT-ORIENTATION-PRACTICE step 2): the release pose (bottom wall on
the bed) against the best-screened alternative 'stable p=0.08' (+y side wall on the bed). One frame per plate, Bambu
only, scratch runs outside run/, same Orange profile and 4 mm outer brim override as the release.

    prepare+slice:  driven by the shell (release_pipeline.py prepare/slice under run_bounded_cad.py)
    analysis:       /tmp/microduck-cad-venv/bin/python scripts/compare_frame_poses.py SCRATCH_DIR

Per slice: ETA, grams, support filament (mm of 1.75 mm filament, mm3, g at 1.24 g/cm3), support XY path length,
native first-layer model area. Support contact: every support extrusion sample (segment ends and midpoint, extruder
offset applied) within 0.8 mm (0.2 top Z gap + 0.42 line + margin) of the part surface, matched to the nearest surface
sample (0.25 mm even sampling with triangle ids); a triangle is support-touched when such a sample is nearest to it.
Touched area is reported per named face group (source frame):
  seatFace       plate face x = -45 (normal +x) that mates to the pack (outside the lip)
  lip            all lip faces, x -45..-37.5, |y| <= 13.2, z 27.3..28.5 (locating sides, underside, front)
  bossTops       the end facets of every boss found by orientation_check.detect_holes (26 bosses)
  lidSeatEdge    rear faces at x = -65.9 (normal -x) where the lid seats
  outerSideWalls outer faces |y| = 32.05 (cosmetic)
  other          everything else (inner wall faces, top-wall underside, web)
Writes ../orientation-decision.json only through --write (the decision text is passed in).
"""
import argparse, json, math, re, sys
from pathlib import Path
import numpy as np
import trimesh
from scipy.spatial import cKDTree
sys.dont_write_bytecode = True
sys.path.insert(0, '/Users/xiangzheng/code/robotics/microduck-sim/build-pack-20260913/redesign-20260913/printing/13-RELEASE-PIPELINE-20261009')
sys.path.insert(0, '/Users/xiangzheng/code/robotics/microduck-sim/guide/print/orientation-study')
import release_pipeline as r  # noqa: E402
import orientation_check as oc  # noqa: E402

FIL_AREA = math.pi * 1.75 ** 2 / 4
DENSITY = 1.24e-3  # g/mm3 PLA


def groups(mesh):
    c = mesh.triangles_center; n = mesh.face_normals; g = np.full(len(c), 'other', dtype=object)
    g[(np.abs(c[:, 1]) > 32.0) & (np.abs(n[:, 1]) > 0.99)] = 'outerSideWalls'
    g[(np.abs(c[:, 0] + 65.9) < 0.01) & (n[:, 0] < -0.99)] = 'lidSeatEdge'
    g[(np.abs(c[:, 0] + 45.0) < 0.01) & (n[:, 0] > 0.99)] = 'seatFace'
    lip = (c[:, 0] > -45.0 + 1e-3) & (np.abs(c[:, 1]) <= 13.2 + 1e-3) & (c[:, 2] >= 27.3 - 1e-3) & (c[:, 2] <= 28.5 + 1e-3)
    g[lip] = 'lip'
    for h in oc.detect_holes(mesh):
        if h['kind'] != 'boss':
            continue
        for e in h['ends']:
            g[mesh.facets[e['facet']]] = 'bossTops'
    return g


def support_samples(gc, machine, cfg):
    off = list(map(float, cfg.get('extruder_offset', ['0x0'])[0].split('x'))) if machine == 'Bambu' else [0., 0.]
    xyz = [0., 0., 0.]; kind = ''; relative = True; e = 0.; pts = []; e_sup = 0.0; length = 0.0
    for line in gc.decode(errors='replace').splitlines():
        if line.startswith(('; FEATURE:', ';TYPE:')): kind = line.split(':', 1)[1].strip().lower()
        if line.startswith('M82'): relative = False
        if line.startswith('M83'): relative = True
        if line.startswith('G92 '):
            m = re.search(r'E([-+\d.]+)', line)
            if m: e = float(m[1])
        if not re.match(r'^G[0123] ', line): continue
        v = {k: float(t) for k, t in re.findall(r'([XYZE])([-+]?\d*\.?\d+)', line.split(';')[0])}
        end = [v.get(k, xyz[i]) for i, k in enumerate('XYZ')]; de = v.get('E', 0) if relative else v.get('E', e) - e
        if 'E' in v: e = v['E'] if not relative else e + v['E']
        if de > 0 and 'support' in kind and end[:2] != xyz[:2]:
            e_sup += de; length += math.hypot(end[0] - xyz[0], end[1] - xyz[1])
            for f in (0.0, 0.5, 1.0):
                pts.append((xyz[0] + f * (end[0] - xyz[0]) + off[0], xyz[1] + f * (end[1] - xyz[1]) + off[1], end[2]))
        xyz = end
    return np.array(pts), e_sup, length


def analyse(run):
    run = Path(run).resolve(); prep = r.read(run / 'preparation.json'); row = prep['rows'][0]; part = prep['parts'][0]
    res = r.read(run / 'native/Orange_Bambu/result.json'); g, cfg, _ = r.native_payload(Path(res['archive']['path']))
    src = r.load_mesh(Path(part['source']['path'])); grp = groups(src)
    T = np.array(part['sourceToPrint']); T[2, 3] += part['dropToBedMm']; pl = row['placements'][0]
    m = src.copy(); m.apply_transform(T); m.apply_translation(pl['translation'])
    samples, fid = trimesh.sample.sample_surface_even(m, 600000, radius=0.25, seed=1)
    pts, e_sup, length = support_samples(g, 'Bambu', cfg)
    d, idx = cKDTree(samples).query(pts, distance_upper_bound=0.8)
    hit = np.isfinite(d); tri = np.unique(fid[idx[hit]])
    on_bed = m.triangles[:, :, 2].max(1) <= 0.01
    tri = tri[~on_bed[tri]]
    area = {}
    for k in ('seatFace', 'lip', 'bossTops', 'lidSeatEdge', 'outerSideWalls', 'other'):
        sel = tri[grp[tri] == k]; nzs = m.face_normals[sel, 2]
        area[k] = dict(landingAreaMm2=round(float(m.area_faces[sel[np.abs(nzs) > 0.5]].sum()), 1),
                       adjacentVerticalAreaMm2=round(float(m.area_faces[sel[np.abs(nzs) <= 0.5]].sum()), 1),
                       groupAreaMm2=round(float(m.area_faces[grp == k].sum()), 1), touchedTriangles=int(len(sel)))
    # direction of the touched faces in the print frame
    nz = m.face_normals[tri, 2]
    first, _ = r.first_layer(g, r.bound(row['project']), 'Bambu')
    gram = float(re.search(r'total filament weight \[g\]\s*:\s*([\d.]+)', g.decode(errors='replace'))[1])
    return dict(run=str(run), archive=res['archive'], sourceToPrint=part['sourceToPrint'], heightMm=round(float(m.extents[2]), 2),
                etaSeconds=r.time_seconds(g, 'Bambu'), totalGrams=gram,
                supportFilamentMm=round(e_sup, 1), supportVolumeMm3=round(e_sup * FIL_AREA, 0), supportGrams=round(e_sup * FIL_AREA * DENSITY, 2),
                supportPathLengthMm=round(length, 0), supportSamples=int(len(pts)), supportSamplesTouchingPart=int(hit.sum()),
                supportOnModelAreaMm2=round(float(m.area_faces[tri].sum()), 1),
                supportOnModelByDirectionMm2=dict(facingDown=round(float(m.area_faces[tri[nz < -0.5]].sum()), 1),
                                                  facingUp=round(float(m.area_faces[tri[nz > 0.5]].sum()), 1),
                                                  vertical=round(float(m.area_faces[tri[np.abs(nz) <= 0.5]].sum()), 1)),
                supportContactByFaceGroup=area,
                nativeFirstLayer={x['name']: dict(modelAreaMm2=round(x['model_area_mm2'], 2), islands=x['modelIslands']) for x in first})


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('scratch'); a = ap.parse_args()
    S = Path(a.scratch)
    out = {k: analyse(S / k) for k in ('current', 'sidewall')}
    (S / 'compare.json').write_text(json.dumps(out, indent=1) + '\n')
    for k, v in out.items():
        print(k, json.dumps({x: y for x, y in v.items() if x not in ('sourceToPrint', 'archive', 'run')}))
