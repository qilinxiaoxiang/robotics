"""Locate the OpenRB-150 stacking-header sockets on the placed ROBOTIS mesh and measure the free depth behind each one.

Socket holes: rays along +x (from behind the board towards it) at the row centre line; a hole shows as a hit deeper than the
socket-top face. Rows: J7 (+y, schematic: from the USB-C end +5V, VIN, +3V3, GND, RESET, D14/PB22 TX, D13/PB23 RX, ...) and
J6 (-y: AREF/PA03, A0/PA02, A1/PB02, A2/PB03, A3/PA04, ...). Socket k counts from the USB-C end (z = -42 end of the board).
Free depth: for a 2.54 mm square plug footprint centred on the socket, the distance from the socket top to the first solid in -x.
Writes ../sockets.json.
"""
import numpy as np, trimesh
import uart_lib as U

board = trimesh.load(U.WORLD / 'openrb-board-upright.stl')
parts = board.split(only_watertight=False)
rows = [p for p in parts if (p.bounds[1][2] - p.bounds[0][2]) > 30 and (p.bounds[1][1] - p.bounds[0][1]) < 3]
rows.sort(key=lambda p: p.bounds[0][1])
assert len(rows) == 2, len(rows)
J6, J7 = rows  # J6 at -y, J7 at +y (see README: photo right row = robot +y in the pack pose)
ray = trimesh.ray.ray_triangle.RayMeshIntersector(board)


def holes(row):
    b = row.bounds; yc = float(b[:, 1].mean()); top = float(b[0][0])
    zs = np.arange(b[0][2] + 0.05, b[1][2] - 0.05, 0.05)
    o = np.c_[np.full(len(zs), -60.0), np.full(len(zs), yc), zs]
    d = np.tile([1.0, 0, 0], (len(zs), 1))
    loc, idx, _ = ray.intersects_location(o, d, multiple_hits=False)
    hitx = np.full(len(zs), np.nan); hitx[idx] = loc[:, 0]
    deep = hitx > top + 0.5
    runs = []; cur = None
    for z, dd in zip(zs, deep):
        if dd and cur is None:
            cur = [z, z]
        elif dd:
            cur[1] = z
        elif cur is not None:
            runs.append(cur); cur = None
    if cur is not None:
        runs.append(cur)
    c = sorted((a + e) / 2 for a, e in runs)
    return yc, top, b, c, runs


J7_NAMES = ['+5V', 'VIN', '+3V3', 'GND', 'RESET', 'D14 (PB22, Serial3 TX)', 'D13 (PB23, Serial3 RX)', 'D12 (PA09)', 'D11 (PA08)',
            'D10 (PA19)', 'D9 (PA17)', 'D8 (PA16)', 'D7 (PA21)', 'D6 (PA20)']
J6_NAMES = ['AREF (PA03)', 'A0 (PA02)', 'A1 (PB02, SERCOM5 PAD0)', 'A2 (PB03, SERCOM5 PAD1)', 'A3 (PA04)', 'A4 (PA05)', 'A5 (PA06)',
            'A6 (PA07)', 'D0 (PA22)', 'D1 (PA23)', 'D2 (PA10)', 'D3 (PA11)', 'D4 (PB10)', 'D5 (PB11)']

obst = {k: U.tm(k) for k in ['regulator', 'rear_pack', 'rear_pack_cover', 'shell_left', 'shell_right']}
cables = {k: U.tube(U.ROUTES[k], U.CABLE_R[k]) for k in ['vin20', 'dxl5', 'dxl10', 'openrbpwr', 'trunk']}
obst_m = {k: U.man(k) for k in obst}


def free_depth(yc, zc, top, w=U.DUP['w']):
    """Prism x from top-60 to top over the plug footprint; the deepest-reaching obstacle face (max x of intersection)."""
    pr = U.box([top - 60, yc - w / 2, zc - w / 2], [top, yc + w / 2, zc + w / 2])
    res = {}
    for k, m in list(obst_m.items()) + list(cables.items()):
        inter = pr ^ m
        if inter.volume() > 1e-6:
            bb = inter.bounding_box(); hi = bb.max() if callable(getattr(bb, 'max', None)) else bb[1]
            res[k] = round(top - float(np.asarray(U.from_m(inter).bounds)[1][0]), 2)
    return dict(sorted(res.items(), key=lambda t: t[1]))


out = {'source': 'guide/print/world/openrb-board-upright.stl (ROBOTIS-derived mesh, V1.8 pack pose); ray cast at the row centre line',
       'socketCountFrom': 'USB-C end (z = -42)', 'pitchNominal': 2.54, 'rows': {}}
for name, row, names in (('J7', J7, J7_NAMES), ('J6', J6, J6_NAMES)):
    yc, top, b, c, runs = holes(row)
    c = sorted(c)  # ascending z = from the USB-C end
    socks = []
    for k, zc in enumerate(c):
        socks.append({'socket': k + 1, 'name': names[k] if k < len(names) else None, 'y': round(yc, 2), 'z': round(zc, 2),
                      'holeZ': U.r3(runs[k]), 'freeDepthBehindTopMm': free_depth(yc, zc, top)})
    out['rows'][name] = {'bodyBounds': U.r3(b.tolist()), 'socketTopX': round(top, 2), 'rowCentreY': round(yc, 2),
                         'nSockets': len(c), 'pitchMeasured': round(float(np.diff(c).mean()), 3) if len(c) > 1 else None,
                         'sockets': socks}
    print(name, 'top', round(top, 2), 'y', round(yc, 2), 'n', len(c), 'pitch', out['rows'][name]['pitchMeasured'])
    for s in socks[:8]:
        print('  ', s['socket'], s['name'], s['z'], s['freeDepthBehindTopMm'])
reg = obst['regulator'].bounds
out['regulatorBounds'] = U.r3(reg.tolist())
out['coverInnerFaceX'] = -45.0
U.jdump(out, U.STUDY / 'sockets.json')
