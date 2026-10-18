#!/usr/bin/env python3
"""Task 1: one integrated study cap = notch-less V1.8 cap + audio 'roof pair' cap edits + Pi-mount option A rails,
with the option A +y web trimmed locally to >= 1.0 mm from jaw_support, static and over the 40 mm cap descent.

Construction (exact manifold3d booleans):
  A      = pi-mount/study-solids/A-head_cap-world.stl (audio extension cap + option A rails; built on V1.8)
  trim   = (jaw_support near the +y web, Minkowski-summed with a vertical capsule r TRIM_R from 0 to -40 mm)
           intersected with option A's +y added material. Descent lowers the cap onto the head, so relative to the cap
           jaw_support moves from 40 mm below to its final place: the capsule covers every descent position.
  A'     = A - trim
  final  = (A' - notch edit box) + (V1.5 pre-notch cap & notch edit box)    (same splice as neck-route/make_nonotch_cap.py)
Checks: bodies, manifold status, watertight after STL round trip; XOR against V1.8 outside the union of every edited
region (audio added/removed, option A added/removed, notch edit box); +y web to jaw_support gap static and over the
descent (0.5 mm steps); the option A beam numbers (pi-mount/scripts/check_options.py rail_strength and web_path)
before and after the trim. Writes ../study-solids/head_cap-integrated-world.stl, web_trim_removed-world.stl, ../cap-build.json.
"""
from __future__ import annotations

import json

import manifold3d as m3
import numpy as np
import trimesh

import int_lib as L
from pm_lib import CAP_V18, Head, bbox, box, load_stl_man, tm_from_man, man_from_tm  # noqa: E402
from check_options import rail_strength, web_path  # noqa: E402

TRIM_R = 1.1          # >= 1.0 mm target; polygon spheres are inscribed, the volumetric check below confirms the real clearance
TRAVEL = 40.0


def solid(M, eps=1e-3):
    """Drop the zero-volume sliver shells that coplanar boolean cuts leave behind (they are not material, but
    min_gap measures them)."""
    return m3.Manifold.batch_boolean([b for b in M.decompose() if b.volume() > eps], m3.OpType.Add)


def main():
    A = load_stl_man(L.PIM / 'study-solids' / 'A-head_cap-world.stl')
    EXT = load_stl_man(L.AUDIO / 'study-solids' / 'head_cap_extension-world.stl')
    # option A's edit, taken as the exact difference of its cap against the audio cap it was built on (pi-mount's
    # A-added-world.stl is not a closed solid after its STL export: trimesh finds 50 open pieces)
    A_add, A_rem = A - EXT, EXT - A
    au_add = load_stl_man(L.AUDIO / 'study-solids' / 'cap_added_material-world.stl')
    au_rem = load_stl_man(L.AUDIO / 'study-solids' / 'cap_removed_material-world.stl')
    V18 = load_stl_man(CAP_V18)
    H = Head()
    js = H.get('jaw_support')
    res = {'what': 'Integrated study cap (not a print file): notch-less V1.8 + audio roof-pair edits + Pi-mount A rails, +y web trimmed'}

    # ---- trim of the +y web
    py = A_add ^ box([0, 0, 0], [120, 80, 220])
    pb = bbox(py)
    crop = js ^ box(pb[0] - 3, pb[1] + [3, 3, TRAVEL + 3])
    caps = m3.Manifold.batch_hull([m3.Manifold.sphere(TRIM_R, 24), m3.Manifold.sphere(TRIM_R, 24).translate([0, 0, -TRAVEL])])
    # exact Minkowski sum of a closed solid with a convex capsule = the solid plus, per surface triangle, the hull of the
    # capsule placed at its three corners
    cv, cf = (np.asarray(a) for a in (crop.to_mesh().vert_properties, crop.to_mesh().tri_verts))
    hulls = [m3.Manifold.batch_hull([caps.translate(list(map(float, cv[i, :3]))) for i in tri]) for tri in cf]
    K = m3.Manifold.batch_boolean([crop] + hulls, m3.OpType.Add)
    trim = K ^ py
    # A - trim would cut along faces shared with the audio cap and leave zero-thickness flaps; instead remove all of
    # K and add the audio cap back inside a slightly larger K2 (overlapping union, no coincident faces):
    # Atr = (A - K) + (EXT & K2)  ==  A minus option A's own material inside K
    caps2 = m3.Manifold.batch_hull([m3.Manifold.sphere(TRIM_R + 0.1, 24), m3.Manifold.sphere(TRIM_R + 0.1, 24).translate([0, 0, -TRAVEL - 0.1])])
    K2 = m3.Manifold.batch_boolean([crop] + [m3.Manifold.batch_hull([caps2.translate(list(map(float, cv[i, :3]))) for i in tri])
                                             for tri in cf], m3.OpType.Add)
    Atr = (A - K) + (EXT ^ K2)
    xor_alt = (Atr - (A - trim)).volume() + ((A - trim) - Atr).volume()
    res['webTrim'] = {'method': f'jaw_support (cropped to the +y web box) Minkowski capsule r {TRIM_R} mm, z 0..-{TRAVEL} mm, '
                                'intersected with option A +y added material',
                      'removedMm3': trim.volume(), 'removedBounds': bbox(trim),
                      'webAddedPlusYBeforeMm3': py.volume(), 'jawSupportCropTriangles': len(cf),
                      'xorTrimmedVsAMinusTrimMm3': xor_alt}

    def descent_gap(M):
        g = 99.0
        for dz in np.arange(0.0, TRAVEL + 1e-9, 0.5):
            P = M.translate([0, 0, float(dz)])
            if (P ^ js).volume() > 1e-9:
                return -1.0
            g = min(g, float(P.min_gap(js, 6)))
        return g

    py_after = solid(py - trim)
    py = solid(py)
    res['webTrim']['jawSupportGapMm'] = {
        'plusYAddedBefore': {'static': float(py.min_gap(js, 6)), 'descentMin': descent_gap(py)},
        'plusYAddedAfter': {'static': float(py_after.min_gap(js, 6)), 'descentMin': descent_gap(py_after)}}
    # whole-cap gap to jaw_support (V1.8 cap vs integrated), for context
    res['webTrim']['wholeCapToJawSupportStaticGapMm'] = {'V1.8': float(V18.min_gap(js, 6)), 'A': float(A.min_gap(js, 6)),
                                                          'trimmed': float(Atr.min_gap(js, 6))}
    res['webTrim']['wholeCapToJawSupportOverlapMm3'] = {'V1.8': (V18 ^ js).volume(), 'trimmed': (Atr ^ js).volume()}

    # ---- notch-less splice
    import sys
    sys.path.insert(0, str(L.NR))
    from nr_lib import GUIDE
    EVID = GUIDE / 'print/release-V1.6/evidence'
    change = json.loads((EVID / 'head_cap-change.json').read_text())
    snap = json.loads((EVID / 'cap-notch-report-snapshot.json').read_text())
    V15p = change['v15Source']['path']
    assert L.sha(V15p) == change['v15Source']['sha256']
    v15 = trimesh.load(V15p, force='mesh')
    v15.apply_transform(np.linalg.inv(np.array(snap['worldToPrint']['matrix4x4'])))
    A15 = man_from_tm(v15)
    lo, hi = (np.array(snap['unchangedGeometry']['editBoxWorldMm'][k]) for k in ('min', 'max'))
    B = box(lo, hi)
    res['editsTouchNotchBoxMm3'] = {'audioAdded': (au_add ^ B).volume(), 'audioRemoved': (au_rem ^ B).volume(),
                                    'optionAAdded': (A_add ^ B).volume(), 'optionARemoved': (A_rem ^ B).volume()}
    final = (Atr - B) + (A15 ^ B)
    bodies = sorted(final.decompose(), key=lambda b: -b.volume())
    res['bodiesBeforeCleanup'] = len(bodies)
    res['looseBodiesDropped'] = [{'mm3': b.volume(), 'bounds': bbox(b)} for b in bodies[1:]]
    final = bodies[0]
    res['bodies'] = len(final.decompose())

    # Volumetric clearance (robust to the zero-thickness flaps that coplanar booleans leave, which min_gap measures):
    # the largest r for which the material has < 1e-4 mm3 inside jaw_support (+y crop) grown by r, statically and
    # with the capsule that covers the 40 mm descent.
    def grown(r, travel):
        cp = m3.Manifold.batch_hull([m3.Manifold.sphere(r, 48), m3.Manifold.sphere(r, 48).translate([0, 0, -travel])])
        return m3.Manifold.batch_boolean([crop] + [m3.Manifold.batch_hull([cp.translate(list(map(float, cv[i, :3]))) for i in tri])
                                                   for tri in cf], m3.OpType.Add)

    def vol_clear(M, travel):
        best = 0.0
        for r in np.arange(0.2, 1.401, 0.05):
            if (M ^ grown(float(r), travel)).volume() < 1e-4:
                best = float(r)
            else:
                break
        return best
    addF = final - V18           # integrated material that V1.8 does not have
    zoneF = final ^ box([45, 20, 110], [66, 46, 150])
    zoneV = V18 ^ box([45, 20, 110], [66, 46, 150])
    res['webTrim']['volumetricClearanceToJawSupportMm'] = {
        'note': 'largest r (0.05 mm steps, polygon spheres with 48 segments are inscribed: true value within ~0.01 mm '
                'above) with < 1e-4 mm3 of material inside jaw_support grown by r; descent = grown along -z by 40 mm',
        'integratedAddedVsV18': {'static': vol_clear(addF, 0.0), 'descent': vol_clear(addF, TRAVEL)},
        'optionA_untrimmed_added': {'static': vol_clear(A - EXT, 0.0), 'descent': vol_clear(A - EXT, TRAVEL)},
        'integratedPlusYRailZone': {'static': vol_clear(zoneF, 0.0), 'descent': vol_clear(zoneF, TRAVEL)},
        'V1.8PlusYRailZone': {'static': vol_clear(zoneV, 0.0), 'descent': vol_clear(zoneV, TRAVEL)}}
    zone = box([45, 20, 110], [66, 46, 150])
    fz = solid(final ^ zone)
    # the V1.8 part of that zone (rail) for reference: its own gap to jaw_support
    vz = solid(V18 ^ zone)
    res['webTrim']['finalCapPlusYRailZoneToJawSupportMm'] = {'static': float(fz.min_gap(js, 6)), 'descentMin': descent_gap(fz),
                                                             'V1.8SameZone': {'static': float(vz.min_gap(js, 6)), 'descentMin': descent_gap(vz)},
                                                             'zone': 'x 45..66, y 20..46, z 110..150'}
    res['manifoldStatus'] = str(final.status())
    res['genus'] = final.genus()
    res['volumes'] = {'V1.8': V18.volume(), 'A': A.volume(), 'integrated': final.volume()}

    # ---- XOR vs V1.8 outside every edited region
    region = m3.Manifold.batch_boolean([au_add, au_rem, A_add, A_rem, B], m3.OpType.Add)
    d1, d2 = final - V18, V18 - final
    res['xorVsV18'] = {'totalMm3': d1.volume() + d2.volume(),
                       'outsideEditedRegionsMm3': (d1 - region).volume() + (d2 - region).volume(),
                       'addedVsV18Mm3': d1.volume(), 'removedVsV18Mm3': d2.volume(),
                       'editedRegion': 'union of audio cap_added/cap_removed, option A (A cap minus audio cap and back), notch edit box'}
    # every piece of the difference larger than 0.001 mm3 that lies outside the regions (expected: none)
    stray = [b for b in ((d1 - region) + (d2 - region)).decompose() if b.volume() > 1e-3]
    res['xorVsV18']['strayPiecesOver0p001Mm3'] = [{'mm3': s.volume(), 'bounds': bbox(s)} for s in stray]

    # ---- export and STL round-trip check
    tm = tm_from_man(final)
    res['meshDirect'] = {'watertight': bool(tm.is_watertight), 'windingConsistent': bool(tm.is_winding_consistent)}
    tm.export(L.INTEGRATED_CAP)
    chk = trimesh.load(L.INTEGRATED_CAP, force='mesh')
    res['stlRoundTrip'] = {'watertight': bool(chk.is_watertight), 'windingConsistent': bool(chk.is_winding_consistent),
                           'bodies': len(chk.split(only_watertight=False)), 'faces': len(chk.faces),
                           'degenerateFaces': int((chk.area_faces < 1e-12).sum())}
    e = chk.edges_sorted
    u, c = np.unique(e, axis=0, return_counts=True)
    pv = chk.vertices[u[c > 2]].reshape(-1, 3)
    rt = man_from_tm(chk)
    res['stlRoundTrip'].update({'edgesSharedByMoreThanTwoFaces': int((c > 2).sum()), 'edgesTotal': len(u),
                                'pinchedEdgeBounds': [pv.min(0), pv.max(0)] if len(pv) else None,
                                'reloadedByManifold3d': {'status': str(rt.status()), 'bodies': len(rt.decompose()),
                                                         'volumeMm3': rt.volume()}})
    for nm, pth in (('optionA_cap', L.PIM / 'study-solids' / 'A-head_cap-world.stl'),
                    ('audio_cap', L.AUDIO / 'study-solids' / 'head_cap_extension-world.stl')):
        t2 = trimesh.load(pth, force='mesh')
        _, c2 = np.unique(t2.edges_sorted, axis=0, return_counts=True)
        res['stlRoundTrip'].setdefault('siblingInputsEdgesSharedByMoreThanTwoFaces', {})[nm] = int((c2 > 2).sum())
    tm_from_man(trim).export(L.SOL / 'web_trim_removed-world.stl')
    added_final = m3.Manifold.batch_boolean([b for b in d1.decompose() if b.volume() > 1e-3], m3.OpType.Add)
    tm_from_man(added_final).export(L.SOL / 'cap_added_vs_V18-world.stl')
    res['outputs'] = {'cap': {'path': L.INTEGRATED_CAP, 'sha256': L.sha(L.INTEGRATED_CAP)},
                      'webTrimRemoved': L.SOL / 'web_trim_removed-world.stl',
                      'capAddedVsV18': L.SOL / 'cap_added_vs_V18-world.stl'}

    # ---- beam numbers, same method as the pi-mount study
    A_tm = trimesh.load(L.PIM / 'study-solids' / 'A-head_cap-world.stl', force='mesh')
    res['strength'] = {'method': 'pi-mount/scripts/check_options.py rail_strength (along the rail, |y| 25..33.5, '
                                 'MPa per N at the lower screw) and web_path (section y = +-33, arm 4 mm)',
                       'A_untrimmed': {'rail': rail_strength(A_tm, 'A'), 'web': web_path(A_tm)},
                       'integrated': {'rail': rail_strength(chk, 'int'), 'web': web_path(chk)}}
    r0 = res['strength']['A_untrimmed']['rail']['plus_y']['worstPush']['mpaPerN_u']
    r1 = res['strength']['integrated']['rail']['plus_y']['worstPush']['mpaPerN_u']
    w0 = res['strength']['A_untrimmed']['web']['plus_y']['mpaPerN']
    w1 = res['strength']['integrated']['web']['plus_y']['mpaPerN']
    res['strength']['plusYChange'] = {'railWorstPushMpaPerN': [r0, r1], 'railPercent': 100 * (r1 / r0 - 1),
                                      'webPathMpaPerN': [w0, w1], 'webPercent': 100 * (w1 / w0 - 1)}
    L.jdump(L.rnd(res, 4), L.STUDY / 'cap-build.json')
    print(json.dumps(L.rnd(res, 3), indent=1, default=str)[:6000])


if __name__ == '__main__':
    main()
