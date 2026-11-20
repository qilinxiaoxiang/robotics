"""Sheet of the built battery backpack V2 rev M (build/ STLs and bought-part envelopes): back view (what you see behind the
robot), front view (the face on the OpenRB pack), a side section through the battery column (y -6.3) and the bought parts
placed in the frame with the cap off. Numbers in the footer come from checks/checks.json and checks/legsit.json.

    ~/.venvs/flight-cad/bin/python render_sheet.py        (after build_v2.py, checks.py, legsit.py; writes sheet.png)
"""
import json, sys
from pathlib import Path
import numpy as np, trimesh
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); import build_v2 as B  # noqa: E402
BUILD = HERE / "build"
ORANGE, CAPC = (0.96, 0.55, 0.20), (0.93, 0.66, 0.38)
PC = {"battery": (0.25, 0.45, 0.80), "DFR1202": (0.55, 0.25, 0.65), "Swann": (0.2, 0.2, 0.2), "balance": (0.95, 0.95, 0.95),
      "foam": (0.7, 0.7, 0.7), "tape": (0.8, 0.8, 0.6), "plug": (0.85, 0.7, 0.1)}


def col(n):
    for k, c in PC.items():
        if k in n: return c
    return (0.5, 0.5, 0.5)


def shade(t, base, light=(-0.5, 0.3, 0.8)):
    l = np.array(light) / np.linalg.norm(light)
    k = 0.45 + 0.55 * np.clip(t.face_normals @ l, 0, 1)
    return np.clip(np.outer(k, base), 0, 1)


def draw(ax, t, base, alpha=1.0, light=(-0.5, 0.3, 0.8)):
    fc = shade(t, base, light); pc = Poly3DCollection(t.vertices[t.faces], facecolors=fc, edgecolor="none", alpha=alpha)
    ax.add_collection3d(pc)


def setup(ax, title, elev, azim, lim=((-80, -40), (-36, 36), (-50, 46))):
    ax.set_title(title, fontsize=11); ax.view_init(elev=elev, azim=azim)
    ax.set_xlim(*lim[0]); ax.set_ylim(*lim[1]); ax.set_zlim(*lim[2]); ax.set_box_aspect([lim[i][1] - lim[i][0] for i in range(3)])
    ax.set_xlabel("x"); ax.set_ylabel("y"); ax.set_zlabel("z"); ax.tick_params(labelsize=6)


def main():
    frame = trimesh.load(BUILD / "battery_v2_frame-world.stl", force="mesh")
    cap = trimesh.load(BUILD / "battery_v2_cap-world.stl", force="mesh")
    parts = {n: B.to_tm(M) for n, M in B.bought_parts().items()}
    ck = json.loads((HERE / "checks/checks.json").read_text())
    ls = json.loads((HERE / "checks/legsit.json").read_text()) if (HERE / "checks/legsit.json").exists() else None
    fig = plt.figure(figsize=(18, 13), dpi=110, facecolor="white")
    ax = fig.add_subplot(2, 2, 1, projection="3d"); setup(ax, "Back view (from behind the robot): cap, Swann 39 rocker, balance-plug notch", 12, 200)
    draw(ax, frame, ORANGE, light=(-1, 0.3, 0.5)); draw(ax, cap, CAPC, light=(-1, 0.3, 0.5))
    for n in ("Swann 39 switch", "Swann 39 snap wings"): draw(ax, parts[n], PC["Swann"], light=(-1, 0.3, 0.5))
    draw(ax, parts["balance plug (JST XH-3P)"], PC["balance"], light=(-1, 0.3, 0.5))
    ax = fig.add_subplot(2, 2, 2, projection="3d"); setup(ax, "Front view (face on the OpenRB pack)", 12, 20)
    draw(ax, frame, ORANGE, light=(1, 0.3, 0.5))
    # side section through the battery column
    ax = fig.add_subplot(2, 2, 3); y0 = (B.BAT[0][1] + B.BAT[1][1]) / 2
    for t, c in ((frame, ORANGE), (cap, CAPC)):
        s = t.section(plane_origin=[0, y0, 0], plane_normal=[0, 1, 0])
        if s is None: continue
        for e in s.discrete: ax.fill(e[:, 0], e[:, 2], color=c, alpha=0.9, lw=0.5, ec="k")
    for n, t in parts.items():
        s = t.section(plane_origin=[0, y0, 0], plane_normal=[0, 1, 0])
        if s is None: continue
        for e in s.discrete: ax.fill(e[:, 0], e[:, 2], color=col(n), alpha=0.45, lw=0.6, ec=col(n))
        c = t.bounds.mean(0)
        if t.bounds[0][1] <= y0 <= t.bounds[1][1] and "tape" not in n:
            ax.text(c[0], c[2], n.split(" (")[0], fontsize=7, ha="center", va="center")
    ax.axhline(-46.0, color="r", lw=0.8, ls="--"); ax.text(-79, -45.5, "z -46 (seated 10 mm)", color="r", fontsize=7)
    ax.set_aspect("equal"); ax.set_xlim(-80, -40); ax.set_ylim(-50, 46); ax.grid(alpha=0.3)
    ax.set_title(f"Side section y = {y0:.1f} (battery column centre), x forward to the right", fontsize=11)
    ax.set_xlabel("x mm"); ax.set_ylabel("z mm")
    ax = fig.add_subplot(2, 2, 4, projection="3d"); setup(ax, "Parts placed, cap off (frame translucent)", 22, 215)
    draw(ax, frame, ORANGE, alpha=0.25)
    for n, t in parts.items():
        draw(ax, t, col(n), alpha=0.95)
    hs = [plt.Rectangle((0, 0), 1, 1, color=c) for c in PC.values()]
    ax.legend(hs, list(PC), fontsize=7, loc="upper left")
    s = ck["solids"]; legs = ls["legs"] if ls else {}
    foot = (f"Frame {s['frame']['volume_cm3']} cm3, cap {s['cap']['volume_cm3']} cm3 (solid); overlaps with robot, bought parts, "
            f"flight pack: 0; wall check fails: {sum(len(v['fail_regions']) for v in ck['wall_check'].values())}; fits: "
            f"{ck['fit_check']['H2S']['tail'][-1]}; seated clearance {ls['seated_min_mm'] if ls else '?'} mm; legs "
            f"{', '.join(f'{k} {v['min_mm']} mm' for k, v in legs.items())}. Switch Swann 39 (moved over), charging on the HTRC B3 through the balance plug.")
    fig.suptitle("MicroDuck battery backpack V2 rev M (minimal): built frame and cap (battery-v2-cad-20261120)", fontsize=14)
    fig.text(0.02, 0.01, foot, fontsize=9)
    fig.tight_layout(rect=(0, 0.03, 1, 0.97)); fig.savefig(HERE / "sheet.png"); plt.close(fig)
    print(HERE / "sheet.png")


if __name__ == "__main__":
    main()
