"""Build the marked reference photos used by pd5991.py (retired 2026-10-13 with the 5991; the guide no longer uses them).

Run once after changing a marker: /tmp/microduck-cad-venv/bin/python guide/content/wiring/make_photos.py
Inputs are the Adafruit photos already recorded in bringup/parts/parts.json (private reference use):
- photos/usb_pd_5991_top.jpg  <- https://cdn-shop.adafruit.com/original/5991-05.jpg (Adafruit 5991, front)
Marker positions are pixel coordinates in those photos, read off a gridded copy and checked 2026-10-12 against
Adafruit's 5991 pinout text and schematic.
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
PHOTOS = HERE.parents[2] / 'bringup' / 'parts' / 'photos'
YELLOW, RED, INK, WHITE = (255, 212, 0), (230, 40, 40), (17, 17, 17), (255, 255, 255)


def font(px: int):
    for path in ('/System/Library/Fonts/Helvetica.ttc', '/Library/Fonts/Arial Unicode.ttf'):
        try:
            return ImageFont.truetype(path, px, index=1) if path.endswith('.ttc') else ImageFont.truetype(path, px)
        except OSError:
            continue
    return ImageFont.load_default(size=px)


def shrink(im, width):
    """Downscale to `width` px so the embedded data URI stays small."""
    return im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)


def marker(d: ImageDraw.ImageDraw, c, n: str, r: int, leader=None):
    """Yellow numbered disc with a black ring and a white halo; optional leader line to the target."""
    if leader:
        d.line([c, leader], fill=WHITE, width=max(3, r // 4))
        d.line([c, leader], fill=YELLOW, width=max(2, r // 7))
    x, y = c
    d.ellipse([x - r - 3, y - r - 3, x + r + 3, y + r + 3], fill=WHITE)
    d.ellipse([x - r, y - r, x + r, y + r], fill=YELLOW, outline=INK, width=max(2, r // 10))
    d.text((x, y), n, fill=INK, font=font(int(r * 1.3)), anchor='mm')


def box(d, xy, color=YELLOW, w=4):
    x0, y0, x1, y1 = xy
    d.rectangle([x0 - 2, y0 - 2, x1 + 2, y1 + 2], outline=WHITE, width=w + 2)
    d.rectangle(xy, outline=color, width=w)


def arrow(d, tail, head, w):
    """Straight arrow with a filled head, yellow on a white halo."""
    import math
    (x0, y0), (x1, y1) = tail, head
    a = math.atan2(y1 - y0, x1 - x0)
    hl = w * 2.6
    base = (x1 - hl * math.cos(a), y1 - hl * math.sin(a))
    tri = [(x1, y1), (base[0] + hl * 0.6 * math.sin(a), base[1] - hl * 0.6 * math.cos(a)),
           (base[0] - hl * 0.6 * math.sin(a), base[1] + hl * 0.6 * math.cos(a))]
    d.line([tail, base], fill=WHITE, width=w + 4)
    d.polygon(tri, fill=WHITE, outline=WHITE, width=3)
    d.line([tail, base], fill=YELLOW, width=w)
    d.polygon(tri, fill=YELLOW)


def tag(d, xy, text, px, anchor='lm'):
    f = font(px)
    l, t, r, b = d.textbbox(xy, text, font=f, anchor=anchor)
    pad = px // 4
    d.rounded_rectangle([l - pad, t - pad, r + pad, b + pad], radius=pad, fill=YELLOW, outline=INK, width=2)
    d.text(xy, text, fill=INK, font=f, anchor=anchor)


# ---------------------------------------------------------------- Adafruit 5991 (photo 772 x 1200 px)
PD_SRC = PHOTOS / 'usb_pd_5991_top.jpg'
PD_BOARD_CROP = (40, 65, 732, 1050)        # whole board, USB-C at the top
PD_ZOOM_CROP = (330, 345, 735, 905)        # ISet jumper, the six DIP switches and the OFF pads
PD_ZOOM_K = 2                              # the close-up is upscaled 2x before the markers are drawn
PD_SW20 = (523, 716, 624, 750)             # slot of DIP switch 1, printed 20V (slider shown in the OFF position)
PD_SW_OTHERS = (523, 497, 624, 712)        # slots of switches 6..2 (5V, 9V, 12V, 15V, 18V): all OFF
PD_ISET = (602, 395, 700, 452)             # ISet jumper: two pads joined by a thin copper bridge
PD_ISET_BRIDGE = (650, 427)
PD_OFF = ((595, 830), (680, 830))          # the two OFF pads below the DIP switch


def pd_photos():
    im = Image.open(PD_SRC).convert('RGB')
    # Whole board: thin outline of the close-up area so the two drawings can be matched.
    board = im.crop(PD_BOARD_CROP)
    d = ImageDraw.Draw(board)
    ox, oy = PD_BOARD_CROP[:2]
    z = PD_ZOOM_CROP
    box(d, (z[0] - ox, z[1] - oy, z[2] - ox - 4, z[3] - oy), color=YELLOW, w=3)
    shrink(board, 460).save(HERE / 'pd5991_board.jpg', quality=70, optimize=True)

    k = PD_ZOOM_K
    zoom = im.crop(PD_ZOOM_CROP)
    zoom = zoom.resize((zoom.width * k, zoom.height * k), Image.LANCZOS)
    d = ImageDraw.Draw(zoom)
    zx, zy = PD_ZOOM_CROP[:2]
    P = lambda x, y: ((x - zx) * k, (y - zy) * k)
    R = lambda r: tuple(v for xy in (P(r[0], r[1]), P(r[2], r[3])) for v in xy)
    # 1: the 20V switch, push its slider towards ON (left, towards the printed ON and 20V).
    box(d, R(PD_SW20), YELLOW, 6)
    sx1, sy1 = P(PD_SW20[2], (PD_SW20[1] + PD_SW20[3]) / 2)
    marker(d, (P(708, 777)[0] - 4, P(708, 777)[1]), '1', 58, leader=(sx1 + 4, sy1))
    ax, ay = P(552, (PD_SW20[1] + PD_SW20[3]) / 2)
    arrow(d, (ax, ay), (ax - 48, ay), 10)
    tag(d, (P(470, 772)[0] - 40, P(470, 772)[1] + 10), 'push left = ON', 54, anchor='lm')
    # Switches 2..6 stay OFF.
    sx0, sy0, sx1, sy1 = R(PD_SW_OTHERS)
    d.rectangle([sx0, sy0, sx1, sy1], outline=WHITE, width=3)
    # 2: ISet bridge to cut.
    box(d, R(PD_ISET), YELLOW, 5)
    bx, by = P(*PD_ISET_BRIDGE)
    d.ellipse([bx - 26, by - 26, bx + 26, by + 26], outline=RED, width=6)
    ix, iy = P(PD_ISET[0], (PD_ISET[1] + PD_ISET[3]) / 2)
    marker(d, (ix - 70, iy + 4), '2', 58)
    tag(d, (798, P(560, 470)[1] + 10), 'cut the line', 54, anchor='rm')
    # 3: OFF pads, leave open.
    (ax, ay), (cx, cy) = (P(*PD_OFF[0]), P(*PD_OFF[1]))
    marker(d, ((ax + cx) / 2, ay - 4), '3', 50)
    tag(d, (798, ay + 96), 'OFF: leave open', 54, anchor='rm')
    shrink(zoom, 600).save(HERE / 'pd5991_dip.jpg', quality=70, optimize=True)


if __name__ == '__main__':
    pd_photos()
    for name in ('pd5991_board.jpg', 'pd5991_dip.jpg'):
        p = HERE / name
        print(name, Image.open(p).size, p.stat().st_size)
