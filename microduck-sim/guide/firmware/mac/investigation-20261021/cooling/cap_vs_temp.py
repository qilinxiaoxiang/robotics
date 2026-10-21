import sys, collections
rows=[]
for line in open(sys.argv[1]):
    if line.startswith('#'): continue
    p=line.split()
    try: t=float(p[0]); temps=[float(x) for x in p[1:9]]; cur=int(p[10]); mx=int(p[12]); load=float(p[14])
    except Exception: continue
    rows.append((t,temps,cur,mx,load))
# bin by cpub temp (index1) and by max of cpul/cpub
bins=collections.defaultdict(lambda: collections.Counter())
for t,temps,cur,mx,load in rows:
    T=max(temps[0],temps[1]); b=int(T)
    bins[b]['full' if mx==1794 else 'capped']+=1
print("maxCPU zone temp bin -> share of samples with cap 1794 MHz (unthrottled)")
for b in sorted(bins):
    c=bins[b]; n=c['full']+c['capped']
    print(f"  {b}-{b+1} C: n={n:4d} full={c['full']/n*100:5.1f}%")
print("overall max temps:", max(max(r[1][0],r[1][1]) for r in rows), "min", min(min(r[1][0],r[1][1]) for r in rows))
print("rows",len(rows), "span s", rows[-1][0]-rows[0][0])
print("zone order: cpul cpub cpul_idle cpub_idle gpu npu ddr skin")
