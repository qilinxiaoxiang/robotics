# MicroDuck assembly guide viewer

`build_guide.py` turns one `guide-data.json` into one self-contained HTML file. The file opens from disk or any static host and makes no network requests: three.js r164.1 and OrbitControls are inlined, and a Content-Security-Policy blocks external loads.

## Build

```bash
cd ~/code/robotics/microduck-sim
python3 guide/build_guide.py --data <guide-data.json> --out <file.html>
python3 guide/build_guide.py --data <guide-data.json> --check     # validate only, exit 1 on errors
```

Options: `--manifest <summary.json>` writes the build summary that is also printed to stdout. `--allow-errors` builds despite validation errors. `--three <dir>` points at another three.js package; the default is `microduck-simulator/app/node_modules/three`. The bundler uses only the Python standard library.

Development fixture (real meshes, placeholder steps and cables):

```bash
python3 guide/dev/make_sample_data.py
python3 guide/build_guide.py --data guide/dev/sample-data.json --out guide/dev/sample.html
```

## Data schema (schemaVersion 1)

Units are millimetres in the world frame (x forward, y left, z up).

- **Top level:** `schemaVersion: 1`, `title`, `subtitle`, `revision`, `units: "mm"`, `frame`, `parts[]`, `chapters[]`, `steps[]`, `cables[]`, an optional `screws[]` and an optional `legend[]`.
- **Part:** `key` (unique), `name`, `color` (`#rrggbb`), `module`, `status` (`assembled | printed | reprint | new-print | purchased | owned`), `positionB64` (little-endian float32 xyz), `indexB64` (uint32 triangles), `bounds` (`[[minx,miny,minz],[maxx,maxy,maxz]]`) and an optional `kit` name. Parts with the same `kit` name (or, without one, the same `name`), colour and status count as one line ×N on a chapter's parts page.
- **Chapter:** `id`, `title`, `summary`, and `intro: false` for a chapter that only lays out the inventory. Every other chapter opens with an "Identify the parts" page (the parts it adds that are not yet on the robot, laid out on the bench) and, when it has screws or loose fasteners and tools, a "Prepare screws and tools" page.
- **Step:**
  - `id`, `chapter` and `title` identify the step.
  - `show` lists parts already installed, drawn solid.
  - `add` lists parts installed in this step. They are outlined and animated in.
  - `context` lists parts drawn as ghosts. The viewer can switch them to solid or hidden.
  - `approach` maps a part key to `[dx,dy,dz]` or to a waypoint list `[[dx,dy,dz], ..., [0,0,0]]`; the part travels from final position plus the first offset through each waypoint to its final position. Use waypoints when a straight line would pass through a part (for example the OpenRB tray: back, then forward, then down).
  - `group` (optional) is `{label, approach}` for placing a subassembly built earlier on the bench; `approach` takes the same vector or waypoint list. All `add` parts travel together with one arrow, and the step panel lists the subassembly as one item.
  - `pose` (optional) is `{parts, pivot: [x,y,z], axis: [x,y,z], deg, from?}`. The listed parts (keys or modules) turn `deg` degrees about the axis through `pivot` for this step, for example the jaw held open. With `from`, they swing from `from` to `deg` while the step plays, after any path has brought them in.
  - `flex` (optional) is `{parts, riders?, ramp: [r0, r1], spread: [-y, +y], window: [in, out]}` for a part whose arms are sprung apart to pass a boss. Vertices of the listed parts with |y| beyond `r1` move outwards by `spread` (mm, −Y arm and +Y arm), with a linear ramp from `r0`. The spread rises over eased progress 0 to `in`, holds, and releases between `out` and 1 as the part snaps home. `riders` maps a part key to −1 or +1: that part moves with the −Y or +Y arm.
  - `bench: true` marks a step done off the robot (servo ID checks, the harness, a subassembly). Its parts count as installed only when a later non-bench step adds them; parts installed in earlier chapters are drawn muted.
  - `camera` holds `{position, target}`.
  - `prepare[]` items are `{item, qty, kind: fastener | printed | electronic | tool | cable | other, note?}`.
  - `instructions[]`, `checks[]` and `warnings[]` are lists of strings.
  - `cables[]` lists cable ids.
  - `images[]` items are `{src: "data:image/...", caption}`.
  - `wiring` (optional) is `{title?, caption?, pinText?, bench}`: a soldering or wiring drawing drawn by `~/code/wiring-kit` above the instructions. `bench` is a wiring-kit Bench (modules, placements, wires, groups; board artwork only as `data:` URIs). `pinText` maps `"module.pin"` to the label drawn at that wire end, for example `"dfr.VIN": "1 VIN"`, so the instructions can refer to numbered markers. The drawing has group filters and a wire-by-wire mode; the guide's arrow keys stay on step navigation. When any step has `wiring`, the bundler inlines `wiring-kit.js` and `wiring-kit.css` from `--wiring-kit` (default `~/code/wiring-kit/dist`). `guide/content/wiring/dfr1202.py` is the example.
- **Cable:** `id`, `label`, `kind` (`dxl | power-20v | power-15v | power-7v | power-5v | ground | usb | uart | i2c | i2s | speaker | csi`), `color`, `radius` (default 0.9), `path` (at least two points, drawn as a centripetal Catmull-Rom tube), `from`, `to`, `lengthMM?`, `note?`.
- **Screw:** `step` (step id), `spec` (for example `M2 x 6 TAP`), `center` (head seat, mm), `axis` (unit vector, head to tip), and optional `kind` (`tap | machine | machine-nut`), `diameterMm`, `lengthMm`, `headDiameterMm`, `headHeightMm`, `nut`, `washer`, `throughPart`, `intoPart` and `where` (short text for the step panel). A step's screws are numbered on screen in list order and coloured by spec; screws from earlier steps stay grey while their part is drawn solid.
- **Legend entry:** `{kind, color, label}`. The viewer lists only the kinds drawn in the current step.

Entries in `show`, `add` and `context` match a part by `key` or by `module`. When a part appears in more than one list, `add` wins over `show`, and `show` wins over `context`. A step's highlighted cables are its own `cables`; cables from earlier steps of the same chapter are drawn faint. Steps are ordered by chapter, then by their order in `steps[]`.

## Viewer behaviour that affects authoring

- **Missing camera:** when `camera` is absent, the viewer frames the shown and added parts from the front-left, above the model. The bundler reports this as a warning.
- **Narrow screens:** authored cameras are treated as framed for a 16:10 viewer. On narrower viewers, such as phones, the camera backs off along the same line, only as far as needed to keep the added parts in frame.
- **Small parts:** added parts with a bounding radius under 15 mm also get a locator box that stays visible through other parts.
- **Timeline:** each step has Play, Pull apart, Seated and a progress slider. Parts travel along their `approach` first, then the step's screws drive in along their axes. A screw already installed in a part that moves in this step (its `throughPart` or `intoPart`) rides along with that part's path and pose.
- **Faint cables:** an earlier cable of the chapter is drawn only while parts at both of its ends are visible.
- **Validation:** the bundler fails on unknown part, module, cable or chapter references, malformed geometry (bad base64, out-of-range indices, NaN), invalid colours or statuses, and non-`data:` images. It warns on bounds that differ from the mesh by more than 1 mm, on duplicate `add`, and on unused cables.

## Output layout

The guide JSON is embedded gzip+base64 without the mesh fields. Part geometry is moved into a single gzip+base64 binary block, and `parts[].geom` holds `[posOffset, posBytes, idxOffset, idxBytes]`. This avoids base64-inside-gzip-inside-base64; the 1.56 M-triangle fixture builds to 15.9 MB. The browser decompresses both blocks with `DecompressionStream('gzip')`, builds each mesh once and computes its normals. A step change only toggles visibility and materials.

`localStorage` holds only done marks, ticked checks, the last step and the context mode. Every access is wrapped, and the page works when storage throws.
