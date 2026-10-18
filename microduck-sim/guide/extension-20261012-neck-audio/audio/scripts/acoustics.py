#!/usr/bin/env python3
"""Acoustic estimates for the roof grille (measured geometry, INFERENCE for every acoustic number).

Measured on the study solids: front-chamber air volume between the speaker front face and the roof inside the chamber
outline; roof thickness along every grille hole axis; head air volume behind the speaker.
Inferred: the grille plus front chamber act as a Helmholtz resonator f = c / (2 pi) * sqrt(S / (V * L')), S = total hole
area, L' = t + 1.7 r (end corrections, both ends flanged). Keep f above the speaker's 10 kHz upper band edge so the
grille does not colour speech. Writes ../acoustics.json.
"""
from __future__ import annotations

import json

import manifold3d as m3
import numpy as np
import trimesh

from build_study import FOAM_COMPRESSED, FRONT_GAP, LIP_W, SPK_L, SPK_W, extrude, frame_T, apply, stadium
from check_lib import FIXED, YAW, Head, man_from_tm, tm_from_man
from scene import STUDY

C_AIR = 343.0e3   # mm/s at about 20 C


def main():
    b = json.loads((STUDY / 'study-build.json').read_text())
    f, g = b['speakerFrame'], b['grille']
    c0, u, v, n = (np.array(f[k]) for k in ('originFrontFaceCentre', 'u_long', 'v_short', 'n_front'))
    T = frame_T(c0, u, v, n)
    H = Head()
    v18 = H.get('head_cap')
    cap_ext = man_from_tm(trimesh.load(STUDY / 'study-solids/head_cap_extension-world.stl', force='mesh'))
    interior = sorted((m3.Manifold.batch_hull([v18]) - v18).decompose(), key=lambda m: -m.volume())[0]
    # front chamber: speaker front face (n = 0) up to the filler plate (n = 0.6 + FRONT_GAP), inside the lip; the air
    # inside the grille holes is the resonator neck, not chamber volume
    chamber = (apply(extrude(stadium(SPK_L, SPK_W, -LIP_W), 0.0, FOAM_COMPRESSED + FRONT_GAP), T) ^ interior) - cap_ext
    V = chamber.volume()
    # roof thickness along each hole axis: from the first cap_ext hit to the exit, ray from the landing plane
    tm = tm_from_man(cap_ext)
    t = []
    for a, bb in g['centresUV']:
        o = c0 + a * u + bb * v + 0.6 * n
        # the hole itself is empty along its axis: sample the wall just outside the hole edge
        oo = o + (g['holeDiameterMm'] / 2 + 0.15) * v
        loc, _, _ = tm.ray.intersects_location([oo], [n])
        d = np.sort((loc - oo) @ n)
        if len(d) >= 2:
            t.append(float(d[1] - d[0]))
    t = np.array(t)
    r = g['holeDiameterMm'] / 2
    S = g['holes'] * np.pi * r ** 2
    Lp = t.mean() + 1.7 * r
    fH = C_AIR / (2 * np.pi) * np.sqrt(S / (V * Lp))
    # head air behind the speaker: cavity under the cap minus every solid inside it
    solids = [H.get(k) for k in FIXED if k != 'head_cap'] + [H.get(k) for k in YAW] + [H.get('jaw_frame')] + \
             [H.get(k) for k in H.pi]
    for k in ('speaker', 'amplifier', 'speaker_retainer'):
        solids.append(man_from_tm(trimesh.load(STUDY / f'study-solids/{k}-world.stl', force='mesh')))
    air = interior - cap_ext - m3.Manifold.batch_boolean(solids, m3.OpType.Add)
    spk_grille = np.pi * 4.0 ** 2 + 6 * np.pi * 1.75 ** 2   # Ø8 + 6 x Ø3.5, scaled from the datasheet drawing
    out = {
        'variant': {'frontGapMm': FRONT_GAP, 'holeDiameterMm': g['holeDiameterMm'], 'pitchMm': g['pitchMm']},
        'measured': {'frontChamberVolumeMm3': round(V, 1), 'roofThicknessAlongHoleAxisMm': [round(t.min(), 2), round(t.mean(), 2), round(t.max(), 2)],
                     'grilleHoles': g['holes'], 'holeDiameterMm': g['holeDiameterMm'], 'grilleOpenAreaMm2': round(S, 1),
                     'chamberOpeningAreaMm2': g['chamberOpeningAreaMm2'], 'speakerOutlineAreaMm2': g['speakerOutlineAreaMm2'],
                     'headAirVolumeUnderCapMm3': round(air.volume(), 0)},
        'fromDrawingApprox': {'speakerOwnFrontGrilleOpenAreaMm2': round(spk_grille, 1),
                              'note': 'Ø8 centre hole + six Ø3.5 holes scaled from the CMS-30204-18X drawing'},
        'inference': {'helmholtzFrontResonanceHz': round(fH, 0), 'effectiveNeckLengthMm': round(Lp, 2),
                      'grilleOpenRatioOfChamberOpening': round(S / g['chamberOpeningAreaMm2'], 3),
                      'grilleOpenRatioOfSpeakerOwnGrille': round(S / spk_grille, 2),
                      'speakerBandHz': [700, 10000],
                      'reading': 'Front resonance above the 10 kHz band edge and grille open area at or above the '
                                 "speaker's own front-grille area: the grille should not throttle speech (inference, "
                                 'lumped model, no measurement).'}}
    import os
    tag = os.environ.get('AUDIO_VARIANT_TAG')
    (STUDY / (f'acoustics-{tag}.json' if tag else 'acoustics.json')).write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


if __name__ == '__main__':
    main()
