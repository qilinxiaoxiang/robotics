"""Measure the DFR1202 power pads on DFRobot's product photo (repo copy guide/content/wiring/dfr1202_top.jpg,
cropped from https://dfimg.dfrobot.com/enshop/image/data/DFR1202/DFR1202_Dim_02.jpg).

DFRobot publishes no pad drawing, so this is a pixel measurement (inference, about +-0.3 mm): the board's dark
outline sets the scale (30 x 26 mm per the product page), and gold pixels in the strip along the pad edge give each
pad's extent along the 26 mm edge and its depth into the board. Writes dfr-pads.json next to this file.
Light job (image only); run under the bounded runner like the fit check.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
PHOTO = HERE.parents[2] / 'content' / 'wiring' / 'dfr1202_top.jpg'
BOARD_MM = (30.0, 26.0)   # DFRobot product page: 30 x 26 x 8 mm


def groups(idx, gap=3):
    out, start, prev = [], idx[0], idx[0]
    for i in idx[1:]:
        if i > prev + gap:
            out.append((int(start), int(prev)))
            start = i
        prev = i
    out.append((int(start), int(prev)))
    return out


def main():
    im = np.asarray(Image.open(PHOTO).convert('RGB')).astype(int)
    r, g, b = im[..., 0], im[..., 1], im[..., 2]
    gold = (r > 140) & (g > 100) & (b < 120) & (r - b > 60)
    h, w = r.shape
    # The repo copy has a white margin round the board: the board is the block of non-white rows and columns.
    board = im.sum(2) < 600
    rows = np.where(board.sum(1) > 100)[0]
    cols = np.where(board.sum(0) > 100)[0]
    left, x1, top, y1 = int(cols[0]), int(cols[-1]), int(rows[0]), int(rows[-1])
    sx, sy = BOARD_MM[0] / (x1 - left + 1), BOARD_MM[1] / (y1 - top + 1)
    strip = gold[:, left:left + int(2.0 / sx)]
    pad_rows = groups(np.where(strip.any(1))[0])
    pads = []
    for (a, c), name in zip(pad_rows, ('VIN', 'GND', 'VOUT')):
        sub = gold[a:c + 1, left:left + int(4.0 / sx)]
        depth_px = int(np.where(sub.any(0))[0].max()) + 1
        pads.append({'pad': name, 'fromMm': round((a - top) * sy, 2), 'toMm': round((c + 1 - top) * sy, 2),
                     'lengthMm': round((c - a + 1) * sy, 2), 'centreMm': round(((a + c + 1) / 2 - top) * sy, 2),
                     'depthMm': round(depth_px * sx, 2)})
    spacing = [round(pads[i + 1]['centreMm'] - pads[i]['centreMm'], 2) for i in range(len(pads) - 1)]
    res = {'source': str(PHOTO.relative_to(HERE.parents[3])), 'imagePx': [w, h],
           'scaleMmPerPx': [round(sx, 4), round(sy, 4)], 'boardPx': {'left': left, 'right': x1, 'top': top, 'bottom': y1},
           'measuredAlongEdgeFrom': 'the VIN end of the 26 mm pad edge', 'pads': pads, 'centreSpacingMm': spacing,
           'status': 'inference: pixel measurement of a vendor photo, about +-0.3 mm'}
    (HERE / 'dfr-pads.json').write_text(json.dumps(res, indent=1) + '\n')
    print(json.dumps(res, indent=1))


if __name__ == '__main__':
    main()
