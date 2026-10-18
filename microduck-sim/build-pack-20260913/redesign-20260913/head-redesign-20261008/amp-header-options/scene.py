"""Shared scene loader for the amp-header study (read-only on guide sources).

Closed audit solids come from the interference-audit cache (ia_lib.CACHE, built by build_solids.py from the current
guide); parts without a cached solid use the guide display mesh. Pi GPIO jumper ends and header pins use guide meshes.
"""
import os, sys, json, pickle
from pathlib import Path
import numpy as np, trimesh
SIM = Path('/Users/xiangzheng/code/robotics/microduck-sim')
os.environ.setdefault('IA_CACHE', '/private/tmp/claude-501/-Users-xiangzheng-code-robotics/'
                      '92b86901-7748-4ca5-958b-34f6db4ff94e/scratchpad/ia-cache')
sys.path.insert(0, str(SIM / 'guide/content/interference-audit'))
import ia_lib
SCRATCH = Path('/private/tmp/claude-501/-Users-xiangzheng-code-robotics/e1201872-a289-4416-aa82-66a41855cb2b/scratchpad/amphdr')
NB = SCRATCH / 'nb.pkl'
JAW_AXIS_POINT = np.array([26.1, 0.0, 118.62])   # whatif.py: mouth_sliding_ring centre; axis +y
JAW_MOVING = ['jaw_frame', 'lower_pad']
STATIC = ['head_cap', 'jaw_support', 'motor15', 'speaker', 'speaker_cradle', 'speaker_keeper', 'pi', 'camera_board',
          'face_panel', 'head_bottom', 'mouth_sliding_ring', 'upper_pad', 'head_yaw_link', 'motor13', 'eye_trim']


def rot_y(deg, p=JAW_AXIS_POINT):
    t = np.radians(deg)
    R = np.array([[np.cos(t), 0, np.sin(t)], [0, 1, 0], [-np.sin(t), 0, np.cos(t)]])
    M = np.eye(4); M[:3, :3] = R; M[:3, 3] = p - R @ p
    return M


def load():
    nb = pickle.load(open(NB, 'rb'))
    meshes, src = {}, {}
    for k in STATIC + JAW_MOVING + ['amplifier']:
        try:
            v, f = ia_lib.load_solid(k); src[k] = 'audit solid cache'
        except Exception:
            if k not in nb['parts']:
                continue
            v, f = nb['parts'][k]['v'], nb['parts'][k]['f']; src[k] = 'guide display mesh'
        meshes[k] = trimesh.Trimesh(v, f, process=False)
    for k, p in nb['parts'].items():
        if k.startswith('head_pi_') and k not in meshes:
            meshes[k] = trimesh.Trimesh(p['v'], p['f'], process=False); src[k] = 'guide display mesh'
    return meshes, src, nb
