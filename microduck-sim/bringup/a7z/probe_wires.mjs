// Probe A7Z-WIRES.html at 390 px: overflow, button font size, and the click-to-highlight behaviour.
// Run: node probe_wires.mjs   (headless Chrome via ../build/probe/cdp.mjs; screenshots in shots/)
import { launch } from '../build/probe/cdp.mjs';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const OUT = path.join(HERE, 'shots');
const PAGE = 'file://' + path.join(HERE, '..', 'A7Z-WIRES.html');
const b = await launch({ profile: path.join(OUT, '.profile') });
await b.page('Emulation.setDeviceMetricsOverride', { width: 390, height: 844, deviceScaleFactor: 2, mobile: true });
await b.page('Page.navigate', { url: PAGE });
await b.waitFor(`document.readyState === 'complete'`);
const click = (sel) => b.eval(`(() => { const e = document.querySelector(${JSON.stringify(sel)});
  e.dispatchEvent(new MouseEvent('click', { bubbles: true })); 
  return { sel: document.getElementById('map').classList.contains('sel'),
           hl: [...document.querySelectorAll('.wire.hl')].map(w => w.dataset.w),
           pins: [...document.querySelectorAll('.pin.hl')].map(p => p.dataset.b + p.dataset.n),
           txt: document.getElementById('txt').textContent }; })()`);
const res = {
  layout: await b.eval(`({ scrollW: document.documentElement.scrollWidth, W: innerWidth,
    small: [...document.querySelectorAll('button')].filter(e => parseFloat(getComputedStyle(e).fontSize) < 16).length })`),
  piPin5: await click('.pin[data-b="p"][data-n="5"]'),
  a7zPin39: await click('.pin[data-b="a"][data-n="39"]'),
  chipTouch: await click('.chip[data-w="t-sda"]'),
  emptyPin: await click('.pin[data-b="a"][data-n="8"]'),
};
await click('.pin[data-b="p"][data-n="7"]');
const { cssContentSize } = await b.page('Page.getLayoutMetrics');
const shot = await b.page('Page.captureScreenshot', { format: 'png', captureBeyondViewport: true,
  clip: { x: 0, y: 0, width: 390, height: Math.ceil(cssContentSize.height), scale: 1 } });
fs.writeFileSync(path.join(OUT, 'mob-A7Z-WIRES-pi7.png'), Buffer.from(shot.data, 'base64'));
res.console = b.consoleProblems();
await b.close();
console.log(JSON.stringify(res, null, 1));
