"""wiring-kit bench for A7Z-TOUCH.html: the XIAO ESP32-S3's four soldered leads to the A7Z 40-pin header.

Same convention as the bring-up page benches (bringup/build/benches.ts): each board is drawn from its real picture with
the pins placed at photo coordinates, and ~/code/wiring-kit routes the jumpers, checks them and renders the
interactive view (wire-by-wire mode, pin details). As soldered on 2026-10-20: red 3V3 -> A7Z 17, black GND -> 25,
blue D5 (SCL) -> 29, green D4 (SDA) -> 31.

Pictures:
- A7Z: Radxa's top photo (guide/print/a7z-head/sources/a7z-top.png) in the portrait pose of photos.py (antenna end at
  the top, header on the right). Scale from the board length: the 862 px crop is the board's 65 mm.
- XIAO: the board area of the Seeed wiki front pinout (sources/xiao-esp32s3-front-pinout-crop.png). Scale from the
  two pad columns, 15.24 mm apart, 480 px apart on the crop.
Pin names: Radxa's 40-pin table (guide/print/a7z-head/sources/radxa-a7z-pin-gpio.md, Function1 column).
"""
from __future__ import annotations

import base64
import io
import json
import re
from pathlib import Path

from PIL import Image, ImageDraw

import photos as P

WK = Path.home() / 'code' / 'wiring-kit' / 'dist'
PIN_TABLE = P.SRC / 'radxa-a7z-pin-gpio.md'

A7Z_PX_MM = (P.TOP_BOX[2] - P.TOP_BOX[0]) / 65.0
XIAO_BOX = (440, 10, 1001, 680)
XIAO_PX_MM = 480 / 15.24

# Wire colours as soldered; the same hex values as the page's colour line. wiring-kit routes in list order; this order
# (with the placement in bench()) gave the fewest crossings in a search over all orders, XIAO turns and offsets.
WIRES = [  # id, XIAO pad, A7Z pin, colour, group, caption
    ('gnd', 'GND', 25, '#1d1d1f', 'power', '黑：XIAO GND → A7Z 25 号针（GND）'),
    ('3v3', '3V3', 17, '#d7263d', 'power', '红：XIAO 3V3 → A7Z 17 号针（3.3 V）'),
    ('sda', 'D4', 31, '#1f9d55', 'i2c', '绿：XIAO D4 → A7Z 31 号针（SDA，数据线）'),
    ('scl', 'D5', 29, '#1f6fd1', 'i2c', '蓝：XIAO D5 → A7Z 29 号针（SCL，时钟线）'),
]


STAGE = '#f5f7f8'   # wiring-kit's --wk-stage: transparent photo edges are flattened onto it


def jpeg_uri(im: Image.Image, quality: int = 82) -> str:
    flat = Image.new('RGB', im.size, STAGE)
    flat.paste(im, (0, 0), im if im.mode == 'RGBA' else None)
    buf = io.BytesIO()
    flat.save(buf, 'JPEG', quality=quality, optimize=True)
    return 'data:image/jpeg;base64,' + base64.b64encode(buf.getvalue()).decode()


def rounded(im: Image.Image, r: int) -> Image.Image:
    """Cut the board out of a black photo background with a rounded-corner mask."""
    mask = Image.new('L', im.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, im.width - 1, im.height - 1), r, fill=255)
    out = im.convert('RGBA')
    out.putalpha(mask)
    return out


def photo_svg(im: Image.Image, w_mm: float, h_mm: float) -> str:
    href = jpeg_uri(im)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="{w_mm:.2f}mm" '
            f'height="{h_mm:.2f}mm" viewBox="0 0 {im.width} {im.height}"><image width="{im.width}" height="{im.height}" '
            f'href="{href}" xlink:href="{href}"/></svg>')


def a7z_names() -> dict[int, str]:
    names = {}
    for line in PIN_TABLE.read_text().splitlines():
        cells = [c.strip() for c in line.strip().strip('|').split('|')]
        if len(cells) < 11:
            continue
        nums = [re.sub(r'<[^>]+>', '', c) for c in (cells[8], cells[9])]
        if not all(n.isdigit() for n in nums):
            continue
        names[int(nums[0])] = cells[7]
        names[int(nums[1])] = cells[10]
    assert sorted(names) == list(range(1, 41)), sorted(names)
    return names


def a7z() -> dict:
    im = Image.open(P.SRC / 'a7z-top.png').convert('RGBA').crop(P.TOP_BOX).transpose(Image.Transpose.ROTATE_270)
    w, h = im.width / A7Z_PX_MM, im.height / A7Z_PX_MM
    names = a7z_names()
    extra = {29: 'PB2 · 触摸板 I2C SCL（TWI0）', 31: 'PB3 · 触摸板 I2C SDA（TWI0）'}
    pins = []
    for n in range(1, 41):
        x, y = P.to_portrait(P.pin_top(n))
        x, y = (x - P.MARGIN) / P.SCALE / A7Z_PX_MM, y / P.SCALE / A7Z_PX_MM
        name = names[n]
        role = 'ground' if name == 'GND' else 'power' if name in ('3.3V', '5V') else 'signal'
        pins.append({'id': f'p{n}', 'label': str(n), 'name': extra.get(n, name), 'role': role,
                     'voltage': None if role == 'ground' else 5 if name == '5V' else 3.3,
                     'multi': role != 'signal', 'x': round(x, 3), 'y': round(y, 3),
                     'note': '里排（单号）' if n % 2 else '外排（双号）'})
    for p in pins:
        if p['voltage'] is None:
            del p['voltage']
    return {'id': 'a7z', 'title': 'Radxa Cubie A7Z', 'subtitle': '头里的主板，40 针排针', 'short': 'A7Z',
            'drawing': {'kind': 'svg', 'svg': photo_svg(im, w, h)}, 'width': round(w, 2), 'height': round(h, 2),
            'pins': pins}


def xiao() -> dict:
    src = Image.open(P.HERE / 'sources' / 'xiao-esp32s3-front-pinout-crop.png').convert('RGB')
    im = rounded(src.crop(XIAO_BOX), 44)
    w, h = im.width / XIAO_PX_MM, im.height / XIAO_PX_MM
    left = ['D0', 'D1', 'D2', 'D3', 'D4', 'D5', 'D6']
    right = ['VBUS', 'GND', '3V3', 'D10', 'D9', 'D8', 'D7']
    rows = [108, 186, 264, 344, 424, 504, 582]
    name = {'VBUS': 'VBUS（5 V，不焊）', 'GND': 'GND', '3V3': '3.3V-OUT', 'D4': 'D4 · I2C SDA', 'D5': 'D5 · I2C SCL',
            'D0': 'D0 · 铜箔 L1', 'D1': 'D1 · 铜箔 R1', 'D2': 'D2 · 铜箔 L2', 'D3': 'D3 · 铜箔 R2', 'D8': 'D8 · 铜箔 M'}
    pins = []
    for col, x in ((left, 480), (right, 960)):
        for pad, y in zip(col, rows):
            role = 'ground' if pad == 'GND' else 'power' if pad in ('3V3', 'VBUS') else 'signal'
            pin = {'id': pad, 'label': pad, 'name': name.get(pad, pad + '（空着）'), 'role': role,
                   'x': round((x - XIAO_BOX[0]) / XIAO_PX_MM, 3), 'y': round((y - XIAO_BOX[1]) / XIAO_PX_MM, 3)}
            if role != 'ground':
                pin['voltage'] = 5 if pad == 'VBUS' else 3.3
            pins.append(pin)
    return {'id': 'xiao', 'title': 'Seeed XIAO ESP32-S3', 'subtitle': '触摸板，贴在头盖左内壁', 'short': 'XIAO',
            'drawing': {'kind': 'svg', 'svg': photo_svg(im, w, h)}, 'width': round(w, 2), 'height': round(h, 2),
            'pins': pins}


def bench() -> dict:
    a, x = a7z(), xiao()
    pin_y = {p['label']: p['y'] for p in a['pins']}
    return {
        'modules': [a, x],
        # XIAO half a turn, right of the A7Z header, its centre 10 mm above the middle of pins 17 to 31. Chosen by a search
        # over turns, offsets and wire orders: one crossing, and no pin label or board name over a wire at 1100 px or at
        # the 324 px the bench gets on a phone. One crossing (blue over green) is forced: round the XIAO the pads run
        # 3V3, GND, D4, D5, but down the header the pins run 17 (3V3), 25 (GND), 29 (D5), 31 (D4), so D4 and D5 swap order;
        # the wires in the head cross the same way.
        'placements': [{'module': 'a7z', 'x': 0, 'y': 0},
                       {'module': 'xiao', 'rotation': 180, 'x': round(a['width'] + 14, 1),
                        'y': round((pin_y['17'] + pin_y['31']) / 2 - x['height'] / 2 - 10, 1)}],
        'groups': [{'id': 'power', 'label': '电源', 'color': '#d7263d'}, {'id': 'i2c', 'label': 'I2C 信号', 'color': '#1f6fd1'}],
        'wires': [{'id': i, 'from': f'xiao.{pad}', 'to': f'a7z.p{pin}', 'color': col, 'group': g, 'label': cap}
                  for i, pad, pin, col, g, cap in WIRES],
    }


TEXT = ("{all:'全部',step:'逐根接线',exitStep:'显示全部',prev:'← 上一根',next:'下一根 →',stepOf:(n,t)=>'第 '+n+' 根，共 '+t+' 根',"
        "zoomIn:'放大两端',zoomOut:'收起放大图',hint:'点一下针脚或导线看详情。',wires:'导线',noWire:'这根针没有接线。',issues:'检查',"
        "part:'型号',unrouted:'找不到不遮挡的走线，用虚线直连表示。',roles:{power:'电源',ground:'地线',signal:'信号',nc:'不接'}}")


def html(host_id: str = 'touch-bench') -> str:
    """The bench as a page fragment: wiring-kit CSS and JS inlined, no network fetch."""
    css = (WK / 'wiring-kit.css').read_text()
    js = (WK / 'wiring-kit.js').read_text().replace('</script', '<\\/script')
    data = json.dumps(bench(), ensure_ascii=False).replace('</', '<\\/')
    return (f'<style>{css}</style><div class="wkhost" id="{host_id}"></div><script>{js}</script>'
            f'<script>WiringKit.render(document.getElementById("{host_id}"),{data},'
            f'{{text:{TEXT},pinLabel:(pin,m)=>m.id==="a7z"?pin.label+" 号":pin.label}});</script>')


if __name__ == '__main__':
    b = bench()
    print(json.dumps({m['id']: [m['width'], m['height'], len(m['pins'])] for m in b['modules']}), b['placements'])
