"""Linear voxel FE of the one-piece jaw_frame for the jaw-bench flex fit (read-only on guide sources).

Mesh: jaw_frame audit solid (robot frame, mm) voxelised at H mm by slicing (manifold3d) and even-odd point tests.
Material: isotropic E=2300 MPa, nu=0.35 (Prusament PLA horizontal specimens, 2.3 GPa). Print Z = robot Z (checked
separately), so sigma_zz is the stress normal to the layers.
BC: nodes with x >= XCLAMP fixed (the hands hold the front of the jaw). Load cases: unit outward force (-y on the -Y
pivot ear/boss patch, +y on the +Y ear patch) over the patches the insertion overlap occupies (jaw-flex.json).
Linear superposition then scales each case to the patch mean displacement the shell forces (4.74 / 1.77 mm, and other
splits). Matrix-free CG with Jacobi preconditioner. Writes jaw-fe.json.
"""
import json
import sys
import time

import numpy as np
import manifold3d as m3
from scipy.sparse.linalg import LinearOperator, cg

sys.path.insert(0, '/Users/xiangzheng/code/robotics/microduck-sim/guide/content/interference-audit')
from ia_lib import load_solid, to_manifold  # noqa: E402

H = float(sys.argv[1]) if len(sys.argv) > 1 else 0.5
XCLAMP = float(sys.argv[2]) if len(sys.argv) > 2 else 66.0
OUT = f'/private/tmp/claude-501/-Users-xiangzheng-code-robotics/92b86901-7748-4ca5-958b-34f6db4ff94e/scratchpad/open-issues/jaw-fe-h{H}-x{XCLAMP:g}.json'
E, NU = 2300.0, 0.35
t0 = time.time()


def log(*a):
    print(f'{time.time() - t0:7.1f}s', *a, flush=True)


jaw = to_manifold(*load_solid('jaw_frame'))
b = jaw.bounding_box()
x0, y0, z0 = b[0] - H, b[1] - H, b[2] - H
nx, ny, nz = int(np.ceil((b[3] - x0) / H)) + 1, int(np.ceil((b[4] - y0) / H)) + 1, int(np.ceil((b[5] - z0) / H)) + 1
xc = x0 + (np.arange(nx) + 0.5) * H
yc = y0 + (np.arange(ny) + 0.5) * H
occ = np.zeros((nx, ny, nz), bool)
XX, YY = np.meshgrid(xc, yc, indexing='ij')
P = np.c_[XX.ravel(), YY.ravel()]
for k in range(nz):
    zc = z0 + (k + 0.5) * H
    cs = jaw.slice(float(zc))
    if cs.is_empty():
        continue
    inside = np.zeros(len(P), bool)
    for poly in cs.to_polygons():
        v = np.asarray(poly, float)
        a, c = v, np.roll(v, -1, axis=0)
        for (ax, ay), (cx, cy) in zip(a, c):
            if ay == cy:
                continue
            m = ((ay > P[:, 1]) != (cy > P[:, 1]))
            xi = ax + (P[m, 1] - ay) * (cx - ax) / (cy - ay)
            idx = np.nonzero(m)[0][P[m, 0] < xi]
            inside[idx] ^= True
    occ[:, :, k] = inside.reshape(nx, ny)
ne = int(occ.sum())
log('voxels', ne, 'volume', round(ne * H ** 3, 1), 'vs solid', round(jaw.volume(), 1))

# nodes
ei, ej, ek = np.nonzero(occ)
corners = np.array([(a, bb, c) for c in (0, 1) for bb in (0, 1) for a in (0, 1)])  # local node n = a + 2b + 4c
gi = (ei[:, None] + corners[:, 0]) * (ny + 1) * (nz + 1) + (ej[:, None] + corners[:, 1]) * (nz + 1) + (ek[:, None] + corners[:, 2])
uniq, inv = np.unique(gi.ravel(), return_inverse=True)
enodes = inv.reshape(ne, 8)
nn = len(uniq)
ni = uniq // ((ny + 1) * (nz + 1)); nj = (uniq // (nz + 1)) % (ny + 1); nk = uniq % (nz + 1)
NX, NY, NZ = x0 + ni * H, y0 + nj * H, z0 + nk * H
ndof = 3 * nn
edofs = (3 * enodes[:, :, None] + np.arange(3)[None, None, :]).reshape(ne, 24)
log('nodes', nn, 'dofs', ndof)

# hex8 stiffness for a cube of side H
D = E / ((1 + NU) * (1 - 2 * NU)) * np.array([
    [1 - NU, NU, NU, 0, 0, 0], [NU, 1 - NU, NU, 0, 0, 0], [NU, NU, 1 - NU, 0, 0, 0],
    [0, 0, 0, (1 - 2 * NU) / 2, 0, 0], [0, 0, 0, 0, (1 - 2 * NU) / 2, 0], [0, 0, 0, 0, 0, (1 - 2 * NU) / 2]])
sg = np.array([-1, 1])[corners]  # node signs


def Bmat(xi):
    dN = np.zeros((8, 3))
    for n in range(8):
        s = sg[n]
        f = (1 + s * xi) / 2
        dN[n, 0] = s[0] / 2 * f[1] * f[2]
        dN[n, 1] = s[1] / 2 * f[0] * f[2]
        dN[n, 2] = s[2] / 2 * f[0] * f[1]
    dN *= 2.0 / H  # d/dx = (2/H) d/dxi
    B = np.zeros((6, 24))
    for n in range(8):
        dx, dy, dz = dN[n]
        B[0, 3 * n] = dx; B[1, 3 * n + 1] = dy; B[2, 3 * n + 2] = dz
        B[3, 3 * n] = dy; B[3, 3 * n + 1] = dx
        B[4, 3 * n + 1] = dz; B[4, 3 * n + 2] = dy
        B[5, 3 * n] = dz; B[5, 3 * n + 2] = dx
    return B


g = 1 / np.sqrt(3)
Ke = np.zeros((24, 24))
for p in corners:
    B = Bmat(np.array([-g, g])[p])
    Ke += B.T @ D @ B * (H / 2) ** 3
B0 = Bmat(np.zeros(3))

fixed_node = NX >= XCLAMP
fixed = np.zeros(ndof, bool)
fixed[(3 * np.nonzero(fixed_node)[0][:, None] + np.arange(3)).ravel()] = True
free = ~fixed
diag = np.bincount(edofs.ravel(), weights=np.tile(np.diag(Ke), ne), minlength=ndof)
diag[fixed] = 1.0


def matvec(u):
    u = np.where(free, u, 0.0)
    f = np.bincount(edofs.ravel(), weights=(u[edofs] @ Ke).ravel(), minlength=ndof)
    return np.where(free, f, u)


A = LinearOperator((ndof, ndof), matvec=matvec, dtype=float)
M = LinearOperator((ndof, ndof), matvec=lambda r: r / diag, dtype=float)

# load patches (jaw-local coordinates of the insertion overlap pieces, jaw-flex.json)
PATCH = {
    'negY': (NX >= 18.0) & (NX <= 34.2) & (NY <= -36.9) & (NY >= -41.8) & (NZ >= 113.0) & (NZ <= 123.3),
    'posY': (NX >= 18.0) & (NX <= 34.2) & (NY >= 39.9) & (NY <= 41.8) & (NZ >= 110.5) & (NZ <= 120.4),
}
res = {'H': H, 'XCLAMP': XCLAMP, 'E': E, 'nu': NU, 'voxels': ne, 'voxelVolume': round(ne * H ** 3, 1), 'solidVolume': round(jaw.volume(), 1),
       'nodes': nn, 'fixedNodes': int(fixed_node.sum()), 'patchNodes': {k: int(v.sum()) for k, v in PATCH.items()}}
U = {}
for name, msk in PATCH.items():
    f = np.zeros(ndof)
    sgn = -1.0 if name == 'negY' else 1.0
    idx = np.nonzero(msk & ~fixed_node)[0]
    f[3 * idx + 1] = sgn * 1.0 / len(idx)  # 1 N total, outward
    it = [0]
    u, info = cg(A, f, M=M, rtol=1e-7, maxiter=40000, callback=lambda xk: it.__setitem__(0, it[0] + 1))
    U[name] = u
    disp = {k: float(np.mean(u[3 * np.nonzero(m)[0] + 1])) for k, m in PATCH.items()}
    res.setdefault('unitCases', {})[name] = {'cgInfo': int(info), 'iterations': it[0], 'patchMeanUy_mm_perN': disp,
                                             'maxAbsU_mm_perN': float(np.abs(u.reshape(-1, 3)).max())}
    log(name, 'cg', info, it[0], disp)
json.dump(res, open(OUT, 'w'), indent=1)

# compliance matrix C[i][j] = mean outward displacement of patch i under unit outward force on patch j
names = ['negY', 'posY']
C = np.array([[abs(res['unitCases'][j]['patchMeanUy_mm_perN'][i]) * (1 if np.sign(res['unitCases'][j]['patchMeanUy_mm_perN'][i]) == (-1 if i == 'negY' else 1) else -1)
               for j in names] for i in names])
res['complianceMmPerN'] = C.tolist()
cent = np.c_[NX[enodes].mean(1), NY[enodes].mean(1), NZ[enodes].mean(1)]


def field(u):
    eps = (u[edofs] @ B0.T)  # ne x 6 (engineering shear)
    T = np.zeros((ne, 3, 3))
    T[:, 0, 0], T[:, 1, 1], T[:, 2, 2] = eps[:, 0], eps[:, 1], eps[:, 2]
    T[:, 0, 1] = T[:, 1, 0] = eps[:, 3] / 2
    T[:, 1, 2] = T[:, 2, 1] = eps[:, 4] / 2
    T[:, 0, 2] = T[:, 2, 0] = eps[:, 5] / 2
    pr = np.linalg.eigvalsh(T)[:, -1]
    sig = eps @ D.T
    vm = np.sqrt(0.5 * ((sig[:, 0] - sig[:, 1]) ** 2 + (sig[:, 1] - sig[:, 2]) ** 2 + (sig[:, 2] - sig[:, 0]) ** 2) + 3 * (sig[:, 3] ** 2 + sig[:, 4] ** 2 + sig[:, 5] ** 2))
    return pr, sig, vm


def summarize(arr, label, unit, scale=1.0):
    k = int(np.argmax(arr))
    # exclude elements touching the load patches and the clamp edge from the peak (point loads / BC singularity)
    near = np.zeros(ne, bool)
    for m in PATCH.values():
        pn = np.zeros(nn, bool); pn[m] = True
        near |= pn[enodes].any(1)
    near |= (cent[:, 0] >= XCLAMP - 2 * H)
    a2 = np.where(near, -np.inf, arr)
    k2 = int(np.argmax(a2))
    return {f'{label}Max{unit}': round(float(arr[k]) * scale, 3), 'at': np.round(cent[k], 1).tolist(),
            f'{label}MaxAwayFromLoadAndClamp{unit}': round(float(a2[k2]) * scale, 3), 'atAway': np.round(cent[k2], 1).tolist(),
            f'{label}P999{unit}': round(float(np.percentile(arr[~near], 99.9)) * scale, 3),
            f'{label}P99{unit}': round(float(np.percentile(arr[~near], 99)) * scale, 3)}


scen = {'guideNominal_4.74_1.77': (4.74, 1.77), 'guideText_5_2': (5.0, 2.0), 'equalised_3.26_3.26': (3.26, 3.26), 'unit_1_0': (1.0, 0.0), 'unit_0_1': (0.0, 1.0)}
for sname, (dn, dp) in scen.items():
    F = np.linalg.solve(C, np.array([dn, dp]))
    u = F[0] * U['negY'] + F[1] * U['posY']
    pr, sig, vm = field(u)
    rec = {'deflectionsMm': [dn, dp], 'forcesN': np.round(F, 2).tolist()}
    rec.update({'principal': summarize(pr, 'strain', 'Pct', 100)})
    rec.update({'sigmaZZ': summarize(sig[:, 2], 'sigmaZZ', 'MPa')})
    rec.update({'vonMises': summarize(vm, 'vm', 'MPa')})
    res.setdefault('scenarios', {})[sname] = rec
    log(sname, rec['forcesN'], rec['principal'], rec['sigmaZZ'])
json.dump(res, open(OUT, 'w'), indent=1)
log('done')
