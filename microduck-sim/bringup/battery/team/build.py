"""Build the English teammate page for the MicroDuck battery backpack.
    python3 build.py   -> ../../BATTERY-BACKPACK-TEAM.html (self-contained, images inlined)
Content source: ../build_battery_wiring.py (Chinese page, 2026-10-17), guide chapter 11, battery plan README (D-010).
Images: Shawn's Swann 39 photo and the backpack CAD renders (guide/print/back-plate/battery-backpack-20261015/renders)."""
import base64, io
from pathlib import Path
from PIL import Image
HERE = Path(__file__).resolve().parent
MS = HERE.parents[2]
R = MS / 'guide/print/back-plate/battery-backpack-20261015/renders'
IMGS = {'swann': HERE.parent / 'img/swann39_side.jpg', 'side': R / 'BP_side_0.png', 'rear': R / 'BP_rear_0.png',
        'low': R / 'BP_low_0.png', 'swap': R / 'BP_swap_0.png', 'out': R / 'BP_out_0.png'}
def uri(p, w=900):
    im = Image.open(p).convert('RGB'); im.thumbnail((w, w * 2))
    b = io.BytesIO(); im.save(b, 'JPEG', quality=82, optimize=True)
    return 'data:image/jpeg;base64,' + base64.b64encode(b.getvalue()).decode()
s = (HERE / 'template.tpl').read_text()
for k, p in IMGS.items():
    s = s.replace('{{IMG:%s}}' % k, uri(p))
assert '{{IMG' not in s
out = HERE.parents[1] / 'BATTERY-BACKPACK-TEAM.html'
out.write_text(s); print(out, len(s))
# Local preview copy with the publish skeleton's viewport meta, for the headless probe only.
(HERE / 'preview.html').write_text('<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"></head><body>' + s + '</body></html>')
