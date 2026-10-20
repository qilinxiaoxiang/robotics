"""Animate how the foot seats in the hot-glue mold without depth pins (left mold, section along the foot's long axis).

    /tmp/microduck-cad-venv/bin/python rim_stop_animation.py     -> rim-stop.gif beside this file

Reads hotglue-mold-left-maps.npz (written by hotglue_mold.py). The glue in the section is drawn by area conservation:
the cavity starts with 2.5/2.1 of the seated coat area (README step 3 fills about 2.5 cm3 for a 2.1 cm3 coat); as the
foot comes down the glue rises in the gap, and what no longer fits under the 3 mm rim leaves through the vents.
"""
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LightSource
import imageio.v2 as imageio
from scipy import ndimage

HERE = Path(__file__).resolve().parent
H_CAST, T = 3.0, 1.0
FILL_RATIO = 2.5 / 2.1


def main():
    z = np.load(HERE / 'hotglue-mold-left-maps.npz')
    xs, ys, S, low = z['xs'], z['ys'], z['S'], z['low']
    foot = ~np.isnan(low)
    X, Y = np.meshgrid(xs, ys, indexing='ij')
    flat = foot & (low < 0.1)
    cy = (Y[flat].min() + Y[flat].max()) / 2
    j = int(np.argmin(np.abs(ys - cy)))
    mold = S[:, j]
    fz = np.where(np.isnan(low[:, j]), np.nan, low[:, j])
    dx = xs[1] - xs[0]
    cav = mold < H_CAST - 1e-6
    # rim contact at the toe end: last cavity column, and where the seated foot crosses z = 3 there
    ic = np.where(cav)[0]
    toe_rim = xs[ic[-1]] + dx / 2
    gap = np.where(foot, low - S, np.inf)
    touch = foot & (gap < 0.05)

    def glue_level(dz, area):
        top = np.where(np.isnan(fz), 99, fz + dz)
        def a(h):
            return float(np.sum(np.clip(np.minimum(h, top) - mold, 0, None)[cav]) * dx)
        if a(H_CAST) <= area:
            return H_CAST, area - a(H_CAST)
        lo_, hi_ = mold[cav].min(), H_CAST
        for _ in range(40):
            mid = (lo_ + hi_) / 2
            lo_, hi_ = (mid, hi_) if a(mid) < area else (lo_, mid)
        return (lo_ + hi_) / 2, 0.0

    seated = float(np.sum(np.clip(np.nan_to_num(fz, nan=99) - mold, 0, None)[cav]) * dx)
    area0 = FILL_RATIO * seated

    # top view, static
    ls = LightSource(azdeg=315, altdeg=35)
    sl = (slice(np.searchsorted(xs, X[foot].min() - 5), np.searchsorted(xs, X[foot].max() + 5)),
          slice(np.searchsorted(ys, Y[foot].min() - 5), np.searchsorted(ys, Y[foot].max() + 5)))
    topimg = ls.shade(np.clip(S[sl], -1.2, 4).T, cmap=plt.cm.gray, vert_exag=8, blend_mode='overlay', vmin=-1.2, vmax=4)
    ext = [xs[sl[0]][0], xs[sl[0]][-1], ys[sl[1]][0], ys[sl[1]][-1]]

    dzs = list(np.linspace(7, 0, 34)) + [0.0] * 14
    frames = []
    for n, dz in enumerate(dzs):
        fig = plt.figure(figsize=(11, 7.2), dpi=90)
        gs = fig.add_gridspec(2, 2, height_ratios=[1.25, 1], width_ratios=[1.1, 1])
        ax = fig.add_subplot(gs[0, :]); az = fig.add_subplot(gs[1, 0]); at = fig.add_subplot(gs[1, 1])
        h, spill = glue_level(dz, area0)
        top = np.where(np.isnan(fz), 99, fz + dz)
        gtop = np.where(cav, np.minimum(h, top), mold)
        for a_, (x0, x1, z0, z1) in ((ax, (xs[ic[0]] - 6, xs[ic[-1]] + 6, -4.5, 12)), (az, (toe_rim - 3.5, toe_rim + 1.5, 0.5, 5))):
            a_.fill_between(xs, -4, mold, color='#3a3a3a', lw=0)
            a_.fill_between(xs, mold, gtop, where=gtop > mold, color='#f4c542', alpha=.85, lw=0)
            m = ~np.isnan(fz)
            a_.fill_between(xs[m], fz[m] + dz, 30, color='#e8d900', lw=0)
            a_.plot(xs[m], fz[m] + dz, color='#6b6300', lw=1)
            a_.set_xlim(x0, x1); a_.set_ylim(z0, z1); a_.set_aspect('equal')
            a_.axhline(H_CAST, color='tab:red', lw=.6, ls=':')
        ax.set_title('Section along the foot (left mold). Yellow = foot, amber = hot glue, dark = mold', fontsize=10)
        ax.set_xlabel('mm'); ax.set_ylabel('mm (foot flat = 0 when seated)')
        if dz > 0.01:
            msg, col = f'Pressing down: the foot is {dz:.1f} mm above its seat', 'black'
        else:
            msg, col = "Stopped: the foot's curved edge sits on the mold rim all round. Glue under it: 1.0-1.1 mm", 'tab:red'
        if spill > 0:
            msg += '\nGlue that no longer fits under the rim leaves through the 8 vents'
        fig.text(0.01, 0.995, msg, fontsize=11, color=col, va='top')
        az.set_title('Zoom at the toe rim', fontsize=10)
        if dz <= 0.01:
            az.plot([toe_rim], [H_CAST], 'o', ms=9, mfc='none', mec='tab:red', mew=2)
            az.annotate('foot surface meets the rim edge\n(about 45 deg: rim 0.1 mm off = coat 0.1 mm off)',
                        (toe_rim, H_CAST), xytext=(toe_rim - 3.3, 4.2), fontsize=8, arrowprops=dict(arrowstyle='->', lw=.7))
        at.imshow(topimg, origin='lower', extent=ext)
        at.plot(X[touch], Y[touch], '.', color='tab:red', ms=2.2)
        at.set_title('Top view: red = where the seated foot touches the rim', fontsize=10)
        at.set_xticks([]); at.set_yticks([])
        fig.tight_layout(rect=(0, 0, 1, 0.93))
        fig.canvas.draw()
        frames.append(np.asarray(fig.canvas.buffer_rgba())[:, :, :3].copy())
        plt.close(fig)
    out = HERE / 'rim-stop.gif'
    imageio.mimsave(out, frames, duration=0.11, loop=0)
    print(out, len(frames), 'frames, seated section coat area', round(seated, 2), 'mm2')


if __name__ == '__main__':
    main()
