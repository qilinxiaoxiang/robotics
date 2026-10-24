#!/usr/bin/env python3
"""1:1 paper drill template for the six speaker port holes in the printed
yellow lower head shell (head_bottom, V1.30), drilled in place.

Inputs (read only):
  ../interface.json                          port_holes: centres, dia, floor z
  ../../world/head_bottom.stl                shell as printed, robot world frame
  ../../neck-exit-20261023/head_bottom_exit-print.stl   same shell, print pose
Outputs (this folder):
  drill-template.pdf, drill-template-proof.png, checks.json, render/ (page renders)

Run:  /tmp/microduck-cad-venv/bin/python make_drill_template.py
The PDF is read back with the system python3 (PyMuPDF, readback_pdf.py); the
proof image and checks use that readback, so they test the PDF itself.
"""
import json
import subprocess
from pathlib import Path

import matplotlib
import numpy as np
import trimesh
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import unary_union

matplotlib.use("Agg")
matplotlib.rcParams["pdf.fonttype"] = 42
matplotlib.rcParams["font.family"] = "DejaVu Sans"
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Circle, Rectangle  # noqa: E402
from matplotlib.patches import Polygon as MPoly  # noqa: E402

HERE = Path(__file__).resolve().parent
PRINT_DIR = HERE.parents[1]
IFACE = HERE.parent / "interface.json"
WORLD_STL = PRINT_DIR / "world/head_bottom.stl"
POSE_STL = PRINT_DIR / "neck-exit-20261023/head_bottom_exit-print.stl"
PDF = HERE / "drill-template.pdf"
PROOF = HERE / "drill-template-proof.png"
CHECKS = HERE / "checks.json"

PAGE_W, PAGE_H = 215.9, 279.4          # US Letter, mm
PT_PER_MM = 72 / 25.4
SIL_X0 = 40.0                           # outer outline drawn from this x forward
INSET = 0.25                            # paper cut line inside the recess walls, mm
U0, V0 = 107.95, 117.0                  # page position of world (x=0, y=0)
RED, BLUE, GREY = (0.8, 0.0, 0.0), (0.0, 0.31, 0.75), (0.55, 0.55, 0.55)


# ---------------------------------------------------------------- geometry
def to_page(x, y):
    """World (x, y) seen from BELOW, beak tip up the page: robot left (+y) is page right."""
    return U0 + np.asarray(y), V0 + np.asarray(x)


def from_page(u, v):
    return np.asarray(v) - V0, np.asarray(u) - U0   # -> (x, y)


def nearest_hits(mesh, origins, dirs):
    loc, ir, _ = mesh.ray.intersects_location(origins, dirs, multiple_hits=True)
    best = np.full((len(origins), 3), np.nan)
    dist = np.full(len(origins), np.inf)
    d = np.linalg.norm(loc - origins[ir], axis=1)
    for p, r, dd in zip(loc, ir, d):
        if dd < dist[r]:
            dist[r], best[r] = dd, p
    return best, dist


def vertical_hits(mesh, pts, z0=80.0):
    o = np.c_[pts, np.full(len(pts), z0)]
    loc, ir, _ = mesh.ray.intersects_location(o, np.tile([0, 0, 1.0], (len(o), 1)),
                                              multiple_hits=True)
    zs = [[] for _ in range(len(pts))]
    for p, r in zip(loc, ir):
        zs[r].append(p[2])
    return [sorted(z) for z in zs]


def recess_polygon(mesh, centre, z, n=1440):
    """Outline of the underside recess at height z: horizontal rays from inside."""
    a = np.linspace(0, 2 * np.pi, n, endpoint=False)
    d = np.c_[np.cos(a), np.sin(a), np.zeros(n)]
    o = np.tile([centre[0], centre[1], z], (n, 1))
    p, dist = nearest_hits(mesh, o, d)
    assert np.isfinite(dist).all(), "recess not closed at this height"
    return Polygon(p[:, :2]).buffer(0), dist


def section(mesh, z):
    s = mesh.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
    pl, _ = s.to_2D(to_2D=np.array([[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, -z], [0, 0, 0, 1.0]]))
    return unary_union(pl.polygons_full)


def silhouette(mesh):
    tri = mesh.triangles[np.abs(mesh.face_normals[:, 2]) > 1e-3][:, :, :2]
    return unary_union([Polygon(t) for t in tri if Polygon(t).area > 1e-6]).buffer(0.01).buffer(-0.01)


def rigid_fit(a, b):
    ca, cb = a.mean(0), b.mean(0)
    u, _, vt = np.linalg.svd((a - ca).T @ (b - cb))
    r = vt.T @ u.T
    if np.linalg.det(r) < 0:
        vt[-1] *= -1
        r = vt.T @ u.T
    return r, cb - r @ ca


# ---------------------------------------------------------------- analysis
def analyse():
    iface = json.loads(IFACE.read_text())["port_holes"]
    holes = np.array(iface["centres_xy"], float)
    dia = float(iface["diameter_mm"])
    z_top, z_bot = float(iface["floor_top_z"]), float(iface["floor_bottom_z"])
    m = trimesh.load(WORLD_STL, process=False)
    mp = trimesh.load(POSE_STL, process=False)
    ck = {"inputs": {"interface": str(IFACE), "world_stl": str(WORLD_STL), "print_pose_stl": str(POSE_STL),
                     "hole_dia_mm": dia, "floor_top_z": z_top, "floor_bottom_z": z_bot}}

    # print pose: same shell? which way did the recess face on the bed?
    r, t = rigid_fit(m.vertices, mp.vertices)
    resid = float(np.abs(m.vertices @ r.T + t - mp.vertices).max())
    floor_pt = r @ np.array([holes[:, 0].mean(), holes[:, 1].mean(), z_bot]) + t
    ck["print_pose"] = {
        "same_shell_rigid_fit_max_residual_mm": resid,
        "recess_floor_normal_in_print_pose": np.round(r @ [0, 0, -1.0], 4).tolist(),
        "recess_floor_height_above_bed_mm": round(float(floor_pt[2] - mp.bounds[0, 2]), 2),
        "meaning": "the recess floor (drilling face) faced the bed about 10 mm up, so it was printed over supports: clear support stubs before laying the paper",
    }

    # the underside recess the lower jaw closes into
    zr = z_bot - 0.05
    centre = (holes[:, 0].mean() - 1.0, 0.0)
    recess, _ = recess_polygon(m, centre, zr)
    # inset, then drop the sub-1.6 mm corner slivers where the side walls meet the rear wall
    paper = recess.buffer(-INSET - 0.8, join_style=2).buffer(0.8, join_style=2)
    rb = recess.bounds
    wall_depth = {}
    for name, (x, y) in {"front": (rb[2] + 0.9, -3.0), "side_at_x68": (68.0, rb[3] - 0.3),
                         "rear": (rb[0] - 0.2, -3.0)}.items():
        z = vertical_hits(m, np.array([[x, y]]))[0]
        wall_depth[name] = round(z_bot - z[0], 2) if z else None
    # floor flatness inside the paper area
    gx, gy = np.meshgrid(np.arange(rb[0], rb[2], 0.5), np.arange(rb[1], rb[3], 0.5))
    pts = np.c_[gx.ravel(), gy.ravel()]
    inner = paper.buffer(-0.3)
    pts = pts[[inner.contains(Point(p)) for p in pts]]
    zs = vertical_hits(m, pts)
    first = np.array([z[0] if z else np.nan for z in zs])
    flat = np.abs(first - z_bot) < 0.1
    # existing holes inside the recess, from a slice through the floor
    sl = section(m, z_bot + 0.5)
    screws = []
    for p in getattr(sl, "geoms", [sl]):
        for ring in p.interiors:
            h = Polygon(ring)
            if 5 < h.area < 60 and recess.contains(h.centroid):
                screws.append({"centre_xy": [round(h.centroid.x, 2), round(h.centroid.y, 2)],
                               "dia_mm": round(2 * np.sqrt(h.area / np.pi), 2)})
    screws.sort(key=lambda s: s["centre_xy"][1])
    # the narrow slot along the rear wall (open from below, roof above the floor)
    slot_x = [float(x) for x in np.arange(rb[0], rb[0] + 2.0, 0.05)
              if (z := vertical_hits(m, np.array([[x, -3.0]]))[0]) and z[0] > z_bot + 0.5]
    slot = [round(min(slot_x), 2), round(max(slot_x) + 0.05, 2)] if slot_x else None
    ck["recess"] = {
        "what": "flat-floored recess on the underside of the beak floor, ringed by a wall on all four sides; the lower jaw closes into it",
        "probe_height_z": zr,
        "x_rear_wall": round(rb[0], 2), "x_front_wall": round(rb[2], 2),
        "half_width_y": {f"x{x}": round(LineString([(x, -60), (x, 60)]).intersection(recess).length / 2, 2)
                         for x in (55, 64, 68, 72, 80)},
        "wall_height_below_floor_mm": wall_depth,
        "floor_points_checked": int(len(pts)), "floor_points_flat_within_0.1mm": int(flat.sum()),
        "floor_z_range_flat_points": [round(float(np.nanmin(first[flat])), 3), round(float(np.nanmax(first[flat])), 3)],
        "non_flat_points_max_distance_to_a_screw_hole_centre_mm": round(float(max(
            min(np.hypot(px - s["centre_xy"][0], py - s["centre_xy"][1]) for s in screws)
            for px, py in pts[~flat])), 2) if (~flat).any() else None,
        "non_flat_meaning": "every non-flat point lies inside one of the two screw holes (radius 2.6): the paper area is otherwise one flat plane",
        "screw_holes": screws,
        "rear_slot_x": slot,
        "paper_inset_mm": INSET,
    }

    # per-hole references and clearances
    res = []
    grid = 0.1
    for i, (hx, hy) in enumerate(holes, 1):
        o = np.array([[hx, hy, zr]] * 4)
        d = np.array([[1, 0, 0], [-1, 0, 0], [0, 1, 0], [0, -1, 0.0]])
        _, dist = nearest_hits(m, o, d)
        # feature scan: every point within 14 mm of the centre that is not plain 2.8 mm floor
        g = np.arange(-14, 14 + grid / 2, grid)
        GX, GY = np.meshgrid(g, g)
        rr = np.hypot(GX, GY).ravel()
        keep = rr <= 14
        P = np.c_[GX.ravel()[keep] + hx, GY.ravel()[keep] + hy]
        Z = vertical_hits(m, P)
        plain = np.array([len(z) == 2 and abs(z[0] - z_bot) < 0.1 and 111.0 <= z[1] <= 111.6 for z in Z])
        R = rr[keep]
        if (~plain).any():
            k = np.argmin(np.where(plain, np.inf, R))
            near = {"xy": np.round(P[k], 2).tolist(), "surface_z_hits": np.round(Z[k], 2).tolist()}
            clear = float(R[k] - dia / 2 - grid / 2)
        else:
            near, clear = None, None
        pa = Point(hx, hy)
        res.append({
            "hole": f"H{i}", "centre_xy": [hx, hy],
            "to_front_wall_mm": round(float(dist[0]), 2), "to_rear_wall_mm": round(float(dist[1]), 2),
            "to_robot_left_wall_mm": round(float(dist[2]), 2), "to_robot_right_wall_mm": round(float(dist[3]), 2),
            "to_paper_edge_mm": round(paper.exterior.distance(pa), 2),
            "to_screw_hole_centres_mm": {f"screw_y{s['centre_xy'][1]:+.0f}": round(float(np.hypot(hx - s["centre_xy"][0], hy - s["centre_xy"][1])), 2) for s in screws},
            "floor_at_centre_z": np.round(vertical_hits(m, np.array([[hx, hy]]))[0], 3).tolist(),
            "min_edge_clearance_to_any_feature_mm": round(clear, 2) if clear is not None else ">11.5",
            "nearest_feature": near,
            "clearance_ok_ge_1.2mm": clear is None or clear >= 1.2,
        })
    ck["holes"] = res
    return dict(m=m, holes=holes, dia=dia, z_top=z_top, z_bot=z_bot, recess=recess, paper=paper,
                screws=screws, slot=slot, sil=silhouette(m), ck=ck)


# ---------------------------------------------------------------- PDF
def mm_text(ax, u, v, s, size=8, **kw):
    ax.text(u, v, s, fontsize=size, color=kw.pop("color", "black"), **kw)


def draw_pdf(G):
    fig = plt.figure(figsize=(PAGE_W / 25.4, PAGE_H / 25.4))
    fig.patch.set_facecolor("white")
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, PAGE_W)
    ax.set_ylim(0, PAGE_H)
    ax.axis("off")

    mm_text(ax, 12, 268, "MicroDuck drill template: 6 speaker holes in the yellow lower head shell", 12.5, weight="bold")
    mm_text(ax, 12, 262.5, "Part: head_bottom V1.30 (already printed). Holes: 6 x dia 2.5 mm, straight through the 2.8 mm floor.", 8.5)

    # scale check
    ax.add_patch(Rectangle((10, 230), PAGE_W - 20, 28, fill=False, lw=0.6, ec="black"))
    mm_text(ax, 13, 253.2, "STEP 1  CHECK THE SCALE FIRST", 9, weight="bold")
    mm_text(ax, 13, 249.3, "Print at Actual size / 100 % (no Fit to page). Measure both bars end to end with a ruler or calipers.", 7.6)
    mm_text(ax, 13, 245.8, "The template is valid only if the 100 mm bar is 99.5 to 100.5 mm and the 50 mm bar is 49.7 to 50.3 mm.", 7.6, weight="bold")
    mm_text(ax, 13, 242.3, "CampusPrinting shrinks Letter pages to 96.3 % (100 mm prints as 96.3 mm) and Chrome's Scale does not fix it: print elsewhere.", 7.6)
    for x0, L, step in ((15, 100, 10), (140, 50, 5)):
        ax.add_patch(Rectangle((x0, 234), L, 2.0, fc="black", ec="none", lw=0))
        for e in (x0, x0 + L):
            ax.plot([e, e], [232.2, 237.8], color="black", lw=0.3, solid_capstyle="butt")
        for k in np.arange(step, L, step):
            ax.plot([x0 + k, x0 + k], [232.6, 234.0], color="black", lw=0.3, solid_capstyle="butt")
        mm_text(ax, x0 + L / 2, 238.4, f"{L} mm", 7.5, ha="center", weight="bold")

    # the template, true scale, seen from below
    from shapely.geometry import box
    sil = G["sil"].intersection(box(SIL_X0, -60, 120, 60))
    for p in getattr(sil, "geoms", [sil]):
        x, y = np.asarray(p.exterior.coords).T
        u, v = to_page(x, y)
        ax.plot(u, v, color=GREY, lw=0.35, ls=(0, (3, 2)))
    x, y = np.asarray(G["recess"].exterior.coords).T
    u, v = to_page(x, y)
    ax.plot(u, v, color=GREY, lw=0.3)
    x, y = np.asarray(G["paper"].exterior.coords).T
    u, v = to_page(x, y)
    ax.add_patch(MPoly(np.c_[u, v], closed=True, fc=(1.0, 0.97, 0.80), ec="none"))
    ax.plot(u, v, color="black", lw=0.8, solid_joinstyle="miter")
    r = G["dia"] / 2
    for i, (hx, hy) in enumerate(G["holes"], 1):
        u, v = to_page(hx, hy)
        ax.add_patch(Circle((u, v), r, fill=False, ec=RED, lw=0.5))
        ax.plot([u - 2.4, u + 2.4], [v, v], color=RED, lw=0.3, solid_capstyle="butt")
        ax.plot([u, u], [v - 2.4, v + 2.4], color=RED, lw=0.3, solid_capstyle="butt")
        side = -1 if hy < -3 else 1
        mm_text(ax, u + side * 2.9, v + 0.4, f"H{i}", 5.5, ha="right" if side < 0 else "left", color=RED, va="bottom")
    for s in G["screws"]:
        u, v = to_page(*s["centre_xy"])
        ax.add_patch(Circle((u, v), s["dia_mm"] / 2, fill=False, ec=BLUE, lw=0.5))
        ax.plot([u - 3.4, u + 3.4], [v, v], color=BLUE, lw=0.25)
        ax.plot([u, u], [v - 3.4, v + 3.4], color=BLUE, lw=0.25)

    ub, vb = to_page(0, 0)
    xr, xf = G["recess"].bounds[0], G["recess"].bounds[2]
    xmax = G["m"].bounds[1, 0]
    _, vtip = to_page(xmax, 0)
    ax.annotate("", xy=(ub, vtip + 9), xytext=(ub, vtip + 2), arrowprops=dict(arrowstyle="-|>", lw=0.8, color="black"))
    mm_text(ax, ub, vtip + 10, "BEAK TIP (front of the head)", 8, ha="center", weight="bold")
    mm_text(ax, 12, 224, "STEP 2  THE TEMPLATE (true size). View from BELOW:", 9, weight="bold")
    mm_text(ax, 12, 220.3, "the underside of the yellow shell, the face the lower jaw closes onto.", 7.6)
    ul, _ = to_page(0, -45.9)
    ur, _ = to_page(0, 45.9)
    _, vmid = to_page(67.0, 0)
    mm_text(ax, ul - 2.5, vmid, "robot RIGHT side", 7.5, rotation=90, ha="right", va="center")
    mm_text(ax, ur + 2.5, vmid, "robot LEFT side", 7.5, rotation=-90, ha="left", va="center")

    # callouts (left and right of the drawing)
    _, vfront = to_page(xf, 0)
    lines_l = [("Bold black line = CUT LINE.", True),
               ("It is the outline of the recess", False), ("on the underside, 0.25 mm in.", False),
               ("The cut paper drops into the", False), ("recess and touches its wall on", False),
               ("all four sides. The wider edge", False), ("goes to the beak tip.", False), ("", False),
               ("Dashed grey = outer outline of", False), ("the shell's front part, for a", False),
               ("first look only.", False), ("", False),
               ("A narrow groove runs along", False), ("the rear wall; the rear paper", False),
               ("edge lies over it.", False)]
    for k, (s, b) in enumerate(lines_l):
        mm_text(ax, 11, 196 - k * 3.6, s, 7.2, weight="bold" if b else "normal")
    hx = G["ck"]["holes"]
    lines_r = [("Red = the 6 holes, dia 2.5", True), ("(H1 to H6).", False), ("", False),
               ("Blue = the 2 existing screw", True), ("holes (dia 5.2). Each must", False),
               ("show centred in its blue", False), ("circle. If not, the paper is", False),
               ("not seated: fix before marking.", False),
               ("(The screw holes sit against", False), ("the side walls, so each circle", False), ("touches the cut line.)", False), ("", False),
               ("Caliper check after taping:", True),
               (f"H3, H6 centres {hx[2]['to_front_wall_mm']:.1f} mm", False), ("from the front wall.", False),
               (f"H1, H4 centres {hx[0]['to_rear_wall_mm']:.1f} mm", False), ("from the rear wall.", False),
               ("Hole rows 8 mm apart,", False), ("holes 4 mm apart in a row.", False),
               (f"H1 centre {hx[0]['to_robot_right_wall_mm']:.1f} mm from the", False), ("robot-right side wall.", False)]
    for k, (s, b) in enumerate(lines_r):
        mm_text(ax, 160, 196 - k * 3.6, s, 7.2, weight="bold" if b else "normal")

    # steps
    y0 = 117
    steps = [
        ("STEP 3  CUT AND SEAT", True),
        ("Take the shell off the robot. Scrape any support stubs off the recess floor and out of its corners (that face was printed on supports).", False),
        ("Cut along the bold line. Lay the paper printed side UP in the recess, beak-tip edge to the front wall. It must lie flat and touch", False),
        ("the wall all round, with both screw holes centred in the blue circles. If one edge rides up, trim that edge a little and try again.", False),
        ("Tape it down at the corners.", False),
        ("STEP 4  MARK", True),
        ("Push a pin or scriber through the centre of each red crosshair, hard enough to leave a dimple in the plastic. Lift the paper and", False),
        ("check that all six dimples are there.", False),
        ("STEP 5  DRILL FROM THIS SIDE (the underside), straight through, square to the flat floor", True),
        ("Support the floor from inside the head on a scrap block at least 10 mm tall and no wider than 60 mm, so it does not flex.", False),
        ("Drill a 1 mm pilot at each dimple, then open it to 2.5 mm. Go slowly so the plastic does not melt. The floor is 2.8 mm thick.", False),
        ("STEP 6  CLEAN UP", True),
        ("Underside: the lower jaw closes 0.3 mm below these holes, so shave any raised lip flush with a sharp knife or a larger drill", False),
        ("bit turned by hand. Inside: clear the chips and burrs; the speaker duct sits on that face later.", False),
        ("Hole positions: robot frame x = 64, 68, 72 mm and y = -7, +1 mm (port_holes in ears-mouth-20261023/interface.json).", False),
    ]
    yy = y0
    for s, b in steps:
        if b:
            yy -= 2.2
        mm_text(ax, 12, yy, s, 7.8 if not b else 9, weight="bold" if b else "normal")
        yy -= 4.4
    fig.savefig(PDF, format="pdf", facecolor="white")
    plt.close(fig)


# ---------------------------------------------------------------- readback + proof
def readback():
    out = subprocess.run(["python3", str(HERE / "readback_pdf.py"), str(PDF), str(HERE / "render")],
                         check=True, capture_output=True, text=True)
    return json.loads(out.stdout)


def proof(G, rb):
    m, z_bot = G["m"], G["z_bot"]
    cut = np.array(rb["cut_lines_pt"][0]) / PT_PER_MM
    cx, cy = from_page(cut[:, 0], cut[:, 1])
    hc = np.array(rb["crosshair_centres_pt"]) / PT_PER_MM
    hxw, hyw = from_page(hc[:, 0], hc[:, 1])
    fig = plt.figure(figsize=(18, 12))
    fig.patch.set_facecolor("white")

    # A: 3D, shell upside down with the paper in the recess
    a = fig.add_subplot(2, 2, 1, projection="3d", computed_zorder=False)
    tri = m.triangles
    sel = (tri[:, :, 0].mean(1) > 20)
    from mpl_toolkits.mplot3d.art3d import Line3DCollection, Poly3DCollection
    n = m.face_normals[sel]
    shade = 0.45 + 0.55 * np.clip(-n @ np.array([0.3, -0.4, -0.85]), 0, 1)
    cols = np.c_[0.98 * shade, 0.80 * shade, 0.10 * shade, np.ones(len(shade))]
    a.add_collection3d(Poly3DCollection(tri[sel], facecolors=cols, edgecolors="none", zorder=1))
    a.add_collection3d(Poly3DCollection([np.c_[cx, cy, np.full(len(cx), z_bot - 0.1)]],
                                        facecolors=[(1, 1, 1, 0.85)], edgecolors="k", linewidths=0.8, zorder=2))
    t = np.linspace(0, 2 * np.pi, 40)
    for x, y in zip(hxw, hyw):
        a.plot(x + 1.25 * np.cos(t), y + 1.25 * np.sin(t), np.full(40, z_bot - 0.12), color="red", lw=1.2, zorder=3)
        a.plot([x, x], [y, y], [z_bot - 6, G["z_top"] + 2], color="red", lw=1.0, zorder=3)
    a.set_xlim(20, 90)
    a.set_ylim(-46, 46)
    a.set_zlim(85, 125)
    a.set_box_aspect((70, 92, 40))
    a.view_init(elev=-55, azim=-150)
    a.set_title("A. Shell upside down: paper (white) read back from the PDF, seated in the underside recess;\nred = the 6 crosshairs and drill axes (vertical, through the 2.8 mm floor)", fontsize=10)
    a.set_axis_off()

    # B: orthographic view from below, same orientation as the page
    b = fig.add_subplot(2, 2, 2)
    xs, ys = np.arange(44, 88, 0.2), np.arange(-47, 47, 0.2)
    X, Y = np.meshgrid(xs, ys)
    Z = vertical_hits(m, np.c_[X.ravel(), Y.ravel()])
    first = np.array([z[0] if z else np.nan for z in Z]).reshape(X.shape)
    U, V = to_page(X, Y)
    im = b.pcolormesh(U, V, first, shading="auto", cmap="YlOrBr_r", vmin=104, vmax=110.5)
    plt.colorbar(im, ax=b, label="height of the first surface seen from below (world z, mm)")
    pu, pv = to_page(cx, cy)
    b.plot(cut[:, 0], cut[:, 1], "k-", lw=1.2, label="cut line (PDF readback)")
    for u, v in hc:
        b.add_patch(Circle((u, v), 1.25, fill=False, ec="red", lw=1.2))
        b.plot([u - 2.4, u + 2.4], [v, v], "r-", lw=0.6)
        b.plot([u, u], [v - 2.4, v + 2.4], "r-", lw=0.6)
    for s in rb["screw_marks_pt"]:
        b.add_patch(Circle((s[0] / PT_PER_MM, s[1] / PT_PER_MM), s[2] / PT_PER_MM / 2, fill=False, ec="blue", lw=1.2))
    b.set_aspect("equal")
    b.set_title("B. True view from below, page orientation (robot left = right). Colour = shell geometry;\nlines = PDF readback mapped back onto it: cut line inside the recess wall, blue on the screw holes", fontsize=10)
    b.set_xlabel("page u (mm)")
    b.set_ylabel("page v (mm)")
    b.legend(loc="lower left", fontsize=8)

    # C: section through the H1-H3 row
    c = fig.add_subplot(2, 2, 3)
    s = m.section(plane_origin=[0, -7, 0], plane_normal=[0, 1, 0])
    for e in s.discrete:
        c.plot(e[:, 0], e[:, 2], "k-", lw=0.9)
    xr = G["paper"].intersection(LineString([(0, -7), (100, -7)])).bounds
    c.plot([xr[0], xr[2]], [z_bot - 0.1] * 2, color="#c9a400", lw=3, label="paper (0.1 mm) on the recess floor")
    for x in G["holes"][:3, 0]:
        c.axvspan(x - 1.25, x + 1.25, ymin=0, ymax=1, color="red", alpha=0.25)
        c.annotate("", xy=(x, G["z_top"] + 1.0), xytext=(x, z_bot - 4), arrowprops=dict(arrowstyle="-|>", color="red"))
    c.text(66, z_bot - 5.4, "drill from below (jaw side), up through the floor", color="red", ha="center", fontsize=9)
    c.set_xlim(44, 90)
    c.set_ylim(100, 116)
    c.set_aspect("equal")
    c.grid(alpha=0.3)
    c.set_xlabel("world x (mm, beak tip to the right)")
    c.set_ylabel("world z (mm)")
    c.set_title("C. Section at y = -7 (H1, H2, H3): plain 2.8 mm floor under every hole; recess walls\nfront and rear hold the paper", fontsize=10)
    c.legend(loc="upper left", fontsize=8)

    # D: front-left corner zoom
    d = fig.add_subplot(2, 2, 4)
    d.pcolormesh(U, V, first, shading="auto", cmap="YlOrBr_r", vmin=104, vmax=110.5)
    d.plot(cut[:, 0], cut[:, 1], "k-", lw=1.5)
    rx, ry = np.asarray(G["recess"].exterior.coords).T
    ru, rv = to_page(rx, ry)
    d.plot(ru, rv, "c--", lw=1.0, label="recess wall at the floor (z 108.45)")
    for s in rb["screw_marks_pt"]:
        d.add_patch(Circle((s[0] / PT_PER_MM, s[1] / PT_PER_MM), s[2] / PT_PER_MM / 2, fill=False, ec="blue", lw=1.5))
    uc, vc = to_page(G["recess"].bounds[2], G["recess"].bounds[3])
    d.set_xlim(uc - 12, uc + 3)
    d.set_ylim(vc - 14, vc + 3)
    d.set_aspect("equal")
    d.legend(loc="lower left", fontsize=8)
    d.set_title("D. Zoom, front corner on the robot-left side: cut line 0.25 mm inside the wall;\nblue mark centred on the existing screw hole", fontsize=10)
    fig.tight_layout()
    fig.savefig(PROOF, dpi=110, facecolor="white")
    plt.close(fig)


def main():
    G = analyse()
    draw_pdf(G)
    rb = readback()
    proof(G, rb)
    ck = G["ck"]
    # page-scale numbers
    bars = {round(b["width_pt"] / PT_PER_MM): b for b in rb["bars"]}
    cut = np.array(rb["cut_lines_pt"][0]) / PT_PER_MM
    cx, cy = from_page(cut[:, 0], cut[:, 1])
    cutpoly = Polygon(np.c_[cx, cy])
    gap = [G["recess"].exterior.distance(Point(p)) for p in np.c_[cx, cy][::5]]
    hc = np.array(rb["crosshair_centres_pt"]) / PT_PER_MM
    hx, hy = from_page(hc[:, 0], hc[:, 1])
    err = [float(min(np.hypot(hx - x, hy - y))) for x, y in G["holes"]]
    scr_err = []
    for s in rb["screw_marks_pt"]:
        x, y = from_page(s[0] / PT_PER_MM, s[1] / PT_PER_MM)
        scr_err.append(round(float(min(np.hypot(x - q["centre_xy"][0], y - q["centre_xy"][1]) for q in G["screws"])), 3))
    ck["page"] = {
        "paper": "US Letter portrait", "page_pt": rb["page_pt"], "expected_pt": [612.0, 792.0],
        "page_count": rb["page_count"], "form_widgets": rb["widgets"],
        "bar_100mm_pdf_pt": round(bars[100]["width_pt"], 3), "bar_100mm_expected_pt": round(100 * PT_PER_MM, 3),
        "bar_50mm_pdf_pt": round(bars[50]["width_pt"], 3), "bar_50mm_expected_pt": round(50 * PT_PER_MM, 3),
        "raster_bar_measurements": rb["raster"],
        "if_printed_at_96.3pct": {"bar_100mm_reads_mm": 96.3, "bar_50mm_reads_mm": 48.15,
                                  "paper_width_shortfall_at_front_mm": round(0.037 * (2 * ck["recess"]["half_width_y"]["x80"]), 1),
                                  "meaning": "invalid; also the paper sits loose in the recess by about 3 mm"},
        "crosshair_centres_found": len(hc),
        "crosshair_vs_interface_max_error_mm": round(max(err), 4),
        "screw_mark_vs_shell_hole_error_mm": scr_err,
        "cut_line_gap_to_recess_wall_mm": [round(min(gap), 3), round(max(gap), 3)],
        "cut_paper_inside_recess": bool(G["recess"].buffer(1e-3).contains(cutpoly)),
        "cut_paper_size_mm": {"depth_front_to_rear": round(cutpoly.bounds[2] - cutpoly.bounds[0], 2),
                              "width_at_front": round(2 * (ck["recess"]["half_width_y"]["x80"] - INSET), 2),
                              "width_at_rear_x55": round(2 * (ck["recess"]["half_width_y"]["x55"] - INSET), 2)},
    }
    ck["outputs"] = {"pdf": str(PDF), "proof_png": str(PROOF), "renders": str(HERE / "render")}
    ck["all_holes_clearance_ok"] = all(h["clearance_ok_ge_1.2mm"] for h in ck["holes"])
    CHECKS.write_text(json.dumps(ck, indent=1))
    print(json.dumps({k: ck[k] for k in ("page", "all_holes_clearance_ok")}, indent=1))
    for h in ck["holes"]:
        print(h["hole"], h["to_front_wall_mm"], h["to_rear_wall_mm"], h["to_robot_left_wall_mm"],
              h["to_robot_right_wall_mm"], h["min_edge_clearance_to_any_feature_mm"], h["nearest_feature"])


if __name__ == "__main__":
    main()
