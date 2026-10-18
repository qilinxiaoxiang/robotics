"""Probe: parts near the rear box region at HOME (guide manifest), bounds clipped to x < -30."""
import sys, json, numpy as np
sys.path.insert(0, '/Users/xiangzheng/code/robotics/microduck-sim/guide/content/interference-audit'); import ia_lib
man = ia_lib.manifest(); rows = {}
for k, rec in man.items():
    lo, hi = np.array(rec['bounds'])
    if lo[0] < -36 and hi[2] > -60:
        v, f = ia_lib.load_solid(k); v = np.asarray(v)
        sel = v[v[:, 0] < -36]
        if len(sel):
            rows[k] = dict(module=rec.get('module'), bounds=np.round(rec['bounds'], 1).tolist(), behindX36=np.round([sel.min(0), sel.max(0)], 1).tolist())
for k, r in sorted(rows.items(), key=lambda kv: kv[1]['behindX36'][0][0]):
    print(k, r['module'], 'all', r['bounds'], 'x<-36', r['behindX36'])
