"""Build FIVE-SYSTEMS.html for the MicroDuck guide server (Mac mini :8766) from index.html.

index.html is the artifact source: it references media/* and embeds/* beside it. The guide server serves only
allowlisted single files, so this build inlines every media file as a data URI, points each embed at its own
allowlisted page, adds the document skeleton, and copies the embed pages into the guide folder.

  python3 output/five-systems/build_standalone.py MEDIA_DIR
MEDIA_DIR holds the resized images (hero.jpg, printer.jpg, ...); videos come from output/shoot-20261024/.
"""
import base64
import re
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROBOTICS = HERE.parents[1]
SIM = ROBOTICS / 'microduck-sim'
GUIDE = SIM / 'build-pack-20260913/redesign-20260913/leg-guide-20261006'
VIDEOS = ROBOTICS / 'output/shoot-20261024'

# embed in index.html -> (route on the guide server, source page)
EMBEDS = {
    'embeds/head-3d.html': ('HEAD-3D.html', SIM / 'guide/extension-20261012-neck-audio/page3d/HEAD-3D.html'),
    'embeds/ducts.html': ('HEAD-DUCTS.html', SIM / 'guide/print/a7z-head/back-to-back/ducts-explainer.html'),
    'embeds/backpack-3d.html': ('BACKPACK-3D.html', SIM / 'bringup/battery/team/backpack-3d.html'),
    'embeds/wire-ties.html': ('WIRE-TIES.html', SIM / 'guide/print/wire-ties-20261109/wire-ties.html'),
    'embeds/build-guide.html': ('MICRODUCK-BUILD.html', SIM / 'guide/dist/MICRODUCK-BUILD.html'),
}
MIME = {'.jpg': 'image/jpeg', '.mp4': 'video/mp4'}


def main():
    media = Path(sys.argv[1])
    page = (HERE / 'index.html').read_text()
    for ref, (route, src) in EMBEDS.items():
        assert ref in page, ref
        page = page.replace(ref, route)
        dest = GUIDE / route
        if not dest.exists() or dest.read_bytes() != src.read_bytes():
            shutil.copyfile(src, dest)

    def inline(m):
        name = m.group(1)
        f = (VIDEOS if name.endswith('.mp4') else media) / name
        return 'data:%s;base64,%s' % (MIME[f.suffix], base64.b64encode(f.read_bytes()).decode())

    page, n = re.subn(r'media/([\w.-]+\.(?:jpg|mp4))', inline, page)
    assert 'media/' not in page and n > 0
    out = GUIDE / 'FIVE-SYSTEMS.html'
    out.write_text('<!doctype html>\n<html lang="zh-CN"><head><meta charset="utf-8">'
                   '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
                   '<style>:root{padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}[hidden]{display:none!important}img{max-width:100%}</style>'
                   '</head><body>\n' + page + '\n</body></html>\n')
    print(out, round(out.stat().st_size / 1e6, 2), 'MB,', n, 'media refs inlined')


if __name__ == '__main__':
    main()
