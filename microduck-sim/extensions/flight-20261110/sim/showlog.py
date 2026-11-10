"""Print a flight log (sim/flight.py --log) every N rows: t, base xyz, rpy deg, z_est, surf, x_est, targets, u, T, V, I, range, leg tau, phase."""
import sys
import numpy as np

L = np.load(sys.argv[1])["log"]
step = int(sys.argv[2]) if len(sys.argv) > 2 else 10
for r in L[::step]:
    print(f"t {r[0]:5.2f} xyz {r[1]:6.3f} {r[2]:6.3f} {r[3]:6.3f} rpy {np.degrees(r[4]):6.1f} {np.degrees(r[5]):6.1f} {np.degrees(r[6]):6.1f} "
          f"zest {r[7]:5.2f} surf {r[8]:4.2f} xe {r[9]:5.2f} tz {r[11]:5.2f} tx {r[12]:5.2f} u {np.round(r[13:17], 2)} "
          f"T {np.round(r[17:21], 1)} V {r[21]:4.1f} I {r[22]:5.1f} rng {r[23]:4.2f} tau {r[24]:4.2f} ph {int(r[25])}")
