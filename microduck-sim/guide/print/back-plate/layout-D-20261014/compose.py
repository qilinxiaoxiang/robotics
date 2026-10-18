"""Label and tile render PNGs.  python compose.py OUT.png "caption" title1=path1 title2=path2 ..."""
import sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont
try:
    F = ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc', 20)
except Exception:
    F = ImageFont.load_default()
out, cap = sys.argv[1], sys.argv[2]
tiles = []
for a in sys.argv[3:]:
    t, p = a.split('=', 1); im = Image.open(p).convert('RGB'); dr = ImageDraw.Draw(im)
    dr.rectangle((0, 0, im.size[0], 30), fill=(0, 0, 0)); dr.text((8, 5), t, fill=(255, 255, 255), font=F); tiles.append(np.array(im))
row = Image.fromarray(np.hstack(tiles)); W, H = row.size
c = Image.new('RGB', (W, H + 36), (0, 0, 0)); c.paste(row, (0, 0)); ImageDraw.Draw(c).text((8, H + 8), cap, fill=(230, 230, 230), font=F); c.save(out); print('ok', out)
