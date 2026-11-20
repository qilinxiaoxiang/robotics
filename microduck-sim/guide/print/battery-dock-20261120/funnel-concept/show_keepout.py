"""Print the keep-out height maps (lowest robot point over each 1 mm cell, dock frame) as 5 mm text grids."""
import sys
import numpy as np
k = np.load(sys.argv[1] if len(sys.argv) > 1 else 'checks/keepout.npz'); xs, ys = k['xs'], k['ys']
def show(H, name, x0=-110, x1=-10, dx=5, y0=-45, y1=45, dy=5):
    print('==', name, '(min z mm; . = none)  rows x, cols y', list(range(y0, y1 + 1, dy)))
    for x in range(x1, x0 - 1, -dx):
        i = int(x - xs[0]); row = []
        for y in range(y0, y1 + 1, dy):
            j = int(y - ys[0]); v = H[max(i - 2, 0):i + 3, max(j - 2, 0):j + 3].min()
            row.append('  .' if np.isinf(v) else f'{v:3.0f}')
        print(f'{x:5d}', ' '.join(row))
for nm in sys.argv[2:] or ['legs', 'trunk', 'seated_legs', 'sit_legs', 'standup_legs', 'stand_legs']:
    show(k[nm], nm)
