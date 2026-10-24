#!/usr/bin/env python3
"""Read the drill template PDF back as a printer would see it.

Runs under the system python3 (PyMuPDF). Prints one JSON object on stdout:
page size, the two check bars measured from the vector content, the hole
crosshair centres, the cut line, the screw-hole marks, and the bar lengths
measured on raster renders from two independent engines (poppler pdftoppm
and macOS Quick Look / PDFKit, the engine behind Preview).

Usage: python3 readback_pdf.py drill-template.pdf <render_dir>
"""
import json
import subprocess
import sys
from pathlib import Path

import fitz
import numpy as np

PT_PER_MM = 72 / 25.4


def close(c, ref, tol=0.02):
    return c is not None and all(abs(a - b) < tol for a, b in zip(c, ref))


def main():
    pdf = Path(sys.argv[1]).resolve()
    rdir = Path(sys.argv[2]).resolve()
    rdir.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(pdf)
    page = doc[0]
    W, H = page.rect.width, page.rect.height
    out = {"page_pt": [W, H], "page_count": len(doc),
           "widgets": len(list(page.widgets() or []))}
    bars, hl, vl, cut, screw = [], [], [], [], []
    for d in page.get_drawings():
        r = d["rect"]
        col, fill, wid = d.get("color"), d.get("fill"), d.get("width") or 0
        if close(fill, (0, 0, 0)) and abs(r.height - 2.0 * PT_PER_MM) < 0.3:
            bars.append({"x0_pt": r.x0, "x1_pt": r.x1, "width_pt": r.width,
                         "y_mid_pt": (r.y0 + r.y1) / 2})
        if close(col, (0.8, 0.0, 0.0)) and wid < 0.4:
            for it in d["items"]:
                if it[0] == "l":
                    p, q = it[1], it[2]
                    mid = ((p.x + q.x) / 2, H - (p.y + q.y) / 2)
                    (hl if abs(p.y - q.y) < 1e-3 else vl).append(mid)
        if close(col, (0, 0, 0)) and abs(wid - 0.8) < 0.05:
            pts = []
            for it in d["items"]:
                if it[0] == "l":
                    pts += [(it[1].x, H - it[1].y), (it[2].x, H - it[2].y)]
            cut.append(pts)
        if close(col, (0.0, 0.31, 0.75)) and d["items"] and d["items"][0][0] == "c":
            screw.append(((r.x0 + r.x1) / 2, H - (r.y0 + r.y1) / 2, r.width))
    centres = []
    for h in hl:
        for v in vl:
            if abs(h[0] - v[0]) < 0.05 and abs(h[1] - v[1]) < 0.05:
                centres.append(((h[0] + v[0]) / 2, (h[1] + v[1]) / 2))
    out["bars"] = sorted(bars, key=lambda b: -b["width_pt"])
    out["crosshair_centres_pt"] = centres
    out["cut_lines_pt"] = sorted(cut, key=len, reverse=True)[:1]
    out["screw_marks_pt"] = screw

    # raster renders: poppler at 600 dpi, Quick Look (PDFKit) at 300 dpi
    renders = {}
    stem = rdir / "page-poppler"
    subprocess.run(["pdftoppm", "-r", "600", "-gray", "-png", "-singlefile",
                    str(pdf), str(stem)], check=True)
    renders["poppler_600dpi"] = (Path(str(stem) + ".png"), 600.0)
    ql = rdir / "quicklook"
    ql.mkdir(exist_ok=True)
    subprocess.run(["qlmanage", "-t", "-s", "3300", "-o", str(ql), str(pdf)],
                   check=True, capture_output=True)
    qpng = ql / (pdf.name + ".png")
    from PIL import Image
    im = Image.open(qpng)
    renders["quicklook_pdfkit"] = (qpng, im.size[1] / (H / 72))  # px per inch
    meas = {}
    for name, (png, dpi) in renders.items():
        a = np.asarray(Image.open(png).convert("L"), dtype=float)
        sc = a.shape[1] / (W / 72 * dpi)  # correct if the engine padded width
        res = {"file": str(png), "px": list(a.shape[::-1]), "dpi_used": dpi}
        for b in out["bars"]:
            row = int(round(b["y_mid_pt"] / 72 * dpi))
            line = a[row] < 128
            x0 = int(b["x0_pt"] / 72 * dpi) + 3
            # walk out from inside the bar to its dark-run ends
            i0 = x0
            while i0 > 0 and line[i0 - 1]:
                i0 -= 1
            i1 = x0
            while i1 < len(line) - 1 and line[i1 + 1]:
                i1 += 1
            mm = (i1 - i0 + 1) / dpi * 25.4 / sc
            res[f"bar_{round(b['width_pt'] / PT_PER_MM)}mm_measured_mm"] = round(mm, 3)
        meas[name] = res
    out["raster"] = meas
    print(json.dumps(out))


if __name__ == "__main__":
    main()
