#!/usr/bin/env python3
"""Check that the V1.9 release solids and the audio study solids sit in the same frame as the V1.8 head parts the 3D page draws.

Read-only. Loads the V1.8 parts from guide/data/guide-data.json (the meshes HEAD-3D.html draws; head_bottom falls back
to print/world/head_bottom.stl because the guide copy is decimated and not closed), the V1.9 release solids from
guide/print/ext-v19/ (sha256-checked against manifest-ext-v19.json) and the audio study solids, then measures:

  frame     V1.8 cap vs V1.9 cap: added / removed volume, compared with integrated/cap-build.json (the release cap is
            the study cap with its mesh repaired, so the record still applies)
  inside    amp, speaker, V1.9 retainer, amp housings and the resistor envelope: overlap with the V1.9 cap, smallest
            gap to it, and whether all their vertices lie inside the cap's convex hull
  grille    rays from a grid on the speaker face along its front normal: how many escape through the V1.9 cap
            (grille holes) and through the V1.8 cap (no grille, so none should)
  seats     Pi on the reinforced rails, amp and retainer screws in the cap posts, audio Pi-end housings over their
            header pins, cap on head_bottom, retainer over the speaker, resistor envelope under the amp board
  clipSeats the four V1.9 clips on their seat parts: torso clip on shell_right, bracket clip on neck_pitch, head clip
            on jaw_support, cap clip on the Pi
  resistor  the fitted gain resistor as build_head3d.py draws it (body, heat-shrink sleeve, U-bent leads, solder
            joints at the U4 placement of resistor-placement.json) against the V1.9 cap, the Pi, the amplifier, the
            amp-end header housings and the Pi-end housings
  wires     tubes swept along route-v19.json (bundle in the head at r 1.7, fan wires at r 0.65) against the V1.8 head
            parts, the V1.9 cap and the V1.9 clips at rest (jaw closed, roll 0)

Writes alignment.json next to this file. Run: /tmp/microduck-cad-venv/bin/python check_alignment.py
"""
from __future__ import annotations

import base64
import hashlib
import json
import sys
from pathlib import Path

import manifold3d as m3
import numpy as np
import trimesh

HERE = Path(__file__).resolve().parent
EXT = HERE.parent
GUIDE = EXT.parent
AUD = EXT / 'audio' / 'study-solids'
V19 = GUIDE / 'print' / 'ext-v19'
sys.path.insert(0, str(HERE))
from build_head3d import RES_REC, resistor_parts  # noqa: E402  (the page's own resistor geometry)


def guide_parts() -> dict:
    data = json.loads((GUIDE / 'data' / 'guide-data.json').read_text())
    return {p['key']: p for p in data['parts']}


GP = guide_parts()
MANIFEST_SHA = {p['key']: p['sha256'] for p in json.loads((V19 / 'manifest-ext-v19.json').read_text())['parts']}
MANIFEST_SHA['resistor_envelope_v19'] = json.loads((V19 / 'resistor-placement.json').read_text())['envelopeStl']['sha256']
SHAS: dict = {}


def gd(key: str) -> trimesh.Trimesh:
    p = GP[key]
    v = np.frombuffer(base64.b64decode(p['positionB64']), '<f4').reshape(-1, 3).astype(np.float64)
    f = np.frombuffer(base64.b64decode(p['indexB64']), '<u4').reshape(-1, 3).astype(np.int64)
    return trimesh.Trimesh(v, f, process=True)


def stl(path: Path) -> trimesh.Trimesh:
    m = trimesh.load(path, force='mesh')
    m.merge_vertices()
    return m


def v19(key: str) -> trimesh.Trimesh:
    path = V19 / f'{key}-world.stl'
    sha = hashlib.sha256(path.read_bytes()).hexdigest()
    SHAS[key] = {'sha256': sha, 'manifestSha256': MANIFEST_SHA.get(key), 'matches': sha == MANIFEST_SHA.get(key)}
    if not SHAS[key]['matches']:
        raise SystemExit(f'{key}: file sha {sha[:12]} does not match the manifest ({str(MANIFEST_SHA.get(key))[:12]})')
    return stl(path)


def man(tm: trimesh.Trimesh):
    mesh = m3.Mesh(vert_properties=np.ascontiguousarray(tm.vertices, np.float32),
                   tri_verts=np.ascontiguousarray(tm.faces, np.uint32))
    M = m3.Manifold(mesh)
    return M if M.status() == m3.Error.NoError and not M.is_empty() else None


def pair(a_name, A, b_name, B, search=5.0) -> dict:
    ma, mb = man(A), man(B)
    rec = {'a': a_name, 'b': b_name}
    if ma is None or mb is None:
        rec['note'] = 'not a closed manifold: ' + ', '.join(n for n, m in ((a_name, ma), (b_name, mb)) if m is None)
        d = trimesh.proximity.closest_point(B, A.vertices[:: max(1, len(A.vertices) // 4000)])[1]
        rec['minVertexDistanceMm'] = round(float(d.min()), 3)
        return rec
    rec['overlapMm3'] = round((ma ^ mb).volume(), 4)
    rec['minGapMm'] = round(float(ma.min_gap(mb, search)), 3)
    return rec


def tube(points: list, r: float, step: float = 0.6) -> trimesh.Trimesh:
    """Closed tube along a polyline: a sphere every `step` mm along the segments, unioned with manifold3d. Used only
    for the gap/overlap measurement; the page itself draws a Catmull-Rom tube through the same points."""
    P = np.asarray([p[:3] for p in points], float)
    balls = []
    for a, b in zip(P[:-1], P[1:]):
        L = float(np.linalg.norm(b - a))
        for t in np.linspace(0.0, 1.0, max(2, int(np.ceil(L / step)) + 1)):
            balls.append(m3.Manifold.sphere(r, 20).translate(list(a + t * (b - a))))
    M = m3.Manifold.batch_boolean(balls, m3.OpType.Add)
    mm = M.to_mesh()
    return trimesh.Trimesh(np.asarray(mm.vert_properties)[:, :3], np.asarray(mm.tri_verts), process=False)


def main() -> None:
    out: dict = {'_doc': __doc__.split('\n\n')[0], 'checks': {}}
    C = out['checks']

    cap18 = gd('head_cap')
    capI = v19('head_cap_v19')
    m18, mI = man(cap18), man(capI)
    build = json.loads((EXT / 'integrated' / 'cap-build.json').read_text())['xorVsV18']
    C['frame'] = {
        'v18CapFrom': 'guide-data.json head_cap',
        'v19CapFrom': 'guide/print/ext-v19/head_cap_v19-world.stl',
        'addedMm3': round((mI - m18).volume(), 3),
        'removedMm3': round((m18 - mI).volume(), 3),
        'recordedAddedMm3': build['addedVsV18Mm3'],
        'recordedRemovedMm3': build['removedVsV18Mm3'],
    }
    C['frame']['matchesRecord'] = (abs(C['frame']['addedMm3'] - build['addedVsV18Mm3']) < 0.5
                                   and abs(C['frame']['removedMm3'] - build['removedVsV18Mm3']) < 0.5)

    retainer = v19('speaker_retainer_v19')
    resistor = v19('resistor_envelope_v19')
    amp = stl(AUD / 'amplifier-world.stl')
    speaker = stl(AUD / 'speaker-world.stl')
    hull = capI.convex_hull
    inside = {}
    for name, tm in (('amplifier', amp), ('speaker', speaker), ('speaker_retainer_v19', retainer),
                     ('amp_housings', stl(AUD / 'amp_housings-world.stl')), ('resistor_envelope_v19', resistor)):
        rec = pair(name, tm, 'head_cap_v19', capI)
        rec['allVerticesInsideCapHull'] = bool(hull.contains(tm.vertices).all())
        inside[name] = rec
    C['insideCap'] = inside

    # Speaker behind its opening: rays from a grid on the speaker front face along its front normal. A ray that leaves
    # the cap without hitting it passed through a grille hole; the V1.8 cap (no grille) must block every ray.
    frame = json.loads((EXT / 'audio' / 'study-build.json').read_text())['speakerFrame']
    c0, u, v, n = (np.array(frame[k]) for k in ('originFrontFaceCentre', 'u_long', 'v_short', 'n_front'))
    gu, gv = np.meshgrid(np.linspace(-14.0, 14.0, 57), np.linspace(-9.0, 9.0, 37))
    origins = c0 + gu.reshape(-1, 1) * u + gv.reshape(-1, 1) * v + 0.05 * n
    dirs = np.repeat(n[None, :], len(origins), axis=0)

    def escaped(mesh):
        hit = trimesh.ray.ray_triangle.RayMeshIntersector(mesh).intersects_any(origins, dirs)
        return int((~hit).sum())

    C['grilleOverSpeaker'] = {'raysFromSpeakerFace': len(origins), 'escapeIntegratedCap': escaped(capI), 'escapeV18Cap': escaped(cap18),
                              'note': 'rays along the speaker front normal; escaping rays pass through grille holes (escapeIntegratedCap = V1.9 cap)'}

    pi = gd('pi')
    hb = stl(GUIDE / 'print' / 'world' / 'head_bottom.stl')
    js = gd('jaw_support')
    seats = {
        'pi_on_rails': pair('pi', pi, 'head_cap_v19', capI),
        'amp_screws_in_posts': pair('amp_screws_envelope', stl(AUD / 'amp_screws_envelope-world.stl'), 'head_cap_v19', capI),
        'speaker_screws_in_bosses': pair('speaker_screws_envelope', stl(AUD / 'speaker_screws_envelope-world.stl'), 'head_cap_v19', capI),
        'retainer_over_speaker': pair('speaker_retainer_v19', retainer, 'speaker', speaker),
        'resistor_under_amp': pair('resistor_envelope_v19', resistor, 'amplifier', amp),
        'cap_on_head_bottom': pair('head_cap_v19', capI, 'head_bottom (print/world)', hb),
    }
    for pin in (4, 12, 35, 40):
        seats[f'housing_pin{pin:02d}_over_header_pin'] = pair(
            f'pi_housing_pin{pin:02d}', stl(AUD / f'pi_housing_pin{pin:02d}-world.stl'),
            f'head_pi_zero_w_header_pin_{pin:02d}', gd(f'head_pi_zero_w_header_pin_{pin:02d}'))
    C['seats'] = seats

    # The fitted resistor as the page draws it. Legs and joints touch the amp model by design: they hook and are soldered
    # to its header tails, which the study model draws 1.5 mm below the board.
    rp = resistor_parts()
    housings = {'amp_housings': stl(AUD / 'amp_housings-world.stl')}
    for f in sorted(AUD.glob('pi_housing_pin*-world.stl')):
        housings[f.name.replace('-world.stl', '')] = stl(f)
    against = {'head_cap_v19': capI, 'pi': pi, 'amplifier': amp, **housings}
    res = {'placement': 'resistor-placement.json candidates.U4_detail', 'bodyCentre': RES_REC['bodyCentre']}
    for part in ('body', 'sleeve', 'legs', 'joints'):
        res[part] = {k: pair(f'resistor_{part}', rp[part], k, M, search=10.0) for k, M in against.items()}
    # The study amp model carries a 1.5 mm slab under the whole board (its through-hole tail allowance, build_study.py
    # `under`), so every underside part overlaps it; the board underside is the slab's top face.
    zs = np.unique(np.round(amp.vertices[:, 2], 3))
    board_under = float(zs[1])
    res['boardUndersideZ'] = board_under
    res['amplifierOverlapNote'] = ('the amplifier model has a 1.5 mm tail-allowance slab under the whole board (z '
                                   f'{zs[0]:.2f} to {board_under:.2f}); overlaps with it are expected, use the gaps to the board underside')
    res['bodyToBoardUndersideMm'] = round(board_under - float(rp['body'].bounds[1][2]), 3)
    res['sleeveToBoardUndersideMm'] = round(board_under - float(rp['sleeve'].bounds[1][2]), 3)
    # Neighbouring header tails (not in the amp model): 0.64 mm square posts, 1.5 mm below the board, on the row at the
    # GAIN hook-centre x. Pin order from -y: LRC, BCLK, DIN, GAIN, SD, GND, Vin; GAIN at y 0.
    row_x = RES_REC['legs']['GAIN']['hookCentre'][0]
    tails = {}
    for i, nm in enumerate(['LRC', 'BCLK', 'DIN', 'GAIN', 'SD', 'GND', 'Vin']):
        if nm in ('GAIN', 'Vin'):
            continue
        y = (i - 3) * 2.54
        tails[f'tail_{nm}'] = trimesh.creation.box(bounds=[[row_x - 0.32, y - 0.32, board_under - 1.5], [row_x + 0.32, y + 0.32, board_under]])
    res['neighbourTails'] = {part: {k: pair(f'resistor_{part}', rp[part], k, M, search=10.0) for k, M in tails.items()}
                             for part in ('sleeve', 'legs', 'joints')}
    C['resistorPart'] = res

    clips = {
        'clip_torso_v19': ('躯干卡扣', 'shell_right', gd('shell_right')),
        'clip_bracket_v19': ('支架卡扣', 'neck_pitch', gd('neck_pitch')),
        'clip_head_v19': ('头部卡扣', 'jaw_support', js),
        'clip_cap_v19': ('头盖卡扣', 'pi', pi),
    }
    clip_meshes = {}
    cs = {}
    for key, (label, seat_name, seat) in clips.items():
        clip_meshes[key] = v19(key)
        rec = pair(key, clip_meshes[key], seat_name, seat)
        rec['label'] = label
        cs[key] = rec
    C['clipSeats'] = cs

    route = json.loads((V19 / 'route-v19.json').read_text())
    pts = [p[:3] for p in route['routes'][0]['points']]
    r_group = route['routes'][0]['groupRadiusMm']
    wires = {}
    v18_keys = ['jaw_support', 'jaw_frame', 'motor15', 'motor13', 'motor14', 'head_yaw_link', 'pi', 'camera_board', 'face_panel']
    others = {k: gd(k) for k in v18_keys}
    others['head_bottom (print/world)'] = hb
    others['head_cap_v19'] = capI
    others['amplifier'] = amp
    others['amp_housings'] = stl(AUD / 'amp_housings-world.stl')
    others['resistor_envelope_v19'] = resistor
    for key, m in clip_meshes.items():
        others[key] = m
    segments = {
        'bundle_slot_to_head_clip (pts 9-16)': tube(pts[9:17], r_group),
        'bundle_head_clip_to_cap_clip (pts 16-24)': tube(pts[16:25], r_group),
        'bundle_cap_clip_to_gather (pts 24-32)': tube(pts[24:33], r_group),
    }
    fan = route['fanWires']
    for pin, poly in sorted(fan['polylines'].items(), key=lambda kv: int(kv[0])):
        segments[f'fan_pin{int(pin):02d}'] = tube(poly, fan['radiusMm'], step=0.4)
    for name, W in segments.items():
        rows = [pair(name, W, k, M, search=3.0) for k, M in others.items()]
        wires[name] = sorted(rows, key=lambda r: r.get('minGapMm', r.get('minVertexDistanceMm', 99)))[:4]
    C['wiresAtRest'] = wires
    C['wiresAtRest']['_note'] = ('tubes are spheres every 0.6 mm (fan 0.4 mm) along the polyline, so a clip channel that holds the bundle '
                                 'shows a small overlap where the tube touches the channel walls; the ext-v19 cable check is the authority')
    out['v19Sources'] = SHAS

    (HERE / 'alignment.json').write_text(json.dumps(out, indent=1, ensure_ascii=False) + '\n')
    print(json.dumps(out, indent=1, ensure_ascii=False))


if __name__ == '__main__':
    main()
