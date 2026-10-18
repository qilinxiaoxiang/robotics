"""Power support geometry: file identity, original vs integrated, added regions, mounted parts.
Writes geometry.json next to this script."""
import json
import sys
from pathlib import Path

import numpy as np
import trimesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pso_lib as L

out = {}
body = L.tm_load(L.CB / 'power-support-integrated-body.stl')
orig = L.tm_load(L.CB / 'original-power-support-body.stl')
src_print = L.tm_load(L.CB / 'power-support-integrated-print.stl')
printed = L.tm_load(L.PRINTED)
design = json.loads((L.CB / 'design.json').read_text())
T = np.array(design['source_transform'])


def vdev(a, b):
    """max nearest-vertex distance a->b and b->a (order independent)."""
    from scipy.spatial import cKDTree
    d1, _ = cKDTree(b).query(a); d2, _ = cKDTree(a).query(b)
    return float(max(d1.max(), d2.max()))


# 1. identity of the files
out['files'] = {
    'integrated_body': dict(path=str(L.CB / 'power-support-integrated-body.stl'), tris=len(body.faces), watertight=bool(body.is_watertight),
                            volume_mm3=body.volume, bounds=body.bounds.round(3).tolist(), components=len(body.split(only_watertight=False))),
    'original_body': dict(path=str(L.CB / 'original-power-support-body.stl'), tris=len(orig.faces), watertight=bool(orig.is_watertight),
                          volume_mm3=orig.volume, bounds=orig.bounds.round(3).tolist()),
    'printed_file': dict(path=str(L.PRINTED), tris=len(printed.faces), volume_mm3=printed.volume, bounds=printed.bounds.round(3).tolist(),
                         maxVertexDev_vs_body_shifted_z57p5=vdev(printed.vertices - [0, 0, 57.5], body.vertices)),
    'compact_battery_print_copy': dict(path=str(L.CB / 'power-support-integrated-print.stl'), bounds=src_print.bounds.round(3).tolist(),
                                       maxVertexDev_vs_body_after_design_source_transform=vdev(
                                           trimesh.transform_points(src_print.vertices, T), body.vertices)),
}
gv, gf = L.solid('power_support')
out['files']['guide_solid'] = dict(source=L.ia_lib.manifest()['power_support']['source'], tris=len(gf),
                                   maxVertexDev_vs_body=vdev(gv, body.vertices),
                                   volume_mm3=float(trimesh.Trimesh(gv, gf, process=False).volume))

# 2. upstream MJCF power_support and NP-F970 battery at qpos0 in the trunk frame
import mujoco
M = mujoco.MjModel.from_xml_path(str(L.XML)); D = mujoco.MjData(M); mujoco.mj_kinematics(M, D)
tb = M.body('trunk_base').id; R0 = D.xmat[tb].reshape(3, 3); p0 = D.xpos[tb]
up = {}
for g in range(M.ngeom):
    if M.geom_bodyid[g] != tb or M.geom_type[g] != mujoco.mjtGeom.mjGEOM_MESH:
        continue
    mid = M.geom_dataid[g]; name = M.mesh(mid).name
    if name in up:
        continue
    va, vn = M.mesh_vertadr[mid], M.mesh_vertnum[mid]
    v = M.mesh_vert[va:va + vn]
    X = ((v @ D.geom_xmat[g].reshape(3, 3).T + D.geom_xpos[g]) - p0) @ R0 * 1000.0
    up[name] = dict(bounds=[X.min(0).round(2).tolist(), X.max(0).round(2).tolist()],
                    geomClass_contype_conaffinity=[int(M.geom_contype[g]), int(M.geom_conaffinity[g])])
    if name == 'power_support':
        up[name]['maxVertexDev_vs_original_body_stl'] = vdev(X, orig.vertices)
out['upstream_trunk_meshes_qpos0'] = up
out['upstream_trunk_body_mass_g'] = float(M.body_mass[tb] * 1000)
del M, D
import gc; gc.collect()

# 3. original vs integrated: added and removed material
B = L.mesh_to_m(body); O = L.mesh_to_m(orig)
added = B - O; removed = O - B; kept = B ^ O
big = 200.0
below = B ^ L.box_m([-big, -big, -big], [big, big, L.ORIG_ZMIN])
out['material'] = dict(
    integrated_mm3=B.volume(), original_mm3=O.volume(), kept_original_mm3=kept.volume(),
    added_mm3=added.volume(), removed_from_original_mm3=removed.volume(),
    removed_bounds=[list(removed.bounding_box()[:3]), list(removed.bounding_box()[3:])],
    below_original_bottom_z=L.ORIG_ZMIN, below_original_bottom_mm3=below.volume(),
    below_bounds=[list(below.bounding_box()[:3]), list(below.bounding_box()[3:])],
    added_outside_original_aabb_mm3=(added - L.box_m(orig.bounds[0], orig.bounds[1])).volume(),
    PLA_g_per_mm3=0.00124,
)
# region partition of the added material
rest = added; regions = {}
for name, (lo, hi) in L.REGIONS:
    part = rest ^ L.box_m(lo, hi); rest = rest - L.box_m(lo, hi)
    bb = part.bounding_box()
    regions[name] = dict(volume_mm3=part.volume(), bounds=[list(np.round(bb[:3], 2)), list(np.round(bb[3:], 2))] if not part.is_empty() else None)
bb = rest.bounding_box()
regions['battery_bay_and_other_added'] = dict(volume_mm3=rest.volume(), bounds=[list(np.round(bb[:3], 2)), list(np.round(bb[3:], 2))])
out['added_regions'] = regions
# the posts are the only link between the deck and the rest of the part
posts = L.box_m([-38, 17.95, -58], [-33, 21, -35.4]) + L.box_m([-38, -21, -58], [-33, -17.95, -35.4])
no_posts = B - posts
comps = no_posts.decompose()
out['connectivity'] = dict(components_without_hanger_posts=len(comps),
                           component_volumes_mm3=sorted([round(c.volume(), 1) for c in comps], reverse=True),
                           component_bounds=[[list(np.round(c.bounding_box()[:3], 2)), list(np.round(c.bounding_box()[3:], 2))] for c in comps])
# post cross-section at several heights (area of the left post slice)
sec = {}
for z in (-54.0, -50.0, -46.0, -42.0, -38.0):
    s = (B ^ L.box_m([-38, 17.95, z - 0.05], [-33, 21, z + 0.05]))
    sec[str(z)] = round(s.volume() / 0.1, 2)
out['left_post_section_area_mm2'] = sec

# 4. the reported contact point
cp = np.array([-33.9, 20.4, -53.5])
pq = trimesh.proximity.ProximityQuery(body)
c1, d1, _ = pq.on_surface([cp])
addm = L.from_m(added)
c2, d2, _ = trimesh.proximity.closest_point(addm, [cp])
c3, d3, _ = trimesh.proximity.closest_point(orig, [cp])
out['reported_contact_point'] = dict(point=cp.tolist(), dist_to_integrated_surface=float(d1[0]), nearest_integrated=c1[0].round(3).tolist(),
                                     dist_to_added_material=float(d2[0]), dist_to_original_part=float(d3[0]),
                                     region=L.region_of(c1[0], added=True),
                                     inside_original_aabb=bool(np.all(cp >= orig.bounds[0]) and np.all(cp <= orig.bounds[1])))

# 5. what the current build mounts on / against the support (exact gaps)
from scipy.spatial import cKDTree
PS_TREE = cKDTree(trimesh.sample.sample_surface(body, 200000, seed=2)[0])
mounted = {}
for key in ['openrb_tray', 'openrb_board', 'regulator', 'regulator_insert', 'junction_j', 'fuse_main', 'xt30_robot', 'imu_clamp',
            'imu_cover', 'imu_board', 'torso_base', 'motor10', 'motor5', 'shell_left', 'shell_right', 'ring10_torso', 'ring5_torso']:
    v, f = L.solid(key); P = L.to_m(v, f)
    gap = B.min_gap(P, 10.0)
    rec = dict(gap_mm=round(gap, 3), overlap_mm3=round((B ^ P).volume(), 3))
    if gap < 1.0:
        pm = trimesh.Trimesh(v, f, process=False)
        pts, _ = trimesh.sample.sample_surface(pm, 40000, seed=1)
        dk, _ = PS_TREE.query(pts, distance_upper_bound=gap + 1.5)
        pts = pts[np.isfinite(dk)][:4000]
        near = np.zeros((0, 3))
        for i in range(0, len(pts), 500):
            cpts, dd, _ = trimesh.proximity.closest_point(body, pts[i:i + 500])
            near = np.vstack([near, cpts[dd < gap + 0.6]])
        labs = {}
        for p in near:
            r = L.region_of(p, added=None)
            labs[r] = labs.get(r, 0) + 1
        rec['near_support_points_by_region'] = labs
        if len(near):
            rec['near_support_bounds'] = [near.min(0).round(2).tolist(), near.max(0).round(2).tolist()]
    mounted[key] = rec
out['mounted_parts'] = mounted
L.jdump(out, Path(__file__).with_name('geometry.json'))
print(json.dumps(out, indent=1, default=float)[:6000])
