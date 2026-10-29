"""Section through the right jaw pivot along its axis: seat halves, uncut boss, the cup ring and the M2 x 10 (numbers from
checks.json and the seat survey of 2026-10-29). Writes concept/cup_ring_section.png.
    /tmp/microduck-cad-venv/bin/python concept/draw_cup_section.py
"""
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Polygon

HERE = Path(__file__).resolve().parent
c = json.loads((HERE.parent / 'checks.json').read_text())
fig, ax = plt.subplots(figsize=(9, 5.2), dpi=160)
Y = lambda y: -y          # draw with the arm on the left: horizontal = distance from the robot centre, growing to the right
# seat halves: yellow lower shell below the axis, black jaw support above (bore r 7.3 bands at y -39.5..-37.5 and -36..-35.5, r 8.4 elsewhere)
# both halves are walls round the bore: the lower shell (yellow) below the axis, the jaw support (black) above; the section
# shows each wall between its bore radius and r 10
for y0, y1, r in ((-39.5, -37.5, 7.3), (-37.5, -36.0, 8.4), (-36.0, -35.5, 7.3), (-35.5, -29.5, 8.4)):
    ax.add_patch(Rectangle((Y(y0), -10.0), Y(y1) - Y(y0), 10.0 - r, color='#e8c547', ec='none'))   # lower shell wall
for y0, y1, r in ((-39.25, -37.5, 7.5), (-37.5, -36.0, 8.4), (-36.0, -35.5, 7.5), (-35.5, -29.25, 8.4)):
    ax.add_patch(Rectangle((Y(y0), r), Y(y1) - Y(y0), 10.0 - r, color='#333333', ec='none'))        # jaw support wall
# jaw arm (y -43.81..-39.7) and its boss (r 5, to y -37.0), yellow
ax.add_patch(Rectangle((Y(-43.81), -8.0), Y(-39.7) - Y(-43.81), 16.0, color='#f0d060', ec='k', lw=0.6))
ax.add_patch(Rectangle((Y(-39.7), -5.0), Y(-37.0) - Y(-39.7), 10.0, color='#f0d060', ec='k', lw=0.6))
ax.add_patch(Rectangle((Y(-43.81), -1.25), Y(-37.0) - Y(-43.81), 2.5, color='white', ec='k', lw=0.4))   # drilled 2.5 hole
# cup ring, black: sleeve r 5.25..7 from -39.6 to -36.8, solid bottom to -33.5, pilot 1.6
for lo, hi in ((5.25, 7.0), (-7.0, -5.25)):
    ax.add_patch(Rectangle((Y(-39.6), lo), Y(-36.8) - Y(-39.6), hi - lo, color='#1a1a1a', ec='none'))
for lo, hi in ((0.8, 7.0), (-7.0, -0.8)):
    ax.add_patch(Rectangle((Y(-36.8), lo), Y(-33.5) - Y(-36.8), hi - lo, color='#1a1a1a', ec='none'))
# M2 x 10: head 3.8 x 1.3 outside the arm, shank to the tip
hs, tip = c['screw']['headSeatY'], c['screw']['tipY']
ax.add_patch(Rectangle((Y(hs) - 1.3, -1.9), 1.3, 3.8, color='#8899aa', ec='k', lw=0.5))
ax.add_patch(Rectangle((Y(hs), -1.0), Y(tip) - Y(hs), 2.0, color='#8899aa', ec='k', lw=0.5))
ax.axhline(0, color='k', lw=0.5, ls='-.')
ax.annotate('jaw arm', (Y(-41.75), 6.0), ha='center', fontsize=8)
ax.annotate('boss dia 10,\nnot cut', (Y(-38.35), -3.6), ha='center', fontsize=7)
ax.annotate('cup ring 6.1 mm:\nsleeve 2.8\nbottom 3.3', (Y(-35.15), 2.2), ha='center', fontsize=7, color='white')
ax.annotate('M2 x 10 from outside, %.1f mm of thread in the bottom' % c['screw']['threadInBottomMm'], (Y(-44.5), -8.9), ha='left', fontsize=8)
ax.annotate('lower shell seat (yellow), bore r 7.3 / 8.4', (Y(-34.5), -10.6), ha='center', fontsize=8)
ax.annotate('jaw support seat (black); its arc starts 2 mm above the axis', (Y(-34.3), 10.3), ha='center', fontsize=8)
ax.annotate('seat is 10 mm long', (Y(-34.5), -12.2), ha='center', fontsize=8)
ax.annotate('', (Y(-39.5), -11.5), (Y(-29.5), -11.5), arrowprops=dict(arrowstyle='<->', lw=0.8))
ax.set_xlim(Y(-45), Y(-28)); ax.set_ylim(-13, 11.5); ax.set_aspect('equal'); ax.set_xticks([]); ax.set_yticks([])
ax.set_title('Right jaw pivot, section along the axis: cup ring on the uncut boss (D-033 reissue, 2026-10-29)', fontsize=9)
fig.tight_layout(); fig.savefig(HERE / 'cup_ring_section.png'); print(HERE / 'cup_ring_section.png')
