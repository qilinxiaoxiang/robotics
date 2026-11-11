"""Fast pre-gate check of the cables near the flight pack, by the print gate's own rule (guide/content/interference-audit/
cables.py: drawn spline and polyline at 0.25 mm, depth = radius + signed distance, a run over 0.1 mm is a finding, a run
within 8 mm of either cable end is an end finding, everything else is mid-route and fails the gate).
Solids: the guide's parts (guide-data.json) with the flight pack replaced by the current cad/build meshes and boxes, exactly as
guide/build_flight_guide.py builds them; swap-alternative sets are respected (ia_lib.apart). Cables: the flight leads from
checks/lead_lengths.json (as the guide draws them) plus every guide cable that comes within 10 mm of the flight parts.
Writes checks/lead_check.json; exit 1 on any mid-route finding.
    /tmp/microduck-cad-venv/bin/python cad/lead_check.py       (after lead_lengths.py; about 1 min)
"""
import json
import sys
from pathlib import Path

import numpy as np
import trimesh

H = Path(__file__).resolve().parent
FLIGHT = H.parent
SIM = FLIGHT.parents[1]
IA = SIM / "guide" / "content" / "interference-audit"
sys.path.insert(0, str(IA))
sys.path.insert(0, str(FLIGHT / "guide"))
import cables as C                                   # noqa: E402  the gate's sampling and run rule
from ia_lib import alternate_of, apart, decode_guide_part, load_guide  # noqa: E402
import build_flight_guide as FG                      # noqa: E402  current flight meshes and cables

THRESH, END = C.THRESH, 8.0


def mesh_of(p):
    v, f = decode_guide_part(p)
    return trimesh.Trimesh(v, f, process=False)


def main():
    g = load_guide()
    frag_keys = {f"fp_{k}" if k in FG.BOUGHT + FG.REMOUNT else k: k for k in FG.PARTS}
    solids = {}
    for k, src in frag_keys.items():
        p = FG.PARTS[src]
        if p["module"] == "duck" and k == src:
            continue                                  # duck part under its own guide key: taken from guide-data below
        solids[k] = mesh_of(p)
    alt = alternate_of(g)
    for k in solids:
        alt.setdefault(k, "flight-pack")
    lo = np.min([m.bounds[0] for m in solids.values()], axis=0) - 10
    hi = np.max([m.bounds[1] for m in solids.values()], axis=0) + 10
    guide_parts = {p["key"]: p for p in g["parts"] if p["key"] not in solids}
    cables = [dict(c) for c in FG.CABLES]
    ids = {c["id"] for c in cables}
    for c in g["cables"]:
        x = np.array(c["path"], float)
        if c["id"] not in ids and np.all(x.max(0) >= lo) and np.all(x.min(0) <= hi):
            cables.append(c)
    loaded = dict(solids)
    findings, cov = [], []
    for c in cables:
        r = float(c.get("radius") or 0.9)
        for mode, (x, seg) in (("drawn-spline", C.spline_samples(c["path"])), ("polyline", C.polyline_samples(c["path"]))):
            s = C.arclen(x)
            clo, chi = x.min(0) - r - 0.2, x.max(0) + r + 0.2
            keys = [k for k in list(solids) + list(guide_parts)]
            for k in keys:
                if apart(alt, c["id"], k):
                    continue
                if k in solids:
                    b = solids[k].bounds
                else:
                    b = np.array(guide_parts[k]["bounds"])
                if np.any(b[1] < clo) or np.any(b[0] > chi):
                    continue
                near = np.all((x >= b[0] - r - 0.2) & (x <= b[1] + r + 0.2), axis=1)
                if not near.any():
                    continue
                if k not in loaded:
                    loaded[k] = mesh_of(guide_parts[k])
                m = loaded[k]
                sd = np.full(len(x), -np.inf)
                idx = np.flatnonzero(near)
                for q in range(0, len(idx), 64):
                    sd[idx[q:q + 64]] = trimesh.proximity.signed_distance(m, x[idx[q:q + 64]])
                depth = sd + r
                for i, j in C.runs(depth > THRESH):
                    kk = i + int(np.argmax(depth[i:j + 1]))
                    at = "start" if s[i] < END else ("end" if s[-1] - s[j] < END else None)
                    findings.append(dict(cable=c["id"], mode=mode, part=k, depthMm=round(float(depth[kk]), 2), atEnd=at,
                                         deepest=np.round(x[kk], 1).tolist(), runStart=np.round(x[i], 1).tolist(),
                                         runEnd=np.round(x[j], 1).tolist(), arc=[round(float(s[i]), 1), round(float(s[j]), 1)],
                                         segments=sorted({int(q) for q in seg[i:j + 1]})))
        cov.append(c["id"])
    mid = [f for f in findings if not f["atEnd"]]
    (H / "checks" / "lead_check.json").write_text(json.dumps(dict(threshold=THRESH, cables=cov, mid=mid,
                                                                  ends=[f for f in findings if f["atEnd"]]), indent=1))
    print(f"{len(cov)} cables, {len(findings)} findings, {len(mid)} mid-route")
    for f in mid:
        print(f"  MID {f['cable']:8s} {f['mode']:12s} {f['part']:24s} {f['depthMm']:5.2f} at {f['deepest']} seg {f['segments']}")
    for f in findings:
        if f["atEnd"]:
            print(f"  end {f['cable']:8s} {f['part']:24s} {f['depthMm']:5.2f} {f['atEnd']}")
    sys.exit(1 if mid else 0)


if __name__ == "__main__":
    main()
