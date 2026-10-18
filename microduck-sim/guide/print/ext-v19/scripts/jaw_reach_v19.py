#!/usr/bin/env python3
"""Where can a clip or the wire group sit on the neck_pitch body (head-pitch bracket) without being reached by the jaw
before the runtime jaw cap allows?

Reach field in the neck_pitch body frame (robot frame at q = 0): for every head pose node of the runtime pose-cap grid
that moves the jaw relative to this body (head_yaw -170..170 step 10, head_roll -25..25 step 5; the bracket group of
pose_cap_sweep.py) and every jaw opening 0..HI deg in STEP deg steps, the jaw surface samples (every jaw surface point
within E_JAW of a sample) are moved into the body frame and binned into VOX mm voxels; each voxel keeps the smallest
jaw angle that reached it. A voxel counts as reached at level L when a sample with angle <= L lies within
DELTA = contact gap 0.3 + E_JAW + half a step of jaw travel (r_jaw * STEP/2) + half a voxel diagonal of it
(conservative: the true jaw surface passes at least that close).
Reported per level L: the free depth beyond the bracket's -y face (y = -17.5) at each (x, z): the distance from that
face to the nearest reached voxel along -y; a part that protrudes less than the free depth at its (x, z) is not
reached below L. Also the free depth at the bracket clip site and along the bundle path, and PNG maps.
Usage: jaw_reach_v19.py   Writes ../checks/jaw-reach-v19.json and ../png/jaw-reach-v19-L<level>.png.
"""
from __future__ import annotations

import json
import math
import sys
import time

import numpy as np

import ext_lib as E

sys.path.insert(0, str(E.EXT / 'jaw-neck-check' / 'scripts'))
import pose_cap_sweep as PCS  # noqa: E402
from nr_lib import FK, JAW_AXIS, JAW_PIVOT, T_about, load_solid  # noqa: E402

HI, STEP, E_JAW, VOX = 27.0, 0.5, 0.75, 0.5
LO = np.array([0.0, -40.0, 60.0])
HI_BOX = np.array([50.0, -8.0, 112.0])
FACE_Y = -17.5
LEVELS = (27.0, 25.0, 22.0, 20.0, 18.0, 15.0)
YAW = np.arange(-170.0, 170.0 + 1e-9, 10.0)
ROLL = np.arange(-25.0, 25.0 + 1e-9, 5.0)


def main():
    t0 = time.time()
    v, f = load_solid('jaw_frame')
    pts = PCS.surface_points(v, f, E_JAW).astype(np.float32)
    d = v - JAW_PIVOT
    r_jaw = float(np.linalg.norm(d - np.outer(d @ JAW_AXIS, JAW_AXIS), axis=1).max())
    angles = np.arange(0.0, HI + 1e-9, STEP)
    Ta = np.stack([T_about(JAW_PIVOT, JAW_AXIS, math.radians(a)) for a in angles])      # jaw in head frame
    shape = np.ceil((HI_BOX - LO) / VOX).astype(int)
    minA = np.full(shape, np.float32(99.0))
    fk = FK()
    for y in YAW:
        for r in ROLL:
            T = fk.part_T({'head_yaw': math.radians(y), 'head_roll': math.radians(r)})
            H = np.linalg.inv(T['neck_pitch']) @ T['jaw_soft']
            for k, a in enumerate(angles):
                M = (H @ Ta[k]).astype(np.float32)
                P = pts @ M[:3, :3].T + M[:3, 3]
                ins = np.all((P >= LO) & (P < HI_BOX), axis=1)
                if not ins.any():
                    continue
                idx = np.floor((P[ins] - LO) / VOX).astype(int)
                np.minimum.at(minA, (idx[:, 0], idx[:, 1], idx[:, 2]), np.float32(a))
    from scipy.ndimage import distance_transform_edt
    delta = 0.3 + E_JAW + r_jaw * math.radians(STEP / 2) + VOX * math.sqrt(3) / 2
    xs = LO[0] + (np.arange(shape[0]) + 0.5) * VOX
    ys = LO[1] + (np.arange(shape[1]) + 0.5) * VOX
    zs = LO[2] + (np.arange(shape[2]) + 0.5) * VOX
    out = {'_method': __doc__.strip(), 'rJawMm': round(r_jaw, 2), 'samples': int(len(pts)), 'deltaMm': round(delta, 3),
           'box': [LO.tolist(), HI_BOX.tolist()], 'voxMm': VOX, 'levels': {}}
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    for L in LEVELS:
        occ = minA <= L
        reached = distance_transform_edt(~occ, sampling=VOX) <= delta if occ.any() else occ
        # free depth beyond the -y face at each (x, z): nearest reached voxel with y <= FACE_Y, measured from the face
        sel = ys <= FACE_Y
        R = reached[:, sel, :]
        ysel = ys[sel]
        free = np.full((shape[0], shape[2]), FACE_Y - LO[1], np.float32)
        anyr = R.any(axis=1)
        # largest reached y per column (closest to the face)
        last = np.where(anyr, len(ysel) - 1 - np.argmax(R[:, ::-1, :], axis=1), -1)
        free[anyr] = np.maximum(0.0, FACE_Y - (ysel[last[anyr]] + VOX / 2))
        def site(x0, x1, z0, z1):
            m = (xs[:, None] >= x0) & (xs[:, None] <= x1) & (zs[None, :] >= z0) & (zs[None, :] <= z1)
            return round(float(free[m].min()), 2)
        rec = {'clipSite_x22-30_z79-86': site(22.0, 30.0, 79.0, 86.0),
               'bundlePath_x24-28_z74-100': site(24.0, 28.0, 74.0, 100.0),
               'rearHalf_x17-22_z74-100': site(17.0, 22.0, 74.0, 100.0),
               'frontHalf_x30-35_z74-100': site(30.0, 35.0, 74.0, 100.0),
               'freeDepthByZ_x17-35': {f'{z:.0f}': round(float(free[(xs >= 17) & (xs <= 35)][:, np.argmin(abs(zs - z))].min()), 2)
                                       for z in range(70, 106, 2)}}
        out['levels'][f'{L:g}'] = rec
        print('level', L, rec, flush=True)
        fig, ax = plt.subplots(figsize=(7, 7))
        im = ax.imshow(free.T, origin='lower', extent=[LO[0], HI_BOX[0], LO[2], HI_BOX[2]], vmin=0, vmax=10, cmap='viridis')
        ax.add_patch(plt.Rectangle((17.0, 73.4), 18.0, 27.7, fill=False, ec='w', lw=1))
        for c in ((20, 82.421), (32, 82.421), (26, 76.421), (26, 88.421)):
            ax.add_patch(plt.Circle(c, 2.0, fill=False, ec='r', lw=1))
        ax.set_xlabel('x (mm)')
        ax.set_ylabel('z (mm)')
        ax.set_title(f'free depth beyond y = -17.5 (mm), jaw <= {L:g} deg, all yaw/roll nodes')
        fig.colorbar(im, ax=ax, shrink=0.8)
        fig.savefig(E.OUT / 'png' / f'jaw-reach-v19-L{L:g}.png', dpi=110)
        plt.close(fig)
    np.save(E.SCRATCH / 'jaw-reach-minA.npy', minA)
    out['elapsedSeconds'] = round(time.time() - t0, 1)
    E.jdump(out, E.OUT / 'checks' / 'jaw-reach-v19.json')
    print('done', out['elapsedSeconds'], flush=True)


if __name__ == '__main__':
    main()
