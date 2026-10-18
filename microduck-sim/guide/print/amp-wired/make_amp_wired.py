#!/usr/bin/env python3
"""Amplifier solid for the soldered-wire amplifier (2026-10-13): the V1.9 audio-study amplifier without its header.

The owner solders five wires straight into the MAX98357A (LRC, BCLK, DIN, GND, Vin) instead of fitting the 7-pin
right-angle header and jumper housings. The board, terminal block, SMD layer and 1.5 mm underside envelope keep the
audio-study parameters and position (extension-20261012-neck-audio/audio/scripts/build_study.py, amplifier block);
only the right-angle header body is left out. The wires are guide cables (routes.json audio_*), and the GAIN resistor
with the 3 mm Vin wire tail stays inside print/ext-v19/resistor_envelope_v19-world.stl.

Writes ../world/amplifier.stl (the header version stays as ../world/amplifier-ra-header.stl) and amp-wired.json.
Run with /tmp/microduck-cad-venv/bin/python.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import manifold3d as m3
import numpy as np
import trimesh

HERE = Path(__file__).resolve().parent
WORLD = HERE.parent / 'world'

AMP_W, AMP_L, AMP_T = 17.78, 19.05, 1.57          # Adafruit 3006 board file
AMP_HOLE_D, AMP_HOLE_IN = 2.5, 2.54
TB_W, TB_D, TB_H = 7.2, 8.0, 10.0                 # terminal block envelope (audio study assumption, height unpublished)
AMP_HEADER_EDGE_X, AMP_PCB_TOP_Z = 41.3, 139.8    # audio-study position (study-build.json amplifier)


def extrude(cs, z0, z1):
    return m3.Manifold.extrude(cs, z1 - z0).translate([0, 0, z0])


def main() -> None:
    xe, zt = AMP_HEADER_EDGE_X, AMP_PCB_TOP_Z
    x0 = xe - AMP_L
    board = extrude(m3.CrossSection.square([AMP_L, AMP_W]).translate([x0, -AMP_W / 2]), zt - AMP_T, zt)
    holes = [(x0 + AMP_HOLE_IN, -AMP_W / 2 + AMP_HOLE_IN), (x0 + AMP_HOLE_IN, AMP_W / 2 - AMP_HOLE_IN)]
    for hx, hy in holes:
        board = board - extrude(m3.CrossSection.circle(AMP_HOLE_D / 2, 24).translate([hx, hy]), zt - 3, zt + 1)
    tb = extrude(m3.CrossSection.square([TB_D, TB_W]).translate([x0 - 0.5, -TB_W / 2]), zt, zt + TB_H)
    smd = extrude(m3.CrossSection.square([AMP_L - TB_D - 4.5, AMP_W - 3]).translate([x0 + TB_D, -AMP_W / 2 + 1.5]), zt, zt + 1.2)
    under = extrude(m3.CrossSection.square([AMP_L - 1, AMP_W - 1]).translate([x0 + 0.5, -AMP_W / 2 + 0.5]), zt - AMP_T - 1.5, zt - AMP_T)
    amp = board + tb + smd + under
    mesh = amp.to_mesh()
    tm = trimesh.Trimesh(vertices=np.asarray(mesh.vert_properties)[:, :3], faces=np.asarray(mesh.tri_verts), process=True)
    old = WORLD / 'amplifier.stl'
    keep = WORLD / 'amplifier-ra-header.stl'
    if not keep.exists():
        keep.write_bytes(old.read_bytes())
    tm.export(old)
    pins = {n: [round(xe - 2.54, 2), round(-AMP_W / 2 + 1.27 + 2.54 * i, 2), zt]
            for i, n in enumerate(['LRC', 'BCLK', 'DIN', 'GAIN', 'SD', 'GND', 'Vin'])}
    rec = {'date': '2026-10-13', 'frame': 'robot frame, mm, x forward, y left, z up',
           'decidedBy': 'user ("功放也做焊接吧", 2026-10-13): five wires soldered into the amplifier, no right-angle header',
           'out': str(old.relative_to(HERE.parent.parent.parent)), 'sha256': hashlib.sha256(old.read_bytes()).hexdigest(),
           'watertight': bool(tm.is_watertight), 'volumeMm3': round(float(tm.volume), 2),
           'bounds': np.round(tm.bounds, 3).tolist(), 'holeCentresFrontFace': pins,
           'replaces': 'amplifier-ra-header.stl (same board, terminal block and position, plus the right-angle header body)'}
    (HERE / 'amp-wired.json').write_text(json.dumps(rec, indent=1) + '\n')
    print(json.dumps(rec, indent=1))


if __name__ == '__main__':
    main()
