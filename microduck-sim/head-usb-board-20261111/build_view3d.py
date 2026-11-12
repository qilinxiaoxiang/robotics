#!/usr/bin/env python3
"""Build board-in-head.html: a rotatable 3D view of the routed head USB board inside the head, for judging its size.

Head parts come from guide/data/guide-data.json (HOME pose); the board, its parts and the plug envelopes are the same
boxes fit_check.py tests (from pcb/build/footprints.json). The page is self-contained: three.js is inlined through
guide-kit's load_three, no network request. Page text is Chinese.

Run (Mac mini): ~/.venvs/microduck-dyn/bin/python build_view3d.py
"""
import base64
import json
import sys
from pathlib import Path

import numpy as np

import fit_check as F
import space_check as S

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'guide'))
from build_guide import DEFAULT_THREE, load_three, script_safe  # noqa: E402

SHELL = {'head_cap', 'head_bottom', 'face_panel', 'eye_trim'}
GONE = S.REMOVED | S.SOFT                      # amp module leaves the head; the camera lead is re-routed
COIN_D, COIN_T = 24.26, 1.75                   # US quarter


def b64(a):
    return base64.b64encode(np.ascontiguousarray(a).tobytes()).decode()


def head_parts():
    out = []
    for p in S.GUIDE['parts']:
        b = p['bounds']
        lo, hi = (b['min'], b['max']) if isinstance(b, dict) else b
        if p['key'] in GONE or hi[2] < 100.0 or hi[0] < -35.0:
            continue
        v, f = S.mesh(p)
        out.append({'key': p['key'], 'name': p['name'], 'color': p.get('color', '#bbbbbb'),
                    'shell': p['key'] in SHELL, 'n': len(v), 'pos': b64(v.astype('<f4')), 'idx': b64(f.astype('<u4'))})
    return out


def board_boxes():
    out = []
    for ref, kind, lo, hi in F.boxes():
        if ref == 'solder tails':
            continue
        if ref == 'pcb':
            group, color = 'pcb', '#1f7a3d'
        elif kind == 'plug':
            group, color = 'plug', '#e8590c'
        elif ref.startswith('J_'):
            group, color = 'part', '#222222'
        elif ref[0] == 'U':
            group, color = 'part', '#333a44'
        elif ref[0] == 'X':
            group, color = 'part', '#b8b8b8'
        else:
            group, color = 'part', '#8a6d3b'
        out.append({'ref': ref, 'group': group, 'color': color, 'lo': [round(float(x), 2) for x in lo],
                    'hi': [round(float(x), 2) for x in hi]})
    bb = S.BREADBOARD
    out.append({'ref': 'breadboard', 'group': 'old', 'color': '#1c7ed6', 'lo': bb[0], 'hi': bb[1]})
    out.append({'ref': 'breadboard plugs', 'group': 'old', 'color': '#74c0fc',
                'lo': [bb[0][0] - S.PLUG, bb[0][1], bb[0][2]], 'hi': [bb[0][0], bb[1][1], bb[1][2]]})
    return out


PAGE = """<!doctype html>
<html lang="zh"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src data:">
<title>头部 USB 板在头里的大小</title>
<style>
:root { color-scheme: light; }
* { box-sizing: border-box; }
body { margin: 0; background: #f6f5f2; color: #1c1c1c; font: 16px/1.55 -apple-system, "PingFang SC", "Helvetica Neue", sans-serif; }
main { max-width: 1100px; margin: 0 auto; padding: 16px; }
h1 { font-size: 22px; margin: 4px 0 6px; }
p { margin: 6px 0; }
#stage { position: relative; width: 100%; height: min(68vh, 640px); min-height: 340px; background: #fff; border: 1px solid #d9d6cf; border-radius: 10px; overflow: hidden; touch-action: none; }
#stage canvas { display: block; width: 100%; height: 100%; }
#hint { position: absolute; left: 10px; bottom: 8px; font-size: 13px; color: #666; background: rgba(255,255,255,.8); padding: 2px 6px; border-radius: 6px; }
.bar { display: flex; flex-wrap: wrap; gap: 8px; margin: 10px 0; }
.bar button, .bar label { font: inherit; font-size: 16px; padding: 8px 12px; border: 1px solid #c9c5bc; border-radius: 8px; background: #fff; color: #1c1c1c; cursor: pointer; display: inline-flex; align-items: center; gap: 6px; }
.bar button:active { background: #eee; }
.bar input { width: 18px; height: 18px; }
.cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(230px, 1fr)); gap: 10px; margin: 12px 0; }
.card { background: #fff; border: 1px solid #d9d6cf; border-radius: 10px; padding: 10px 12px; }
.card b { display: block; }
.sw { display: inline-block; width: 12px; height: 12px; border-radius: 3px; margin-right: 6px; vertical-align: -1px; }
small { color: #666; }
</style></head><body><main>
<h1>头部 USB 板在头里的大小</h1>
<p>绿色方板就是新板子：<b>30 x 30 mm</b>，连最高的插座一共约 <b>11.6 mm</b> 厚，贴在摄像头背面。拖动旋转，滚轮或双指缩放，右键或双指拖动平移。</p>
<div id="stage"><div id="hint">HOME 姿态，只有零件，没有电线</div></div>
<div class="bar">
  <button data-view="rear">从后上方看</button>
  <button data-view="side">从右侧看</button>
  <button data-view="top">从上面看</button>
  <button data-view="board">只看板子</button>
</div>
<div class="bar">
  <label><input type="checkbox" id="t-shell" checked>头壳（半透明）</label>
  <label><input type="checkbox" id="t-inner" checked>头里的其他零件</label>
  <label><input type="checkbox" id="t-plug" checked>插头伸出的范围</label>
  <label><input type="checkbox" id="t-old">现在的小面包板（对照）</label>
  <label><input type="checkbox" id="t-coin">25 美分硬币（比大小）</label>
</div>
<div class="cards">
  <div class="card"><b><span class="sw" style="background:#1f7a3d"></span>新板子</b>30 x 30 mm，板厚 1.6 mm。上面约 13.5 mm 高的一条是插头区，下面是芯片。</div>
  <div class="card"><b><span class="sw" style="background:#e8590c"></span>插头伸出的范围</b>橙色半透明块：杜邦插头加线出口，从插座顶再往后 16 mm；两个 5 针小插座往后到 14 mm。</div>
  <div class="card"><b><span class="sw" style="background:#1c7ed6"></span>现在的小面包板</b>蓝色块是今天装在同一位置的面包板（20 x 15 mm）和它的插头范围，勾选后可以对比。</div>
  <div class="card"><b><span class="sw" style="background:#c9b037"></span>硬币</b>直径 24.26 mm 的 25 美分硬币，立在板子右边，只用来比大小，不是零件。点“只看板子”时自动出现。</div>
</div>
<p><small>__INFO__</small></p>
</main>
<script>
__THREE__
</script>
<script type="application/json" id="data">__DATA__</script>
<script>
(function () {
  const data = JSON.parse(document.getElementById('data').textContent);
  const stage = document.getElementById('stage');
  const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.setClearColor(0xffffff);
  stage.insertBefore(renderer.domElement, stage.firstChild);
  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(32, 1, 1, 2000);
  camera.up.set(0, 0, 1);                                  // robot frame: z up, x forward, y left
  const controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  scene.add(new THREE.HemisphereLight(0xffffff, 0x9a958c, 1.9));
  const sun = new THREE.DirectionalLight(0xffffff, 1.6);
  sun.position.set(-200, -120, 300);
  scene.add(sun);
  const fill = new THREE.DirectionalLight(0xffffff, 0.7);
  fill.position.set(-150, 200, 60);
  scene.add(fill);

  const groups = { shell: new THREE.Group(), inner: new THREE.Group(), pcb: new THREE.Group(), part: new THREE.Group(),
                   plug: new THREE.Group(), old: new THREE.Group(), coin: new THREE.Group() };
  Object.values(groups).forEach(g => scene.add(g));
  const bytes = s => Uint8Array.from(atob(s), c => c.charCodeAt(0)).buffer;
  for (const p of data.parts) {
    const geo = new THREE.BufferGeometry();
    geo.setAttribute('position', new THREE.BufferAttribute(new Float32Array(bytes(p.pos)), 3));
    geo.setIndex(new THREE.BufferAttribute(new Uint32Array(bytes(p.idx)), 1));
    geo.computeVertexNormals();
    const mat = p.shell
      ? new THREE.MeshStandardMaterial({ color: 0xcfd4da, transparent: true, opacity: 0.16, depthWrite: false, side: THREE.DoubleSide, roughness: 0.9 })
      : new THREE.MeshStandardMaterial({ color: p.color, roughness: 0.75, metalness: 0.05, side: THREE.DoubleSide });
    const m = new THREE.Mesh(geo, mat);
    if (p.shell) m.renderOrder = 5;
    (p.shell ? groups.shell : groups.inner).add(m);
  }
  for (const b of data.boxes) {
    const size = [0, 1, 2].map(i => b.hi[i] - b.lo[i]);
    const geo = new THREE.BoxGeometry(size[0], size[1], size[2]);
    const soft = b.group === 'plug' || b.group === 'old';
    const mat = new THREE.MeshStandardMaterial({ color: b.color, roughness: 0.6, transparent: soft, opacity: soft ? 0.38 : 1, depthWrite: !soft });
    const m = new THREE.Mesh(geo, mat);
    m.position.set((b.lo[0] + b.hi[0]) / 2, (b.lo[1] + b.hi[1]) / 2, (b.lo[2] + b.hi[2]) / 2);
    if (soft) m.renderOrder = 3;
    groups[b.group].add(m);
    if (b.group !== 'part' || size[0] > 3) {
      const e = new THREE.LineSegments(new THREE.EdgesGeometry(geo), new THREE.LineBasicMaterial({ color: soft ? b.color : 0x000000, transparent: true, opacity: 0.55 }));
      e.position.copy(m.position);
      groups[b.group].add(e);
    }
  }
  const c = data.coin;
  const coin = new THREE.Mesh(new THREE.CylinderGeometry(c.d / 2, c.d / 2, c.t, 64), new THREE.MeshStandardMaterial({ color: 0xc9b037, metalness: 0.6, roughness: 0.35 }));
  coin.rotation.z = Math.PI / 2;                             // cylinder axis y -> x: the coin faces backwards like the board
  coin.position.set(c.at[0], c.at[1], c.at[2]);
  groups.coin.add(coin);
  groups.old.visible = false;

  const target = new THREE.Vector3(data.centre[0], data.centre[1], data.centre[2]);
  const views = { rear: [-150, -35, 150], side: [-60, -230, 40], top: [-40, -10, 250], board: [-95, -45, 35] };
  function setView(name) {
    const v = views[name];
    controls.target.copy(target);
    camera.position.set(target.x + v[0], target.y + v[1], target.z + v[2]);
    const only = name === 'board';
    if (only || setView.only) {
      for (const [id, g] of [['t-shell', 'shell'], ['t-inner', 'inner']]) {
        document.getElementById(id).checked = !only;
        groups[g].visible = !only;
      }
    }
    if (only) {                                            // the coin would hide the board in the head views
      document.getElementById('t-coin').checked = true;
      groups.coin.visible = true;
    }
    setView.only = only;
    controls.update();
  }
  document.querySelectorAll('button[data-view]').forEach(b => b.addEventListener('click', () => setView(b.dataset.view)));
  for (const [id, g] of [['t-shell', 'shell'], ['t-inner', 'inner'], ['t-plug', 'plug'], ['t-old', 'old'], ['t-coin', 'coin']]) {
    const box = document.getElementById(id);
    groups[g].visible = box.checked;
    box.addEventListener('change', () => { groups[g].visible = box.checked; });
  }
  function resize() {
    const w = stage.clientWidth, h = stage.clientHeight;
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
  }
  window.addEventListener('resize', resize);
  resize();
  setView(new URLSearchParams(location.search).get('view') || 'rear');
  (function loop() { controls.update(); renderer.render(scene, camera); requestAnimationFrame(loop); })();
})();
</script>
</body></html>
"""


def main():
    boxes = board_boxes()
    pcb = next(b for b in boxes if b['group'] == 'pcb')
    centre = [(pcb['lo'][i] + pcb['hi'][i]) / 2 for i in range(3)]
    data = {'parts': head_parts(), 'boxes': boxes, 'centre': centre,
            'coin': {'d': COIN_D, 't': COIN_T, 'at': [pcb['lo'][0], pcb['lo'][1] - COIN_D / 2 - 3.0, centre[2]]}}
    three_js, orbit_js = load_three(DEFAULT_THREE)
    info = (f"模型来源：装配指南 {S.GUIDE['revision']} 的头部零件网格，板子和插头范围与 fit_check.py 用的是同一组方块"
            f"（{len(boxes)} 个）。功放小板已经拿掉（它的芯片在新板上），摄像头线没画。")
    html = (PAGE.replace('__THREE__', three_js + orbit_js)
            .replace('__DATA__', script_safe(json.dumps(data, separators=(',', ':')), 'data'))
            .replace('__INFO__', info))
    out = HERE / 'board-in-head.html'
    out.write_text(html, encoding='utf-8')
    print(out, round(out.stat().st_size / 1e6, 2), 'MB;', len(data['parts']), 'head parts;', len(boxes), 'boxes')


if __name__ == '__main__':
    main()
