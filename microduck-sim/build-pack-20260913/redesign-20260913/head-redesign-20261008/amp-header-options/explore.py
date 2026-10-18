import sys, numpy as np, matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from scene import load, SCRATCH
M, src, nb = load()
print({k: v for k, v in src.items() if not k.startswith('head_pi_')})
cols = plt.cm.tab20(np.linspace(0, 1, 20))
def sec(ax, normal, origin, dims, title):
    for i, (k, m) in enumerate(sorted(M.items())):
        s = m.section(plane_origin=origin, plane_normal=normal)
        if s is None: continue
        for e in s.entities:
            p = s.vertices[e.points]
            ax.plot(p[:, dims[0]], p[:, dims[1]], lw=0.6, color=('k' if k=='head_cap' else 'r' if k=='amplifier' else cols[i % 20]),
                    label=k if not k.startswith('head_pi_') else None)
    ax.set_title(title); ax.set_aspect('equal'); ax.grid(alpha=.3)
fig, axs = plt.subplots(2, 3, figsize=(24, 15))
sec(axs[0,0], [0,0,1], [0,0,133.3], (0,1), 'z=133.3 (x right, y up)')
sec(axs[0,1], [0,0,1], [0,0,136.0], (0,1), 'z=136')
sec(axs[0,2], [0,0,1], [0,0,140.0], (0,1), 'z=140')
sec(axs[1,0], [1,0,0], [26,0,0], (1,2), 'x=26 (y right, z up)')
sec(axs[1,1], [0,1,0], [0,31.26,0], (0,2), 'y=31.26 (x right, z up)')
sec(axs[1,2], [0,1,0], [0,24,0], (0,2), 'y=24')
for a in axs.flat:
    h, l = a.get_legend_handles_labels(); d = dict(zip(l, h))
axs[0,0].legend(d.values(), d.keys(), fontsize=6, loc='lower left')
plt.tight_layout(); plt.savefig(SCRATCH / 'explore.png', dpi=70)
