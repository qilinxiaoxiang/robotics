import sys, numpy as np, trimesh
import ext_lib as E
for nm in sys.argv[1:]:
    p = E.PARTS[nm]
    raw = trimesh.load(p, force='mesh', process=False)
    m = trimesh.load(p, force='mesh')
    print(nm, 'raw', len(raw.vertices), len(raw.faces), 'merged', len(m.vertices), len(m.faces), 'wt', m.is_watertight)
    e = np.sort(m.edges, axis=1)
    u, c = np.unique(e, axis=0, return_counts=True)
    bad = u[c > 2]
    for a, b in bad[:10]:
        print('  pinch', m.vertices[a].round(4), m.vertices[b].round(4), np.linalg.norm(m.vertices[a]-m.vertices[b]).round(5))
    M = E.stl_man(p)
    print('  manifold', M.status(), 'bodies', len(M.decompose()), 'genus', M.genus(), 'vol', M.volume())
    bodies = m.split(only_watertight=False)
    print('  trimesh split', [round(b.area, 3) for b in bodies])
