"""Check 7: printability in the print poses (body standing on its bottom wall, z up; cover flat on its outer face).
Overhang = face whose normal points more than 45 degrees below horizontal and that is not on the bed. Writes check_print.json."""
import json
import numpy as np, trimesh
import pack_lib as P

OUT = P.OUT
res = {}


def regions(mesh, mask):
    """Connected groups of masked faces -> list of (area, bbox, centroid)."""
    adj = mesh.face_adjacency
    keep = mask[adj[:, 0]] & mask[adj[:, 1]]
    import networkx as nx
    g = nx.Graph(); g.add_nodes_from(np.flatnonzero(mask)); g.add_edges_from(adj[keep])
    out = []
    for comp in nx.connected_components(g):
        comp = np.array(sorted(comp)); a = float(mesh.area_faces[comp].sum())
        tri = mesh.triangles[comp].reshape(-1, 3)
        out.append(dict(areaMm2=round(a, 2), bbox=[np.round(tri.min(0), 2).tolist(), np.round(tri.max(0), 2).tolist()],
                        centroid=np.round(tri.mean(0), 2).tolist(), faces=int(len(comp))))
    return sorted(out, key=lambda r: -r['areaMm2'])


def analyse(name, mesh, R, note):
    v = mesh.vertices @ R.T; m = trimesh.Trimesh(v, mesh.faces, process=False)
    n = m.face_normals; bed = float(m.bounds[0][2])
    fzmax = m.triangles[:, :, 2].max(1); fzmin = m.triangles[:, :, 2].min(1)
    on_bed = (np.abs(n[:, 2] + 1) < 1e-3) & (fzmax < bed + 0.02)
    over = (n[:, 2] < -0.7072) & ~on_bed
    steep = (n[:, 2] < -0.7072) & (n[:, 2] > -0.999) & ~on_bed      # sloped undersides steeper than 45
    flat_under = (n[:, 2] <= -0.999) & ~on_bed                        # horizontal undersides (bridges / unsupported)
    regs = regions(m, over)
    out = dict(printFrameNote=note, bedContactAreaMm2=round(float(m.area_faces[on_bed].sum()), 1), bedZ=bed,
               heightMm=round(float(m.bounds[1][2] - bed), 2), footprintXY=[np.round(m.bounds[0][:2], 2).tolist(), np.round(m.bounds[1][:2], 2).tolist()],
               overhangFaces=int(over.sum()), overhangAreaMm2=round(float(m.area_faces[over].sum()), 2),
               horizontalUndersideAreaMm2=round(float(m.area_faces[flat_under].sum()), 2), slopedOver45AreaMm2=round(float(m.area_faces[steep].sum()), 2),
               overhangRegionsLargestFirst=regs[:25], regionsCount=len(regs))
    # 45-degree-or-better undersides (gussets, teardrops, foot wedges): area of faces with normal between -45 and 0 degrees below horizontal
    ok_slope = (n[:, 2] < -1e-3) & (n[:, 2] >= -0.7072)
    out['selfSupportingUndersideAreaMm2'] = round(float(m.area_faces[ok_slope].sum()), 2)
    print(name, {k: v for k, v in out.items() if k != 'overhangRegionsLargestFirst'})
    for r in regs[:12]:
        print('   ', r)
    return out


bm = P.load_stl(OUT / 'rear_pack-world.stl'); cm = P.load_stl(OUT / 'rear_pack_cover-world.stl')
res['body'] = analyse('body', bm, np.eye(3), 'as modelled: world z up, standing on the bottom wall (z -44)')
Rc = np.array([[0, 1, 0], [0, 0, 1], [1, 0, 0]], float)   # x' = y, y' = z, z' = x  -> outer face (x -47) becomes the lowest plane
res['cover'] = analyse('cover', cm, Rc, "rotated: x' = y, y' = z, z' = x; outer face x = -47 lies on the bed")
# where the original had 45-degree gussets above the upper lugs: check the donor gusset is present (body material in the gusset box)
B = P.mesh_to_m(bm); PS = P.solid_m('power_support')
for s, nm in ((1, 'plus_y'), (-1, 'minus_y')):
    bx = P.box((-21.0, min(s * 11.5, s * 13.0), 25.2), (-16.5, max(s * 11.5, s * 13.0), 27.4))
    res[f'upperGussetBox_{nm}'] = dict(box=np.round(P.from_m(bx).bounds, 2).tolist(), bodyVolMm3=round(float((B ^ bx).volume()), 3), psVolMm3=round(float((PS ^ bx).volume()), 3))
P.jdump(res, OUT / 'check_print.json')
print('DONE')
