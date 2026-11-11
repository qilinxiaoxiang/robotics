"""Marked side and inlet views of the active fan set (flight_params.FAN) for cad/FAN-MEASURE.md: letters A..K name the
caliper measurements, drawn from the provisional parameters (so the figure shows what the CAD assumes today).
    /tmp/microduck-cad-venv/bin/python cad/fan_measure_figure.py      -> cad/fan-measure.png
"""
import math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Polygon, Rectangle

import flight_params as Pm

H = Path(__file__).resolve().parent
F = Pm.FAN


def dim(ax, p, q, label, off=(0, 0), color="#c0392b"):
    ax.annotate("", xy=q, xytext=p, arrowprops=dict(arrowstyle="<->", color=color, lw=1.4))
    ax.text((p[0] + q[0]) / 2 + off[0], (p[1] + q[1]) / 2 + off[1], label, color=color, fontsize=15, fontweight="bold",
            ha="center", va="center", bbox=dict(fc="white", ec="none", pad=0.5))


def side(ax):
    """Side view: t runs left to right (inlet on the left), radius up and down."""
    def body(t0, t1, r0, r1=None, fc="#555"):
        r1 = r0 if r1 is None else r1
        ax.add_patch(Polygon([(t0, r0), (t1, r1), (t1, -r1), (t0, -r0)], closed=True, fc=fc, ec="black", lw=0.8))
    body(*F["spinner_t"], 1.5, F["spinner_od"] / 2, fc="#333")
    body(*F["lip_t"], F["lip_od"] / 2, F["duct_od"] / 2 + 0.5)
    body(*F["duct_t"], F["duct_od"] / 2)
    body(*F["rim_t"], F["rim_od"] / 2)
    body(*F["stator_t"], F["stator_od"][0] / 2, F["stator_od"][1] / 2, fc="#444")
    body(*F["motor_t"], F["motor_od"] / 2, fc="#1abc9c")
    e0, e1 = F["ear_t"]
    ax.add_patch(Rectangle((e0, F["duct_od"] / 2), e1 - e0, F["ear_r"] - F["duct_od"] / 2, fc="#888", ec="black"))
    ax.add_patch(Rectangle((e0, -F["ear_r"]), e1 - e0, F["ear_r"] - F["duct_od"] / 2, fc="#888", ec="black"))
    lt = sum(F["lead_t"]) / 2
    ax.plot([lt, lt + 6, lt + 30], [F["motor_od"] / 2, F["motor_od"] / 2 + 8, F["motor_od"] / 2 + 12], color="#d35400", lw=3)
    ax.axvline(0, color="#2980b9", lw=1, ls="--")
    ax.text(-1, F["lip_od"] / 2 + 33, "lip face (t = 0)", color="#2980b9", fontsize=10, ha="right")
    top = F["lip_od"] / 2 + 4
    dim(ax, (-3, -F["lip_od"] / 2), (-3, F["lip_od"] / 2), "A", off=(-3, 0))
    dim(ax, (0, top), (F["duct_t"][0], top), "B", off=(0, 3))
    dim(ax, (F["duct_t"][1] - 4, -F["duct_od"] / 2), (F["duct_t"][1] - 4, F["duct_od"] / 2), "C", off=(-3, 0))
    dim(ax, (0, top + 9), (F["rim_t"][0], top + 9), "D", off=(0, 3))
    dim(ax, (F["rim_t"][1] + 1.5, -F["rim_od"] / 2), (F["rim_t"][1] + 1.5, F["rim_od"] / 2), "E", off=(3, 6))
    dim(ax, (0, -top - 4), (e0, -top - 4), "F1", off=(0, -3))
    dim(ax, (0, -top - 12), (e1, -top - 12), "F2", off=(0, -3))
    dim(ax, (F["motor_t"][0] + 8, -F["motor_od"] / 2), (F["motor_t"][0] + 8, F["motor_od"] / 2), "G", off=(4, 0))
    dim(ax, (0, -top - 20), (F["motor_t"][1], -top - 20), "H", off=(0, -3))
    dim(ax, (F["spinner_t"][0], top + 18), (0, top + 18), "I", off=(0, 3))
    dim(ax, (0, top + 27), (lt, top + 27), "J", off=(0, 3))
    ax.set_xlim(F["spinner_t"][0] - 8, F["motor_t"][1] + 34)
    ax.set_ylim(-F["lip_od"] / 2 - 32, F["lip_od"] / 2 + 36)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title("Side view (inlet left, motor right)", fontsize=12)


def inlet(ax):
    """Looking into the inlet: ears and the lead direction (provisional: ears at lead -45 / +135 deg, counter-clockwise)."""
    ax.add_patch(Circle((0, 0), F["lip_od"] / 2, fc="#666", ec="black"))
    ax.add_patch(Circle((0, 0), F["duct_od"] / 2 - 1, fc="#ddd", ec="black"))
    ax.add_patch(Circle((0, 0), F["spinner_od"] / 2, fc="#333"))
    lead = 0.0
    for o in F["ear_from_lead_deg"]:
        a = math.radians(lead + o)
        c, s = math.cos(a), math.sin(a)
        w, r0, r1 = F["ear_w"] / 2, F["duct_od"] / 2, F["ear_r"]
        ax.add_patch(Polygon([(r0 * c - w * s, r0 * s + w * c), (r1 * c - w * s, r1 * s + w * c),
                              (r1 * c + w * s, r1 * s - w * c), (r0 * c + w * s, r0 * s - w * c)], fc="#888", ec="black"))
    ax.plot([F["lip_od"] / 2, F["lip_od"] / 2 + 25], [0, 0], color="#d35400", lw=4)
    ax.text(F["lip_od"] / 2 + 12, 4, "leads", color="#d35400", fontsize=11)
    a = math.radians(-45)
    dim(ax, (-F["ear_r"] * math.cos(a), -F["ear_r"] * math.sin(a)), (F["ear_r"] * math.cos(a), F["ear_r"] * math.sin(a)), "K",
        off=(5, 5))
    a = math.radians(F["ear_from_lead_deg"][1])
    ax.text((F["ear_r"] + 7) * math.cos(a), (F["ear_r"] + 7) * math.sin(a), "M", color="#c0392b", fontsize=15, fontweight="bold",
            ha="center", va="center")
    ax.text(-30, -42, "L: angle from the leads to the nearest ear,\nclockwise or counter-clockwise (seen like this)", fontsize=10)
    ax.set_xlim(-42, 62)
    ax.set_ylim(-50, 42)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title("Looking into the inlet", fontsize=12)


def main():
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(15, 6.5), gridspec_kw=dict(width_ratios=[1.5, 1]))
    side(a1)
    inlet(a2)
    fig.suptitle(f"{Pm.FAN_ID}: what to measure (shapes drawn from today's provisional numbers)", fontsize=13)
    fig.tight_layout()
    fig.savefig(H / "fan-measure.png", dpi=110)
    print("wrote", H / "fan-measure.png")


if __name__ == "__main__":
    main()
