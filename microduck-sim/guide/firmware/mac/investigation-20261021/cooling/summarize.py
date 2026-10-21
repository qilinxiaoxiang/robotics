import sys, statistics
path = sys.argv[1]
boots = []
cur = None
for line in open(path):
    if line.startswith('# boot'):
        cur = {'hdr': line.strip(), 'rows': []}
        boots.append(cur)
        continue
    p = line.split()
    if len(p) < 14 or cur is None:
        continue
    try:
        t = float(p[0]); temps = [float(x) for x in p[1:9]]
        curf = int(p[10]); mx = int(p[12]); load = float(p[14])
    except Exception:
        continue
    cur['rows'].append((t, temps, curf, mx, load))
for i, b in enumerate(boots):
    r = b['rows']
    if not r:
        print(i, b['hdr'], 'no rows'); continue
    t0 = r[0][0]; t1 = r[-1][0]
    cpub = [x[1][1] for x in r]; cpul = [x[1][0] for x in r]; skin = [x[1][7] for x in r]; ddr=[x[1][6] for x in r]
    cf = [x[2] for x in r]; mxs = [x[3] for x in r]
    print(f"boot {i+1}: {b['hdr'][7:26]} rows {len(r)} span {t1-t0:.1f}s")
    print(f"  cpub first {cpub[0]:.1f} min {min(cpub):.1f} max {max(cpub):.1f} last {cpub[-1]:.1f} | cpul max {max(cpul):.1f} | ddr max {max(ddr):.1f} | skin {min(skin):.1f}-{max(skin):.1f}")
    print(f"  cur MHz min {min(cf)} max {max(cf)} median {statistics.median(cf)} | max-cap values {sorted(set(mxs))}")
    # time share by cap
    from collections import Counter
    c = Counter(mxs); tot = len(mxs)
    print("  cap share:", {k: f"{v/tot*100:.0f}%" for k, v in sorted(c.items())})
    # every 60 s print a sample
    nxt = t0
    for x in r:
        if x[0] >= nxt:
            print(f"   +{x[0]-t0:6.1f}s cpub {x[1][1]:.1f} cpul {x[1][0]:.1f} ddr {x[1][6]:.1f} skin {x[1][7]:.1f} cur {x[2]} max {x[3]} load {x[4]}")
            nxt += 10
