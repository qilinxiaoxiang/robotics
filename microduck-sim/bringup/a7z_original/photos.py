"""Marked official Radxa photos of the Cubie A7Z for the A7Z bench pages (python3 + Pillow).

Both board photos are turned to the portrait pose of Radxa's GPIO picture: component side up, antenna (IPEX) end at
the top, 40-pin header on the right; pin 1 top of the inner row, pin 2 top of the edge row.
Pixel coordinates below were read on the source photos (sources/a7z-top.png 2400 x 600, a7z-bottom.png 2400 x 600)
and checked by viewing the marked output (shots/check_*.png).
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
SRC = HERE.parent.parent / 'guide' / 'print' / 'a7z-head' / 'sources'
FONT = '/System/Library/Fonts/Hiragino Sans GB.ttc'

SCALE = 1.6          # upscale of the 430 x 862 portrait crop
MARGIN = 170         # white margin left and right for the number circles

# a7z-top.png: board crop box, then rotated 90 degrees clockwise (header from top edge to right edge).
TOP_BOX = (770, 85, 1632, 515)   # 862 x 430 landscape crop
PIN1_TOP = (886, 152)            # pin 1 (inner row) on a7z-top.png
PITCH = 33.1                     # header pitch on a7z-top.png (px)
EDGE_DY = -30                    # edge row is 30 px above the inner row on a7z-top.png
IPEX_TOP = (804, 286)            # gold IPEX socket
FAN_TOP = (807, 370)             # white 2-pin fan socket
USBC1_TOP = (1480, 450)          # USB-C 2.0 OTG & power (Radxa interface 1)
USBC2_TOP = (1310, 450)          # USB-C 3.1 OTG & DP (interface 2)
SD_END_TOP = (1614, 290)         # microSD end of the board (the socket is on the underside)


def pin_top(n: int) -> tuple[float, float]:
    """Pin n position on a7z-top.png (landscape: header along the top edge, pin 1 at the left)."""
    k = (n + 1) // 2 - 1
    x = PIN1_TOP[0] + k * PITCH
    y = PIN1_TOP[1] + (0 if n % 2 else EDGE_DY)
    return x, y


def to_portrait(p) -> tuple[float, float]:
    """Point on a7z-top.png -> point on the scaled portrait canvas (incl. left margin)."""
    cx, cy = p[0] - TOP_BOX[0], p[1] - TOP_BOX[1]
    h = TOP_BOX[3] - TOP_BOX[1]
    px, py = (h - 1 - cy), cx                    # 90 degrees clockwise
    return MARGIN + px * SCALE, py * SCALE


def portrait_top() -> Image.Image:
    im = Image.open(SRC / 'a7z-top.png').convert('RGBA').crop(TOP_BOX).transpose(Image.Transpose.ROTATE_270)
    im = im.resize((round(im.width * SCALE), round(im.height * SCALE)), Image.LANCZOS)
    canvas = Image.new('RGB', (im.width + 2 * MARGIN, im.height), 'white')
    canvas.paste(im, (MARGIN, 0), im)
    return canvas


# a7z-bottom.png: board crop, rotated 90 degrees counter-clockwise, so the microSD end is at the bottom and the header
# holes run down the LEFT side (the board turned over about its long axis).
BOT_BOX = (770, 88, 1632, 498)
SD_BOT = (912, 294)
PIN1_HOLE_BOT = (1514, 154)      # pin-1 hole seen from the underside (header holes along the top edge, pin 1 right)


def to_portrait_bottom(p) -> tuple[float, float]:
    cx, cy = p[0] - BOT_BOX[0], p[1] - BOT_BOX[1]
    w = BOT_BOX[2] - BOT_BOX[0]
    px, py = cy, (w - 1 - cx)                    # 90 degrees counter-clockwise
    return MARGIN + px * SCALE, py * SCALE


def portrait_bottom() -> Image.Image:
    im = Image.open(SRC / 'a7z-bottom.png').convert('RGBA').crop(BOT_BOX).transpose(Image.Transpose.ROTATE_90)
    im = im.resize((round(im.width * SCALE), round(im.height * SCALE)), Image.LANCZOS)
    canvas = Image.new('RGB', (im.width + 2 * MARGIN, im.height), 'white')
    canvas.paste(im, (MARGIN, 0), im)
    return canvas


def draw_marks(im: Image.Image, marks) -> Image.Image:
    """marks: (label, (tx, ty) target, (lx, ly) circle centre, ring radius or 0, ring colour, circle fill)."""
    im = im.copy()
    d = ImageDraw.Draw(im)
    for label, (tx, ty), (lx, ly), ring, col, fill in marks:
        d.line([(tx, ty), (lx, ly)], fill='#0d47a1', width=4)
    for label, (tx, ty), (lx, ly), ring, col, fill in marks:
        if ring:
            d.ellipse([tx - ring - 3, ty - ring - 3, tx + ring + 3, ty + ring + 3], outline='white', width=12)
            d.ellipse([tx - ring, ty - ring, tx + ring, ty + ring], outline=col, width=6)
        else:
            d.ellipse([tx - 8, ty - 8, tx + 8, ty + 8], fill='#0d47a1')
        r = 29
        font = ImageFont.truetype(FONT, 34 if len(label) < 3 else 26)
        d.ellipse([lx - r, ly - r, lx + r, ly + r], fill=fill, outline='white', width=4)
        d.text((lx, ly), label, font=font, fill='white', anchor='mm')
    return im


def spread(ys, gap=66):
    """Push label y positions apart (sorted order kept) so number circles never overlap."""
    order = sorted(range(len(ys)), key=lambda i: ys[i])
    out = list(ys)
    for a, b in zip(order, order[1:]):
        if out[b] < out[a] + gap:
            out[b] = out[a] + gap
    shift = (sum(ys) - sum(out)) / len(ys)          # recentre the group on its targets
    out = [y + shift for y in out]
    lo = min(out)
    if lo < 34:
        out = [y + 34 - lo for y in out]
    return out


PIN_FILL = '#1565c0'
LAND_FILL = '#e65100'


def top_figure(pins, landmarks=()):
    """pins: [(n, ring colour)], drawn with their pin number in the right margin.
    landmarks: [(label, point on a7z-top.png, ring radius, label y on canvas)], drawn in the left margin."""
    im = portrait_top()
    W = im.width
    tgt = [to_portrait(pin_top(n)) for n, _ in pins]
    ly = spread([t[1] for t in tgt])
    marks = [(str(n), t, (W - MARGIN / 2, y), 21, col, PIN_FILL) for (n, col), t, y in zip(pins, tgt, ly)]
    for label, p, ring, y in landmarks:
        marks.append((label, to_portrait(p), (MARGIN / 2, y), ring, '#ff6f00', LAND_FILL))
    return draw_marks(im, marks)


def bottom_figure():
    im = portrait_bottom()
    return draw_marks(im, [('SD', to_portrait_bottom(SD_BOT), (MARGIN / 2, 1150), 40, '#ff6f00', LAND_FILL),
                           ('1', to_portrait_bottom(PIN1_HOLE_BOT), (MARGIN / 2, 80), 20, '#ffd600', PIN_FILL)])


# Seeed XIAO ESP32-S3 front pinout (Seeed wiki XIAO_ESP32-S3_front_pinout.png, 7680 x 4320), cropped to x 2400-5200,
# y 960-2320 and halved: sources/xiao-esp32s3-front-pinout-crop.png. Pad centres read on that crop (2026-10-15).
XIAO_PADS = {'GND': (960, 186), '3V3': (960, 264), 'D4': (480, 424), 'D5': (480, 504)}


def xiao_figure(pads):
    """pads: [(pad name, label, ring colour)]; the number circle sits just inside the board next to its pad."""
    im = Image.open(HERE / 'sources' / 'xiao-esp32s3-front-pinout-crop.png').convert('RGB')
    marks = []
    for name, label, col in pads:
        x, y = XIAO_PADS[name]
        lx = x + 82 if x < im.width / 2 else x - 82
        marks.append((label, (x, y), (lx, y), 26, col, PIN_FILL))
    return draw_marks(im, marks)
