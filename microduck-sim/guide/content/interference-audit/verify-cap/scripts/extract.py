"""Extract head-region meshes (robot frame, mm) from the guide data and the full-resolution CAD export.

Writes guide-head.npz and source-head.npz plus extract-report.json in this folder.
"""
import base64, json, sys, gc, hashlib
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = Path('/Users/xiangzheng/code/robotics/microduck-sim')
GUIDE = ROOT / 'guide/data/guide-data.json'
SRC = ROOT / 'guide/data/sources/full-build-data-current.json'
LO = np.array([-45.0, -60.0, 95.0]); HI = np.array([105.0, 60.0, 170.0])


def decode(p):
    v = np.frombuffer(base64.b64decode(p['positionB64']), '<f4').reshape(-1, 3).astype(np.float64)
    f = np.frombuffer(base64.b64decode(p['indexB64']), '<u4').reshape(-1, 3).astype(np.int64)
    return v, f


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as fh:
        for b in iter(lambda: fh.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def grab(path, tag):
    d = json.loads(path.read_text())
    arrays, meta = {}, {}
    for p in d['parts']:
        v, f = decode(p)
        lo, hi = v.min(0), v.max(0)
        if np.any(hi < LO) or np.any(lo > HI):
            continue
        k = p['key']
        arrays[k + '__v'] = v; arrays[k + '__f'] = f
        meta[k] = dict(faces=int(len(f)), verts=int(len(v)), lo=lo.round(3).tolist(), hi=hi.round(3).tolist(),
                       module=p.get('module', p.get('moduleId')), name=p.get('name'))
    del d; gc.collect()
    np.savez_compressed(HERE / f'{tag}-head.npz', **arrays)
    return meta


rep = {'guide': {'path': str(GUIDE), 'sha256': sha(GUIDE)}, 'source': {'path': str(SRC), 'sha256': sha(SRC)}}
rep['guide']['parts'] = grab(GUIDE, 'guide')
gc.collect()
rep['source']['parts'] = grab(SRC, 'source')
json.dump(rep, open(HERE / 'extract-report.json', 'w'), indent=1)
print('guide parts', len(rep['guide']['parts']), 'source parts', len(rep['source']['parts']))
import resource
print('maxrss MiB', resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 2**20)
