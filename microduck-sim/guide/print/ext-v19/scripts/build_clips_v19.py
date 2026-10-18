#!/usr/bin/env python3
"""Build the four V1.9 bundle clips (release solids, robot frame at q = 0) and their screw records.

Shapes: clips_v19.py (torso and bracket: channel on the joint axis between the four horn screws; head and cap clips:
see their functions there). Every clip is trimmed against the static parts of its own body that stand above its seat
plane: those parts, cropped to the clip's neighbourhood and to n > 0.05 mm above the seat, are grown in the seat plane
by CLEAR (8 in-plane offsets plus the part itself) and subtracted, so the clip keeps >= ~0.3 mm from them and its
mounting face stays whole; then each same-body part that still overlaps the tab near the seat plane is subtracted
as it is, so the tab bottom follows the host face (no seat overlap). The clip's own screw head (lifted by the tab) and
the neighbouring screw heads get the same clearance, the neighbours through the whole tab thickness. Writes ../clip_*_v19-world.stl, ../checks/clips-build-v19.json.
Usage: build_clips_v19.py [torso bracket head cap]
"""
from __future__ import annotations

import json
import sys

import manifold3d as m3
import numpy as np

import clips_v19 as C
import ext_lib as E
import meshcheck as MC
from nr_lib import body_of


MIN_TRIM = 0.01        # mm3; smaller trims are skipped (see trim_static)


def trim_static(clip, rec, body, extra_keys=(), skip=()):
    """Subtract same-body static parts above the seat plane, grown in-plane by C.CLEAR."""
    c, n = np.asarray(rec['seat']), np.asarray(rec['n'])
    u, v, _ = E.frame(n)
    bb = E.bbox(clip)
    box = m3.Manifold.cube((bb[1] - bb[0] + 2.0).tolist()).translate((bb[0] - 1.0).tolist())
    # half-space n > 0.05 above the seat plane, as a large box in the seat frame
    T = np.eye(4)
    T[:3, 0], T[:3, 1], T[:3, 2], T[:3, 3] = u, v, n, c
    half = m3.Manifold.cube([400, 400, 400]).translate([-200, -200, 0.05]).transform(T[:3, :])
    man = E.ia_lib.manifest()
    keys = [k for k, m in man.items() if (body_of(k) or 'trunk_base') == body and k not in skip and
            np.all(np.array(m['bounds'])[0] <= bb[1] + 1) and np.all(np.array(m['bounds'])[1] >= bb[0] - 1)]
    keys += list(extra_keys)
    cut, used, skipped = [], {}, {}
    for k in keys:
        M = E.stl_man(E.PARTS['head_cap_v19']) if k == 'head_cap' else E.load_man(k)
        L = M ^ box ^ half
        if L.volume() < 1e-6:
            continue
        offs = [L] + [L.translate((C.CLEAR * (np.cos(a) * u + np.sin(a) * v)).tolist()) for a in np.radians(np.arange(0, 360, 45))]
        G = m3.Manifold.batch_boolean(offs, m3.OpType.Add)
        before = clip.volume()
        trimmed = clip - G
        removed = before - trimmed.volume()
        if 1e-6 < removed < MIN_TRIM:
            # a corner grazing the grown envelope: cutting it would leave sub-0.1 mm slivers (not printable, and
            # they fail the mesh check); keep the clip and record its true gap to the ungrown part instead
            skipped[k] = {'removedWouldBeMm3': round(removed, 4), 'gapToPartMm': round(float(clip.min_gap(L, 1.0)), 3)}
            continue
        clip = trimmed
        used[k] = round(removed, 4)
    rec['trimmedAgainst'] = used
    rec['tinyTrimsSkipped'] = skipped
    # seat pass: the grown trim above leaves the seat slab (n <= 0.05) untouched, so a host face that stands a few
    # hundredths above the nominal seat plane (E-pi-04 seats 0.04 mm inside the Pi) or a shell face that rises inside
    # the tab footprint still overlaps the tab. Subtract each same-body part itself (ungrown) where it overlaps: the tab's
    # bottom then follows the host surface.
    conform = {}
    for k in keys:
        M = E.stl_man(E.PARTS['head_cap_v19']) if k == 'head_cap' else E.load_man(k)
        ov = (clip ^ M).volume()
        if ov > 1e-4:
            I = clip ^ M
            clip = clip - M
            conform[k] = {'overlapRemovedMm3': round(ov, 4), 'at': E.rnd(E.bbox(I), 3),
                          'depthAlongNMm': E.rnd([float(((np.asarray(I.to_mesh().vert_properties)[:, :3] - c) @ n).min()),
                                                  float(((np.asarray(I.to_mesh().vert_properties)[:, :3] - c) @ n).max())], 3)}
    rec['seatConformedAgainst'] = conform
    return clip


def screw_keepout(rec, screw_ids, own=None):
    """Heads of neighbouring screws (+CLEAR) and the clip's own lifted head (+CLEAR)."""
    F = E.fasteners()
    ko = []
    for sid in screw_ids:
        r = F[sid]
        cc = np.array(r['center'], float)
        ax = np.array(r['axis'], float)
        ax /= np.linalg.norm(ax)
        hd = max(r['headDiameterMm'], 4.0 if r['diameterMm'] == 2.0 else 5.0)
        hh = max(r['headHeightMm'], 1.6 if r['diameterMm'] == 2.0 else 1.75)
        if sid == own:
            # own head, lifted by the tab: everything from the tab top outwards stays clear
            ko.append(E.cyl(cc - (C.TAB_T + 0.02) * ax, -ax, hh + 20.0, hd / 2 + C.CLEAR, 64))
        else:
            # a neighbouring head sits on the host face: clear it through the whole tab, from 0.3 mm below the seat
            # plane to the head top + CLEAR (no film under or over the head)
            ko.append(E.cyl(cc + 0.3 * ax, -ax, 0.3 + hh + C.CLEAR, hd / 2 + C.CLEAR, 64))
    return m3.Manifold.batch_boolean(ko, m3.OpType.Add)


def build(which):
    out = {}
    if 'torso' in which:
        # raised channel, x 22.6..27.6: the group passes over the lifted S12-horn-025 head and enters along +x
        clip, rec = C.horn_clip('S12-horn-025', axis_point=[C.TORSO_X0 + C.TORSO_L / 2, -18.401, C.TORSO_ZC],
                                channel_dir=[1, 0, 0], raised=True, length=C.TORSO_L, channel_kw=C.HORN_CH)
        clip = clip - screw_keepout(rec, ['S12-horn-026', 'S12-horn-027', 'S12-horn-028', 'S12-horn-025'], own='S12-horn-025')
        clip = trim_static(clip, rec, 'trunk_base')
        out['clip_torso_v19'] = (clip, rec)
    if 'bracket' in which:
        clip, rec = C.horn_clip('S11-horn-040', axis_point=[26.0, -17.5, 82.421], channel_dir=[0, 0, 1],
                                channel_kw=C.HORN_CH)
        clip = clip - screw_keepout(rec, ['S11-horn-037', 'S11-horn-038', 'S11-horn-039', 'S11-horn-040'], own='S11-horn-040')
        clip = trim_static(clip, rec, 'neck_pitch')
        out['clip_bracket_v19'] = (clip, rec)
    if 'head' in which and hasattr(C, 'head_clip'):
        clip, rec = C.head_clip()
        clip = clip - screw_keepout(rec, rec.get('neighbourScrews', []) + ['H-jaw_support-03'], own='H-jaw_support-03')
        clip = trim_static(clip, rec, 'jaw_soft', skip=('head_cap', 'pi') + tuple(k for k in E.ia_lib.manifest() if k.startswith('head_pi_')))
        out['clip_head_v19'] = (clip, rec)
    if 'cap' in which and hasattr(C, 'cap_clip'):
        clip, rec = C.cap_clip()
        clip = clip - screw_keepout(rec, ['E-pi-04'], own='E-pi-04')
        clip = trim_static(clip, rec, 'jaw_soft')
        rec['hdmiEnvelopeGapMm'] = float(clip.min_gap(C.hdmi_envelope(), 2.0))
        out['clip_cap_v19'] = (clip, rec)
    res = {}
    for nm, (clip, rec) in out.items():
        bodies = sorted(clip.decompose(), key=lambda b: -b.volume())
        rec['bodiesBeforeCleanup'] = len(bodies)
        rec['droppedMm3'] = float(sum(b.volume() for b in bodies[1:]))
        clip = bodies[0]
        v0 = clip.volume()
        clip = clip.simplify(1e-4)            # drop collinear slivers left by the booleans (they pinch after STL merge)
        rec['simplifyVolumeChangeMm3'] = clip.volume() - v0
        p = E.PARTS[nm]
        E.tm(clip).export(p)
        chk, _ = MC.check(p)
        rec.update({'path': p, 'sha256': E.sha(p), 'volumeMm3': clip.volume(), 'bounds': E.bbox(clip),
                    'meshCheck': {k: chk[k] for k in ('clean', 'watertight', 'bodies', 'edgesSharedByMoreThanTwoFaces',
                                                       'boundaryEdges', 'coincidentFaceGroupsByGeometry',
                                                       'needleFacesInradiusBelow1e-4', 'volumeMm3')}
                    | {'separationDefects': chk['faceSeparationTest']['defectFacesFailingAllEps']}})
        res[nm] = E.rnd(rec, 4)
        print(nm, json.dumps(res[nm], default=str)[:1500], flush=True)
    path = E.OUT / 'checks' / 'clips-build-v19.json'
    old = json.loads(path.read_text()) if path.exists() else {}
    old.update(res)
    E.jdump(old, path)


if __name__ == '__main__':
    build(sys.argv[1:] or ['torso', 'bracket', 'head', 'cap'])
