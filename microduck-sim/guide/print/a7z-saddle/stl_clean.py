"""Make a manifold3d export watertight for trimesh: manifold3d leaves zero-area sliver triangles whose middle vertex sits on a
neighbour's edge (a T-junction). Deleting them alone opens the mesh (edge used once each side), so each sliver is removed
and the neighbouring face across its long edge is split at the middle vertex. Repeats until no sliver is left; the result
passes trimesh is_watertight after exact vertex deduplication (the release pipeline's load_mesh)."""
import numpy as np, trimesh


def clean(mesh, tol=1e-6):
    v, inv = np.unique(np.asarray(mesh.vertices, float), axis=0, return_inverse=True)
    F = inv.reshape(-1)[np.asarray(mesh.faces)].copy() if inv.ndim > 1 else inv[np.asarray(mesh.faces)].copy()
    for _ in range(50):
        F = F[(F[:, 0] != F[:, 1]) & (F[:, 1] != F[:, 2]) & (F[:, 0] != F[:, 2])]
        P = v[F]; area2 = np.linalg.norm(np.cross(P[:, 1] - P[:, 0], P[:, 2] - P[:, 0]), axis=1)
        bad = np.flatnonzero(area2 < tol)
        if not len(bad):
            break
        edge_faces = {}
        for fi, f in enumerate(F):
            for k in range(3):
                e = tuple(sorted((f[k], f[(k + 1) % 3])))
                edge_faces.setdefault(e, []).append(fi)
        drop = set(); add = []
        for fi in bad:
            f = F[fi]; p = v[f]
            # the middle vertex is the one with the largest opposite edge
            lens = [np.linalg.norm(p[(k + 1) % 3] - p[(k + 2) % 3]) for k in range(3)]
            k = int(np.argmax(lens)); c = f[k]; a, b = f[(k + 1) % 3], f[(k + 2) % 3]
            drop.add(fi)
            for nb in edge_faces.get(tuple(sorted((a, b))), []):
                if nb == fi or nb in drop:
                    continue
                g = F[nb]; d = [x for x in g if x not in (a, b)]
                if len(d) != 1:
                    continue
                d = d[0]; i_a = list(g).index(a); i_b = list(g).index(b)
                # keep the winding: replace (a,b,d) in g's order by (a,c,d) and (c,b,d)
                if (i_b - i_a) % 3 == 1:
                    add += [[a, c, d], [c, b, d]]
                else:
                    add += [[b, c, d], [c, a, d]]
                drop.add(nb)
                break
        F = np.r_[F[[i for i in range(len(F)) if i not in drop]], np.array(add, dtype=F.dtype).reshape(-1, 3)]
    return split_pinches(trimesh.Trimesh(v, F, process=False))


def split_pinches(mesh, nudge=1e-4):
    """An edge used by four faces is two sheets of the solid touching along a line (a pinch, e.g. where the floor's
    normal-offset underside folds at the shell/pack step). The four faces are sorted by angle around the edge and paired
    into sheets (neighbours in that order); at each end vertex the faces around it are grouped into fans connected across
    their shared edges (the pinch edge connects only within a sheet), and every fan but the first gets its own copy of the
    vertex, moved 0.1 um into the fan's mean direction: the print is the same, trimesh sees every edge twice."""
    V = np.asarray(mesh.vertices, float).copy(); F = np.asarray(mesh.faces).copy()
    for _ in range(20):
        e = np.sort(F[:, [[0, 1], [1, 2], [2, 0]]].reshape(-1, 2), axis=1)
        u, inv, cnt = np.unique(e, axis=0, return_inverse=True, return_counts=True); inv = inv.reshape(-1)
        bad = np.flatnonzero(cnt == 4)
        if not len(bad):
            break
        sheet_pairs = {}   # pinch edge -> [(f, f), (f, f)]
        for bi in bad:
            a, b = u[bi]; fids = np.unique(np.flatnonzero(inv == bi) // 3)
            if len(fids) != 4:
                continue
            axis = V[b] - V[a]; axis /= np.linalg.norm(axis); ref = None; angs = []
            for fi in fids:
                c = [x for x in F[fi] if x not in (a, b)][0]; w = V[c] - V[a]; w = w - axis * (w @ axis); w /= max(np.linalg.norm(w), 1e-12)
                if ref is None:
                    ref = w; ref2 = np.cross(axis, ref)
                angs.append(np.arctan2(w @ ref2, w @ ref))
            o = fids[np.argsort(angs)]; sheet_pairs[(int(a), int(b))] = [(int(o[0]), int(o[1])), (int(o[2]), int(o[3]))]
        touched = sorted({v for ab in sheet_pairs for v in ab})
        for vtx in touched:
            fids = np.flatnonzero((F == vtx).any(axis=1)); fset = set(fids.tolist())
            # union-find over faces around vtx
            parent = {f: f for f in fids}
            def find(x):
                while parent[x] != x:
                    parent[x] = parent[parent[x]]; x = parent[x]
                return x
            def join(x, y): parent[find(x)] = find(y)
            by_edge = {}
            for fi in fids:
                for x in F[fi]:
                    if x != vtx:
                        by_edge.setdefault((min(vtx, x), max(vtx, x)), []).append(fi)
            for ed, fs in by_edge.items():
                if ed in sheet_pairs:
                    for pr in sheet_pairs[ed]:
                        if pr[0] in fset and pr[1] in fset:
                            join(pr[0], pr[1])
                elif len(fs) == 2:
                    join(fs[0], fs[1])
            comps = {}
            for fi in fids:
                comps.setdefault(find(fi), []).append(fi)
            groups = sorted(comps.values(), key=lambda g: min(g))
            for g in groups[1:]:
                others = np.array([x for fi in g for x in F[fi] if x != vtx]); d = (V[others] - V[vtx]).mean(axis=0); d = d / max(np.linalg.norm(d), 1e-12) * nudge
                nv = len(V); V = np.r_[V, (V[vtx] + d)[None]]
                for fi in g:
                    F[fi] = [nv if x == vtx else x for x in F[fi]]
    return trimesh.Trimesh(V, F, process=False)


if __name__ == '__main__':
    import sys
    for p in sys.argv[1:]:
        m = trimesh.load(p, force='mesh', process=False); c = clean(m)
        print(p, 'faces', len(m.faces), '->', len(c.faces), 'watertight', c.is_watertight, 'winding', c.is_winding_consistent, 'vol', round(m.volume, 1), round(c.volume, 1))
