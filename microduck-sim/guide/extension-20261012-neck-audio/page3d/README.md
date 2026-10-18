# Head extension 3D exploded view

`HEAD-3D.html` is a self-contained interactive 3D page (Chinese UI) that shows the V1.9 neck-route + audio extension
inside the head. You can orbit, zoom and pan, pull the head apart with the 拆开 slider, click a part to see what it is,
hide parts, and switch to a wiring view of the amplifier. Open the file directly in a browser. It needs no network,
server or browser storage.

The printed parts (head cap, speaker retainer, four clips) are the V1.9 release solids from `guide/print/ext-v19/`,
sha256-checked against `manifest-ext-v19.json` at build time. The amplifier, speaker, connector housings and screw
envelopes are still the audio and pi-mount study solids. This folder changes no design source.

## Rebuild

Run these from this folder with the CAD venv:

```bash
/tmp/microduck-cad-venv/bin/python check_alignment.py      # writes alignment.json (read-only checks, a few seconds)
/tmp/microduck-cad-venv/bin/python build_head3d.py         # writes HEAD-3D.html and build-summary.json (about 25 s)
node probe_head3d.mjs HEAD-3D.html <out-dir>               # headless Chrome check at 1280 px and 390 px
```

Both Python scripts re-hash every V1.9 solid they read and stop on a mismatch with `manifest-ext-v19.json`
(`resistor-placement.json` for the resistor envelope), so a solid that is being rebuilt cannot get in under a stale
manifest. `build-summary.json` records the sha of each solid the page was built from.

The builder embeds the alignment lines from `alignment.json`, so run the checker first after any geometry change.
The probe prints one `ok`/`FAIL` line per width and saves screenshots plus `report.json` in `<out-dir>`. It uses
`../../../bringup/build/probe/cdp.mjs` and needs Chrome. The only console messages it should see are Chrome's
"GPU stall due to ReadPixels" warnings, which come from the probe reading back pixels.

## Files

- `build_head3d.py`: the generator. It holds the part list (`ITEMS`: Chinese name, status class, role, fixing, notes,
  sources), the explode blocks (`BLOCKS`), the wiring labels and camera presets. It decimates meshes, packs them into one
  gzip + base64 blob and inlines three.js r164.1 and OrbitControls through `guide/build_guide.py` (`load_three`).
- `src/template.html`, `src/style.css`, `src/app.js`: page shell, styles (light theme, bottom sheet under 760 px) and
  viewer logic.
- `check_alignment.py` → `alignment.json`: frame and fit checks between the V1.9 solids, the study solids and the V1.8
  parts.
- `probe_head3d.mjs`: the headless acceptance check.
- `build-summary.json`: output size, triangle counts, the cap-added cleanup numbers, the V1.9 source shas, the route
  length, and every part with its status class.

## Sources

All paths are relative to `guide/extension-20261012-neck-audio/` unless they start with `guide/`.

- V1.8 parts: `guide/data/guide-data.json` (the meshes the V1.8 assembly guide draws, already in the head frame).
  The torso shells and neck parts are drawn only as the hidden 脖子 background.
- V1.9 printed parts: `guide/print/ext-v19/head_cap_v19-world.stl`, `speaker_retainer_v19-world.stl`,
  `clip_torso_v19-world.stl`, `clip_bracket_v19-world.stl`, `clip_head_v19-world.stl`, `clip_cap_v19-world.stl`.
- Gain resistor: built in `build_head3d.py` (`resistor_parts()`) from trimesh/manifold3d primitives at the U4 placement in
  `guide/print/ext-v19/resistor-placement.json` (`candidates.U4_detail.record`): 6.3 × 2.4 mm body in a 7 × 2.8 mm
  heat-shrink sleeve, two 0.6 mm U-bent leads hooked round the GAIN and Vin tails, a solder blob on each tail. The 4 mm
  underside envelope `guide/print/ext-v19/resistor_envelope_v19-world.stl` is a hidden comparison item that carries the
  clearance figures. Facts from `resistor-placement.json` and `bringup/build/audio-bench/README.md` with its drawings.
- Wires: `guide/print/ext-v19/route-v19.json`. The bundle is drawn as tubes through the route points (9–16, 16–24,
  24–32 inside the head; 0–9 as the hidden neck background), the fan wires and the audio jumpers from its `fanWires` and
  `audioWires`. Jumper lengths from `audio/wires.json`. The rejected pin-14 ground alternative still comes from
  `audio/wire-routes.json`.
- Speaker, amplifier, screw envelopes, header housings: `audio/study-solids/*.stl`. Pi screws:
  `pi-mount/study-solids/A-pi_screws_envelope-world.stl` with E-pi-04 replaced by its V1.9 M2 × 8 envelope from
  `guide/content/fasteners.json` (`pi_screws_v19()`).
- Text: `guide/print/ext-v19/README.md` (parts, screws, connection methods, check numbers),
  `HANDOFF-20261013.md`, `integrated/README.md`, `audio/README.md`, `pi-mount/README.md`. Anything a source calls
  inference carries a 推测 badge on the page.

Two meshes are derived here rather than read from a file:

- **Cap-added highlight.** It is the V1.9 cap minus the V1.8 cap, recomputed with manifold3d (5054.9 mm³, matching
  `integrated/cap-build.json`). Where the two caps share a surface, the boolean leaves zero-volume fins that render as
  long blades. A face is kept only if a point 0.02 mm behind it lies inside the V1.9 cap and outside the V1.8 cap.
- **Pi pin 34 housing.** No STL exists. It is the pin 14 housing moved −25.4 mm in y, the same way
  `integrated/scripts/route_scene.py` builds it.

## How the page works

- **Status colours.** Each part has one class: 改动的 V1.8 件 (V1.9 cap), 新打印件 (retainer, four clips), 外购电子件
  (amp, resistor, speaker, Pi, camera), 线和插头, 螺丝, V1.8 不变. Material added to the cap is yellow. The neck, torso
  shells and the neck part of the bundle are hidden background items.
- **Lower clips.** The torso and bracket clips sit below the head (z 30–40 and 79–86). They are visible by default but
  excluded from camera framing (`noframe`), so the home view stays on the head; the 脖子 toggle shows the parts they sit
  on and the wire that runs through them.
- **Explode.** From 0 to 50 % the cap lifts straight up with the Pi, amplifier, resistor, speaker, retainer and cap clip,
  because they all hang from it. From 50 to 100 % each block moves by its own offset. Wires that join two blocks stretch
  between them: each tube vertex moves by a blend of the two block offsets, weighted by its position along the wire.
- **Wiring view.** Non-audio parts fade out. The five jumpers get signal colours, and labels name each Pi pin and signal.
  The panel lists amp-to-Pi pins, header order (GAIN marked as taken by the resistor), wire lengths and the speaker
  leads as recorded. Where the records say nothing, the panel says so.
- **Test hooks.** `window.__head3d` exposes `setExplode`, `setMode`, `setView`, `select`, `state`, `sample` and `screenOf`
  for the probe.

## Not modelled or not recorded

- Which amplifier terminal and which speaker pad is +.
- Real jumper wire colours. The page colours are for telling the wires apart.
- The 1 mm foam ring under the speaker, the Kapton strip over the resistor legs and the CSI ribbon.
- Pin 34 housing exists only as the derived solid described above.
- The 3006 terminal-block identity and the SD-pin mono mode are inference in `audio/README.md`, and the page marks them
  推测.
- `alignment.json` `wiresAtRest` measures sphere-swept tubes against the solids; the authority for cable clearance is
  `guide/print/ext-v19/checks/cable-check-v19.json`.
