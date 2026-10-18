"""Build the study solids for every UART connection option and check them with exact manifold3d booleans.

Writes ../options.json and ../study-solids/*.stl. Robot frame, mm. All plug/wire dimensions marked (inference) in uart_lib.
Option ids:
  A    J6 sockets 3 (A1/PB02) and 4 (A2/PB03), straight male Dupont through a window in the cover (recommended)
  A+G  as A plus J7 socket 4 (GND) through a second window
  B    J6 sockets 3/4 with the male pin bent 90 deg, housings lying inside the pack (no cut)
  D0   J7 sockets 6/7 (D13/D14, current firmware), straight plug (cover window only)
  D1   J7 sockets 6/7, bent pin, housings towards -y or +y
  C    J12 PH header with plain Dupont female housings
"""
import json
import numpy as np
import manifold3d as m3
import uart_lib as U

S = json.loads((U.STUDY / 'sockets.json').read_text())
TOP = S['rows']['J7']['socketTopX']            # socket top face, x = -34.96
W = U.DUP['w']; H14 = U.DUP['housing']


def sock(row, n):
    s = S['rows'][row]['sockets'][n - 1]
    return s['y'], s['z']


A1 = sock('J6', 3); A2 = sock('J6', 4); GND = sock('J7', 4); D14 = sock('J7', 6); D13 = sock('J7', 7)

# ------------------------------------------------------------------ neighbours
class Lazy(dict):
    """Neighbour solids loaded on first use; bounds from the solid-cache manifest for the AABB prefilter."""
    def __missing__(self, k):
        v = U.man(k); self[k] = v; return v


NB = Lazy()
MANI = U.ia_lib.manifest()
BOUNDS = {k: tuple(MANI[k]['bounds'][0]) + tuple(MANI[k]['bounds'][1]) for k in U.NEIGHBOURS}
COVER = NB['rear_pack_cover']
CAB = {k: U.tube(U.ROUTES[k], U.CABLE_R[k]) for k in ['dxl5', 'dxl10', 'dxl12', 'openrbpwr', 'trunk', 'imu']}
VIN20_OLD = U.tube(U.ROUTES['vin20'], U.CABLE_R['vin20'])
# Re-routed 20 V pigtail: leaves the VIN/GND pad joints as now, then drops at y -7.0 just behind the board instead of at y -9.5,
# so it stays out of the J6 plug column (|y| 9.16..11.70); same tether opening and XT30 position as the guide route.
VIN20_NEW_PTS = [[-41, -4, -4], [-38.6, -6.2, -5.2], [-36.6, -7.0, -7.5], [-36.4, -7.0, -34.5], [-38.5, -4.5, -38.5],
                 [-40.5, -1.5, -41], [-42, 0, -45], [-42, 0, -53]]
VIN20_NEW = U.tube(VIN20_NEW_PTS, U.CABLE_R['vin20'])


def housing_x(yc, zc, x0=TOP, length=H14, face_gap=0.0):
    """Straight plug housing, seated: its front face on the socket top, body running -x."""
    return U.box([x0 - length, yc - W / 2, zc - W / 2], [x0 - face_gap, yc + W / 2, zc + W / 2])


# ------------------------------------------------------------------ option A: cover windows
CL = 0.5   # clearance round the 2.54 housing in the window (plugs cannot sit one pitch off)
def window(socks):
    ys = [s[0] for s in socks]; zs = [s[1] for s in socks]
    lo = [-47.6, min(ys) - W / 2 - CL, min(zs) - W / 2 - CL]
    hi = [-44.4, max(ys) + W / 2 + CL, max(zs) + W / 2 + CL]
    return U.box(lo, hi), (lo, hi)


WIN6, WIN6_BOX = window([A1, A2])
WIN7, WIN7_BOX = window([GND])
COVER_A = COVER - WIN6
COVER_AG = COVER - WIN6 - WIN7

# wires outside: out of the housing tail (x -48.96), turn up within 1.7 mm, up the cover's rear face, over its top edge at
# z ~30.6 (free band between the cover top 29.5 and the shell, see options.json shellBand), forward and inboard to the guide's
# existing UART path at (-27.2, -0.4, 33) -> notch row z 37 -> neck bundle.
XT = TOP - H14            # -48.96 housing tail
XW = -50.6                # vertical run on the cover's back face (cover outer face x -47; plug tail -48.96)
TAIL = [[-27.2, -0.4, 33.0], [-26.5, -0.4, 37.0], [-19.5, -0.4, 37.0], [-16.0, 1.5, 41.0]]


def outside_wire(yc, zc, yrun, ytop):
    return [[XT, yc, zc], [XT - 1.0, yc + (yrun - yc) * 0.5, zc + 0.4], [XW, yrun, zc + 1.8], [XW, yrun, 28.0],
            [-48.6, yrun, 30.5], [-45.5, ytop, 30.7], [-40.0, ytop * 0.4 - 1.5, 30.7], [-33.0, -1.8 + (ytop - yrun) * 0, 30.7],
            [-28.6, -1.2, 30.9]] + TAIL


W_A1 = outside_wire(A1[0], A1[1], A1[0] - 0.68, -11.0)
W_A2 = outside_wire(A2[0], A2[1], A2[0] + 0.68, -9.6)
W_G = [[XT, GND[0], GND[1]], [XT - 1.0, GND[0], GND[1] + 0.4], [XW, GND[0], GND[1] + 1.8], [XW, GND[0], 28.0],
       [-48.6, GND[0], 30.5], [-45.5, 8.0, 30.7], [-41.0, 2.0, 30.7], [-37.0, -2.0, 30.7], [-33.0, -2.75, 30.9],
       [-28.6, -2.75, 31.0], [-25.5, -2.75, 33.6], [-24.0, -2.75, 34.3], [-19.5, -2.75, 34.3], [-16.0, -1.0, 38.5]]
# GND (optional) leaves through the notch's lower row beside link N (y -0.5, z 34.3); the upper row has room for two wires only
# between link R (y -3.2) and the Pi lead (y 1.6).
# shift the two signal wires' shared tail by -/+ 0.65 so the pair lies side by side
W_A1 = W_A1[:9] + [[p[0], p[1] - 1.0, p[2]] for p in TAIL]   # upper notch row: free y -2.1..0.8 between R and the Pi lead
W_A2 = W_A2[:9] + [[p[0], p[1] + 0.3, p[2]] for p in TAIL]
WR = U.WIRE_R


def aabb_gap(a, b):
    lo = np.maximum(np.array(a[:3]), np.array(b[:3])); hi = np.minimum(np.array(a[3:]), np.array(b[3:]))
    return float(np.linalg.norm(np.maximum(lo - hi, 0)))


def check(solids, env, label, exclude=(), search=6.0, contact_ok=()):
    """Exact overlap volume and min gap of each study solid against env (name -> manifold, or a neighbour key loaded lazily).
    Pairs whose bounding boxes are further apart than `search` are skipped (they cannot be closer)."""
    out = {}
    for sn, sm in solids.items():
        sb = sm.bounding_box(); row = {}
        for en, em in env.items():
            if en in exclude:
                continue
            eb = BOUNDS[en] if isinstance(em, str) else em.bounding_box()
            if aabb_gap(sb, eb) > search:
                continue
            em = NB[em] if isinstance(em, str) else em
            g, ov = U.gap(sm, em, search)
            if ov > 0 or g < search:
                row[en] = {'gapMm': round(g, 3), 'overlapMm3': round(ov, 3)}
        out[sn] = dict(sorted(row.items(), key=lambda t: (t[1]['gapMm'], -t[1]['overlapMm3'])))
    worst = min(((v['gapMm'], -v['overlapMm3'], sn, en) for sn, r in out.items() for en, v in r.items()
                 if (sn, en) not in contact_ok), default=None)
    return {'label': label, 'searchMm': search, 'pairs': out,
            'worst': None if worst is None else {'solid': worst[2], 'neighbour': worst[3], 'gapMm': worst[0], 'overlapMm3': -worst[1]}}


res = {'frame': 'robot, mm (x forward, y left, z up)', 'socketTopX': TOP,
       'sockets': {'J6-3 A1/PB02': A1, 'J6-4 A2/PB03': A2, 'J7-4 GND': GND, 'J7-6 D14/PB22': D14, 'J7-7 D13/PB23': D13},
       'assumptions': {'duponHousingMm': [W, W, H14], 'malePinOutMm': U.DUP['pin'], 'wireRadiusMm': WR,
                       'status': 'inference: common Dupont dimensions, measure the owned jumpers'}}

ENV = {k: k for k in U.NEIGHBOURS}; ENV.update({'cable_' + k: v for k, v in CAB.items()})

# ---------- D0: original sockets, straight plug, cover window only (why it fails)
d0 = {f'plug_{n}': housing_x(*p) for n, p in (('D14', D14), ('D13', D13), ('GND', GND))}
env_d0 = dict(ENV); env_d0['rear_pack_cover'] = COVER - window([D14, D13])[0] - WIN7; env_d0['cable_vin20'] = VIN20_OLD
res['D0'] = check({k: v - U.box([TOP - 0.05, -50, -50], [0, 50, 50]) for k, v in d0.items()}, env_d0,
                  'J7 D13/D14/GND straight Dupont, windows in the cover', exclude=('openrb_board',))

# ---------- D1: original sockets, bent male pin, housing lying flat towards -y (centre) or +y (side wall)
def bent(yc, zc, direction, lift=1.6):
    """Male pin bent 90 deg: vertical stub out of the socket, housing axis at x = TOP - lift, running along +-y."""
    xa = TOP - lift
    stub = U.box([xa - 0.32, yc - 0.32, zc - 0.32], [TOP, yc + 0.32, zc + 0.32])
    y0 = yc + direction * 1.4
    y1 = y0 + direction * H14
    hb = U.box([xa - W / 2, min(y0, y1), zc - W / 2], [xa + W / 2, max(y0, y1), zc + W / 2])
    wire = U.tube([[xa, y1, zc], [xa, y1 + direction * U.BEND_ROOM, zc]], WR)
    return stub + hb + wire


env_bent = dict(ENV); env_bent['cable_vin20'] = VIN20_OLD
for dname, dirn in (('minusY', -1), ('plusY', +1)):
    sol = {f'bent_{n}': bent(*p, dirn) for n, p in (('D14', D14), ('D13', D13))}
    res[f'D1_{dname}'] = check(sol, env_bent, f'J7 D13/D14 bent pin, housings towards {dname}', exclude=('openrb_board',))

# ---------- C: J12 PH header with Dupont female housings standing on the header top (x -32.45), pads 3/4 at y -1.7 / -3.7, z 6.7
c_sol = {'dupont_on_J12_pad3': U.box([-32.45 - H14, -1.7 - W / 2, 6.7 - W / 2], [-32.45, -1.7 + W / 2, 6.7 + W / 2]),
         'dupont_on_J12_pad4': U.box([-32.45 - H14, -3.7 - W / 2, 6.7 - W / 2], [-32.45, -3.7 + W / 2, 6.7 + W / 2])}
res['C'] = check(c_sol, {'regulator': 'regulator', 'rear_pack_cover': COVER}, 'J12 with Dupont female housings')
res['C']['housingsOverlapEachOtherMm3'] = round(float((c_sol['dupont_on_J12_pad3'] ^ c_sol['dupont_on_J12_pad4']).volume()), 3)

# ---------- A / A+G: remapped sockets, straight plugs through windows
plugs = {'plug_A1': housing_x(*A1), 'plug_A2': housing_x(*A2)}
plug_g = {'plug_GND': housing_x(*GND)}
wires = {'wire_A1': U.tube(W_A1, WR), 'wire_A2': U.tube(W_A2, WR)}
wire_g = {'wire_GND': U.tube(W_G, WR)}
trim = lambda d: {k: v - U.box([TOP - 0.05, -50, -50], [0, 50, 50]) for k, v in d.items()}   # face on the socket top = intended contact
for oid, cov, sol, lab in (('A', COVER_A, {**trim(plugs), **wires}, 'J6 A1/A2 straight Dupont through one cover window'),
                           ('A+G', COVER_AG, {**trim(plugs), **trim(plug_g), **wires, **wire_g}, 'A plus J7 GND through a second window')):
    env = dict(ENV); env['rear_pack_cover'] = cov; env['cable_vin20_rerouted'] = VIN20_NEW
    r = check(sol, env, lab)
    env_old = dict(ENV); env_old['rear_pack_cover'] = cov; env_old['cable_vin20_guide'] = VIN20_OLD
    r['withGuideVin20Route'] = check({k: v for k, v in sol.items() if k.startswith('plug')}, {'cable_vin20_guide': VIN20_OLD},
                                     'plugs vs the guide vin20 route (before the re-route)')['pairs']
    # seated contact: the housing face on the socket top
    r['seatedOnSocketTop'] = {k: round(float(U.gap(v, NB['openrb_board'], 2)[0]), 3) for k, v in
                              {**plugs, **(plug_g if oid == 'A+G' else {})}.items()}
    # insertion: housing from 25 mm behind the cover to seated, straight along +x through the window
    ins = {k: U.box([TOP - H14 - 25, *(np.array(sock_) - W / 2)], [TOP - 0.05, *(np.array(sock_) + W / 2)])
           for k, sock_ in (('ins_A1', A1), ('ins_A2', A2)) + ((('ins_GND', GND),) if oid == 'A+G' else ())}
    ins = {k: U.box([TOP - H14 - 25, s_[0] - W / 2, s_[1] - W / 2], [TOP - 0.05, s_[0] + W / 2, s_[1] + W / 2])
           for k, s_ in (('ins_A1', A1), ('ins_A2', A2)) + ((('ins_GND', GND),) if oid == 'A+G' else ())}
    r['insertion'] = check(ins, env, 'insertion sweep along +x from 25 mm behind the cover')
    res[oid] = r

# window details + what the window exposes
res['windows'] = {'J6_A1A2': {'box': U.r3(WIN6_BOX), 'sizeYxZ': U.r3([WIN6_BOX[1][1] - WIN6_BOX[0][1], WIN6_BOX[1][2] - WIN6_BOX[0][2]]),
                              'removedFromCoverMm3': round(float((COVER ^ WIN6).volume()), 2)},
                  'J7_GND': {'box': U.r3(WIN7_BOX), 'sizeYxZ': U.r3([WIN7_BOX[1][1] - WIN7_BOX[0][1], WIN7_BOX[1][2] - WIN7_BOX[0][2]]),
                             'removedFromCoverMm3': round(float((COVER ^ WIN7).volume()), 2)},
                  'neighbourHolesHidden': {
                      'J6 socket 2 hole top z': S['rows']['J6']['sockets'][1]['holeZ'][1], 'window bottom z': round(WIN6_BOX[0][2], 2),
                      'J6 socket 5 hole bottom z': S['rows']['J6']['sockets'][4]['holeZ'][0], 'window top z': round(WIN6_BOX[1][2], 2)}}
# cover material left round the windows (to the plate edge / holes)
res['windows']['coverMaterialNote'] = 'cover plate |y| <= 18.6 there; nearest cover hole (+-16.1, -36.5) / (+-16.1, 26.0)'

# vin20 re-route on its own against everything
env_v = dict(ENV); env_v['plug_A1'] = plugs['plug_A1']; env_v['plug_A2'] = plugs['plug_A2']; env_v['plug_GND'] = plug_g['plug_GND']
env_v['room_leg_plugs'] = U.box([-42.45, -4.3, -27.75], [-32.45, 3.6, -17.75])
res['vin20_reroute'] = check({'vin20_rerouted': VIN20_NEW}, env_v, 'vin20 re-routed at y -7.0',
                             contact_ok=(('vin20_rerouted', 'regulator'), ('vin20_rerouted', 'rear_pack')))
res['vin20_reroute']['guideRouteVsRegulator'] = dict(zip(('gapMm', 'overlapMm3'), [round(v, 3) for v in U.gap(VIN20_OLD, NB['regulator'])]))
res['vin20_reroute']['points'] = VIN20_NEW_PTS
res['vin20_reroute']['lengthGuideMm'] = round(float(sum(np.linalg.norm(np.diff(np.array(U.ROUTES['vin20']), axis=0), axis=1))), 1)
res['vin20_reroute']['lengthNewMm'] = round(float(sum(np.linalg.norm(np.diff(np.array(VIN20_NEW_PTS), axis=0), axis=1))), 1)

# ---------- B: remapped sockets, bent pins inside the pack, housings towards +y (centre)
env_b = dict(ENV); env_b['cable_vin20_guide'] = VIN20_OLD
res['B'] = check({f'bent_{n}': bent(*p, +1) for n, p in (('A1', A1), ('A2', A2))}, env_b,
                 'J6 A1/A2 bent pin, housings towards +y inside the pack', exclude=('openrb_board',))
res['B']['bentPinBudget'] = {'pinOutMm': U.DUP['pin'], 'liftToHousingAxisMm': 1.6, 'bendArcMm': round(np.pi / 2 * 0.9, 2),
                             'straightBeforeHousingMm': 0.5,
                             'insertionLeftMm': round(U.DUP['pin'] - 0.5 - np.pi / 2 * 0.9 - (1.6 - 0.9), 2),
                             'straightPlugInsertionMm': U.DUP['pin']}

# wire path lengths (option A), so the owner knows the jumper length needed
L = lambda pts: float(sum(np.linalg.norm(np.diff(np.array(pts), axis=0), axis=1)))
res['wireLengths'] = {'A1_to_notch_row_mm': round(L(W_A1[:-1]), 1), 'A2_to_notch_row_mm': round(L(W_A2[:-1]), 1),
                      'GND_to_notch_row_mm': round(L(W_G[:-1]), 1),
                      'guide_uart_lower_mm': round(L(U.ROUTES['uart_lower'][:-1]), 1),
                      'note': 'from the plug tail to the notch exit (-19.5, y, 37); the rest of the run (neck + head) is the guide uart path'}
res['outsideRun'] = {'verticalOnCoverBackX': XW, 'coverOuterFaceX': -47.0, 'plugTailX': XT,
                     'plugProtrusionBeyondCoverMm': round(-47.0 - XT, 2), 'wireProtrusionBeyondCoverMm': round(-47.0 - (XW - WR), 2)}

# ---------- save study solids
out = U.STUDY / 'study-solids'
out.mkdir(exist_ok=True)
save = {'cover_with_window_A.stl': COVER_A, 'cover_with_windows_A+G.stl': COVER_AG,
        'plugs_A.stl': U.union(list(plugs.values())) if hasattr(U, 'union') else plugs['plug_A1'] + plugs['plug_A2'],
        'plug_GND.stl': plug_g['plug_GND'], 'wires_A.stl': wires['wire_A1'] + wires['wire_A2'], 'wire_GND.stl': wire_g['wire_GND'],
        'vin20_rerouted.stl': VIN20_NEW, 'window_cutter_J6.stl': WIN6, 'window_cutter_J7.stl': WIN7}
for n, mm in save.items():
    U.from_m(mm).export(out / n)
# added material outside the pack body (for the walking sweep): everything of option A+G behind x -47 plus the over-top run
OUTSIDE = U.box([-60, -30, -60], [-47.0, 30, 60]) + U.box([-60, -30, 29.5], [-24, 30, 60])
added = ((plugs['plug_A1'] + plugs['plug_A2'] + plug_g['plug_GND'] + wires['wire_A1'] + wires['wire_A2'] + wire_g['wire_GND']) ^ OUTSIDE)
U.from_m(added).export(out / 'added_outside_pack_A+G.stl')
res['addedOutsidePackMm3'] = round(float(added.volume()), 2)
res['addedOutsideBounds'] = U.r3(np.asarray(U.from_m(added).bounds).tolist())

# shell band over the cover top (where the wires pass)
band = {}
for k in ('shell_left', 'shell_right'):
    cut = NB[k] ^ U.box([-48, -12, 29.0], [-27, 12, 34.0])
    band[k] = round(cut.bounding_box()[2], 2) if not cut.is_empty() else None
res['shellBand'] = {'lowestShellZ_over_x-48..-27_y+-12': band, 'coverTopZ': 29.5, 'packWallAndLipTopZ': 28.5}
U.jdump(res, U.STUDY / 'options.json')
for k in ('D0', 'D1_minusY', 'D1_plusY', 'C', 'A', 'A+G', 'B', 'vin20_reroute'):
    print(k, res[k]['worst'])
print('windows', res['windows']['J6_A1A2']['sizeYxZ'], res['windows']['J7_GND']['sizeYxZ'])
print('wireLengths', res['wireLengths']); print('shell', res['shellBand']); print('added', res['addedOutsidePackMm3'], res['addedOutsideBounds'])
print('B budget', res['B']['bentPinBudget'])
