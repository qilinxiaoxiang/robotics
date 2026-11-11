"""Linear-elastic finite-element check of one printed part (open source: gmsh mesh, scikit-fem P2 tetrahedra, pyamg CG).
Reads out/fea_inputs.json (written by fea_setup.py on the MacBook) and the part STL; writes out/fea_<model>.json and
out/fea_<model>_*.png. Solid isotropic PLA (E 3000 MPa, nu 0.35); the printed-structure correction is applied afterwards
from the hand-calc sections (README).
    (Mac mini) .venv/bin/python strength/fea_run.py <model> [--h 1.6]
Self-contained: no cad/ imports, so it runs in the mirror with only the STLs and the input JSON.
"""
import json
import math
import sys
import time
from pathlib import Path

import numpy as np

H = Path(__file__).resolve().parent
OUT = H / "out"
E, NU = 3000.0, 0.35


def mesh_stl(stl, h):
    import gmsh
    gmsh.initialize()
    gmsh.option.setNumber("General.Terminal", 0)
    gmsh.merge(str(stl))
    gmsh.model.mesh.classifySurfaces(30 * math.pi / 180, True, True, math.pi)
    gmsh.model.mesh.createGeometry()
    surfs = [s[1] for s in gmsh.model.getEntities(2)]
    loop = gmsh.model.geo.addSurfaceLoop(surfs)
    gmsh.model.geo.addVolume([loop])
    gmsh.model.geo.synchronize()
    gmsh.option.setNumber("Mesh.MeshSizeMax", h)
    gmsh.option.setNumber("Mesh.MeshSizeMin", h * 0.35)
    gmsh.option.setNumber("Mesh.MeshSizeFromCurvature", 12)
    gmsh.option.setNumber("Mesh.Algorithm3D", 10)
    gmsh.model.mesh.generate(3)
    _, xyz, _ = gmsh.model.mesh.getNodes()
    tags, coords, _ = gmsh.model.mesh.getNodes()
    idx = {t: i for i, t in enumerate(tags)}
    p = coords.reshape(-1, 3)
    et, en = gmsh.model.mesh.getElementsByType(4)
    t = np.array([idx[n] for n in en]).reshape(-1, 4)
    gmsh.finalize()
    used = np.unique(t)
    remap = -np.ones(len(p), int); remap[used] = np.arange(len(used))
    return p[used], remap[t]


def mesh_voxels(stl, pitch, origin=None):
    """Hexahedral voxel mesh of a watertight STL (exact for the box-built wing plate; staircase on curved faces).
    origin: a point that falls on grid nodes (puts the support and load faces exactly on voxel faces).
    Node order follows skfem.MeshHex: (0,0,0) (1,0,0) (0,1,0) (0,0,1) (1,1,0) (1,0,1) (0,1,1) (1,1,1)."""
    import trimesh
    tm = trimesh.load(stl, force="mesh")
    lo = tm.bounds[0].copy()
    if origin is not None:
        o = np.asarray(origin, float)
        lo = o - pitch * np.ceil((o - lo) / pitch - 1e-9)
    n = np.ceil((tm.bounds[1] - lo) / pitch).astype(int) + 1
    gx, gy, gz = [lo[k] + pitch * (np.arange(n[k]) + 0.5) for k in range(3)]
    # inside test by ray parity along z for every (x, y) column: count crossings below each voxel centre
    occ = np.zeros(n, bool)
    from trimesh.ray.ray_triangle import RayMeshIntersector
    rays = RayMeshIntersector(tm)
    X, Y = np.meshgrid(gx, gy, indexing="ij")
    org = np.c_[X.ravel(), Y.ravel(), np.full(X.size, lo[2] - 1.0)]
    org[:, 0] += 1e-4 * pitch; org[:, 1] += 1.3e-4 * pitch          # avoid hitting edges exactly
    locs, ri, _ = rays.intersects_location(org, np.tile([0, 0, 1.0], (len(org), 1)), multiple_hits=True)
    hits = [[] for _ in range(len(org))]
    for z, r in zip(locs[:, 2], ri):
        hits[r].append(z)
    for r, hz in enumerate(hits):
        if not hz:
            continue
        hz = np.unique(np.round(np.sort(hz), 6))
        i, j = divmod(r, n[1])
        cnt = np.searchsorted(hz, gz)
        occ[i, j, :] = cnt % 2 == 1
    ijk = np.argwhere(occ)
    corners = np.array([(0, 0, 0), (1, 0, 0), (0, 1, 0), (0, 0, 1), (1, 1, 0), (1, 0, 1), (0, 1, 1), (1, 1, 1)])
    allc = (ijk[:, None, :] + corners[None]).reshape(-1, 3)
    key = (allc[:, 0] * (n[1] + 2) + allc[:, 1]) * (n[2] + 2) + allc[:, 2]
    uk, inv = np.unique(key, return_inverse=True)
    t = inv.reshape(-1, 8)
    ci = np.zeros((len(uk), 3), int)
    ci[inv] = allc
    p = lo + pitch * ci
    return p, t


def linear_traction(cent, area, normal, F, M):
    """Traction per facet (centroids, areas, outward normal of the patch) giving resultant F and moment M about the
    patch centroid: normal part linear in (u, v) for the in-plane moments, uniform in-plane part plus a twist."""
    n = np.asarray(normal, float); n /= np.linalg.norm(n)
    e1 = np.cross(n, [0, 0, 1.0]) if abs(n[2]) < 0.9 else np.cross(n, [1.0, 0, 0]); e1 /= np.linalg.norm(e1)
    e2 = np.cross(n, e1)
    A = area.sum()
    c = (cent * area[:, None]).sum(0) / A
    r = cent - c
    u, v = r @ e1, r @ e2
    Iuu, Ivv, Iuv = (area * u * u).sum(), (area * v * v).sum(), (area * u * v).sum()
    F, M = np.asarray(F, float), np.asarray(M, float)
    a, b = np.linalg.solve([[Iuu, Iuv], [Iuv, Ivv]], [M @ np.cross(e1, n), M @ np.cross(e2, n)])
    J = Iuu + Ivv
    tw = (M @ n) / J
    Fn = F @ n
    Fs = F - Fn * n
    t = (Fn / A + a * u + b * v)[:, None] * n + Fs / A + tw * np.cross(n, r)
    return t, c


def main():
    model = sys.argv[1]
    h = float(sys.argv[sys.argv.index("--h") + 1]) if "--h" in sys.argv else 1.6
    cfg = json.loads((OUT / "fea_inputs.json").read_text())[model]
    t0 = time.time()
    import skfem as fe
    from skfem.models.elasticity import lame_parameters, linear_elasticity
    if "--tet" in sys.argv:
        p, t = mesh_stl(H / cfg["stl"], h)
        m = fe.MeshTet(p.T.copy(), t.T.copy())
        e = fe.ElementVector(fe.ElementTetP2())
    else:
        p, t = mesh_voxels(H / cfg["stl"], h, cfg.get("grid_origin"))
        m = fe.MeshHex(p.T.copy(), t.T.copy())
        e = fe.ElementVector(fe.ElementHex1())
    ib = fe.Basis(m, e, intorder=3)
    lam, mu = lame_parameters(E, NU)
    K = fe.asm(linear_elasticity(lam, mu), ib)
    nd = ib.N
    log = dict(nodes=int(p.shape[0]), tets=int(t.shape[0]), dofs=int(nd), h=h, mesh_s=round(time.time() - t0, 1))
    print(log, flush=True)

    # boundary facets: centroid, normal, area
    bf = m.boundary_facets()
    fx = m.p[:, m.facets[:, bf]]                         # 3 x nv x nf
    cen = fx.mean(axis=1).T
    nrm = np.cross((fx[:, 1] - fx[:, 0]).T, (fx[:, 2] - fx[:, 0]).T)
    # any three corners of a square voxel face span half its area, whatever the node order
    area = (1.0 if fx.shape[1] == 4 else 0.5) * np.linalg.norm(nrm, axis=1)
    nrm = nrm / np.maximum(np.linalg.norm(nrm, axis=1), 1e-12)[:, None]
    # orient outward: compare with the vector from the owning tet's centroid
    own = m.f2t[0, bf]
    tc = m.p[:, m.t[:, own]].mean(axis=1).T
    flip = np.einsum("ij,ij->i", nrm, cen - tc) < 0
    nrm[flip] *= -1

    def select(sel):
        ok = np.ones(len(bf), bool)
        for k, (lo, hi) in sel.get("box", {}).items():
            j = "xyz".index(k)
            ok &= (cen[:, j] >= lo) & (cen[:, j] <= hi)
        if "normal" in sel:
            ok &= nrm @ np.asarray(sel["normal"], float) > sel.get("cos", 0.9)
        if "cyl" in sel:            # facets on a cylinder: axis point, axis dir, radius range
            a0, ad, (r0, r1) = np.asarray(sel["cyl"][0]), np.asarray(sel["cyl"][1]) / np.linalg.norm(sel["cyl"][1]), sel["cyl"][2]
            d = cen - a0
            rr = np.linalg.norm(d - np.outer(d @ ad, ad), axis=1)
            ok &= (rr >= r0) & (rr <= r1)
        if "any" in sel:
            ok2 = np.zeros(len(bf), bool)
            for s2 in sel["any"]:
                ok2 |= select(s2)
            ok &= ok2
        return ok

    # fixed dofs
    fixed = np.zeros(len(bf), bool)
    for s in cfg["fixed"]:
        fixed |= select(s)
    fixed_facets = bf[fixed]
    D = ib.get_dofs(facets=fixed_facets).all()
    print("fixed facets", int(fixed.sum()), "dofs", len(D), flush=True)

    # Winkler (normal springs) on selected facets: k (N/mm^3) * (u.n)(v.n), plus a weak tangential spring
    if cfg.get("winkler"):
        from skfem.helpers import dot
        wsel = np.zeros(len(bf), bool)
        for s in cfg["winkler"]["sel"]:
            wsel |= select(s)
        fb = fe.FacetBasis(m, e, facets=bf[wsel], intorder=4)
        kn, kt = cfg["winkler"]["k"], cfg["winkler"].get("kt", cfg["winkler"]["k"] * 1e-3)

        @fe.BilinearForm
        def wink(u, v, w):
            un, vn = dot(u, w.n), dot(v, w.n)
            return kn * un * vn + kt * (dot(u, v) - un * vn)
        K = K + fe.asm(wink, fb)

    # load cases: each a list of patches with (sel, F, M about patch centroid) or a uniform traction "t"
    cases = cfg["cases"]
    from skfem.helpers import dot  # noqa
    RHS, meta = [], {}
    for cname, patches in cases.items():
        f = np.zeros(nd)
        info = []
        for pa in patches:
            s = select(pa["sel"])
            if s.sum() == 0:
                raise SystemExit(f"{model}/{cname}: patch {pa.get('name')} selects no facets")
            if "forces" in pa:          # point loads [(F, P)] carried to the patch centroid as F and M
                c0 = (cen[s] * area[s, None]).sum(0) / area[s].sum()
                Ft = sum(np.asarray(fp[0], float) for fp in pa["forces"])
                Mt = sum(np.cross(np.asarray(fp[1], float) - c0, np.asarray(fp[0], float)) for fp in pa["forces"])
                pa = dict(pa, F=Ft.tolist(), M=Mt.tolist())
            if "t_resultant" in pa:     # uniform traction carrying a resultant (bore friction / bearing)
                c = (cen[s] * area[s, None]).sum(0) / area[s].sum()
                tr = np.tile(np.asarray(pa["t_resultant"], float) / area[s].sum(), (s.sum(), 1))
                pa = dict(pa, F=pa["t_resultant"])
            elif "F" in pa:
                tr, c = linear_traction(cen[s], area[s], pa["normal"], pa["F"], pa.get("M", [0, 0, 0]))
            else:
                tr = np.tile(np.asarray(pa["t"], float), (s.sum(), 1)); c = (cen[s] * area[s, None]).sum(0) / area[s].sum()
            fb = fe.FacetBasis(m, e, facets=bf[s], intorder=3)
            # piecewise-constant traction per facet: interpolate via facet index
            trf = tr.T[:, :, None] * np.ones((1, 1, fb.X.shape[-1]))

            @fe.LinearForm
            def load(v, w):
                return dot(w["tr"], v)
            f += fe.asm(load, fb, tr=trf)
            info.append(dict(name=pa.get("name"), facets=int(s.sum()), area=round(float(area[s].sum()), 1), centroid=np.round(c, 2).tolist(),
                             F=pa.get("F"), M=pa.get("M")))
        RHS.append(f); meta[cname] = info

    # solve with pyamg-preconditioned CG (near-nullspace = rigid modes)
    import pyamg
    from scipy.sparse.linalg import cg
    I = ib.complement_dofs(D)
    Kii = K[I][:, I].tocsr()
    xy = ib.doflocs[:, I]
    B = np.zeros((len(I), 6))
    cmp_all = np.zeros(nd, int)
    for k, ix in enumerate(ib.split_indices()):
        cmp_all[ix] = k
    cmp_i = cmp_all[I]
    for k in range(3):
        B[cmp_i == k, k] = 1.0
    X, Y, Z = xy
    B[cmp_i == 1, 3] = -Z[cmp_i == 1]; B[cmp_i == 2, 3] = Y[cmp_i == 2]
    B[cmp_i == 0, 4] = Z[cmp_i == 0]; B[cmp_i == 2, 4] = -X[cmp_i == 2]
    B[cmp_i == 0, 5] = -Y[cmp_i == 0]; B[cmp_i == 1, 5] = X[cmp_i == 1]
    ml = pyamg.smoothed_aggregation_solver(Kii, B=B, max_coarse=500)
    Mpre = ml.aspreconditioner()
    results = {}
    import skfem.helpers as hp
    from skfem import ElementTetDG, ElementTetP1
    for (cname, patches), f in zip(cases.items(), RHS):
        ts = time.time()
        x = np.zeros(nd)
        xi, info = cg(Kii, f[I], rtol=1e-8, maxiter=4000, M=Mpre)
        x[I] = xi
        # stresses at element quadrature points -> per-element max von Mises and max principal
        from skfem.helpers import sym_grad, ddot, eye, trace
        uq = ib.interpolate(x)
        epsq = sym_grad(uq)
        tr_ = trace(epsq)
        sig = 2 * mu * epsq + lam * eye(tr_, 3)
        s = np.moveaxis(np.moveaxis(sig, 0, -1), 0, -1)          # nel x nq x 3 x 3
        w = np.linalg.eigvalsh(s)
        s1 = w[..., -1]; s3 = w[..., 0]
        dev = s - np.trace(s, axis1=-2, axis2=-1)[..., None, None] / 3 * np.eye(3)
        vm = np.sqrt(1.5 * np.einsum("...ij,...ij->...", dev, dev))
        el_vm, el_s1, el_s3 = vm.max(axis=1), s1.max(axis=1), s3.min(axis=1)
        ec = m.p[:, m.t].mean(axis=1).T
        # ignore the elements touching the fixed facets and load patches (singular at a fixed edge) for the peak
        near = np.zeros(m.t.shape[1], bool)
        excl_pts = cen[fixed]
        for pa in patches:
            excl_pts = np.vstack([excl_pts, cen[select(pa["sel"])]])
        from scipy.spatial import cKDTree
        dmin, _ = cKDTree(excl_pts).query(ec)
        near = dmin < cfg.get("exclude_mm", 2.5)
        res = dict(cg_info=int(info), solve_s=round(time.time() - ts, 1))
        for lab, v in (("von_mises", el_vm), ("max_principal", el_s1), ("min_principal", el_s3)):
            vv = np.where(near, 0.0, np.abs(v) if lab == "min_principal" else v)
            i = int(np.argmax(vv)); i_all = int(np.argmax(np.abs(v)))
            res[lab] = dict(peak=round(float(vv[i]), 2), at=np.round(ec[i], 1).tolist(),
                            peak_incl_supports=round(float(np.abs(v[i_all])), 2), at_incl=np.round(ec[i_all], 1).tolist())
        # region peaks (boxes named in the config)
        for rn, box in cfg.get("regions", {}).items():
            ok = np.ones(len(ec), bool)
            for k, (lo, hi) in box.items():
                j = "xyz".index(k); ok &= (ec[:, j] >= lo) & (ec[:, j] <= hi)
            ok &= ~near
            if ok.any():
                j = np.argmax(np.where(ok, el_s1, -1e9)); jv = np.argmax(np.where(ok, el_vm, -1e9))
                res.setdefault("regions", {})[rn] = dict(max_principal=round(float(el_s1[j]), 2), at=np.round(ec[j], 1).tolist(),
                                                         von_mises=round(float(el_vm[jv]), 2), vm_at=np.round(ec[jv], 1).tolist())
        # section slabs: normal stress on a cut plane (element centres within half a cell), its peak and its moment
        # resultants (equilibrium check against the applied loads) -- the like-for-like comparison with hand_calcs
        if cfg.get("sections"):
            sc = np.einsum("enij->eij", s) / s.shape[1]       # element-mean stress tensor
            for sn in cfg["sections"]:
                ax = "xyz".index(sn["axis"])
                for v0 in sn["at"]:
                    layer = ec[np.argmin(np.abs(ec[:, ax] - v0)), ax]          # the voxel layer nearest the cut
                    sel = np.abs(ec[:, ax] - layer) < 1e-3
                    if sn.get("box"):
                        for k, (lo, hi) in sn["box"].items():
                            j = "xyz".index(k); sel &= (ec[:, j] >= lo) & (ec[:, j] <= hi)
                    if not sel.any():
                        continue
                    snn = sc[sel, ax, ax]
                    dA = h * h
                    others = [k for k in range(3) if k != ax]
                    c = ec[sel]
                    Fn = float(snn.sum() * dA)
                    Ma = float((snn * c[:, others[0]]).sum() * dA)   # first moments (about the global origin)
                    Mb = float((snn * c[:, others[1]]).sum() * dA)
                    i = int(np.argmax(np.abs(snn)))
                    # shear on the cut and von Mises of the element-mean tensor: the torsion the hand model carries as tau
                    ss = sc[sel]
                    tau = np.hypot(ss[:, ax, others[0]], ss[:, ax, others[1]])
                    dv = ss - np.trace(ss, axis1=1, axis2=2)[:, None, None] / 3 * np.eye(3)
                    vmc = np.sqrt(1.5 * np.einsum("eij,eij->e", dv, dv))
                    # same, without the cells within exclude_mm of supports and load patches (the corner/patch peaks)
                    far = ~near[sel]
                    jt, jv = int(np.argmax(tau)), int(np.argmax(vmc))
                    jvf = int(np.argmax(np.where(far, vmc, -1.0))) if far.any() else jv
                    Mt = float((ss[:, ax, others[1]] * (c[:, others[0]] - c[:, others[0]].mean())
                                - ss[:, ax, others[0]] * (c[:, others[1]] - c[:, others[1]].mean())).sum() * dA)
                    res.setdefault("sections", []).append(dict(axis=sn["axis"], at=v0, sigma_nn_peak=round(float(abs(snn[i])), 2),
                                                               where=np.round(c[i], 1).tolist(), N=round(Fn, 2),
                                                               tau_peak=round(float(tau[jt]), 2), tau_where=np.round(c[jt], 1).tolist(),
                                                               vm_peak=round(float(vmc[jv]), 2), vm_where=np.round(c[jv], 1).tolist(),
                                                               vm_peak_far=round(float(vmc[jvf]), 2), vm_far_where=np.round(c[jvf], 1).tolist(),
                                                               torque_about_centroid=round(Mt, 1),
                                                               first_moments=[round(Ma, 1), round(Mb, 1)], cells=int(sel.sum())))
        # displacements at probe points (stiffness)
        for pn, pt in cfg.get("probes", {}).items():
            dl = ib.doflocs
            k = np.argmin(np.linalg.norm(dl.T - np.asarray(pt), axis=1))
            loc = dl[:, k]
            same = np.where(np.linalg.norm(dl.T - loc, axis=1) < 1e-9)[0]
            uvec = np.zeros(3)
            for dd in same:
                uvec[cmp_all[dd]] = x[dd]
            res.setdefault("probes", {})[pn] = dict(at=np.round(loc, 1).tolist(), u_mm=np.round(uvec, 4).tolist())
        res["patches"] = meta[cname]
        results[cname] = res
        print(cname, json.dumps({k: res[k] for k in ("von_mises", "max_principal")}), res.get("probes"), flush=True)
        # plot: surface elements coloured by max principal (two views)
        try:
            plot(m, bf, el_s1, near, cfg, model, cname)
        except Exception as ex:  # noqa
            print("plot failed", ex)
    out = dict(model=model, stl=cfg["stl"], stl_sha256=cfg.get("stl_sha256"), mesh=log, E_MPa=E, nu=NU, cases=results,
               note="solid isotropic linear elastic; peaks exclude elements within exclude_mm of supports and load patches")
    (OUT / f"fea_{model}.json").write_text(json.dumps(out, indent=1))


def plot(m, bf, el_s1, near, cfg, model, cname):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    tri = m.facets[:, bf].T
    own = m.f2t[0, bf]
    val = el_s1[own]
    vmax = cfg.get("plot_vmax", float(np.percentile(val[~near[own]], 99.5)))
    fig = plt.figure(figsize=(12, 5.2))
    for k, (el, az) in enumerate(cfg.get("views", [(25, -60), (25, 120)])):
        ax = fig.add_subplot(1, 2, k + 1, projection="3d")
        P = m.p.T[tri]
        col = plt.cm.inferno_r(np.clip(val / vmax, 0, 1)) if False else plt.cm.viridis(np.clip(val / vmax, 0, 1))
        pc = Poly3DCollection(P, facecolors=col, edgecolors="none", linewidths=0)
        ax.add_collection3d(pc)
        lo, hi = m.p.min(axis=1), m.p.max(axis=1)
        ax.set_xlim(lo[0], hi[0]); ax.set_ylim(lo[1], hi[1]); ax.set_zlim(lo[2], hi[2])
        ax.set_box_aspect(hi - lo)
        ax.view_init(el, az)
        ax.set_xlabel("x"); ax.set_ylabel("y"); ax.set_zlabel("z")
    sm = plt.cm.ScalarMappable(cmap="viridis", norm=plt.Normalize(0, vmax))
    fig.colorbar(sm, ax=fig.axes, shrink=0.7, label="max principal stress, MPa (solid PLA, linear)")
    fig.suptitle(f"{model}: {cname}")
    fig.savefig(OUT / f"fea_{model}_{cname}.png", dpi=110)
    plt.close(fig)


if __name__ == "__main__":
    main()
