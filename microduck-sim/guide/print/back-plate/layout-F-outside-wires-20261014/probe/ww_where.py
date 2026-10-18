import json, numpy as np
from scipy.spatial import cKDTree
W = json.loads(open('wires_F.json').read())
def rs(p, step=0.25):
    s = np.r_[0, np.cumsum(np.linalg.norm(np.diff(p, axis=0), axis=1))]; t = np.arange(0, s[-1], step)
    return np.c_[[np.interp(t, s, p[:, i]) for i in range(3)]].T
P = {k: rs(np.array(v['points'])) for k, v in W.items()}
for a, b in (('5V_a', '5V_b'), ('7V_a', '7V_b'), ('7V_b', '5V_a')):
    d, j = cKDTree(P[b]).query(P[a]); i = int(np.argmin(d)); print(a, b, round(float(d[i] - 1.8), 2), np.round(P[a][i], 1), np.round(P[b][j[i]], 1))
