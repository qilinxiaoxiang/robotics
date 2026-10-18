"""Downscale and re-encode one photo as JPEG for inlining. Usage: shrink.py IN OUT MAXSIDE QUALITY"""
import sys
from PIL import Image

src, dst, side, q = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
im = Image.open(src)
if im.mode not in ("RGB", "L"):
    bg = Image.new("RGB", im.size, (255, 255, 255))
    bg.paste(im, mask=im.convert("RGBA").split()[3])
    im = bg
im.thumbnail((side, side), Image.LANCZOS)
im.save(dst, "JPEG", quality=q, optimize=True, progressive=True)
