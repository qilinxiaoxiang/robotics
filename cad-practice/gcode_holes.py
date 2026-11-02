#!/usr/bin/env python3
"""Read the fit-relevant slicer settings and the as-sliced hole wall paths from a sliced plate.

Usage: gcode_holes.py PLATE.gcode.3mf|PLATE.gcode [--dmin 1.0 --dmax 3.5] [--settings-only]

For every small round hole the slicer walls with arcs (G2/G3, arc fitting on) or closed polygons, it prints the wall
path diameter per feature ("Outer wall" is the loop touching the hole surface) and the hole that path leaves:
hole = outer-wall path diameter - outer wall line width. That is what the printer is told to make; physical shrink
comes on top. Bambu Studio and Orca headers carry "; key = value" setting lines, which are printed first.
"""
import math
import re
import sys
import zipfile
from collections import defaultdict

KEYS = ["printer_model", "printer_settings_id", "print_settings_id", "filament_settings_id", "curr_bed_type",
        "layer_height", "wall_loops", "wall_generator", "line_width", "outer_wall_line_width", "inner_wall_line_width",
        "xy_hole_compensation", "xy_contour_compensation", "elefant_foot_compensation", "enable_circle_compensation",
        "precise_outer_wall", "slice_closing_radius", "resolution", "enable_arc_fitting", "wall_sequence",
        "filament_flow_ratio", "outer_wall_speed", "nozzle_diameter", "filament_shrink", "hole_to_polyhole"]


def read_gcode(path):
    if path.endswith(".3mf"):
        z = zipfile.ZipFile(path)
        name = next(n for n in z.namelist() if n.endswith(".gcode") and n.startswith("Metadata/plate_"))
        return z.read(name).decode(errors="ignore").splitlines()
    return open(path, errors="ignore").read().splitlines()


def settings(lines):
    out, version = {}, None
    for ln in lines:
        if version is None and ("BambuStudio" in ln or "OrcaSlicer" in ln or "ElegooSlicer" in ln) and ln.startswith(";"):
            version = ln.strip("; ").strip()
        m = re.match(r"^; ([a-z_0-9]+) = (.*)$", ln)
        if m and m.group(1) in KEYS:
            out.setdefault(m.group(1), m.group(2))
    return version, out


def holes(lines, dmin, dmax):
    x = y = z = 0.0
    feat = ""
    arcs = defaultdict(list)          # (feature, cx, cy) -> [(z, d)]
    loop, loop_feat = [], ""

    def flush():
        nonlocal loop
        if len(loop) > 8 and math.dist(loop[0], loop[-1]) < 0.05:
            cx = sum(p[0] for p in loop) / len(loop)
            cy = sum(p[1] for p in loop) / len(loop)
            rs = [math.dist(p, (cx, cy)) for p in loop]
            if max(rs) - min(rs) < 0.06 and dmin <= 2 * sum(rs) / len(rs) <= dmax:
                arcs[(loop_feat, round(cx, 1), round(cy, 1))].append((z, 2 * sum(rs) / len(rs)))
        loop = []

    for ln in lines:
        if ln.startswith("; FEATURE:"):
            flush()
            feat = ln.split(":", 1)[1].strip()
            continue
        if ln.startswith("; Z_HEIGHT:") or ln.startswith(";Z:"):
            flush()
            z = float(ln.split(":")[1])
            continue
        g = ln[:2]
        if g not in ("G0", "G1", "G2", "G3"):
            continue
        v = {k: float(n) for k, n in re.findall(r"([XYIJE])(-?[\d.]+)", ln)}
        nx, ny = v.get("X", x), v.get("Y", y)
        extruding = v.get("E", 0.0) > 0
        if g in ("G2", "G3") and "I" in v and extruding and "wall" in feat.lower():
            d = 2 * math.hypot(v["I"], v["J"])
            if dmin <= d <= dmax:
                arcs[(feat, round(x + v["I"], 1), round(y + v["J"], 1))].append((z, d))
        if g == "G1" and extruding and "wall" in feat.lower():
            if not loop:
                loop.append((x, y))
                loop_feat = feat
            loop.append((nx, ny))
        elif ("X" in v or "Y" in v) and not extruding:
            flush()
        x, y = nx, ny
    flush()
    return arcs


def main(argv):
    path = argv[1]
    dmin = float(argv[argv.index("--dmin") + 1]) if "--dmin" in argv else 1.0
    dmax = float(argv[argv.index("--dmax") + 1]) if "--dmax" in argv else 3.5
    lines = read_gcode(path)
    version, s = settings(lines)
    print(f"# {path.split('/')[-1]}\n# slicer: {version}")
    for k in KEYS:
        if k in s:
            print(f"  {k} = {s[k]}")
    if "--settings-only" in argv:
        return 0
    ow = float(re.split(r"[,; ]", s.get("outer_wall_line_width", "0.42"))[0] or 0.42)
    arcs = holes(lines, dmin, dmax)
    # merge clusters that drift by one 0.1 bin; report the outer-wall loops (the hole surface)
    rows = []
    for (feat, cx, cy), v in arcs.items():
        if len(v) < 4 or feat != "Outer wall":
            continue
        ds = sorted(d for _, d in v)
        med = ds[len(ds) // 2]
        rows.append((cx, cy, len(v), min(t for t, _ in v), max(t for t, _ in v), med, med - ow))
    rows.sort()
    print(f"# outer-wall hole loops ({len(rows)}): centre, layers, z span, path d, hole d = path - {ow}")
    for cx, cy, n, z0, z1, med, hole in rows:
        print(f"  ({cx:7.1f}, {cy:7.1f})  n {n:3d}  z {z0:5.1f}-{z1:5.1f}  path {med:.3f}  hole {hole:.3f}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
