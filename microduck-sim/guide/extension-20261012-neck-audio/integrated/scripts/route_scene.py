"""The integrated head scene for routing and checks (head frame = robot frame at q = 0, mm).

Every solid carries a group:
  lower  head parts already on the robot when the cap goes on (lower shell, jaw support, face, trim, camera, motors 14/15,
         mouth ring) and the servo cables inside the head
  cap    parts that ride on the cap and come down with it: the integrated cap, the Pi group (board, components, header,
         the 8 receiving housings of the neck bundle), Pi screws, the audio parts (speaker, retainer, amplifier, amp
         housings, the five audio Pi-end housings on pins 4, 12, 34, 35, 40), the audio wires and screw envelopes
  csi    the camera ribbon (Pi to camera; spans both)
  jaw    jaw frame (swept 0..40 deg about the jaw pivot)
  yaw    yaw body inside the head (motor13, head_yaw_link, both roll rings; swept over head roll -25..+25 deg)
Pin-34 housing: the audio study built pins 4, 12, 14, 35, 40; its recommendation moves ground from pin 14 to pin 34, so
the pin-34 housing is the pin-14 housing moved 10 pitches (-25.4 mm) along y (same row), and the pin-14 jumper is
replaced by the audio study's alt_gnd_pin34 route.
"""
from __future__ import annotations

import json

import manifold3d as m3
import numpy as np
import trimesh

import int_lib as L
from pm_lib import audio_solid, audio_wire_tubes, csi_ribbon_strip, load_stl_man, man_from_tm  # noqa: E402
from check_lib import ROLL_P, rot  # noqa: E402
from scene import JAW_PIVOT, load_man, manifest, pi_group_keys  # noqa: E402

LOWER = ['head_bottom', 'jaw_support', 'face_panel', 'eye_trim', 'camera_board', 'motor14', 'motor15', 'mouth_sliding_ring']
YAWP = ['motor13', 'head_yaw_link', 'head_roll_ring_a', 'head_roll_ring_b']
AUDIO_CAP = ['speaker', 'speaker_retainer', 'amplifier', 'amp_housings', 'amp_screws_envelope', 'speaker_screws_envelope',
             'speaker_leads_envelope', 'pi_housing_pin04', 'pi_housing_pin12', 'pi_housing_pin35', 'pi_housing_pin40']
HEAD_CABLES = ['dxl-11-13', 'dxl-13-14', 'dxl-14-15']
BUNDLE_HOUSINGS = [f'head_pi_gpio_pin_{p:02d}_receiving' for p in (1, 2, 3, 5, 6, 8, 9, 10)]
JAW_SWEEP = np.arange(0.0, 40.0 + 1e-9, 2.0)
ROLL_SWEEP = np.arange(-25.0, 25.0 + 1e-9, 2.5)


def cable_tube(path, r, seg=12):
    p = np.asarray(path, float)
    out = []
    for a, b in zip(p[:-1], p[1:]):
        d = b - a
        Ln = float(np.linalg.norm(d))
        if Ln < 1e-6:
            continue
        z = d / Ln
        x = np.cross(z, [0, 0, 1.0]) if abs(z[2]) < 0.9 else np.cross(z, [1.0, 0, 0])
        x /= np.linalg.norm(x)
        y = np.cross(z, x)
        out.append(m3.Manifold.cylinder(Ln, r, r, seg).transform(np.c_[x, y, z, a]))
        out.append(m3.Manifold.sphere(r, seg).translate(a.tolist()))
    out.append(m3.Manifold.sphere(r, seg).translate(p[-1].tolist()))
    return m3.Manifold.batch_boolean(out, m3.OpType.Add)


def pin34_housing():
    return audio_solid('pi_housing_pin14').translate([0.0, -25.4, 0.0])


def scene(include_bundle_housings=True):
    """dict name -> (manifold, group)."""
    S = {}
    for k in LOWER:
        S[k] = (load_man(k), 'lower')
    S['head_cap_integrated'] = (load_stl_man(L.INTEGRATED_CAP), 'cap')
    for k in pi_group_keys(manifest()):
        if not include_bundle_housings and k in BUNDLE_HOUSINGS:
            continue
        S[k] = (load_man(k), 'cap')
    S['pi_screws'] = (load_stl_man(L.PIM / 'study-solids' / 'A-pi_screws_envelope-world.stl'), 'cap')
    for k in AUDIO_CAP:
        S['audio_' + k] = (audio_solid(k), 'cap')
    S['audio_pi_housing_pin34'] = (pin34_housing(), 'cap')
    for k, M in audio_wire_tubes().items():
        if k == 'audio_wire_amp_gnd_pin14':
            continue
        S[k] = (M, 'cap')
    S['csi_ribbon_strip'] = (csi_ribbon_strip(), 'csi')
    from nr_lib import ia_lib
    g = ia_lib.load_guide()
    for c in g['cables']:
        if c['id'] in HEAD_CABLES:
            S['cable_' + c['id']] = (cable_tube(c['path'], float(c.get('radius') or 0.9)), 'lower')
    S['jaw_frame'] = (load_man('jaw_frame'), 'jaw')
    for k in YAWP:
        S[k] = (load_man(k), 'yaw')
    return S


def jaw_T(deg):
    return rot([0, 1, 0], deg, JAW_PIVOT)


def roll_T(deg):
    return rot([-1, 0, 0], deg, ROLL_P)


def poses(name, M, group):
    """The solid at every sampled pose of its sweep (one pose for rigid head parts)."""
    if group == 'jaw':
        return [M.transform(jaw_T(a)) for a in JAW_SWEEP]
    if group == 'yaw':
        return [M.transform(roll_T(a)) for a in ROLL_SWEEP]
    return [M]
