"""Assemble wire-ties.html (self-contained, three.js inlined) from page.template.html and data.json.
Also writes the body-only copy for the Artifact publish to the path given as argv[1], if any. python3 build_page.py [body_out]"""
import re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
three = (HERE.parents[3] / 'guide-kit/three/build/three.module.js').read_text()
assert '</script' not in three
three, n = re.subn(r'\nexport \{.*?\};?\s*$', '\n', three, flags=re.S)
assert n == 1
body = (HERE / 'page.template.html').read_text().replace('/*DATA*/', (HERE / 'data.json').read_text()).replace('/*THREE*/', three)
(HERE / 'wire-ties.html').write_text('<!doctype html>\n<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"></head><body>\n' + body + '\n</body></html>\n')
if len(sys.argv) > 1:
    Path(sys.argv[1]).write_text(body)
print('html MB', round((HERE / 'wire-ties.html').stat().st_size / 1e6, 2))
