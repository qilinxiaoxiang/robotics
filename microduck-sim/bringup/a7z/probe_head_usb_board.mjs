// Probe ../HEAD-USB-BOARD.html at 1280 px and 390 px: horizontal overflow, small controls, broken images, tables, external
// files, wiring-kit issues, console problems. Saves full-page screenshots and one close shot per wiring view in shots/.
// Run: node probe_head_usb_board.mjs [profile dir]   (uses ../build/probe/cdp.mjs and the installed Google Chrome, headless)
import { launch } from '../build/probe/cdp.mjs';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const OUT = path.join(HERE, 'shots');
const PAGE = path.join(HERE, '..', 'HEAD-USB-BOARD.html');
const profile = process.argv[2] || fs.mkdtempSync(path.join(os.tmpdir(), 'hub-probe-'));
const views = [
  { name: 'desk', width: 1280, height: 900, deviceScaleFactor: 1, mobile: false },
  { name: 'mob', width: 390, height: 844, deviceScaleFactor: 1, mobile: true },
];
const CHECK = `(() => {
  const W = innerWidth, wide = [];
  for (const el of document.querySelectorAll('body *')) {
    const r = el.getBoundingClientRect();
    if (r.width && r.right > W + 1) wide.push(el.tagName.toLowerCase() + '.' + [...el.classList].join('.') + ' ' + Math.round(r.right));
  }
  const small = [...document.querySelectorAll('input,textarea,select,button')].filter(e => parseFloat(getComputedStyle(e).fontSize) < 16).map(e => e.tagName + ' ' + (e.textContent || '').trim().slice(0, 8) + ' ' + getComputedStyle(e).fontSize);
  const broken = [...document.querySelectorAll('img')].filter(i => !i.complete || i.naturalWidth === 0).map(i => i.alt);
  const hosts = [...document.querySelectorAll('.wkhost')].map(h => { const r = h.getBoundingClientRect(); return { id: h.id, x: r.left + scrollX, y: r.top + scrollY, w: r.width, h: r.height, svg: h.querySelectorAll('svg').length, text: (h.innerText.match(/检查[^\\n]*\\n[^\\n]*/) || [''])[0] }; });
  return { scrollW: document.documentElement.scrollWidth, W, wide: wide.slice(0, 8), small, broken, hosts,
           tables: document.querySelectorAll('table').length, imgs: document.querySelectorAll('img').length,
           ext: [...document.querySelectorAll('script[src],link[href]')].length, h: document.documentElement.scrollHeight };
})()`;
const b = await launch({ profile });
const report = [];
for (const v of views) {
  await b.page('Emulation.setDeviceMetricsOverride', v);
  await b.page('Page.navigate', { url: 'file://' + PAGE });
  await b.waitFor(`document.readyState === 'complete' && [...document.images].every(i => i.complete)`);
  await new Promise((r) => setTimeout(r, 800));
  const m = await b.eval(CHECK);
  const { cssContentSize } = await b.page('Page.getLayoutMetrics');
  const h = Math.min(Math.ceil(cssContentSize.height), 30000);
  const shot = await b.page('Page.captureScreenshot', { format: 'png', captureBeyondViewport: true, clip: { x: 0, y: 0, width: v.width, height: h, scale: 1 } });
  const file = path.join(OUT, `${v.name}-HEAD-USB-BOARD.png`);
  fs.writeFileSync(file, Buffer.from(shot.data, 'base64'));
  for (const host of m.hosts) {
    const s = await b.page('Page.captureScreenshot', { format: 'png', captureBeyondViewport: true, clip: { x: 0, y: Math.max(0, host.y - 8), width: v.width, height: Math.ceil(host.h) + 16, scale: 1 } });
    fs.writeFileSync(path.join(OUT, `${v.name}-HEAD-USB-BOARD-${host.id}.png`), Buffer.from(s.data, 'base64'));
  }
  report.push({ view: v.name, file, ...m });
}
const problems = b.consoleProblems();
await b.close();
fs.writeFileSync(path.join(OUT, 'head-usb-board-report.json'), JSON.stringify({ date: new Date().toISOString(), report, problems }, null, 1));
let fail = false;
for (const r of report) {
  const bad = r.scrollW > r.W + 1 || r.small.length || r.broken.length || r.tables || r.ext || r.hosts.some((x) => !x.svg);
  fail = fail || bad;
  console.log(`${bad ? 'FAIL' : 'ok  '} ${r.view} scrollW=${r.scrollW}/${r.W} h=${r.h} imgs=${r.imgs} views=${r.hosts.length} tables=${r.tables} ext=${r.ext}`
    + (r.wide.length ? ' wide=' + r.wide.join('|') : '') + (r.small.length ? ' small=' + r.small.join('|') : '') + (r.broken.length ? ' broken=' + r.broken.join('|') : ''));
  for (const x of r.hosts) if (x.text) console.log('   ', x.id, x.text.replace(/\n/g, ' '));
  console.log('   ', r.file);
}
console.log('console problems:', JSON.stringify(problems).slice(0, 1500));
process.exit(fail ? 1 : 0);
