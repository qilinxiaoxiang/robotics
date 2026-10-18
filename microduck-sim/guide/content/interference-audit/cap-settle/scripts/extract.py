"""Extract head-region meshes (robot frame, mm; x forward, y left, z up) for the cap-settle study.

Inputs (read only):
  guide/data/guide-data.json                    current guide (Pi group already shifted for V1.7, shiftMm per part)
  guide/data/sources/full-build-data-current.json  full-resolution CAD export (Pi group at its V1.6 seat)
Writes:
  $CS_CACHE/guide-head.npz, $CS_CACHE/source-head.npz  (scratch cache, not part of the repository)
  ../extract-report.json                          hashes, per-part bounds, guide shiftMm values
"""
import base64, gc, hashlib, json, os, resource
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
OUTDIR = HERE.parent
ROOT = Path('/Users/xiangzheng/code/robotics/microduck-sim')
GUIDE = ROOT / 'guide/data/guide-data.json'
SRC = ROOT / 'guide/data/sources/full-build-data-current.json'
CACHE = Path(os.environ.get('CS_CACHE', '/private/tmp/claude-501/-Users-xiangzheng-code-robotics/'
                                        '92b86901-7748-4ca5-958b-34f6db4ff94e/scratchpad/cap-settle-cache'))
CACHE.mkdir(parents=True, exist_ok=True)
LO = np.array([-45.0, -60.0, 90.0]); HI = np.array([110.0, 60.0, 175.0])


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
        meta[k] = dict(faces=int(len(f)), lo=lo.round(3).tolist(), hi=hi.round(3).tolist(),
                       shiftMm=p.get('shiftMm'), name=p.get('name'), kit=p.get('kit'))
    extra = {}
    if tag == 'guide':
        extra['screwsInHead'] = [s for s in d.get('screws', []) if 'camera' in json.dumps(s).lower() or 'E-pi' in json.dumps(s)][:20]
    del d; gc.collect()
    np.savez_compressed(CACHE / f'{tag}-head.npz', **arrays)
    return meta, extra


rep = {'guide': {'path': str(GUIDE), 'sha256': sha(GUIDE)}, 'source': {'path': str(SRC), 'sha256': sha(SRC)}, 'cache': str(CACHE)}
rep['guide']['parts'], rep['guide']['extra'] = grab(GUIDE, 'guide')
gc.collect()
rep['source']['parts'], _ = grab(SRC, 'source')
# Pi group: guide position minus source position must equal the recorded shiftMm
chk = {}
for k, m in rep['guide']['parts'].items():
    if m.get('shiftMm') and k in rep['source']['parts']:
        s = rep['source']['parts'][k]
        chk[k] = {'shiftMm': m['shiftMm'], 'boundsDelta': (np.array(m['lo']) - np.array(s['lo'])).round(3).tolist()}
rep['piGroupShiftCheck'] = chk
rep['maxRssMiB'] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 2 ** 20
json.dump(rep, open(OUTDIR / 'extract-report.json', 'w'), indent=1)
print('guide parts', len(rep['guide']['parts']), 'source parts', len(rep['source']['parts']), 'shifted', len(chk))
print('maxrss MiB', rep['maxRssMiB'])
