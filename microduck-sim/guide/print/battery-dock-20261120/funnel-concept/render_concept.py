"""Concept sheet: top, side and rear views of the funnel dock (concept geometry boxes), the seated backpack, pads and
legs (sim seated pose), the leg envelope over stand, sit and rise, and the tail's sit path. Numbers on the sheet come
from checks/results.json (analyse.py). Writes concept-sheet.png. Runs on the MacBook (microduck-cad venv), light."""
import json, math
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
font_manager.fontManager.addfont("/Library/Fonts/Arial Unicode.ttf")
plt.rcParams["font.family"] = "Arial Unicode MS"
from matplotlib.patches import Polygon
from scipy.spatial import ConvexHull
import concept as C

HERE = Path(__file__).resolve().parent
CK = HERE / "checks"
R = json.loads((CK / "results.json").read_text())
P = R["concept_params"]
pts = np.load(CK / "pose_points.npz")
track = json.loads((CK / "baseline.json").read_text())["pad_centre_track_D"]

COL = dict(old="#9aa3ad", new="#e07b1a", bp="#2f6db3", pad="#c9a227", leg="#3a9a5b", env="#bfe3c9", path="#7a3fb0")


def box_corners(b):
    h = np.asarray(b["size"]); Rm = np.asarray(b["R"]); c = np.asarray(b["pos"])
    s = np.array([[i, j, k] for i in (-1, 1) for j in (-1, 1) for k in (-1, 1)])
    return (s * h) @ Rm.T + c


def hull_poly(P2):
    if len(P2) < 3:
        return P2
    h = ConvexHull(P2)
    return P2[h.vertices]


def draw_boxes(ax, boxes, axes, new_names):
    for b in boxes:
        q = box_corners(b)[:, axes]
        q = q[:, :]
        # clip to the floor for the side and rear views (boxes run a little below z 0 where their thickness pokes)
        if 2 in axes:
            k = axes.index(2)
            q[:, k] = np.maximum(q[:, k], 0)
        new = b["name"] in new_names or b["name"].startswith(("rail", "ramp"))
        ax.add_patch(Polygon(hull_poly(q), closed=True, fc=COL["new"] if new else COL["old"], ec="k", lw=0.4,
                             alpha=0.55 if new else 0.45, zorder=3))


def occupancy(ax, P3, axes, color, step=1.5, alpha=1.0, z=1):
    a, b = P3[:, axes[0]], P3[:, axes[1]]
    ia, ib = np.floor(a / step).astype(int), np.floor(b / step).astype(int)
    cells = np.unique(np.c_[ia, ib], axis=0)
    for (u, v) in cells:
        ax.add_patch(plt.Rectangle((u * step, v * step), step, step, fc=color, ec="none", alpha=alpha, zorder=z))


def main():
    boxes = C.dock_geometry(P)
    new_names = {"ramp_stop", "ramp_l", "ramp_r"}
    fig = plt.figure(figsize=(17, 12.5), dpi=130)
    gs = fig.add_gridspec(2, 3, height_ratios=[1.15, 1], width_ratios=[1.25, 1.25, 1.0])
    views = [("Top view (looking down)  x forward, y left", (0, 1), gs[0, 0], (-110, 0), (-60, 60)),
             ("Side view (from the robot's left)  x forward, z up", (0, 2), gs[0, 1], (-110, 0), (-2, 75)),
             ("Rear view (from behind the dock)  y left, z up", (1, 2), gs[0, 2], (-60, 60), (-2, 75))]
    for title, axes, g, xl, yl in views:
        ax = fig.add_subplot(g)
        ax.set_title(title, fontsize=10, loc="left")
        env = pts["leg_envelope"]
        sel = (env[:, 0] > xl[0] - 5) & (env[:, 0] < xl[1] + 40)
        occupancy(ax, env[sel], axes, COL["env"], step=2.0, z=1)
        occupancy(ax, pts["seated_legs"], axes, COL["leg"], step=1.5, alpha=0.55, z=2)
        draw_boxes(ax, boxes, list(axes), new_names)
        bp = pts["seated_backpack"]
        lower = bp[bp[:, 2] < 47.5]
        ax.add_patch(Polygon(hull_poly(lower[:, list(axes)]), closed=True, fc="none", ec=COL["bp"], lw=1.6, zorder=5))
        upper = bp[bp[:, 2] >= 46.5]
        if len(upper) > 3:
            ax.add_patch(Polygon(hull_poly(upper[:, list(axes)]), closed=True, fc="none", ec=COL["bp"], lw=0.8, ls="--", zorder=5))
        pads = pts["seated_pads"]
        for sgn in (1, -1):
            pp = pads[pads[:, 1] * sgn > 0]
            ax.add_patch(Polygon(hull_poly(pp[:, list(axes)]), closed=True, fc=COL["pad"], ec="k", lw=0.4, zorder=6))
        # leaves (contact zone) in the top view
        if axes == (0, 1):
            tip = C.LEAF_TIP_10_9 + P.get("bias", 0) + P.get("leaf_dx", 0)
            for sgn in (1, -1):
                ax.add_patch(plt.Rectangle((tip - 0.75, sgn * C.LEAF_Y - C.LEAF_W / 2), 2.1, C.LEAF_W, fc="#b5651d",
                                           ec="k", lw=0.4, zorder=7, alpha=0.9))
        tr = np.array([r[1:4] for r in track if 4.8 <= r[0] <= 6.0])
        ax.plot(tr[:, axes[0] if axes[0] < 3 else 0], tr[:, axes[1]], color=COL["path"], lw=1.2, zorder=8)
        ax.set_xlim(*xl); ax.set_ylim(*yl); ax.set_aspect("equal"); ax.grid(alpha=0.25, lw=0.4)
        ax.tick_params(labelsize=7)
        if axes == (0, 1):
            ann_top(ax)
        elif axes == (0, 2):
            ann_side(ax)
        else:
            ann_rear(ax)
    tx = fig.add_subplot(gs[1, :]); tx.axis("off")
    tx.text(0, 1, "\n".join(R["sheet_text"]), va="top", ha="left", fontsize=8.6, family="Arial Unicode MS")
    handles = [plt.Rectangle((0, 0), 1, 1, fc=COL["old"], alpha=.45), plt.Rectangle((0, 0), 1, 1, fc=COL["new"], alpha=.55),
               plt.Line2D([], [], color=COL["bp"], lw=1.6), plt.Rectangle((0, 0), 1, 1, fc=COL["pad"]),
               plt.Rectangle((0, 0), 1, 1, fc="#b5651d"), plt.Rectangle((0, 0), 1, 1, fc=COL["leg"], alpha=.55),
               plt.Rectangle((0, 0), 1, 1, fc=COL["env"]), plt.Line2D([], [], color=COL["path"], lw=1.2)]
    fig.legend(handles, ["dock A1 (released)", "new in the concept", "backpack lower tier, seated (dashed: upper tier)",
                         "charge pads", "5209 leaf contact zone", "legs, seated", "legs: everywhere in stand, sit and rise",
                         "pad centre path during the sit"], loc="upper right", ncol=4, fontsize=8, frameon=False,
               bbox_to_anchor=(0.99, 0.995))
    fig.suptitle(R["title"], x=0.01, ha="left", fontsize=13, fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.965))
    fig.savefig(HERE / "concept-sheet.png")
    print("wrote", HERE / "concept-sheet.png")


def dim(ax, p0, p1, text, off=(0, 0), fs=7):
    ax.annotate("", xy=p1, xytext=p0, arrowprops=dict(arrowstyle="<->", lw=0.7, color="k"), zorder=9)
    ax.text((p0[0] + p1[0]) / 2 + off[0], (p0[1] + p1[1]) / 2 + off[1], text, fontsize=fs, ha="center", va="center",
            zorder=10, bbox=dict(fc="white", ec="none", alpha=0.8, pad=0.5))


def geom():
    b = P.get("bias", 0)
    c, zv, zt, sl = P["c"], P["z_v"], P["z_top"], P["slope_deg"]
    run = (zt - zv) / math.tan(math.radians(sl))
    yl, yr = C.BP_Y[1] + c, C.BP_Y[0] - c
    return b, c, zv, zt, sl, run, yl, yr


def ann_top(ax):
    b, c, zv, zt, sl, run, yl, yr = geom()
    x0, x1 = P["x0"] + b, P["x1"] + b
    dim(ax, (x1 + 3, yr), (x1 + 3, yl), f"guide gap {yl - yr:.1f}\n(backpack 47.1 + 2 x {c})", off=(7, 0))
    dim(ax, (x0, yl + run + P['w'] + 4), (x1, yl + run + P['w'] + 4), f"rails x {x0:.0f} .. {x1:.0f}", off=(0, 3))
    dim(ax, (x1 + 3, yl), (x1 + 3, yl + run), f"lead-in {run:.1f}", off=(6, 2))
    ax.text(-76.5 + b, -50, f"stop face x {-76.5 + b:.1f}\n(A1: -76.5)", fontsize=7, ha="center")
    ax.text(-40, 52, "legs and feet are all\nforward of x -40 here", fontsize=7, ha="center", color=COL["leg"])


def ann_side(ax):
    b, c, zv, zt, sl, run, yl, yr = geom()
    ax.axhline(10.2, color=COL["pad"], lw=0.5, ls=":")
    ax.text(-8, 11.5, "pads seated z 9.9-10.3 (sim)", fontsize=7, ha="right")
    dim(ax, (P["x1"] + b + 4, 0), (P["x1"] + b + 4, zv), f"guide face {zv:.0f}", off=(7, 0))
    dim(ax, (P["x1"] + b + 14, 0), (P["x1"] + b + 14, zt), f"rail top {zt:.0f}", off=(7, 4))
    ax.text(-93 + b, 34, "45 deg rear lead-in\nfrom the stop top edge", fontsize=7, ha="center")
    ax.text(-58, 64, "tail path: arrives from the front,\n68 mm forward and 59 mm up", fontsize=7, color=COL["path"])


def ann_rear(ax):
    b, c, zv, zt, sl, run, yl, yr = geom()
    ax.text(0, 66, f"lead-in {sl:.0f} deg, capture +-{c + run:.1f} mm\nbeyond the guide face", fontsize=7, ha="center")
    dim(ax, (yr, zv + 2), (yl, zv + 2), f"{yl - yr:.1f}", off=(0, 2))


if __name__ == "__main__":
    main()
