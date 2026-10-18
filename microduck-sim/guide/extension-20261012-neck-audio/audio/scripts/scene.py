"""Shared scene loader for the head-audio extension study (read-only on the V1.8 design).

Loads the closed audit solids that ia_lib/build_solids.py cached (robot frame, mm, x forward, y left, z up). The head
parts in that cache are the V1.8 print/world STLs; the Pi group carries PI_SHIFT [-4.6, 0, 1.0] as in guide-data.json.
Set IA_CACHE to the solid cache directory (default: the cache of the last full audit run).
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
STUDY = HERE.parent
SIM = STUDY.parents[2]
IA = SIM / 'guide' / 'content' / 'interference-audit'
os.environ.setdefault('IA_CACHE', '/private/tmp/claude-501/-Users-xiangzheng-code-robotics/'
                                  '92b86901-7748-4ca5-958b-34f6db4ff94e/scratchpad/ia-cache')
sys.path.insert(0, str(IA))
import ia_lib  # noqa: E402

HEAD_KEYS_FIXED = ['head_bottom', 'face_panel', 'eye_trim', 'camera_board', 'motor15', 'jaw_support',
                   'mouth_sliding_ring', 'motor13', 'motor14', 'head_yaw_link', 'head_roll_ring_a', 'head_roll_ring_b',
                   'neck_pitch_ring', 'neck_pitch']
JAW_PIVOT = np.array([26.1, 0.0, 118.6146])


def manifest():
    return ia_lib.manifest()


def pi_group_keys(man=None):
    man = man or manifest()
    return sorted(k for k in man if k == 'pi' or k.startswith('head_pi_'))


def housing_keys(man=None):
    return [k for k in pi_group_keys(man) if k.endswith('_receiving')]


def load_tm(key):
    import trimesh
    v, f = ia_lib.load_solid(key)
    return trimesh.Trimesh(v, f, process=False)


def load_man(key):
    v, f = ia_lib.load_solid(key)
    return ia_lib.to_manifold(v, f)


def rot_y(deg, about=JAW_PIVOT):
    """4x4 rotation about +y through `about` (jaw opening is positive about +y: the lip swings down)."""
    a = np.radians(deg)
    c, s = np.cos(a), np.sin(a)
    R = np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])
    T = np.eye(4)
    T[:3, :3] = R
    T[:3, 3] = about - R @ about
    return T
