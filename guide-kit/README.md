# guide-kit: assembly guide viewer, bundler and exact audits

One editable source for every robot or hardware assembly guide (MicroDuck, Scout Mini, RIG, ...). A project writes one `guide-data.json` (schemaVersion 1); the kit turns it into one self-contained HTML page and audits what that page animates.

- `build_guide.py`: bundler and validator. `python3 build_guide.py --data guide-data.json --out page.html` (`--check` validates only). Standard library only.
- `viewer/`: `app.js`, `style.css`, `template.html`. `viewer/README.md` is the data schema (parts, chapters, steps, `approach`, `group`, `pose`, `flex`, `screws`, `legend`, `lang`).
- `three/`: three.js 0.164.1, only the files the bundler inlines (MIT, `three/LICENSE`).
- `audit/`: exact geometry audits of a guide (`guide_geom.py`, `path_audit.py`, `pair_audit.py`); needs `requirements-audit.txt`.
- `scripts/sync_guide_kit.py`: copies a pinned kit commit into another repository and checks that copy.

## Authoring rules every guide follows

- **Fasteners use the `screws[]` contract**, never anonymous part meshes: each screw has `step`, `spec` (for example `M5 x 12`), `center`, `axis`, and optionally `kind`, `lengthMm`, `nut`, `washer`, `throughPart`, `intoPart`, `where`. The viewer numbers them per step, colours them by spec and lists them in the step panel; the parts page counts them per chapter.
- **Per-step part lists**: `add` holds only what this step installs, `show` what is already on the build and must be seen, `context` only the ghosts that orient the builder. A step that shows every component is wrong.
- **Chinese guides** set `"lang": "zh"` and write all content in Chinese (rule `assembly-guides-chinese-foolproof.md`).
- **Release gate**: `path_audit.py` and `pair_audit.py` both exit 0 on the built page. Box checks do not count.

## Audits

```bash
python3 audit/path_audit.py --guide page.html --adapter adapter.json --out path-audit.json
python3 audit/pair_audit.py --guide page.html --adapter adapter.json --out pair-audit.json
```

`--guide` takes `guide-data.json` or the built page (the audit then reads exactly the data and meshes the page carries). The path audit plays every step as `viewer/app.js` does (staggered timeline windows, easing, waypoint paths, `group`, `pose` swings, `flex` spread and riders) and intersects each moving part exactly (manifold3d) with every other part drawn in the step, other moving parts at their own place on the timeline. A collision is new overlap above 0.5 mm³ beyond the seated overlap of that pair with median thickness above 0.1 mm. The pair audit intersects every touching pair at the final pose. Both exit 1 on any finding, and on any part whose mesh is not a closed volume (listed under `unaudited`; give the adapter a solid for it).

The adapter is the only project-specific input (all keys optional):

```json
{"solids": {"camera": "/abs/camera-solid.stl"},
 "flexible": ["wire_*", "zip_tie_*"],
 "designedContacts": [{"a": "sleeve_*", "b": "post_*", "why": "press fit, 0.2 mm interference"}],
 "apart": [["rear_box_*", "backpack_*"]],
 "ignoreSteps": ["overview"],
 "stagger": "items"}
```

Heavy runs (MicroDuck: 1.5 M triangles) go to the Mac mini: `rsync` the kit and the page to `~/code/guide-kit-mirror/`, run with `~/.venvs/guide-kit/bin/python`, `rsync` the reports back. MicroDuck's full 91-step path audit takes about 14 s there.

MicroDuck's own release gate (`microduck-sim/guide/content/interference-audit/run_gate.py`) keeps its project rules on top of this: installed-before and bench state, designed contacts in `pair_classes.py`, cables, lead-in reachability.

## Consuming the kit from another repository

Never edit a copy. In the consumer repository:

```bash
python3 ~/code/robotics/guide-kit/scripts/sync_guide_kit.py sync --dest vendor/guide-kit      # pinned to robotics HEAD; --ref <commit> for another
python3 vendor/guide-kit/check_guide_kit.py                                                  # in the build and CI; exit 1 on any drift
python3 vendor/guide-kit/build_guide.py --data build/guide-data.json --out dist/assembly/index.html
python3 vendor/guide-kit/audit/path_audit.py --guide dist/assembly/index.html --adapter guide-adapter.json
python3 vendor/guide-kit/audit/pair_audit.py --guide dist/assembly/index.html --adapter guide-adapter.json
```

`sync` writes the files exactly as committed (uncommitted kit edits never ship), `KIT-MANIFEST.json` with the commit and every file's sha256, and `check_guide_kit.py`. The check fails on an edited, missing or extra file; `--kit ~/code/robotics` also confirms the manifest against the kit's history and prints how many kit commits the pin is behind. A viewer change a consumer needs goes into the kit as an opt-in data field so other guides build unchanged, is committed here, and is synced.
