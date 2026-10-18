// Probe BRINGUP.html navigation at desktop and phone width: deep link landing, Back/Forward between steps,
// sticky step list / step bar while scrolling, and no runtime exceptions.
// Usage: node probe/probe-nav.mjs /abs/path/BRINGUP.html /abs/out-dir
import { launch } from './cdp.mjs';
import fs from 'node:fs';
import path from 'node:path';

const PAGE = process.argv[2];
const OUT = process.argv[3];
fs.mkdirSync(OUT, { recursive: true });
const views = [
  { name: 'desk', width: 1280, height: 900, deviceScaleFactor: 1, mobile: false },
  { name: 'mob', width: 390, height: 844, deviceScaleFactor: 2, mobile: true },
];
const b = await launch({ profile: path.join(OUT, '.profile') });
const sleep = ms => new Promise(r => setTimeout(r, ms));
const results = [];
const SUBSECS = 12; // .subsec sections in the template: pw-1..5 and ab-1,2,3,6,7,8,9
const check = (view, name, ok, detail) => { results.push({ view, name, ok, detail }); console.log(`${ok ? 'ok  ' : 'FAIL'} ${view} ${name} ${JSON.stringify(detail)}`); };
const ready = async () => { await b.waitFor(`document.readyState === 'complete' && !!document.querySelector('.step.on')`); };
// Position of a heading relative to the sticky header (and the step bar when it is one).
const headPos = (id) => `(() => {
  const el = document.getElementById(${JSON.stringify(id)}); const h = el.querySelector('h2') || el;
  const r = h.getBoundingClientRect(); const hdr = document.querySelector('header.top').getBoundingClientRect().bottom;
  const list = document.querySelector('#steplist'); const bar = getComputedStyle(list).display === 'flex' ? list.getBoundingClientRect().bottom : hdr;
  return { top: Math.round(r.top), bottom: Math.round(r.bottom), hdr: Math.round(hdr), bar: Math.round(bar), inner: innerHeight, on: document.querySelector('.step.on').id, scrollY: Math.round(scrollY) };
})()`;
const listPos = `(() => { const l = document.querySelector('#steplist').getBoundingClientRect(); return { top: Math.round(l.top), bottom: Math.round(l.bottom), inner: innerHeight, scrollY: Math.round(scrollY), on: document.querySelector('.step.on').id, pos: getComputedStyle(document.querySelector('#steplist')).position, hash: location.hash }; })()`;

for (const v of views) {
  await b.page('Emulation.setDeviceMetricsOverride', v);
  await b.page('Emulation.setTouchEmulationEnabled', { enabled: v.mobile });

  // (a) fresh load of a section deep link inside step 13
  await b.page('Page.navigate', { url: 'file://' + PAGE + '#ab-8' });
  await ready();
  await sleep(3000);
  const a = await b.eval(headPos('ab-8'));
  check(v.name, 'deep link #ab-8 shows s13, heading below sticky header/bar and inside viewport', a.on === 's13' && a.top >= a.bar - 1 && a.bottom <= a.inner, a);
  await b.screenshot(path.join(OUT, `${v.name}-deeplink.png`));

  // (b) list clicks create history entries; Back/Forward show the right step
  await b.page('Page.navigate', { url: 'file://' + PAGE + '?tab=steps&step=0' });
  await ready();
  await sleep(500);
  const h0 = await b.eval('location.hash');
  check(v.name, 'initial load replaces URL with the step hash', h0 === '#s0', { hash: h0 });
  await b.eval(`document.querySelector('#steplist button[data-i="7"]').click()`);
  await sleep(300);
  const s7 = await b.eval(listPos);
  check(v.name, 'click step 7 shows s7 with hash #s7', s7.on === 's7' && s7.hash === '#s7', s7);
  await b.eval(`document.querySelector('#steplist button[data-i="13"]').click()`);
  await sleep(300);
  const s13 = await b.eval(listPos);
  check(v.name, 'click step 13 shows s13 with hash #s13', s13.on === 's13' && s13.hash === '#s13', s13);
  const len = await b.eval('history.length');
  await b.eval('history.back()');
  await sleep(500);
  const back = await b.eval(listPos);
  check(v.name, 'history.back() returns to s7', back.on === 's7' && back.hash === '#s7', { ...back, historyLength: len });
  await b.eval('history.forward()');
  await sleep(500);
  const fwd = await b.eval(listPos);
  check(v.name, 'history.forward() returns to s13', fwd.on === 's13' && fwd.hash === '#s13', fwd);
  await b.eval('history.back()');
  await sleep(500);
  await b.eval('history.back()');
  await sleep(500);
  const back2 = await b.eval(listPos);
  check(v.name, 'two more back() reach the first entry s0 (no duplicate first entry)', back2.on === 's0' && back2.hash === '#s0', back2);
  await b.eval('history.forward(); history.forward()');
  await sleep(600);
  // prev/next buttons are history entries too
  await b.eval(`document.querySelector('#prevStep').click()`);
  await sleep(300);
  const prev = await b.eval(listPos);
  check(v.name, 'prev button shows s12 with hash #s12', prev.on === 's12' && prev.hash === '#s12', prev);
  await b.eval('history.back()');
  await sleep(500);
  const back3 = await b.eval(listPos);
  check(v.name, 'back() after prev returns to s13', back3.on === 's13' && back3.hash === '#s13', back3);

  // (c) sticky list / bar after scrolling inside step 13 (wide layout) and inside a column-layout step (s4)
  await b.eval('window.scrollTo(0, 3000)');
  await sleep(300);
  const c13 = await b.eval(listPos);
  check(v.name, 'after scrollY=3000 in s13 the step list/bar is inside the viewport', c13.scrollY >= 2500 && c13.top >= 0 && c13.top < c13.inner && c13.bottom > 0, c13);
  await b.eval(`document.querySelector('#steplist button[data-i="4"]').click()`);
  await sleep(300);
  await b.eval('window.scrollTo(0, 3000)');
  await sleep(300);
  const c4 = await b.eval(listPos);
  check(v.name, 'after scrollY=3000 in s4 the step list/bar is inside the viewport', c4.on === 's4' && c4.scrollY >= 2500 && c4.top >= 0 && c4.top < c4.inner && c4.bottom > 0, c4);
  await b.screenshot(path.join(OUT, `${v.name}-scrolled-s4.png`));

  // section link inside the page: ab-jump pill → heading under the bar
  await b.eval(`document.querySelector('#steplist button[data-i="13"]').click()`);
  await sleep(300);
  await b.eval(`document.querySelector('.ab-jump a[href="#ab-8"]').click()`);
  await sleep(600);
  const j = await b.eval(headPos('ab-8'));
  check(v.name, 'ab-jump link lands #ab-8 heading below the bar', j.on === 's13' && j.top >= j.bar - 1 && j.bottom <= j.inner, j);

  // id tags present
  const tags = await b.eval(`({ steps: document.querySelectorAll('.step > h1 > .idtag').length, subs: document.querySelectorAll('.subsec > h2 > .idtag').length, sample: document.querySelector('#s13 > h1 > .idtag').textContent, sub: document.querySelector('#ab-8 > h2 > .idtag').textContent, size: getComputedStyle(document.querySelector('#ab-8 > h2 > .idtag')).fontSize })`);
  check(v.name, 'id tags on every step h1 and subsec h2', tags.steps === 14 && tags.subs === SUBSECS && tags.sample === '#s13' && tags.sub === '#ab-8', tags);
  await b.eval('window.scrollTo(0, 0)');
  await sleep(200);
  await b.screenshot(path.join(OUT, `${v.name}-s13-top.png`));
  // clicking a tag copies the link (clipboard, or a prompt fallback) and must not change the hash
  try { await b.send('Browser.grantPermissions', { permissions: ['clipboardReadWrite', 'clipboardSanitizedWrite'] }); } catch (e) { /* not grantable for file:// in this build */ }
  const before = await b.eval('location.hash');
  const seen = b.events.length;
  const clickDone = b.eval(`document.querySelector('#s13 > h1 > .idtag').click(); 0`);
  // The clipboard path shows '已复制链接' on the tag for 1.4 s; the fallback path opens a prompt dialog (a CDP event).
  let dialog = null, copied = false;
  for (let i = 0; i < 20 && !dialog && !copied; i++) {
    await sleep(100);
    dialog = b.events.slice(seen).find(e => e.method === 'Page.javascriptDialogOpening');
    if (dialog) await b.page('Page.handleJavaScriptDialog', { accept: false });
    else copied = await b.eval(`document.querySelector('#s13 > h1 > .idtag').textContent === '已复制链接'`);
  }
  await clickDone;
  const tag = await b.eval(`({ hash: location.hash, text: document.querySelector('#s13 > h1 > .idtag').textContent })`);
  const prompted = !!dialog;
  check(v.name, 'tag click copies the link (clipboard or prompt fallback) and keeps the hash', (copied || prompted) && tag.hash === before, { ...tag, copied, prompted, promptUrl: dialog ? dialog.params.defaultPrompt : null });

  // tab switch and back
  await b.eval(`document.querySelector('#tabs button[data-tab="parts"]').click()`);
  await sleep(300);
  const tp = await b.eval(`({ hash: location.hash, tab: document.querySelector('.tab.on').id })`);
  check(v.name, 'parts tab via hash', tp.hash === '#parts' && tp.tab === 'tab-parts', tp);
  await b.eval('history.back()');
  await sleep(500);
  const tb = await b.eval(`({ hash: location.hash, tab: document.querySelector('.tab.on').id, on: document.querySelector('.step.on').id })`);
  check(v.name, 'back() from parts returns to the steps tab at #ab-8', tb.tab === 'tab-steps' && tb.hash === '#ab-8' && tb.on === 's13', tb);
}
const exceptions = b.events.filter(e => e.method === 'Runtime.exceptionThrown').map(e => JSON.stringify(e.params.exceptionDetails).slice(0, 300));
check('all', 'no Runtime.exceptionThrown', exceptions.length === 0, exceptions);
const problems = b.consoleProblems();
console.log('console problems:', JSON.stringify(problems).slice(0, 1500));
fs.writeFileSync(path.join(OUT, 'nav-report.json'), JSON.stringify({ results, problems }, null, 1));
b.proc.kill();
process.exit(results.every(r => r.ok) ? 0 : 1);
