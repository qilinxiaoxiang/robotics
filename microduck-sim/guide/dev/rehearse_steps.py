"""Rehearse guide steps headless (no browser pane, no approval prompts): load dist/MICRODUCK-BUILD.html at each #step id,
wait for the viewer, nudge the mouse so the on-demand renderer draws a frame, screenshot, and collect console errors.
    uv run --with playwright python guide/dev/rehearse_steps.py [step-id ...]   (uses the installed Google Chrome)
Writes pw/<step>.png and pw/result.json in the current directory."""
import os
import sys, json, time
from playwright.sync_api import sync_playwright
PAGE = 'file:///Users/xiangzheng/code/robotics/microduck-sim/guide/dist/MICRODUCK-BUILD.html'
STEPS = sys.argv[1:] or ['saddle-mount','saddle-antenna','saddle-board','saddle-card','saddle-copper','saddle-plugs','saddle-fan','saddle-head-plugs','saddle-lid']
out = {}
with sync_playwright() as p:
    b = p.chromium.launch(channel='chrome', args=['--use-angle=swiftshader','--enable-unsafe-swiftshader','--ignore-gpu-blocklist'])
    pg = b.new_page(viewport={'width':1280,'height':900})
    errs = []
    pg.on('console', lambda m: errs.append(m.text) if m.type in ('error','warning') else None)
    pg.on('pageerror', lambda e: errs.append('PAGEERROR '+str(e)))
    pg.goto(PAGE + '#' + STEPS[0], wait_until='load'); pg.wait_for_timeout(12000)
    for s in STEPS:
        pg.evaluate(f"location.hash='#{s}'"); pg.wait_for_timeout(6000)
        box = pg.locator('canvas').first.bounding_box()
        pg.mouse.move(box['x']+box['width']/2, box['y']+box['height']/2); pg.mouse.move(box['x']+box['width']/2+30, box['y']+box['height']/2+20)
        pg.wait_for_timeout(1500)
        title = pg.evaluate("document.querySelector('h1, .step-title, [data-step-title]')?.textContent?.trim()")
        os.makedirs('pw', exist_ok=True); pg.screenshot(path=f'pw/{s}.png')
        out[s] = dict(title=title, url=pg.url)
        print(s, '|', title)
    out['console'] = [e for e in errs if 'GL Driver Message' not in e]
    b.close()
json.dump(out, open('pw/result.json','w'), indent=1)
print('console (non-GL):', out['console'][:10])
