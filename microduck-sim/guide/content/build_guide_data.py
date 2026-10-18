#!/usr/bin/env python3
"""Generate guide/data/guide-data.json (schemaVersion 1) for the MicroDuck torso, neck, head and wiring guide.

    /tmp/microduck-cad-venv/bin/python guide/content/build_guide_data.py
    python3 guide/build_guide.py --data guide/data/guide-data.json --out guide/dist/MICRODUCK-BUILD.html

Needs numpy, trimesh and fast_simplification (mesh decimation). Inputs:
- guide/data/sources/full-build-data-current.json  current whole-robot CAD export (robot frame, mm)
- guide/print/world/*.stl                          current printed parts in the robot frame (v18-sources.json): V1.9 head cap
                                                   (reprinted white in V1.14) and V2.0 side shells (V1.14, white),
                                                   speaker retainer and four wire clips; V1.8 face panel, eye trim and lower
                                                   head shell; V1.9 rear electronics pack; rear converter box frame and lid
- guide/print/world/xl4015_left.stl, xl4015_right.stl, pd5991.stl  the two XL4015 converters (xl4015_left: top tier, #1, 7 V;
  xl4015_right: middle tier, #2, 5 V; file names kept from the CAD export) and the 5991
                                                   and the Adafruit 5991 (bottom tier) in the rear converter box
                                                   (print/back-plate/layout-F/, approved 2026-10-14)
- guide/print/world/speaker.stl, amplifier.stl      speaker and MAX98357A amplifier at their V1.9 cap positions (audio study);
                                                   the amplifier has five soldered wires and no header (print/amp-wired/)
- guide/print/world/openrb-board-upright.stl        OpenRB-150 with trimmed header tails, standing upright in the rear pack
                                                   (fed 7.40 V, the 7 V rail, by a 22 AWG pair from XL4015 #1 (top board) in the rear converter box; 15 V from
                                                   an Adafruit 5991; PROJECT-CONTEXT.json current_build.servo_rail_7v_20261014)
- guide/print/world/imu_board.stl, imu_sh4_receiving.stl  BNO085 and its plug turned onto the pack's front plate
- guide/print/world/camera_board.stl                Radxa Camera 13M 214 on the A7Z face bosses (print/face-a7z/), connector edge +y
- guide/print/world/a7z_*.stl, antenna*.stl, camera_ribbon.stl  Radxa Cubie A7Z board ('pi' key) and components, AC019
                                                   antenna with coax and IPEX plug, A7Z end of the camera ribbon (print/a7z-head/)
- guide/content/routes.json                         cable centerlines
- guide/content/steps.py                            chapters, steps and cable wording
"""
from __future__ import annotations

import base64
import json
import math
import re
import sys
from pathlib import Path

import numpy as np
import trimesh
import fast_simplification

HERE = Path(__file__).resolve().parent
GUIDE = HERE.parent
SRC = GUIDE / 'data' / 'sources' / 'full-build-data-current.json'
PRINT = GUIDE / 'print'
OUT = GUIDE / 'data' / 'guide-data.json'
FASTENERS = HERE / 'fasteners.json'
REUSED_SCREWS = HERE / 'reused-leg-screws.json'   # hip screws the torso chapter takes out and puts back
FOV_DEG = 32.0

sys.path.insert(0, str(HERE))
import steps as content  # noqa: E402

# Parts the new design no longer uses, and GPIO sockets that changed. The camera and speaker screw meshes are
# replaced by their fasteners.json records, which every screw step draws and counts. camera_retainer is retired with
# the V1.8 face: the camera sits on four lands and two M2 x 8 hold it through the face into the eye trim. The V1.8 rear
# pack (print/rear-pack/) replaces the integrated power support, the regulator insert, the OpenRB tray (never in the
# source export) and the IMU clamp and rear cover; the fuses are gone with it. 2026-10-13: the DFR1202 converter
# ('regulator') is gone too (USB-C 5 V straight into the OpenRB terminal block); its pack channel stays empty.
DROP = {'openrb', 'head_pi_gpio_pin_20_receiving', 'camera_clamp_screw_1', 'camera_clamp_screw_2', 'camera_clamp_screw_3',
        'speaker_mount_screw_1', 'speaker_mount_screw_2', 'camera_retainer',
        'power_support', 'regulator_insert', 'regulator', 'imu_clamp', 'imu_cover', 'upper_pad', 'lower_pad',
        # V1.9 (2026-10-13): the speaker and amplifier are back, at the audio-study positions under the V1.9 cap roof
        # (print/world/speaker.stl, amplifier.stl override the source geometry below); the V1.6 speaker cage stays out.
        # The jumper ends on pins 4, 12, 35 and 40 come from the source; pin 34 (amplifier ground) is made from pin 6;
        # pin 14 is not used.
        'speaker_cradle', 'speaker_keeper', 'head_pi_gpio_pin_14_receiving',
        # 2026-10-15 Radxa Cubie A7Z head: the IMU is back on pins 3 and 5 (TWI7 hardware I2C), so their source jumper
        # ends stay, and so does the pin 12 end (I2S0 BCLK, an ordinary Dupont plug; its wire bends down at the plug end
        # in the 1.8 mm between the plug and the bare back of the camera board).
        'head_pi_zero_w_gpio_solder_tails'}
# Pi Zero W board components from the source export; the A7Z components (print/world/a7z_*.stl) replace them.
DROP_PREFIX = ('head_pi_component_',)

STATUS = {
    # assembled legs keep 'assembled'; everything else is assigned here
    'printed': ['torso_base', 'ring10_torso', 'ring5_torso',
                'neck_link_a', 'neck_link_b', 'head_yaw_link', 'head_roll_ring_a', 'head_roll_ring_b',
                'idler11', 'idler12', 'idler_cap11', 'idler_cap12'],
    'new-print': ['shell_left', 'shell_right', 'rear_pack', 'rear_frame', 'rear_lid', 'neck_pitch', 'head_bottom', 'face_panel', 'head_cap', 'eye_trim', 'jaw_support', 'mouth_sliding_ring', 'jaw_frame', 'neck_pitch_ring',
                  'speaker_retainer', 'clip_torso', 'clip_bracket', 'clip_head', 'clip_cap',
                  'battery_backpack_frame', 'battery_backpack_cap'],
    'purchased': ['imu_board', 'imu_sh4_receiving', 'camera_board', 'speaker', 'amplifier', 'pi', 'camera_ribbon',
                  'antenna', 'antenna_coax', 'antenna_ipex'],
}
STATUS_OF = {k: s for s, ks in STATUS.items() for k in ks}

# Motors are 112k triangles each in the CAD export; 15 of them dominate the file size.
DECIMATE_OVER = 30000
# Pi seat on the V1.8 head cap, relative to the full-build source position (robot frame, mm): 4.6 mm back (V1.7,
# interference-audit/verify-cap) and 1.0 mm up (V1.8: the rails are raised so the jumper-wire ends on the header clear
# the windowless V1.8 lower shell by 1.59 mm; print/world/v18-sources.json).
PI_SHIFT = [-4.6, 0.0, 1.0]
# Header pin axis of the head computer (unit, robot frame): the board leans 10 deg forward (print/a7z-head/pi-frame-raw.json).
PIN_AXIS = np.array([0.984808, 0.0, -0.173648])
A7Z_NAMES = {'csi_connector': 'A7Z camera connector (31-pin, underside, pin-1 end)', 'microsd_card': 'microSD card in the A7Z',
             'microsd_socket': 'A7Z microSD socket', 'ipex_socket': 'A7Z antenna socket (IPEX)', 'fan_connector': 'A7Z fan socket',
             'micro_hdmi': 'A7Z micro HDMI', 'usb_c_power': 'A7Z USB-C power', 'usb_c_otg_dp': 'A7Z USB-C (OTG, DisplayPort)',
             'soc_a733': 'A7Z processor (Allwinner A733)', 'ram': 'A7Z memory', 'pmic_area': 'A7Z power chip area',
             'wifi_module_fcu760k': 'A7Z Wi-Fi module', 'pcie_fpc': 'A7Z PCIe connector', 'uboot_button': 'A7Z boot button',
             'underside_smd': 'A7Z underside components'}
A7Z_COLORS = {'microsd_card': '#2b4a8b', 'micro_hdmi': '#b0b0b0', 'usb_c_power': '#b0b0b0', 'usb_c_otg_dp': '#b0b0b0',
              'ipex_socket': '#d4af37', 'csi_connector': '#e8e2d0', 'pcie_fpc': '#e8e2d0', 'fan_connector': '#f2f2f2'}
# Every XL330 is simplified straight to 36,000 triangles (0.02 mm from its source). A 9,000 start let ID12 and ID14
# pass the surface test at about 23,000 triangles while moving the surface 2.6 mm into their neighbours.
MOTOR_TARGET = 36000
OTHER_TARGET = 20000


def b64(arr: np.ndarray) -> str:
    return base64.b64encode(np.ascontiguousarray(arr).astype('<f4' if arr.dtype.kind == 'f' else '<u4').tobytes()).decode()


def decode(p: dict) -> tuple[np.ndarray, np.ndarray]:
    v = np.frombuffer(base64.b64decode(p['positionB64']), '<f4').reshape(-1, 3).astype(np.float64)
    f = np.frombuffer(base64.b64decode(p['indexB64']), '<u4').reshape(-1, 3).astype(np.int64)
    return v, f


SCREW_FIELDS = ('id', 'step', 'spec', 'kind', 'diameterMm', 'lengthMm', 'headDiameterMm', 'headHeightMm', 'nut', 'washer',
                'center', 'axis', 'throughPart', 'intoPart', 'tool', 'reuse')
TAP_ITEM = re.compile(r'^(M[\d.]+) × ([\d.]+) self-tapping screw \(TAP\)$')


def spec_key(spec: str) -> tuple[str, str] | None:
    """('M2', '6') from 'M2 x 6 TAP', 'M2 × 6' or 'M2x6'."""
    m = re.match(r'\s*(M[\d.]+)\s*[x×]\s*([\d.]+)', spec)
    return (m.group(1), m.group(2).rstrip('0').rstrip('.') if '.' in m.group(2) else m.group(2)) if m else None


def attach_screws(parts: dict, steps: list) -> tuple[list, list]:
    """Screws from fasteners.json, each with a short 'where' line; their steps drop the generic TAP prepare rows.

    Returns (screws, problems). A step whose screw count per size differs from its written prepare rows is a problem,
    so the text and the 3D markers cannot silently disagree.
    """
    if not FASTENERS.exists():
        return [], ['fasteners.json missing: no screws drawn']
    src = json.loads(FASTENERS.read_text())
    raws = list(src.get('screws', []))
    if REUSED_SCREWS.exists():
        raws += json.loads(REUSED_SCREWS.read_text()).get('screws', [])
    by_id = {st['id']: st for st in steps}
    name = lambda k: parts[k]['name'] if k in parts else k
    screws, problems = [], []
    for raw in raws:
        st = by_id.get(raw.get('step'))
        if st is None:
            problems.append(f"screw {raw.get('id')}: unknown step {raw.get('step')!r}")
            continue
        rec = {k: raw[k] for k in SCREW_FIELDS if raw.get(k) not in (None, '')}
        thru = [k for k in (raw.get('throughParts') or [raw.get('throughPart')]) if k]
        into = raw.get('intoPart')
        lead = ' and '.join(name(k) for k in thru)
        where = (f'through {lead} into {name(into)}' if lead and into else f'into {name(into)}' if into else '')
        if raw.get('nut'):
            where += f", {raw['nut']} nut behind"
        if where:
            rec['where'] = where[0].upper() + where[1:]
        # Builder-facing notes come from the step (per size); the audit's measurement notes stay in fasteners.json.
        note = (st.get('screwNotes') or {}).get(raw.get('spec'))
        if note is None and raw.get('reuse'):
            note = 'Reuse the screw you took out here.'
        if note:
            rec['note'] = note
        screws.append(rec)
    for st in steps:
        mine = [x for x in screws if x['step'] == st['id']]
        if not mine:
            continue
        drawn: dict = {}
        for x in mine:
            k = spec_key(x['spec'])
            drawn[k] = drawn.get(k, 0) + 1
        written: dict = {}
        keep = []
        for item in st.get('prepare', []):
            m = TAP_ITEM.match(item.get('item', '')) if item.get('kind') == 'fastener' else None
            if m:
                k = (m.group(1), m.group(2))
                written[k] = written.get(k, 0) + int(item.get('qty') or 0)
            else:
                keep.append(item)
        if written != drawn:
            problems.append(f"step {st['id']}: prepare lists {written} but fasteners.json draws {drawn}")
        st['prepare'] = keep
    for st in steps:
        st.pop('screwNotes', None)
    return screws, problems


def orient_outward(v: np.ndarray, f: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Wind every shell consistently and every closed shell outward.

    The viewer outlines added parts with an inverted hull pushed out along the vertex normals; an inward-wound
    shell (the IMU board, the OpenRB board, the Pi component boxes, the feet) turns that hull into a blue skin.
    """
    m = trimesh.Trimesh(v, f, process=False)
    trimesh.repair.fix_normals(m, multibody=True)
    return np.asarray(m.vertices, dtype=np.float64), np.asarray(m.faces, dtype=np.int64)


def decimate(v: np.ndarray, f: np.ndarray, target: int, what: str = '') -> tuple[np.ndarray, np.ndarray]:
    if len(f) <= target:
        return v, f
    # Weld first. The servo sources are partly unwelded; collapsing edges on loose triangles
    # stretches stray faces through the neighbouring parts (585,000 mm2 of surface on a 10,000 mm2 servo).
    m = trimesh.Trimesh(v, f, process=True)
    m.merge_vertices(digits_vertex=4)
    # Keep at least 90 % of the surface; a small dense board needs a larger budget than a shell.
    while target < len(m.faces):
        vv, ff = fast_simplification.simplify(m.vertices.astype(np.float32), m.faces.astype(np.int32), target_reduction=1 - target / len(m.faces))
        after = trimesh.Trimesh(vv, ff, process=False).area
        if 0.9 * m.area <= after <= 1.05 * m.area:
            return vv.astype(np.float64), ff.astype(np.int64)
        target *= 2
    return np.asarray(m.vertices, dtype=np.float64), np.asarray(m.faces, dtype=np.int64)


def box(lo, hi) -> tuple[np.ndarray, np.ndarray]:
    m = trimesh.creation.box(extents=np.subtract(hi, lo), transform=trimesh.transformations.translation_matrix(np.add(lo, hi) / 2))
    return np.asarray(m.vertices), np.asarray(m.faces)


def cylinder(a, b, r) -> tuple[np.ndarray, np.ndarray]:
    m = trimesh.creation.cylinder(radius=r, segment=[a, b], sections=16)
    return np.asarray(m.vertices), np.asarray(m.faces)


def load_stl(path: Path) -> tuple[np.ndarray, np.ndarray]:
    m = trimesh.load(path, force='mesh', process=True)
    return np.asarray(m.vertices, dtype=np.float64), np.asarray(m.faces, dtype=np.int64)


def first_existing(*paths: Path) -> Path | None:
    for p in paths:
        if p and p.exists():
            return p
    return None


def polyline_length(path) -> float:
    return sum(math.dist(a, b) for a, b in zip(path, path[1:]))


def point_along(path, dist_mm):
    """Point at arc length dist_mm along a polyline, and the index of the segment it falls in."""
    acc = 0.0
    for i, (a, b) in enumerate(zip(path, path[1:])):
        seg = math.dist(a, b)
        if acc + seg >= dist_mm:
            t = (dist_mm - acc) / seg
            return [round(a[k] + (b[k] - a[k]) * t, 1) for k in range(3)], i
        acc += seg
    return list(path[-1]), len(path) - 2


class Ctx:
    """What steps.py needs: part bounds for cameras, cable lengths, part presence."""

    def __init__(self, parts: dict, lengths: dict):
        self.parts = parts
        self.L = lengths

    def has(self, key: str) -> bool:
        return key in self.parts

    def keys(self, *keys):
        return [k for k in keys if k in self.parts]

    def module_keys(self, module: str):
        return [k for k, p in self.parts.items() if p['module'] == module]

    def bounds(self, refs):
        bs = []
        for r in refs:
            if r in self.parts:
                bs.append(self.parts[r]['bounds'])
            else:
                bs += [p['bounds'] for p in self.parts.values() if p['module'] == r]
        if not bs:
            raise SystemExit(f'camera framing: no parts for {refs}')
        lo = [min(b[0][a] for b in bs) for a in range(3)]
        hi = [max(b[1][a] for b in bs) for a in range(3)]
        return lo, hi

    def cam(self, refs, direction=(1.0, 1.1, 0.75), margin=1.1, target=None):
        lo, hi = self.bounds(refs)
        c = target or [(lo[a] + hi[a]) / 2 for a in range(3)]
        radius = math.dist(lo, hi) / 2
        dist = radius / math.sin(math.radians(FOV_DEG) / 2) * margin
        n = math.sqrt(sum(d * d for d in direction))
        return {'position': [round(c[a] + direction[a] / n * dist, 1) for a in range(3)], 'target': [round(x, 1) for x in c]}


def build_parts() -> dict:
    src = json.loads(SRC.read_text())
    parts: dict[str, dict] = {}
    for p in src['parts']:
        if p['key'] in DROP or p['key'].startswith(DROP_PREFIX):
            continue
        v, f = decode(p)
        n = len(f)
        if n > DECIMATE_OVER:
            v, f = decimate(v, f, MOTOR_TARGET if p.get('partKind') == 'motor' else OTHER_TARGET, p['key'])
        module = p['moduleId']
        status = 'assembled' if 'leg' in module else STATUS_OF.get(p['key'])
        if status is None:
            status = 'owned' if p.get('partKind') == 'motor' or p['key'].startswith('head_pi') or p['key'] == 'pi' else 'purchased'
        name = p['name']
        if p['key'] == 'jaw_support':
            name = 'Jaw support (restored original)'
        parts[p['key']] = {'key': p['key'], 'name': name, 'color': p['color'], 'module': module, 'status': status, 'v': v, 'f': f}

    # GPIO sockets on the Radxa Cubie A7Z (2026-10-15, same header place as the Pi). The 32 mm camera board covers the
    # edge-row (even) Dupont ends of pins 10 to 34, so the UART uses UART2 on inner-row pins 7 (TX) and 11 (RX) and the
    # amplifier ground uses inner-row pin 39; inner-row ends are made from pin 9 (2.54 mm pitch, higher pins are -y).
    # The touch readout (XIAO ESP32-S3, extension-20261015-touch/) takes inner-row pins 17 (3.3 V), 25 (GND), 29 (I2C
    # SCL, PB2) and 31 (I2C SDA, PB3); no stock A7Z overlay serves them (PLAN.md).
    odd = parts['head_pi_gpio_pin_09_receiving']
    for pin in (7, 11, 17, 25, 29, 31, 39):
        key = f'head_pi_gpio_pin_{pin:02d}_receiving'
        parts[key] = dict(odd, key=key, v=odd['v'] + [0, (9 - pin) * 1.27, 0])
    # Each socket is one female jumper-wire end (about 2.5 x 2.5 x 14 mm) on its pin; the kit list counts them as one item.
    for key, part in parts.items():
        if key.startswith('head_pi_gpio_pin_') and key.endswith('_receiving'):
            pin = int(key.split('_')[4])
            part.update(name=f'Jumper-wire end on A7Z pin {pin}', kit='Female jumper-wire end (half of a female-to-female jumper)',
                        status='purchased')

    # The V1.8 head cap seats the Pi 4.6 mm further back (V1.7: the plugged jumper-wire ends clear the camera while the
    # cap comes down, interference-audit/verify-cap) and 1.0 mm higher (V1.8: the lower shell's beak-roof window is
    # filled, and the raised rails keep the jumper-wire ends 1.59 mm off that roof). The Pi, its header, its components
    # and the jumper ends all move with it; the E-pi screws in fasteners.json carry the same shift.
    for key, part in parts.items():
        if key == 'pi' or key.startswith('head_pi'):
            part['v'] = part['v'] + PI_SHIFT
            part['shiftMm'] = PI_SHIFT

    # Radxa Cubie A7Z (print/a7z-head/build_a7z_head.py, 2026-10-15): the board, its components and the antenna are
    # already in the robot frame on the shifted Pi seat (frame from the shifted header pins), so they take no shift. The
    # 'pi' key stays for the head computer so the screw records (E-pi-01..04) and the steps keep their part.
    world = PRINT / 'world'
    pcb = first_existing(world / 'a7z_pcb.stl')
    if pcb:
        v, f = load_stl(pcb)
        parts['pi'].update(v=v, f=f, name='Radxa Cubie A7Z with soldered 40-pin header', color='#1f5f3a', status='purchased',
                           source=str(pcb))
        parts['pi'].pop('shiftMm', None)
        for path in sorted(world.glob('a7z_*.stl')):
            if path.name == 'a7z_pcb.stl':
                continue
            comp = path.stem[4:]
            v, f = load_stl(path)
            key = f'head_pi_a7z_{comp}'
            parts[key] = {'key': key, 'name': A7Z_NAMES.get(comp, comp.replace('_', ' ')), 'color': A7Z_COLORS.get(comp, '#3b3b3b'),
                          'module': parts['pi']['module'], 'status': 'purchased', 'v': v, 'f': f, 'source': str(path)}
        for key, name, color in (('camera_ribbon', 'Camera ribbon, A7Z end (150 mm, 31-pin, contacts towards the board)', '#ff8f00'),
                                 ('antenna', 'AC019 Wi-Fi antenna (FPC sticker, 42 x 11.9 mm) inside the cap roof', '#c9a227'),
                                 ('antenna_coax', 'AC019 antenna cable (50 mm coax)', '#6d6d6d'),
                                 ('antenna_ipex', 'AC019 IPEX plug on the A7Z antenna socket', '#c9c9c9')):
            path = first_existing(world / f'{key}.stl')
            if path:
                v, f = load_stl(path)
                parts[key] = {'key': key, 'name': name, 'color': color, 'module': parts['pi']['module'], 'status': 'purchased',
                              'v': v, 'f': f, 'source': str(path)}

    # New printed and placed parts (print/world/v18-sources.json).
    board = first_existing(world / 'openrb-board-upright.stl')
    cap = first_existing(world / 'head_cap.stl')
    # V1.8 head set: plate-only face with camera lands and pegs, eye trim with the two camera-screw pilots, lower shell
    # without the beak-roof window, and the camera turned 180 deg (connector to -y).
    face = first_existing(world / 'face_panel.stl')
    trim = first_existing(world / 'eye_trim.stl')
    shell = first_existing(world / 'head_bottom.stl')
    # V1.8 jaw: the lower lip pad prints as part of the jaw frame (print/jaw-pad/), so nothing in the beak is glued.
    jaw = first_existing(world / 'jaw_frame.stl')
    camera = first_existing(world / 'camera_board.stl')
    # V1.9 neck: the head-pitch sliding ring lengthened to 4.9 mm so it reaches the ID13 case (print/neck-ring/).
    neck_ring = first_existing(world / 'neck_pitch_ring.stl')
    # V1.8 torso: the rear electronics pack behind the hip-yaw motors (print/rear-pack/) and the BNO085 with its plug
    # standing in the pack's plate slot between the hip-yaw motors. 2026-10-14: the pack cover (rear_pack_cover.stl, kept
    # in print/world for the record) is retired; the rear converter box frame carries the same cover plate (below).
    pack = first_existing(world / 'rear_pack.stl')
    imu = first_existing(world / 'imu_board.stl')
    imu_plug = first_existing(world / 'imu_sh4_receiving.stl')
    if board:
        v, f = decimate(*load_stl(board), 25000, 'openrb_board')
        parts['openrb_board'] = {'key': 'openrb_board', 'name': 'OpenRB-150 (header tails trimmed), upright in the rear pack', 'color': '#2d6fb5',
                                 'module': 'controller', 'status': 'owned', 'v': v, 'f': f, 'source': str(board)}
    if pack:
        v, f = load_stl(pack)
        parts['rear_pack'] = {'key': 'rear_pack', 'name': 'Rear electronics pack (new print)', 'color': parts['head_cap']['color'],
                              'module': 'torso', 'status': 'new-print', 'v': v, 'f': f, 'source': str(pack)}
    # 2026-10-14 rear converter box, layout F (print/back-plate/layout-F/layout_f.json): the frame (cover plate, three-tier box
    # walls, bosses, side windows, the wire notch at the top-wall front edge, USB-C window) and the lid, orange like the pack; the two ROBOTIS XL4015
    # converters lying flat, long axis along y, IN ends -y, OUT ends +y, components to the lid (top tier PCB z 15.1..41.3: #1, 7 V rail to
    # OpenRB J4; middle tier PCB z -13.5..12.7: #2, 5 V Pi lead) and the Adafruit 5991 on its back face at x -50 in the
    # 31.2 mm wide bottom tier (USB-C to +y, screw terminal to -y; the y-mirrored F of 16:23).
    BOX_PARTS = {'rear_frame': ('Rear converter box frame (new print)', 'torso', 'new-print', None),
                 'rear_lid': ('Rear converter box lid (new print)', 'torso', 'new-print', None),
                 'xl4015_top': ('XL4015 #1, 7 V rail set to 7.40 V (OMX-AI kit DC converter), top tier of the rear box', 'controller', 'owned', '#1f3f8f'),
                 'xl4015_mid': ('XL4015 #2, 5.00 V for the Pi (OMX-AI kit DC converter), middle tier of the rear box', 'controller', 'owned', '#1f3f8f'),
                 'pd5991': ('Adafruit 5991 USB-C PD board set to 15 V, bottom tier of the rear box', 'controller', 'purchased', '#26282b')}
    BOX_FILES = {'xl4015_top': 'xl4015_left', 'xl4015_mid': 'xl4015_right'}   # CAD export names: left = top tier, right = middle tier
    for key, (name, module, status, color) in BOX_PARTS.items():
        path = first_existing(world / f'{BOX_FILES.get(key, key)}.stl')
        if path:
            v, f = load_stl(path)
            if len(f) > DECIMATE_OVER:
                v, f = decimate(v, f, 25000, key)
            parts[key] = {'key': key, 'name': name, 'color': color or parts['head_cap']['color'], 'module': module,
                          'status': status, 'v': v, 'f': f, 'source': str(path)}
    # 2026-10-15 battery backpack (D-010, print/back-plate/battery-backpack-20261015/): the swap alternative to the rear converter
    # box on the same four cover screws. Frame and cap print orange; the REV-31-1387 switch rocker-down in the floor pocket, the
    # Tattu 2S 650 upright behind it, the DFR1202 clipped behind the front plate, the battery and feed XT30 joints (plugs 1, 2)
    # with the balance plug, and the two swap plugs (XT30 servo, MR30 A7Z) standing in the pack channel. guide-data
    # 'alternates' names the two sets: never on the robot together, so the gate skips pairs and cables across them.
    BACKPACK_PARTS = {'battery_backpack_frame': ('Battery backpack frame (new print)', 'torso', 'new-print', None),
                      'battery_backpack_cap': ('Battery backpack cap (new print)', 'torso', 'new-print', None),
                      'bp_switch': ('REV-31-1387 XT30 switch, rocker down in the backpack floor', 'controller', 'purchased', '#26282b'),
                      'bp_battery': ('Tattu 2S 650 mAh 75C LiPo, XT30 (listing size 57 x 31 x 12 mm), upright in the backpack', 'controller', 'purchased', '#3a6b35'),
                      'bp_dfr1202': ('DFRobot DFR1202 5 V converter for the A7Z, clipped behind the backpack front plate', 'controller', 'owned', '#1f3f8f'),
                      'bp_plugs': ('Plug 1 (battery to switch, XT30), plug 2 (switch to feed, XT30) and the battery balance plug', 'controller', 'purchased', '#f2c14e'),
                      'bp_swap_plugs': ('Swap plugs in the pack channel: plug 3 (servo, XT30) and plug 4 (A7Z 5 V, MR30)', 'controller', 'purchased', '#f2c14e')}
    for key, (name, module, status, color) in BACKPACK_PARTS.items():
        path = first_existing(world / f'{key}.stl')
        if path:
            v, f = load_stl(path)
            if len(f) > DECIMATE_OVER:
                v, f = decimate(v, f, 25000, key)
            parts[key] = {'key': key, 'name': name, 'color': color or parts['head_cap']['color'], 'module': module,
                          'status': status, 'v': v, 'f': f, 'source': str(path)}
    if cap:
        v, f = load_stl(cap)
        parts['head_cap'].update(v=v, f=f, name='Head cap for the A7Z: V1.9 cap with relieved board rails and two end slots (white)', source=str(cap))
    # V1.9 (print/ext-v19/): speaker retainer and the four neck-bundle wire clips (new prints, orange like the cap), and
    # the speaker and amplifier at their audio-study positions under the cap roof (purchased; the source export's old
    # positions are overridden).
    V19_PRINTS = {'speaker_retainer': ('Speaker retainer frame (new print)', 'electronics'),
                  'clip_torso': ('Torso wire clip (new print)', 'neck'), 'clip_bracket': ('Bracket wire clip (new print)', 'neck'),
                  'clip_head': ('Head wire clip (new print)', 'head'), 'clip_cap': ('Cap wire clip (new print)', 'electronics')}
    for key, (name, module) in V19_PRINTS.items():
        path = first_existing(world / f'{key}.stl')
        if path:
            v, f = load_stl(path)
            parts[key] = {'key': key, 'name': name, 'color': parts['head_cap']['color'], 'module': module, 'status': 'new-print',
                          'v': v, 'f': f, 'source': str(path)}
    if 'clip_cap' in parts:
        parts['clip_cap']['name'] = 'Cap wire clip with the micro HDMI notch (A7Z print, orange)'
    tape = first_existing(world / 'speaker_tape.stl')
    if tape:   # 2026-10-14: a closed loop of foam double-sided tape (two halves) on the collar's 0.6 mm lip ring at the speaker edge (compressed 1 mm tape)
        v, f = load_stl(tape)
        parts['speaker_tape'] = {'key': 'speaker_tape', 'name': 'Foam double-sided tape, two strips making one loop on the collar lip ring (pressed to 0.6 mm)', 'color': '#f2c14e',
                                 'module': 'electronics', 'status': 'purchased', 'v': v, 'f': f, 'source': str(tape)}
    for key, name in (('speaker', 'Speaker CMS-30204-18SP, 30 x 20 x 4 mm: metal grille with seven holes towards the roof, magnet and two solder pads on the back, pads at the amplifier end'),
                      ('amplifier', 'MAX98357A I2S amplifier with five soldered wires and the terminal block')):
        path = first_existing(world / f'{key}.stl')
        if path and key in parts:
            v, f = load_stl(path)
            parts[key].update(v=v, f=f, name=name, source=str(path))
    # 2026-10-15 touch extension (extension-20261015-touch/build_touch_geometry.py): a Seeed XIAO ESP32-S3 on foam tape on
    # the inner left wall of the cap reads five copper-tape pads stuck to the cap's inner face. Its nine wires are soldered
    # to its edge pads (an approved soldering exception, like the amplifier).
    TOUCH = {'touch_xiao_tape': ('Foam double-sided tape under the XIAO, 21 x 17.8 mm, 1 mm pressed to 0.8 mm', '#f2c14e'),
             'touch_xiao': ('Seeed XIAO ESP32-S3 touch readout with nine soldered wires', '#2e5d8a'),
             **{f'touch_pad_{p}': (f'Copper foil tape pad {p.upper()} inside the cap', '#c87533') for p in ('l1', 'r1', 'l2', 'r2', 'm')}}
    for key, (name, color) in TOUCH.items():
        path = first_existing(world / f'{key}.stl')
        if path:
            v, f = load_stl(path)
            parts[key] = {'key': key, 'name': name, 'color': color, 'module': 'electronics', 'status': 'purchased',
                          'v': v, 'f': f, 'source': str(path)}
    for key, path in (('face_panel', face), ('eye_trim', trim), ('head_bottom', shell), ('camera_board', camera),
                      ('imu_board', imu), ('imu_sh4_receiving', imu_plug), ('jaw_frame', jaw), ('neck_pitch_ring', neck_ring)):
        if path:
            v, f = load_stl(path)
            if len(f) > DECIMATE_OVER:
                v, f = decimate(v, f, 25000, key)
            parts[key].update(v=v, f=f, source=str(path))
    # 2026-10-15 A7Z head (print/face-a7z/): the face with four camera bosses and the Radxa Camera 13M 214 with its ribbon stub.
    if face:
        parts['face_panel']['name'] = 'Face panel with four camera bosses (A7Z print, white)'
    if camera:
        parts['camera_board']['name'] = 'Radxa Camera 13M 214 (IMX214), connector edge to the left (+Y), with the first part of its ribbon'
    if jaw:
        parts['jaw_frame'].update(name='Jaw frame with the lower lip (new print)', color=parts['head_bottom']['color'])
    # V1.14 white plate (colour scheme C): the V1.9 cap reprints white and the V2.0 side shells (print/v20-source/) print white (the face panel white). Set last,
    # because the orange prints above take their colour from the source cap.
    WHITE = parts['face_panel']['color']
    if cap:
        parts['head_cap']['color'] = WHITE
    for key, name in (('shell_left', 'Left torso shell, screwed to the pack (V2.0 print, white)'),
                      ('shell_right', 'Right torso shell, screwed to the pack (V2.0 print, white)')):
        path = first_existing(world / f'{key}.stl')
        if path:
            v, f = load_stl(path)
            parts[key].update(v=v, f=f, name=name, color=WHITE, source=str(path))
    for p in parts.values():
        p['v'], p['f'] = orient_outward(p['v'], p['f'])
        v = p['v']
        p['bounds'] = [[round(float(x), 3) for x in v.min(0)], [round(float(x), 3) for x in v.max(0)]]
    return parts


def build_cables(routes: dict) -> tuple[list, dict]:
    R = routes['routes']
    L: dict[str, float] = {}
    cab = []

    def add(cid, label, kind, color, path, frm, to, note='', radius=None, slack=0.0):
        path = [[round(float(x), 1) for x in p] for p in path]
        clean = [path[0]] + [p for a, p in zip(path, path[1:]) if math.dist(a, p) > 1e-6]
        length = polyline_length(clean)
        L[cid] = round(length)
        c = {'id': cid, 'label': label, 'kind': kind, 'color': color, 'path': clean, 'from': frm, 'to': to, 'lengthMM': round(length + slack)}
        if radius:
            c['radius'] = radius
        if note:
            c['note'] = note
        cab.append(c)
        return c

    # The controller links start at their plug mouths: leg links R and L in the two vertical-entry centre ports (plugs
    # point -x into the channel under the converter), neck link N in the +y side port through the wall window (plug points
    # +y, outside the pack). The servos take their power through the OpenRB ports; there is no bypass. R and L loop from
    # their plugs into the open -y bay under the converter (where their spare length lies), come back under the lane
    # entrance and climb the lane between the board's component side and the converter at y 5..7 (risers L x -34.6,
    # R -32.2, ORB -30.2, PI -29.4, UART -28.4; measured board clearance >= 0.8 mm); everything that leaves the pack
    # crosses the plate through its top notch in two rows (upper z 37: R, UART, PI, L; lower z 34.3: N) into the open
    # neck region.
    mouth = {'dxl5': [-40.5, -0.4, -25.2], 'dxl10': [-40.5, -0.4, -20.2], 'dxl12': [-28.55, 22.4, -22.75]}
    for rid, cid, lab, frm, to in (
            ('dxl5', 'dxl-r5', 'Controller link R (180 mm kit cable)', 'OpenRB lower centre port', 'ID5 socket 13 (right hip yaw)'),
            ('dxl10', 'dxl-l10', 'Controller link L (180 mm kit cable)', 'OpenRB upper centre port', 'ID10 socket 13 (left hip yaw)'),
            ('dxl12', 'dxl-n12', 'Controller link N (180 mm kit cable)', 'OpenRB +Y side port, through the pack window', 'ID12 socket 14 (neck pitch)')):
        add(cid, lab, 'dxl', '#6a3df0', [mouth[rid]] + R[rid], frm, to, radius=1.1)

    # Power wires in the rear converter box, layout F (2026-10-14, current_build.servo_rail_7v_20261014; routes.json
    # powerWiresF from print/back-plate/layout-F/wires_F.json). 22 AWG solid pairs, red + black, one centreline per pair.
    # Every terminal in the box is reached through a side window: the wire leaves the terminal sideways, makes one U-loop
    # outside the wall and stays outside the box (no rear lane, no passage: P1 deleted 2026-10-14). The 15 V feed runs from the 5991 terminal
    # (bottom tier, -y window) under the step and up the outside of the -y wall to XL4015 #2 IN (middle board, -y), the link
    # outside the -y wall from #2 IN to #1 IN (top board, -y); the 7 V pair leaves #1 OUT (+y window), climbs the outside of the +y
    # wall, crosses the box top, drops through the notch in the top-wall front edge and under the shell lip through the
    # cover-top notch into the pack, then along the cover lip to the OpenRB terminal block J4. The OpenRB powers the
    # servos through its DXL ports. lengthMM of each power cable is its cut length (powerWiresF.cutMm).
    pw = routes.get('powerWiresF', {}).get('cutMm', {})
    for cid in ('pw-15v', 'pw-15v-link', 'pw-7v', 'pi-lead'):
        if cid not in pw:
            raise SystemExit(f'routes.json powerWiresF.cutMm lacks {cid}')
        L[f'cut:{cid}'] = pw[cid]
    add('pw-15v', '15 V feed (22 AWG solid, red + black, 5991 → XL4015 #2 IN)', 'power-15v', '#ef6c00', R['pw-15v'],
        'Adafruit 5991 screw terminal (+ / −), bottom tier of the rear box', 'XL4015 #2 IN (+ / −), middle board', radius=1.0,
        note='Out of the 5991 terminal through the −Y window of the bottom tier, under the step and up the outside of the right (−Y) '
             'wall, in through the −Y window of the middle board and into #2 IN; the wire stays outside the box. Two solid wires under '
             'each #2 IN screw (with the link).')['lengthMM'] = pw['pw-15v']
    add('pw-15v-link', '15 V link (22 AWG solid, red + black, XL4015 #2 IN → #1 IN)', 'power-15v', '#ef6c00', R['pw-15v-link'],
        'XL4015 #2 IN (+ / −), under the same screws as the feed', 'XL4015 #1 IN (+ / −), top board', radius=1.0,
        note='Out through the middle −Y window, up the outside of the right (−Y) wall, window to window, in through the top −Y window and into #1 IN.')['lengthMM'] = pw['pw-15v-link']
    add('pw-7v', '7 V servo pair (22 AWG solid, red + black, XL4015 #1 OUT → OpenRB J4)', 'power-7v', '#d32f2f', R['pw-7v'],
        'XL4015 #1 OUT (+ / −), +Y end of the top board in the rear box', 'OpenRB terminal block J4 (+ / −)', radius=1.0,
        note='Out through the top +Y window, up the outside of the left (+Y) wall, across the box top, down through the notch at the '
             'front edge of the box top and under the shell lip through the notch in the cover-plate top edge into the pack, then along '
             'the cover lip and up to J4. One wire per J4 screw.')['lengthMM'] = pw['pw-7v']

    # Bundle: up the pack, over the plate through its top notch, up behind the neck, through the cap notch to the GPIO
    # header. Slack 60 = 39 for the worst neck and head pose (print/ext-v19/checks/route-v19-motion.json: 38.8 mm over the full
    # MJCF joint ranges and the yaw sweep; trained policy 18.5, walking 11.4; lifting the cap needs 17 and happens with the
    # neck at rest) + about 20 for the stripped ends, the jumper-sleeve splice and dressing. The 130 mm service loop of the
    # old cap-notch route is gone with that route (Shawn, 2026-10-13: the 500/600 mm cut was far too long).
    # V1.9 (print/ext-v19/route-v19.json): the three guide cables follow one centreline from the pack notch through the
    # four wire clips to the gather point in front of the Pi header, then their own fan wire to pin 2, 3 or 8. The
    # bundle no longer passes a cap notch: it enters the head through the -y side of the lower shell's floor opening.
    neck = R.get('bundle_neck')
    head = R.get('bundle_head')
    if not neck or not head:
        raise SystemExit('routes.json lacks bundle_neck/bundle_head (neck exterior and head interior bundle routes)')
    # Pi 5 V lead: two jumper chains (30 cm male-female into 30 cm female-female, joint taped) whose bare ends sit under the
    # XL4015 #2 OUT screws (middle board, +y end) in the rear converter box (layout F, 2026-10-14); the female ends go on Pi
    # pins 2 and 6. Route pi-lead: out through the middle +Y window, up the outside of the +y wall in front of the 7 V pair, across
    # the box top and down the same notch (lanes y 8.6 and 10.7), under the shell lip onto the cover lip, along the lip under the
    # shell roof rib, up in front of the rib and out through the head notch to the neck bundle point, then the bundle path.
    add('pi-lead', 'Head 5 V lead (two jumper chains, red + black)', 'power-5v', '#ad1457', R['pi-lead'],
        'XL4015 #2 OUT (+ / −), +Y end of the middle board in the rear box', 'A7Z header pins 2 (5 V) and 6 (GND)')['lengthMM'] = pw['pi-lead']
    add('imu', 'IMU lead (4397 cable, extended)', 'i2c', '#1e88e5', R['imu'], 'BNO085 STEMMA QT socket (plug from above)',
        'A7Z header pins 1, 3, 5, 9', slack=60, radius=0.8)
    add('uart', 'UART link (two jumper wires)', 'uart', '#00897b', R['uart'], 'OpenRB J12 pad 3 (RX) and pad 4 (TX)',
        'A7Z header pins 7 (UART2 TX) and 11 (UART2 RX)', slack=60, radius=0.7)
    L['bundle_neck'] = round(polyline_length(neck))
    L['bundle_head'] = round(polyline_length(head))

    # Neck chain (kit cables). Paths are the middle-conductor centerlines.
    for rid, cid, lab, frm, to in (
            ('ttl-11-12', 'dxl-12-11', 'Neck chain 12 → 11 (100 mm kit cable)', 'ID12 socket 13', 'ID11 socket 14'),
            ('ttl-13-11', 'dxl-11-13', 'Neck chain 11 → 13 (180 mm kit cable)', 'ID11 socket 13', 'ID13 socket 14'),
            ('ttl-14-13', 'dxl-13-14', 'Neck chain 13 → 14 (100 mm kit cable)', 'ID13 socket 13', 'ID14 socket 14'),
            ('ttl-15-14', 'dxl-14-15', 'Neck chain 14 → 15 (180 mm kit cable)', 'ID14 socket 13', 'ID15 socket 13')):
        add(cid, lab, 'dxl', '#6a3df0', R[rid], frm, to, radius=1.1)

    # Leg chains (kit cables), one link per joint pair. Paths are the middle conductors of the neutral routes reviewed on
    # 2026-10-09 (leg_routes.py). Socket numbers are the registered geometric sockets, not IN/OUT.
    for rid, cid, lab, frm, to in (
            ('ttl-05-04', 'dxl-5-4', 'Right leg 5 → 4, hip yaw to hip roll (180 mm kit cable)', 'ID5 socket 14 (hip yaw)', 'ID4 socket 13 (hip roll)'),
            ('ttl-04-03', 'dxl-4-3', 'Right leg 4 → 3, hip roll to hip pitch (100 mm kit cable)', 'ID4 socket 14 (hip roll)', 'ID3 socket 14 (hip pitch)'),
            ('ttl-03-02', 'dxl-3-2', 'Right leg 3 → 2, inside the thigh (180 mm kit cable)', 'ID3 socket 13 (hip pitch)', 'ID2 socket 14 (knee)'),
            ('ttl-02-01', 'dxl-2-1', 'Right leg 2 → 1, knee to ankle (180 mm kit cable)', 'ID2 socket 13 (knee)', 'ID1 socket 13 (ankle)'),
            ('ttl-10-09', 'dxl-10-9', 'Left leg 10 → 9, hip yaw to hip roll (180 mm kit cable)', 'ID10 socket 14 (hip yaw)', 'ID9 socket 14 (hip roll)'),
            ('ttl-09-08', 'dxl-9-8', 'Left leg 9 → 8, hip roll to hip pitch (100 mm kit cable)', 'ID9 socket 13 (hip roll)', 'ID8 socket 13 (hip pitch)'),
            ('ttl-08-07', 'dxl-8-7', 'Left leg 8 → 7, inside the thigh (180 mm kit cable)', 'ID8 socket 14 (hip pitch)', 'ID7 socket 13 (knee)'),
            ('ttl-07-06', 'dxl-7-6', 'Left leg 7 → 6, knee to ankle (180 mm kit cable)', 'ID7 socket 14 (knee)', 'ID6 socket 14 (ankle)')):
        if rid in R:
            add(cid, lab, 'dxl', '#6a3df0', R[rid], frm, to, radius=0.9)

    # Head wiring. The A7Z camera ribbon is drawn as parts (the camera_board stub and camera_ribbon), not as a cable.
    # V1.9 audio: five wires soldered into the amplifier (2026-10-13, no header), each ending in a jumper sleeve on its Pi
    # pin (ground on pin 34), and the two speaker leads into the amplifier terminal block (radius 0.65).
    for rid, cid, lab, frm, to in (
            ('audio_amp_lrc_pin35', 'amp-lrc', 'Amplifier LRC to A7Z pin 35 (soldered wire)', 'Amplifier LRC hole (soldered)', 'A7Z header pin 35 (I2S0 LRCK)'),
            ('audio_amp_bclk_pin12', 'amp-bclk', 'Amplifier BCLK to A7Z pin 12 (soldered wire)', 'Amplifier BCLK hole (soldered)', 'A7Z header pin 12 (I2S0 BCLK)'),
            ('audio_amp_din_pin40', 'amp-din', 'Amplifier DIN to A7Z pin 40 (soldered wire)', 'Amplifier DIN hole (soldered)', 'A7Z header pin 40 (I2S0 DOUT0)'),
            ('audio_amp_gnd_pin39', 'amp-gnd', 'Amplifier GND to A7Z pin 39 (soldered wire)', 'Amplifier GND hole (soldered)', 'A7Z header pin 39 (GND)'),
            ('audio_amp_vin_pin04', 'amp-vin', 'Amplifier Vin to A7Z pin 4 (soldered wire)', 'Amplifier Vin hole (soldered)', 'A7Z header pin 4 (5 V)')):
        add(cid, lab, 'i2s', '#8e24aa', R[rid], frm, to, radius=0.65)
    # Touch extension: five pad leads from the copper pads to XIAO touch pins and four leads from XIAO edge pads to the A7Z,
    # all soldered at the XIAO; the pad leads are soldered to the copper, the A7Z leads end in a jumper plug.
    TOUCH_WIRES = [(f'touch_pad_{p}', f'touch-{p}', f'Touch pad {p.upper()} lead (soldered both ends)', f'Copper pad {p.upper()} (soldered)', f'XIAO {pin} edge pad (soldered)')
                   for p, pin in (('l1', 'D0'), ('r1', 'D1'), ('l2', 'D2'), ('r2', 'D3'), ('m', 'D8'))]
    TOUCH_WIRES += [(f'touch_a7z_pin{n}', f'touch-pin{n}', f'XIAO {sig} to A7Z pin {n} (soldered at the XIAO)', f'XIAO {sig} edge pad (soldered)', f'A7Z header pin {n} ({what})')
                    for n, sig, what in ((17, '3V3', '3.3 V'), (25, 'GND', 'GND'), (29, 'D5 (SCL)', 'I2C SCL, PB2'), (31, 'D4 (SDA)', 'I2C SDA, PB3'))]
    for rid, cid, lab, frm, to in TOUCH_WIRES:
        if rid in R:
            add(cid, lab, 'touch', '#c87533', R[rid], frm, to, radius=0.65)
    add('spk-plus', 'Speaker + lead', 'speaker', '#5d4037', R['audio_spk_plus'], 'Speaker + pad', 'Amplifier terminal +', radius=0.65)
    add('spk-minus', 'Speaker - lead', 'speaker', '#5d4037', R['audio_spk_minus'], 'Speaker - pad', 'Amplifier terminal -', radius=0.65)
    return cab, L


ALTERNATES = [
    {'id': 'bench-box', 'label': 'Rear converter box (USB-C bench supply, D-007)',
     'parts': ['rear_frame', 'rear_lid', 'xl4015_top', 'xl4015_mid', 'pd5991'],
     'cables': ['pw-15v', 'pw-15v-link', 'pw-7v', 'pi-lead']},
    {'id': 'battery-backpack', 'label': 'Battery backpack (2S LiPo, D-010)',
     'parts': ['battery_backpack_frame', 'battery_backpack_cap', 'bp_switch', 'bp_battery', 'bp_dfr1202', 'bp_plugs', 'bp_swap_plugs'],
     'cables': []},
]


def main() -> None:
    routes = json.loads((HERE / 'routes.json').read_text())
    parts = build_parts()
    cables, lengths = build_cables(routes)
    ctx = Ctx(parts, lengths)
    chapters, steps, legend = content.build(ctx)
    screws, screw_problems = attach_screws(parts, steps)

    out_parts = []
    for p in parts.values():
        v = p['v'].astype(np.float32)
        f = p['f'].astype(np.uint32)
        out_parts.append({'key': p['key'], 'name': p['name'], 'color': p['color'], 'module': p['module'], 'status': p['status'],
                          **({'kit': p['kit']} if p.get('kit') else {}),
                          'positionB64': base64.b64encode(v.astype('<f4').tobytes()).decode(),
                          'indexB64': base64.b64encode(f.astype('<u4').tobytes()).decode(),
                          **({'shiftMm': p['shiftMm']} if p.get('shiftMm') else {}),
                          'bounds': p['bounds']})
    data = {
        'schemaVersion': 1,
        'title': 'MicroDuck build guide: torso, neck, head and wiring',
        'subtitle': 'USB-C powered build: 15 V from an Adafruit 5991, 7.4 V (the 7 V rail) for the servos and 5.0 V for the Pi from two XL4015 converters stacked in a rear converter box, the OpenRB-150 in a printed rear pack behind the hip motors, BNO085 on its front rib, Radxa Cubie A7Z with the Radxa Camera 13M 214, speaker and amplifier in the head, neck bundle in four wire clips; chapter 11 swaps in the 2S battery backpack',
        'revision': 'guide-20261015-backpack',
        'units': 'mm',
        'frame': 'x forward, y left, z up',
        'parts': out_parts,
        'chapters': chapters,
        'steps': steps,
        'cables': cables,
        'screws': screws,
        'legend': legend,
        # Swap alternatives: never on the robot together. The print gate (pairs.py, cables.py) skips part pairs and
        # cable-part pairs across two sets; steps.py removes one set in the swap step.
        'alternates': [a for a in ALTERNATES if all(k in parts for k in a['parts'])],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, separators=(',', ':')))
    tri = sum(len(p['f']) for p in parts.values())
    print(json.dumps({'out': str(OUT), 'parts': len(out_parts), 'triangles': tri, 'chapters': len(chapters), 'steps': len(steps),
                      'cables': len(cables), 'screws': len(screws), 'screwProblems': screw_problems,
                      'bytes': OUT.stat().st_size, 'lengths': lengths,
                      'sources': {k: p.get('source') for k, p in parts.items() if p.get('source')}}, indent=1))


if __name__ == '__main__':
    main()
