"""Shared helpers for the MicroDuck V1.6 guide interference audit (read-only on guide sources).

Solid library: one audit solid per guide part key, in the robot frame (mm, x forward, y left, z up),
cached as .npz under CACHE. Each record says where the solid came from and whether it is a closed,
consistently wound volume (manifold3d accepts it), which is what an exact boolean needs.
"""
from __future__ import annotations

import base64
import json
import os
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
GUIDE = HERE.parents[1]
SIM = GUIDE.parent
GUIDE_DATA = GUIDE / 'data' / 'guide-data.json'
SRC = GUIDE / 'data' / 'sources' / 'full-build-data-current.json'
FINAL = GUIDE / 'print' / 'release-V1.6-final' / 'final-V1.6.json'
WORLD = GUIDE / 'print' / 'world'
CACHE = Path(os.environ.get('IA_CACHE', '/private/tmp/claude-501/-Users-xiangzheng-code-robotics/'
                                         '92b86901-7748-4ca5-958b-34f6db4ff94e/scratchpad/ia-cache'))
CACHE.mkdir(parents=True, exist_ok=True)

V16_KEY = {'jaw_support_original': 'jaw_support', 'neck_pitch_integrated_1mm_seats': 'neck_pitch'}

# Guide keys whose current geometry is a print/world file (build_guide_data.py loads these the same way). The V1.6
# release files of the same name are superseded: V1.7 tray and board, V1.8 head set (print/world/v18-sources.json).
WORLD_FILE = {'openrb_board': 'openrb-board-upright.stl', 'head_cap': 'head_cap.stl',
              'face_panel': 'face_panel.stl', 'eye_trim': 'eye_trim.stl', 'head_bottom': 'head_bottom.stl',
              'camera_board': 'camera_board.stl',
              # V1.8 torso: the rear electronics pack and its cover, the OpenRB-150 standing upright in the pack, and the
              # BNO085 with its SH4 plug turned onto the pack's front plate (print/world/v18-sources.json). The V1.7 tray
              # (openrb_tray.stl) is retired with the pack.
              'rear_pack': 'rear_pack.stl', 'rear_pack_cover': 'rear_pack_cover.stl',
              'imu_board': 'imu_board.stl', 'imu_sh4_receiving': 'imu_sh4_receiving.stl',
              # V1.8 jaw: the 10/1 jaw frame with the lower lip pad printed as part of it (print/jaw-pad/).
              'jaw_frame': 'jaw_frame.stl',
              # V1.9 neck: the head-pitch sliding ring lengthened to 4.9 mm (print/neck-ring/).
              'neck_pitch_ring': 'neck_pitch_ring.stl',
              # V1.9 head cap set and neck route (print/ext-v19/): the V1.9 cap replaces head_cap.stl above; the speaker
              # retainer and the four wire clips are new prints; the speaker and amplifier are purchased parts at their
              # audio-study positions (not the full-build source positions). The V1.9 rear pack replaces rear_pack.stl.
              'speaker_retainer': 'speaker_retainer.stl', 'clip_torso': 'clip_torso.stl', 'clip_bracket': 'clip_bracket.stl',
              'clip_head': 'clip_head.stl', 'clip_cap': 'clip_cap.stl', 'speaker_tape': 'speaker_tape.stl', 'speaker': 'speaker.stl', 'amplifier': 'amplifier.stl',
              # 2026-10-14 rear converter box, layout F (print/back-plate/layout-F/, V1.11; replaced layout C revision 2): the
              # frame and lid replace the pack cover as current parts; xl4015_left is the top-tier XL4015 (7 V), xl4015_right
              # the middle-tier one (5 V), and the Adafruit 5991 sits in the narrow bottom tier.
              'rear_frame': 'rear_frame.stl', 'rear_lid': 'rear_lid.stl', 'xl4015_left': 'xl4015_left.stl',
              'xl4015_right': 'xl4015_right.stl', 'pd5991': 'pd5991.stl',
              # 2026-10-14 V1.12 (print/v20-source/): the white V2.0 side shells, screwed to the V1.9 pack shoulder bars, with
              # the cross tunnel filled and seven horn-screw counterbores; head_cap.stl above is the V2.0 cap (M2 x 8 pilots).
              'shell_left': 'shell_left.stl', 'shell_right': 'shell_right.stl',
              # 2026-10-15 Radxa Cubie A7Z head (print/a7z-head/, print/face-a7z/): the board ('pi' key kept for the head
              # computer), its components, the AC019 antenna with coax and plug, and the A7Z end of the camera ribbon; head_cap,
              # clip_cap, face_panel and camera_board above now hold the A7Z versions.
              'pi': 'a7z_pcb.stl', 'camera_ribbon': 'camera_ribbon.stl', 'antenna': 'antenna.stl',
              'antenna_coax': 'antenna_coax.stl', 'antenna_ipex': 'antenna_ipex.stl',
              # 2026-10-15 battery backpack (D-010, print/back-plate/battery-backpack-20261015/to_guide_world.py): an alternative
              # to the rear converter box on the same four cover screws; guide-data.json 'alternates' keeps the two apart.
              'battery_backpack_frame': 'battery_backpack_frame.stl', 'battery_backpack_cap': 'battery_backpack_cap.stl',
              'bp_switch': 'bp_switch.stl', 'bp_battery': 'bp_battery.stl', 'bp_dfr1202': 'bp_dfr1202.stl',
              'bp_plugs': 'bp_plugs.stl', 'bp_swap_plugs': 'bp_swap_plugs.stl',
              **{f'head_pi_a7z_{p.stem[4:]}': p.name for p in sorted(WORLD.glob('a7z_*.stl')) if p.name != 'a7z_pcb.stl'}}


def decode_guide_part(p: dict) -> tuple[np.ndarray, np.ndarray]:
    """guide-data.json writes float32 positions and uint32 indices (build_guide_data.b64; viewer reads Uint32Array)."""
    v = np.frombuffer(base64.b64decode(p['positionB64']), '<f4').reshape(-1, 3).astype(np.float64)
    f = np.frombuffer(base64.b64decode(p['indexB64']), '<u4').reshape(-1, 3).astype(np.int64)
    return v, f


def load_guide() -> dict:
    return json.loads(GUIDE_DATA.read_text())


def alternate_of(g: dict) -> dict:
    """Part key or cable id -> its swap-alternative set id (guide-data.json 'alternates': sets never on the robot together)."""
    out = {}
    for alt in g.get('alternates', []):
        for k in alt['parts'] + alt.get('cables', []):
            out[k] = alt['id']
    return out


def apart(alt: dict, a: str, b: str) -> bool:
    """True when a and b (part keys or cable ids) belong to different swap alternatives, so they never meet."""
    return a in alt and b in alt and alt[a] != alt[b]


def solid_path(key: str) -> Path:
    return CACHE / f'solid-{key}.npz'


def load_solid(key: str):
    z = np.load(solid_path(key), allow_pickle=False)
    return z['v'], z['f']


def manifest() -> dict:
    return json.loads((CACHE / 'solids-manifest.json').read_text())


def to_manifold(v: np.ndarray, f: np.ndarray):
    import manifold3d as m3
    mesh = m3.Mesh(vert_properties=np.ascontiguousarray(v, dtype=np.float32),
                   tri_verts=np.ascontiguousarray(f, dtype=np.uint32))
    man = m3.Manifold(mesh)
    return man


def manifold_ok(man) -> bool:
    import manifold3d as m3
    return man.status() == m3.Error.NoError and not man.is_empty()


def from_manifold(man) -> tuple[np.ndarray, np.ndarray]:
    mm = man.to_mesh()
    return np.asarray(mm.vert_properties)[:, :3].astype(np.float64), np.asarray(mm.tri_verts).astype(np.int64)


def obb_extents(v: np.ndarray) -> np.ndarray:
    """Extents of a PCA-aligned box around points (sorted ascending). The smallest is the overlap thickness."""
    if len(v) < 4:
        return np.zeros(3)
    c = v - v.mean(0)
    _, _, vt = np.linalg.svd(c, full_matrices=False)
    p = c @ vt.T
    return np.sort(p.max(0) - p.min(0))


def aabb_overlap(a, b, pad=0.0) -> bool:
    return all(a[0][i] - pad <= b[1][i] and b[0][i] - pad <= a[1][i] for i in range(3))


def rnd(x, n=2):
    if isinstance(x, (list, tuple, np.ndarray)):
        return [rnd(y, n) for y in x]
    return round(float(x), n)
