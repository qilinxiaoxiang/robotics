# MicroDuck V1.6 guide interference audit

Guide revision `guide-20261009` (`guide/data/guide-data.json`). Findings are in `findings.json`; this file gives the method, thresholds, coverage and the main issues.

**Current state (2026-10-10, V1.7 parts).** `steps_audit.py` on the current guide: 63 steps, 0 premature parts, 0 path collisions. Two reprints are adopted: the notched `openrb_tray` (issue 1) and the `head_cap` with the Pi seat 4.6 mm back (issue 3, `verify-cap/README.md`). The jaw is the original one-piece part, fitted from below with its arms sprung apart (issue 2). The sections below record the first audit of the V1.6 guide.

## Result

Three real design interferences need printed-part changes; everything else is guide data, intended contact or a display artifact.

- **Class a, real design interference (3 issues, 4 findings):** the OpenRB tray rails block both side servo ports (reprint `openrb_tray`); the one-piece jaw cannot be assembled with the lower head shell (reprint 4 parts from the existing `jaw-access` candidate); the plugged 2x20 GPIO housing cannot pass the camera stack when the cap is lowered (reprint `head_cap`).
- **Class b, guide data error (29 findings):** 14 cable segments (13 drawn, 1 raw polyline only) and 15 step problems (approach vectors, step order, parts drawn before they are installed, a part never installed).
- **Class c, intended contact (36 findings):** 22 part pairs (cap seam, mated connectors, knee press fits, screws in pilot holes, header pins in their contacts) and 14 cable ends inside their terminals, junction or fuse.
- **Class d, display-mesh artifact (4 findings):** motor12 and motor14 viewer meshes are decimated 2.59 mm away from their solids.

By section: pairs 26 (c 22, d 4), cables 30 (a 2, b 14, c 14), steps 17 (a 2, b 15). Every geometric class b fix was re-checked with the same sweep or cable test that found the problem. The two bench-context fixes (`context=[]`) need only a re-run of `steps_audit.py` after the edit.

### Current state (2026-10-12, V1.8 head)

The guide now shows the V1.8 head set from `guide/print/world/` (face plate with four camera lands, two pegs and two Ø2.2 screw holes; eye trim with two Ø1.7 pilots; lower shell with the beak-roof window filled; cap with the Pi rails 1 mm higher and the two rear OpenRB bosses removed) and the camera turned 180° so its ribbon connector faces −y. The camera is held by two M2 × 8 TAP screws from behind the board into the trim pilots (`C-camera-01/02`, engagement 4.18 mm after the 0.3 mm lead-in, 1.12 mm tip margin, no intrusion; the clamp ring and its three screws are gone). `register_v18.py` confirms each guide display mesh equals its print/world file (7/7, ICP 0 mm for the five printed parts, 0.057 mm for the trimmed OpenRB board); `register_v16.py` lists those five parts as superseded and the other 8 as the released V1.6 geometry. Re-run on this state: 154/154 closed solids (build_solids 97.9 s, peak RSS 1533 MiB); pairs 564 candidates, 59 touching, 17 deeper than 0.1 mm, all intended contacts (13 header pins in their jumper ends, the cap seam at 0.199 mm, the two knee press fits, the IMU header); cables 20 checked, 30 findings of which 28 are ends inside their terminals and 2 are the known `vout` fuse-holder ends, no mid-route penetration (the bundle tail was raised 1.25 mm over the Pi top edge for the higher Pi: pi-trunk 0.51 mm, imu 0.61 mm, uart 0.71 mm clear; the new `head_csi` route keeps 0.55 mm to the cap and 0.60 mm to the Pi CSI connector hull); steps 63 swept, 0 path collisions, 0 parts drawn before they are installed. Head numbers are collected in `v18-audit.json`; `findings.json` and `whatif.py` still describe the first audit.

### Current state (2026-10-12, V1.8 rear pack; guide revision `guide-20261012`)

The torso now shows the printed rear electronics pack and its cover from `guide/print/world/` in place of the power support, regulator insert, OpenRB tray, fuse bank, IMU clamp and IMU rear cover (`register_v16.py`: 5 parts same as V1.6, 4 superseded by the V1.8 head, 4 retired; `register_v18.py`: guide meshes equal the world files for the pack, cover, upright board and turned IMU parts). The OpenRB stands upright on four pads (B-openrb-01..04), the DFR1202 sits in the channel behind it, J in the channel's lower +Y pocket, the BNO085 on the plate front, and there is no fuse anywhere. Re-run on this state: 150/150 closed solids (build_solids 78.5 s, peak RSS 1463 MiB); pairs 549 candidates, 58 touching, 17 deeper than 0.1 mm, all intended contacts (13 header pins in their jumper ends at 0.64 mm, the IMU plug in its socket at 0.35 mm, the cap seam at 0.199 mm, the two knee press fits at 0.173 mm) and none between the pack, cover, board, converter, junction or IMU parts beyond the IMU plug; cables 20 checked, 24 findings, every one an end inside its terminal, junction, converter pad, XT30 or camera connector, zero mid-route penetration on the drawn spline or the raw polyline; steps 62 swept, 0 path collisions, 0 parts drawn before they are installed (pack in, board drop-in, converter, J, IMU and cover paths all clean). Torso routes in `routes.json` were rewritten for the pack and screened before the audit with the cable-to-cable and cable-to-solid check in the session scratchpad (`route_check.py`): leg links R and L loop from the centre ports into the open −Y bay under the converter, where their splices sit 7 mm from the plug, then climb the lane between the board and the converter at y 5–7 (risers from the converter forward: L x −34.6, R −32.2, ORB −30.2, PI −29.4, UART −28.4; bare-point clearance to the board at least 0.8 mm); the notch in the plate top carries two rows (upper z 37: R, UART, PI, L; lower z 34.3: N); the 20 V pair runs down the −Y side of the channel and the 5 V pair drops straight into the J pocket. Pack numbers, the classification of the pack seams and the walking-sweep clearances are collected in `rear-pack/pack-audit.json` (the incremental evidence named by the V1.8 release manifest); the bend-forward leg-reach study that moved J inboard is in `rear-pack/README.md`.

### Current state (2026-10-12, leg servo cables)

The guide now draws the eight in-leg kit cables (`dxl-5-4` ... `dxl-7-6`, routes from `guide/content/leg_routes.py`). The six thigh and ankle links reuse the 2026-10-09 neutral leg routes unchanged; against the current solids they keep at least 0.002 mm (spline) and show no finding. The 2026-10-09 hip links coiled in the old power support's rear pocket and ran 1.9 mm into `rear_pack`; both were rerouted through the torso base's central 12 × 6 mm slot (A* on the current closed solids at 1 mm voxels with 2 mm clearance, the R/L controller plugs blocked as boxes, then hand-set control points). `cable_check.py dxl-5-4 dxl-10-9`: no finding; smallest clearances torso_base 0.46 / 0.62 mm, imu_board 0.50 / 0.71 mm, rear_pack 1.07 mm. Leg cables keep at least 1 mm surface gap to every other drawn cable. Full re-run: `cables.py` 22 cables, 10 findings, all terminal ends identical to the previous run, zero mid-route; `steps_audit.py` 64 steps, 0 premature, 0 path collisions. `pack_audit.py` and `v18_summary.py` were not re-run: no pack, cover, board or head geometry changed, and the V1.8 release manifest binds the existing `pack-audit.json`. The hip cables' spare length (about 90 / 105 mm of the 180 mm cables) is an instruction to fold it flat on the outer half of each hip-yaw motor top (free 10 × 10 × 10 mm box under the shell, checked on the voxel grid); it is not drawn.

### Current state (2026-10-13, head order and lead-in check)

The old step 46 lowered the roll fork with ID14 onto ID13 after the lower head shell was on. That cannot be built: the shell's floor opening rings the neck, so the fork with ID14 has to drop into the shell from above before the head goes onto ID13. The 30 mm sweep did not see this because the fork was already inside the shell at the start of its path. The head chapter is now jaw bench, `neck-roll` (bench), `head-fork-in` (bench: fork with ID14 lowered into the shell), then `neck-yaw-case` (the shell with jaw and fork lowered over ID13 as one group, 4 × M2 × 10). `steps_audit.py` now also checks the lead-in of every approach (method 5). The guide also gained the four `P-passive_tab` screws (M2 × 6, step `hip-roll-refit`) found by `unscrewed-holes/`. Re-run: `steps_audit.py` 64 steps, 0 premature, 0 path collisions including lead-ins; `cables.py` 22 cables, 10 findings, all terminal ends, zero mid-route.

## Coverage

- **Parts:** 160 of 160 guide parts have a closed audit solid (147 used as they are; 13 Pi component boxes repaired by vertex weld, duplicate-face removal and hole fill). Every solid is accepted by manifold3d, so all overlap volumes are exact booleans.
- **Released V1.6 geometry:** all 13 V1.6 printed parts in the guide match the release files (volume, area and principal moments within 2.6e-4 relative; ICP point-to-surface residual at most 0.105 mm). See `v16-registration.json`.
- **Part pairs:** 612 candidate pairs whose boxes come within 0.2 mm, all intersected exactly. 115 overlap at all; 22 overlap deeper than 0.1 mm.
- **Cables:** 20 of 20 cables. Each is sampled at 0.25 mm or finer along the drawn spline (26,495 samples) and the raw route polyline (8,919 samples) against every solid near it.
- **Steps:** 50 of 50 steps resolved as the viewer resolves them. Every approach vector (41 samples per path) is swept against everything drawn in the step.

## Method

1. `build_solids.py`: builds one closed solid per guide key in the robot frame. It uses the V1.6 robot-frame release file when its bounds match within 0.05 mm, the `print/world` STL for the tray, board and cap, and the full-resolution full-build source mesh otherwise. Guide primitives (junction J, main fuse, XT30) and the two shifted GPIO envelopes use the same geometry as `build_guide_data.py`. It also records how far each viewer mesh deviates from its solid (`solids-report.json`).
2. `register_v16.py`: proves the guide shows the released V1.6 geometry (rigid invariants plus ICP).
3. `pairs.py`: exact intersection of every candidate pair. Depth is the area-weighted median local thickness of the overlap (rays cast inward from the overlap surface), so a thin seam reads as its thickness, not its length. `pairs_display.py` repeats this on the viewer meshes to find display-only overlaps.
4. `cables.py`: rebuilds the viewer tube (centripetal Catmull-Rom, radius from the cable or 0.9 mm). Penetration depth at a sample is tube radius plus signed distance into the solid. A run of samples deeper than 0.1 mm is one finding. `cable_fix.py` pushes the movable route points out to radius + 0.5 mm clearance and re-verifies the whole cable with the same test.
5. `steps_audit.py`: resolves each step and reconstructs the physical state (legs start installed; non-bench steps install their adds; consecutive bench steps of one chapter accumulate a bench subassembly). It sweeps every approach as the viewer plays it: waypoint paths, group paths, held and swinging `pose` rotations, and `flex` deformation (manifold `warp_batch` with the viewer's ramp and spread). The lead-in check extends each approach's first leg backwards in 1.5 mm steps, up to 600 mm, until the moving parts' box clears every other part's box; any position along that line that overlaps a present part more than it does when seated (above 0.5 mm³ and 0.1 mm thick) is a `lead-in` path collision, so a part that starts its drawn path already trapped inside another is caught. `approach_search.py` screens 68 straight vectors per colliding approach against the parts that are really present. `whatif.py` checks multi-leg paths, group moves, changed step order and the jaw opened about its ring axis.
6. `tray_port.py`: the OpenRB side ports against the tray rails, and the proposed notch. `pi_shift.py`: the head_cap Pi-seat change (moved Pi group, moved and trimmed rails, descent of the modified populated cap). `cap_swing.py`: the cap lowered tilted and swung closed about a front axis.
7. `cable_verify.py`: re-checks hand-set route waypoints with the `cables.py` test. `render.py`: section drawings in `png/`. `build_findings.py`: assembles `findings.json` from the measured JSON.

**Thresholds:** part overlap depth > 0.1 mm; cable penetration > 0.1 mm; path collision = excess over the final-pose overlap > 0.5 mm3 with local thickness > 0.1 mm.

**Classes:** a = real design interference, b = guide data error, c = intended contact, d = display-mesh artifact.

## Main issues

**1. OpenRB tray rails block the side ports (class a, reprint `openrb_tray`).** Each side rail's inner face is 0.6 mm outside the header mouth and covers 6.3 of its 10 mm width, so links R and L cannot be plugged (cable segment 0 enters the rail 2.06 / 2.10 mm). Fix: cut each rail at x -66.2..-58.0, |y| 13.0..15.7, from z -49.4 up. On the notched tray the plug envelope overlap is 0 and both cables clear by 1.8 mm. Figure `png/01`.

**2. Jaw and lower shell cannot be assembled (class a; resolved without a reprint).** Current resolution: the original one-piece jaw is kept. The jaw/shell overlap is the same on the upstream original shell (`jaw-vs-shells.json` in the session study), so it is the original design's flex fit, not a V1.6 defect. The guide builds the jaw on the bench: lower shell first, then the jaw from below with the −Y arm sprung about 5 mm and the +Y arm about 2 mm past the sliding ring and the support boss (`jaw-bench` step, `flex`). The audit sweeps the deformed jaw with manifold `warp_batch` and finds no collision. The flex itself is a physical check on the first build. First audit: Raised from below, the shell passes through the closed jaw (lower_pad 3,447 mm3, jaw_frame 2,946 mm3). No straight direction (0 of 68) works. The jaw opened 30 deg also fails. The shell alone goes on cleanly before the jaw, but the jaw cannot follow it: not as a group, not the moving jaw alone, and not swung in. This matches the design's own negative control. The split-jaw candidate `head-redesign-20261008/jaw-access/` was considered and withdrawn. Figure `png/04`.

**3. Cap cannot close over the plugged GPIO housing (class a, reprint `head_cap`).** The housing front (x 78.97) sits under the camera stack (screws from x 74.88), and the cap can only come straight down: jaw_support is 3.2 mm and motor15 4.9 mm behind the Pi rail, and the face blocks the front. Fix: move the Pi rails and posts 4.6 mm back and trim their rear face to x >= 52.8. The descent is then clean, with no new final-pose overlap (`pi-shift.json`). Adopted as V1.7 (`verify-cap/`): `build_guide_data.py` moves the Pi group and housing envelopes by `PI_SHIFT` [-4.6, 0, 0] and records `shiftMm` per part; `build_solids.py` applies the same shift and prefers the `print/world` cap, tray and board over same-size V1.6 release files; E-pi-01..04 moved, E-pi-02 is M2 x 4; `bundle_head` takes the over-the-top-edge route from `verify-cap/measurements.json`; the cap-on step now has no collision. Figure `png/05`.

**4. Cable routes cut through parts (class b, `routes.json`).** 13 drawn segments pass 0.18-3.69 mm into the power support, junction J, main fuse, OpenRB board, head yaw link, motor14, amplifier and Pi. All 8 affected cables have waypoint moves in `cable-fix.json` (7 from `cable_fix.py`, orb-pwr hand-set under the board ledge). Re-checked with the `cables.py` test, no drawn segment penetrates a part by more than 0.1 mm. The optimiser aims for radius + 0.5 mm clearance; `converged: false` means it did not reach that margin everywhere. Figures `png/02`, `png/03`.

**5. Approach vectors and step order (class b, `steps.py`).** Main fixes:
- torso-base: fit the rings and base with ID5 and ID10 off, then refit the motors.
- converter: slide the insert and converter in as one group from the rear [-40, 0, 0], and install `xt30_robot`, which no step installs now.
- tray: use the two-leg path [[-30,0,4],[0,0,4],[0,0,0]].
- close: open the jaw 30 deg before the upper pad goes in from below.
- Shorter or reversed vectors for board, IMU plug, jaw group, face, camera, speaker cage, amplifier and Pi.
- Bench context: pd-tether and servo-ids need `context=[]`.

**6. Display decimation (class d, `build_guide_data.py`).** motor12 and motor14 show up to 0.78 mm overlap with neighbours that their source solids do not have. Fix: rebuild these two from the shared XL330 mesh. Figure `png/06`.

## Files

- `findings.json`: pairs, cables and steps, each with class, explanation and fix.
- Raw measurements: `pairs-raw.json`, `pairs-display.json`, `cables-raw.json`, `cable-fix.json`, `steps-raw.json`, `approach-search.json`, `whatif.json`, `tray-port.json`, `pi-shift.json`, `cap-swing.json`, `solids-report.json`, `v16-registration.json`.
- V1.8 head: `v18-registration.json` (guide meshes against `guide/print/world/`), `camera-screws-v18.json` (ray-cast evidence for the camera and Pi screws, also written into `fasteners.json`), `v18-audit.json` (every pairs, cables and steps finding that involves a head part, with the intended-contact classification).
- V1.8 rear pack: `rear-pack/pack-audit.json` (every pairs, cables and steps finding that involves the pack, cover, board, converter, XT30 or IMU parts, with the intended-contact classification, the display-mesh registration and the walking-sweep clearances from `guide/print/rear-pack/checks.json`), `rear-pack/reach-pitch.json` and `reach-pitch.png` (bend-forward leg reach, see `rear-pack/README.md`).
- `png/01-tray-rail-blocks-side-ports.png` to `png/07-torso-base-sandwich.png`.

## Re-running

Every geometry job runs under the bounded runner, one at a time, with the solid cache in the session scratchpad (`IA_CACHE` overrides it):

```
R=microduck-sim/build-pack-20260913/redesign-20260913/head-redesign-20261008/run_bounded_cad.py
/tmp/microduck-cad-venv/bin/python $R --max-mib 1536 --seconds 900 --wait-lock-seconds 60 --report run.json -- \
  /tmp/microduck-cad-venv/bin/python build_solids.py
```

Order: `build_solids.py`, `register_v16.py`, `pairs.py`, `pairs_display.py`, `cables.py`, `steps_audit.py`, `approach_search.py --only <i> --dirs 64`, `whatif.py [scenario ...]`, `tray_port.py`, `pi_shift.py -4.6 -4.6:52.6 -4.6:53.6`, `cap_swing.py 85,152,10 80,150,10`, `cable_fix.py <cable>` (orb-pwr: `cable_verify.py orb-pwr openrbpwr:3=-35,-4,-39.15 openrbpwr:4=-25,-4,-39.15 openrbpwr:5=-18.5,-1.5,-38.9`), `render.py`, then `build_findings.py` (no geometry). Peak RSS was 1500 MiB for `build_solids.py` (it parses the 72 MB full-build JSON) and below 1000 MiB for every other job.

For the V1.8 head state the order is `build_solids.py` (reads `guide/print/world/` for the keys in `ia_lib.WORLD_FILE`), `camera_screws_v18.py`, `register_v18.py`, `register_v16.py`, `pairs.py`, `cables.py`, `steps_audit.py`, then `v18_summary.py` (no geometry). After a `routes.json` edit, rebuild `guide-data.json` and run `cable_check.py <cable id> ...` for the touched cables before the full `cables.py`. `build_solids.py` peaked at 1533 MiB on this state; nothing else may run beside it.

For the V1.8 rear-pack state the same chain applies (`build_solids.py` reads the pack, cover, upright board and IMU files named in `ia_lib.WORLD_FILE`; `register_v16.py` lists the retired keys), followed by `rear-pack/pack_audit.py` (no geometry; writes `rear-pack/pack-audit.json`). A torso route edit needs only `build_guide_data.py`, `cables.py`, `steps_audit.py`, `v18_summary.py` and `pack_audit.py` again (about 1.5 minutes); the release manifest records the sha256 of `pack-audit.json`, so the release is prepared only after that file is final.

## Inference and limits

- The plug-plus-wire envelope at the OpenRB side ports (10 mm beyond the board edge) is assumed from a JST EH plug and three wire bends; the rail position, the mouth position and the overlap with the cable centreline are measured.
- "The cap sits up to 0.2 mm high at the seam" and "the knee sleeve may grow into its running clearance" are inferences from the measured overlaps.
- The stiffness of the tray rail after the notch was not computed.
- The GPIO housing envelopes come from the design's receiving model (housing plus wire exit); their size is an assumption, not a measurement. The head_cap change was checked for rigid clearance only. The CSI ribbon, USB plug access, the Pi screw bosses in the trimmed rails and rail strength are unverified.
- The jaw flex fit is checked as the viewer draws it (a linear spread of the arms), not as a stress analysis. Whether the printed arms take a 5 mm spread without cracking is a physical check; the guide tells the builder to stop if they crack.
- The real 2x20 housing length is not measured; `verify-cap` used about 14 mm from product listings. A housing of 10.1 mm or less would have cleared the camera without the Pi shift.
- Path checks treat each moving set as rigid. Flexible parts (wires, zip ties) and snap-fit deflection are not modelled.
