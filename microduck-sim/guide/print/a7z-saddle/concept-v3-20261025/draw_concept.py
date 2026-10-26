"""V3 concept sketch (2026-10-25 evening, after Shawn rejected the tray + lid-pressure scheme): section at x -25 viewed from behind.
Left: V3 concept (saddle floor is the board carrier, side lugs screwed into the shell flanks, lid is a cover). Right: V2 as released.
    /tmp/microduck-cad-venv/bin/python draw_concept.py"""
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt, numpy as np
from matplotlib.patches import Rectangle, Polygon, Circle
fig, axs = plt.subplots(1, 2, figsize=(15, 7.2))
yy = np.linspace(-36, 36, 200); roof = 42.0 - 0.004 * yy**2
def common(ax):
    ax.fill_between(yy, roof - 2.0, roof, color='#dddddd')
    for s in (-1, 1):
        ax.add_patch(Polygon([[s*34, roof[-1]-2], [s*36.5, roof[-1]-2], [s*36.5, 20], [s*34.5, 20]], color='#dddddd'))
        ax.add_patch(Rectangle((s*34.4 - (1.6 if s>0 else 0), 42.5), 1.6, 23.3, color='#f28c28'))
    ax.add_patch(Rectangle((-32.5, 48), 65, 1.0, color='#2e8b57')); ax.add_patch(Rectangle((-8, 49), 16, 1.6, color='#4477aa'))
    ax.add_patch(Rectangle((-8, 50.6), 16, 0.6, color='#88ccee')); ax.add_patch(Rectangle((-30, 51.2), 60, 3.1, color='#999999'))
    for i in range(12): ax.add_patch(Rectangle((-29 + i*5.1, 54.3), 2.2, 6.9, color='#aaaaaa'))
    for y in (-29, 29): ax.add_patch(Rectangle((y-2.5, 49), 5, 2.2, color='#8a8a8a'))
    ax.add_patch(Rectangle((-34.4, 65.8), 68.8, 1.6, color='#f28c28'))
    ax.set_xlim(-52, 52); ax.set_ylim(18, 72); ax.set_aspect('equal'); ax.set_xlabel('y (mm), robot left is +y')
ax = axs[0]; common(ax); ax.set_title('V3 concept, section at x -25 from behind: saddle floor IS the board carrier', fontsize=11)
m = (yy > -34.4) & (yy < 34.4); ax.fill_between(yy[m], roof[m] + 0.3, 45.2, color='#f28c28', alpha=.9)
for s in (-1, 1):
    ax.add_patch(Rectangle((s*36.5 - (1.8 if s>0 else 0), 24), 1.8, 21.2, color='#f28c28'))
    ax.plot([s*38.3, s*33.0], [32, 32], color='k', lw=3); ax.add_patch(Circle((s*38.3, 32), 1.6, color='k'))
for y in (-29, 29):
    ax.add_patch(Rectangle((y-3, 45.2), 6, 2.8, color='#f28c28')); ax.plot([y, y], [44.3, 51.2], color='k', lw=2.5); ax.add_patch(Rectangle((y-1.8, 43.5), 3.6, 0.9, color='k'))
ax.text(0, 66.6, 'lid = cover only: 0.8 mm above the fins, no pressing bars, nothing is held by it', ha='center', va='center', fontsize=8)
ax.text(0, 46.3, 'saddle floor carries the board: 4 x M2x6 up from below through counterbores in the floor,\nthrough the board, into the 6530B bosses (bench assembly, saddle + board = one unit)', ha='center', fontsize=8.5)
ax.text(-44, 28, '4 x M2x6 side screws\nthrough printed lugs\ninto the shell flank\n(1.6 mm pilot drilled\nwith a printed guide)', fontsize=8.5, ha='center')
ax.text(0, 38.5, 'the two roof screws (-21.5, +-20) are driven first; the floor passes 0.65 mm over their heads', ha='center', fontsize=8.5, color='#444')
ax.set_ylabel('z (mm)')
ax = axs[1]; common(ax); ax.set_title('V2 as released today (rejected): tray loose on posts, lid presses the heatsink', fontsize=11)
ax.fill_between(yy[m], roof[m] + 0.3, 44.0, color='#f28c28', alpha=.9)
for y in (-29.5, 29.5): ax.add_patch(Rectangle((y-2.5, 44), 5, 1.5, color='#f28c28'))
ax.add_patch(Rectangle((-32.65, 45.5), 65.3, 1.4, color='#c86a10'))
for y in (-29, 29): ax.add_patch(Rectangle((y-3, 46.9), 6, 1.1, color='#c86a10')); ax.plot([y, y], [46.5, 51.2], color='k', lw=2.5)
for y in (-27, 27): ax.add_patch(Rectangle((y-2, 61.2), 4, 4.6, color='#f28c28'))
ax.text(0, 63.5, 'bars press on the hot heatsink: PLA creeps, the grip goes', ha='center', fontsize=8.5, color='red')
ax.text(0, 42.8, 'tray: not fixed to the saddle, only located by the walls', ha='center', fontsize=8.5, color='red'); ax.set_yticks([])
plt.tight_layout(); plt.savefig('v3-concept-section.png', dpi=130); print('ok')
