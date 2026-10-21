import sys, datetime as dt
path=sys.argv[1]; boots=[]; cur=None
for line in open(path):
    if line.startswith('# boot'):
        cur={'hdr':line.split()[2],'rows':[]}; boots.append(cur); continue
    p=line.split()
    try: t=float(p[0]); cpub=float(p[2]); cpul=float(p[1]); curf=int(p[10]); mx=int(p[12])
    except Exception: continue
    cur['rows'].append((t,cpul,cpub,curf,mx))
u=lambda t: dt.datetime.fromtimestamp(t,dt.timezone.utc).strftime('%H:%M:%S.%f')[:-4]
prev_end=None
for i,b in enumerate(boots):
    r=b['rows']; t0=r[0][0]; t1=r[-1][0]
    dts=[r[k+1][0]-r[k][0] for k in range(len(r)-1)]
    rate=len(r)/(t1-t0) if t1>t0 else 0
    gap = (t0-prev_end) if prev_end else None
    hottest=max(max(x[1],x[2]) for x in r)
    print(f"start#{i+1} hdr {b['hdr']} first {u(t0)} last {u(t1)} rows {len(r)} rate {rate:.1f}/s maxgap {max(dts) if dts else 0:.2f}s gap_from_prev {gap if gap is None else round(gap,1)} s  hottest {hottest}")
    prev_end=t1
