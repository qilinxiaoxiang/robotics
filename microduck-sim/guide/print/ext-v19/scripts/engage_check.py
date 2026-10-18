#!/usr/bin/env python3
"""Screw stacks at the four clip screws with the V1.9 clip tab and the longer screw (ray cast on the release meshes).

For each screw: the head seat moves out by the tab thickness (2.0 mm) and the screw becomes 2 mm longer, so the tip
stays where fasteners.json has it. Rays parallel to the screw axis (on the axis, and on rings at r = 0.75 (core),
r = 1.0 / 1.25 (M2 / M2.5 thread crest) at 12 angles) are cast through the clip, the through-part(s), the receiving
part and every other part within 12 mm (the release head cap replaces the cached V1.8 cap). Per part: material
intervals along the axis from the new seat. Reported per screw:
  shank in the receiving part = length of the screw (from the new seat to the tip) over which the receiving part has
  material at the thread-crest ring (all angles) and none on the axis (pilot open); engagement = that minus the 0.3 mm
  tip lead-in (fasteners.json convention); tip margin = first material on the axis or on a r = 0.5 ring (inside any pilot) past the tip (any part).
Also measured: the four new audio screws (speaker retainer 2 x M2 x 6 into the cap collar bosses, amplifier 2 x M2 x 6
into the cap posts), seats and axes taken from the audio study's screw envelopes (proposed ids H-speaker_retainer-0x,
H-amplifier-0x), against the release cap and retainer and the study amplifier.
Also re-measured, unchanged: the other cap screws (E-pi-01..03, K-head_close-01..03) against the release cap, with the
fasteners.json engagement for comparison.
Writes ../checks/screw-engagement-v19.json.
"""
from __future__ import annotations

import json

import numpy as np
import trimesh

import ext_lib as E

TAB = 2.0
# screw id -> (clip key or None, new length, seat shift = clip tab thickness)
SCREWS = {'S12-horn-025': ('clip_torso_v19', 8.0, TAB), 'S11-horn-040': ('clip_bracket_v19', 8.0, TAB),
          'E-pi-04': ('clip_cap_v19', 8.0, TAB), 'H-jaw_support-03': ('clip_head_v19', 8.0, TAB),
          'H-speaker_retainer-01': (None, 6.0, 0.0), 'H-speaker_retainer-02': (None, 6.0, 0.0),
          'H-amplifier-01': (None, 6.0, 0.0), 'H-amplifier-02': (None, 6.0, 0.0),
          # unchanged screws into the cap: the release cap must give them the V1.8 engagement
          'E-pi-01': (None, 6.0, 0.0), 'E-pi-02': (None, 4.0, 0.0), 'E-pi-03': (None, 6.0, 0.0),
          'K-head_close-01': (None, 8.0, 0.0), 'K-head_close-02': (None, 8.0, 0.0), 'K-head_close-03': (None, 8.0, 0.0)}
LEAD_IN = 0.3
EXTRA_MESHES = {'speaker_retainer_v19': E.PARTS['speaker_retainer_v19'],
                'amplifier': E.AUDIO / 'study-solids' / 'amplifier-world.stl',
                'speaker': E.AUDIO / 'study-solids' / 'speaker-world.stl'}


def audio_screws():
    """New V1.9 screw records (proposed ids) from the audio study's screw envelopes: each body is a 4.0 x 1.5 head
    plus a 2.0 x 6.0 shank; the seat is the head/shank plane, the axis points from the head into the shank."""
    out = {}
    for env, through, ids in (('speaker_screws_envelope', 'speaker_retainer_v19', ('H-speaker_retainer-01', 'H-speaker_retainer-02')),
                              ('amp_screws_envelope', 'amplifier', ('H-amplifier-01', 'H-amplifier-02'))):
        M = E.stl_man(E.AUDIO / 'study-solids' / f'{env}-world.stl')
        bodies = sorted(M.decompose(), key=lambda b: E.bbox(b)[0][1])
        for sid, b in zip(ids, bodies):
            V = np.asarray(b.to_mesh().vert_properties)[:, :3]
            c0 = V.mean(0)
            _, _, vt = np.linalg.svd(V - c0)
            a = vt[0]
            pr = (V - c0) @ a
            rad = np.linalg.norm((V - c0) - np.outer(pr, a), axis=1)
            head = rad > 1.5
            if pr[head].mean() > pr[~head].mean():
                a, pr = -a, -pr
            seat = c0 + a * pr[head].max()
            out[sid] = {'id': sid, 'spec': 'M2 x 6 TAP', 'kind': 'TAP', 'diameterMm': 2.0, 'lengthMm': 6.0,
                        'headDiameterMm': 4.0, 'headHeightMm': 1.5, 'center': seat.round(3).tolist(),
                        'axis': a.round(6).tolist(), 'throughPart': through, 'intoPart': 'head_cap',
                        'shankLengthFromEnvelopeMm': round(float(pr.max() - pr[head].max()), 3)}
    return out


def intervals(mesh, origin, d, length):
    locs, idx_ray, _ = mesh.ray.intersects_location([origin], [d], multiple_hits=True)
    locs = np.asarray(locs, float).reshape(-1, 3)
    t = np.sort(np.unique(np.round((locs - origin) @ d, 6)))
    t = t[(t >= 0) & (t <= length)]
    inside0 = bool(mesh.contains([origin])[0])
    edges = ([0.0] if inside0 else []) + t.tolist()
    if len(edges) % 2:
        edges.append(length)
    return [(edges[i], edges[i + 1]) for i in range(0, len(edges), 2)]


def covered(ivs, a, b, step=0.05):
    s = np.arange(a + step / 2, b, step)
    m = np.zeros(len(s), bool)
    for lo, hi in ivs:
        m |= (s >= lo) & (s <= hi)
    return s, m


def main():
    F = E.fasteners()
    F.update(audio_screws())
    man = E.ia_lib.manifest()
    out = {}
    for sid, (clip_key, L, tab) in SCREWS.items():
        r = F[sid]
        c = np.array(r['center'], float)
        ax = np.array(r['axis'], float)
        ax /= np.linalg.norm(ax)
        seat = c - tab * ax
        tip = L
        u, v, _ = E.frame(ax)
        crest = r['diameterMm'] / 2
        keys = [k for k, m in man.items() if k != 'head_cap' and
                np.linalg.norm(np.maximum(0, np.maximum(np.array(m['bounds'])[0] - c, c - np.array(m['bounds'])[1]))) < 12]
        meshes = {k: trimesh.Trimesh(*E.ia_lib.load_solid(k), process=False) for k in keys}
        capp = E.PARTS['head_cap_v19']
        meshes['head_cap_v19'] = trimesh.load(capp, force='mesh')
        if clip_key and E.PARTS[clip_key].exists():
            meshes[clip_key] = trimesh.load(E.PARTS[clip_key], force='mesh')
        for k, pth in EXTRA_MESHES.items():
            mm = trimesh.load(pth, force='mesh')
            lo, hi = mm.bounds
            if np.linalg.norm(np.maximum(0, np.maximum(lo - c, c - hi))) < 12:
                meshes[k] = mm
        rings = {'axis': [np.zeros(3)]}
        for rr in (0.5, 0.75, crest):
            rings[f'r{rr}'] = [rr * (np.cos(a) * u + np.sin(a) * v) for a in np.radians(np.arange(0, 360, 30))]
        span = tip + 10.0
        stack = {}
        for k, M in meshes.items():
            per = {}
            for nm, offs in rings.items():
                per[nm] = [intervals(M, seat + o - 0.5 * ax, ax, span + 0.5) for o in offs]
                per[nm] = [[(lo - 0.5, hi - 0.5) for lo, hi in iv] for iv in per[nm]]
            if any(iv for lst in per.values() for iv in lst):
                stack[k] = per
        into = r['intoPart']
        into_key = 'head_cap_v19' if into == 'head_cap' else into
        rec = {'spec': f"M{r['diameterMm']:g} x {L:g} TAP", 'oldSpec': r['spec'] if clip_key else None, 'newSeat': seat,
               'axis': ax, 'tipFromNewSeatMm': tip, 'intoPart': into_key, 'throughPart': r.get('throughPart'),
               'clip': clip_key, 'fastenersJsonEngagementMm': r.get('engagementMm'),
               'fastenersJsonTipMarginMm': r.get('tipMarginMm'), 'parts': {}}
        for k, per in stack.items():
            ax_iv = per['axis'][0]
            ring = per[f'r{crest}']
            core = per['r0.75']
            rec['parts'][k] = {'axisIntervals': [(round(a, 2), round(b, 2)) for a, b in ax_iv],
                               'crestRingUnion': [(round(min(a for iv in ring for a, _ in iv), 2) if any(ring) else None)]}
        # engagement in the receiving part
        s, m_axis = covered(stack.get(into_key, {}).get('axis', [[]])[0], 0, tip)
        crest_all = np.ones(len(s), bool)
        for iv in stack.get(into_key, {}).get(f'r{crest}', []):
            crest_all &= covered(iv, 0, tip)[1]
        shank = float(((crest_all) & (~m_axis)).sum() * 0.05)
        rec['shankInReceivingPartMm'] = shank
        rec['engagementMm'] = shank - LEAD_IN
        rec['bottoming'] = bool(m_axis.any())
        # tip margin: first material on the axis or the r = 0.5 ring past the tip (inside the pilot), any part
        first = np.inf
        who = None
        for k, per in stack.items():
            for iv in per['axis'] + per['r0.5']:
                for lo, hi in iv:
                    if hi > tip and lo < span:
                        st = max(lo, tip)
                        if st - tip < first:
                            first, who = st - tip, k
        rec['tipMarginMm'] = None if not np.isfinite(first) else first
        rec['tipMarginPart'] = who
        # through-stack: what the shank passes before the receiving part (axis-adjacent crest ring)
        rec['clipTabOnAxisRing'] = None
        if clip_key and clip_key in stack:
            iv = stack[clip_key][f'r{crest}']
            rec['clipTabOnCrestRing'] = [[(round(a, 2), round(b, 2)) for a, b in x] for x in iv[:3]]
            ivh = stack[clip_key]['axis'][0]
            rec['clipOnAxis'] = ivh
        out[sid] = E.rnd(rec, 3)
        print(sid, json.dumps({k: out[sid][k] for k in ('spec', 'shankInReceivingPartMm', 'engagementMm', 'bottoming',
                                                       'tipMarginMm', 'tipMarginPart', 'fastenersJsonEngagementMm')}), flush=True)
        print('   parts', {k: v['axisIntervals'] for k, v in out[sid]['parts'].items()}, flush=True)
    E.jdump(out, E.OUT / 'checks' / 'screw-engagement-v19.json')


if __name__ == '__main__':
    main()
