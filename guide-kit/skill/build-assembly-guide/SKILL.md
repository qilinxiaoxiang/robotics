---
name: build-assembly-guide
description: Build or change a robot or hardware assembly/build guide page (MicroDuck, Scout Mini, RIG or a new project) with the shared guide-kit viewer, fastener contract and exact path/pair audits. Use before writing guide data, exporting steps, changing the viewer or releasing a guide.
---
# Build an assembly guide

Every guide is built from one shared kit, `guide-kit`, whose source lives in the `qilinxiaoxiang/robotics` repository (`guide-kit/`). It holds the viewer, the bundler (`build_guide.py`) and the exact audits (`audit/`). Detail: the kit's `README.md`; data schema: `viewer/README.md`.

Where the kit is:
- **In the robotics repository:** `guide-kit/` itself. MicroDuck builds through `microduck-sim/guide/build_guide.py`.
- **In any other project (for example scout-mini-design-review):** a pinned, read-only copy in `vendor/guide-kit/` with `KIT-MANIFEST.json`. This skill file is shipped with that copy.

Never hand-edit a vendored copy; the project build fails on it.

## Shortest route

1. **Check the kit first.** In a consumer project run `python3 vendor/guide-kit/check_guide_kit.py`, and make the project build run it before anything else.
   - **Need a viewer, bundler or audit change?** Make it in `robotics/guide-kit` as an opt-in data field, so pages that do not use the field are byte-identical. Confirm that MicroDuck's built page hash is unchanged, commit, then refresh each consumer with `python3 <robotics>/guide-kit/scripts/sync_guide_kit.py sync --dest <project>/vendor/guide-kit`.
   - **No robotics checkout?** Open a pull request on `qilinxiaoxiang/robotics` with the kit change, and ask Shawn to resync.
2. **Write `guide-data.json` from the adopted CAD.**
   - **Fasteners** go in `screws[]` with `spec`, `center`, `axis`, `step` and `throughPart`/`intoPart`. They do not go in as loose part meshes.
   - **Each step lists** only what it installs (`add`), what must be seen (`show`) and a few orienting ghosts (`context`). The parts and prepare pages then count hardware by spec per chapter.
   - **One bought item is one part:** a nut with its spring ball is one mesh.
   - **Same slot, one at a time:** several nuts entering the same slot queue in order, so they never pass through each other.
3. **Write for the builder.** One action per instruction, in build order. Name each part by what it looks like and where it sits, with the screw size and count on the same line.
   - **Language:** guides for Shawn's own builds use `"lang": "zh"`. Shared project guides stay in English.
   - **Design out manual work:** anything a builder would have to cut, drill, file or measure on a printed part is removed in CAD. The part is reprinted rather than explained.
4. **Gate the release on the built page.**
   - **Run both audits:** `audit/path_audit.py` and `audit/pair_audit.py`, with the project's adapter. The adapter lists closed solids, flexible globs, and designed contacts with their reasons.
   - **Both must exit 0:** zero pass-throughs, zero unclassified final-pose overlaps, zero `unaudited` parts.
   - **Box or AABB checks do not count.**
   - **Fix every hit** in the approach, the order or the geometry. Never widen the adapter without a stated physical reason.
   - **MicroDuck** also runs its own `run_gate.py` (robotics `AGENTS.md`).
5. **Check the exact delivered page.** Open it in headless Chrome at desktop width and at 390 px.
   - No horizontal overflow.
   - The step panel lists the screws by spec.
   - The densest step is readable.
   - Light background, and inputs at 16 px or more on mobile.

## Boundaries

- **The audit plays the kit viewer's timeline.** A page built by an edited viewer is not a kit page, and its audit result says nothing about the kit.
- **Heavy audits:** on Shawn's machines, audits that run longer than about a minute or use a few hundred MB run on the Mac mini, at `~/code/guide-kit-mirror` with `~/.venvs/guide-kit`.
- **Review:** insertion order, tool access and cable-before-closure are reviewed with the `assembly-guide-review` skill where it is installed.
