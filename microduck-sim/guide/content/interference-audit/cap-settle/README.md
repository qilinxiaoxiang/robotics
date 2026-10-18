# MicroDuck head cap settle (P5/P6)

> Superseded 2026-10-12. The cap this study calls "V1.8" (IDC socket seat, Pi 3.3 mm back and 2.0 mm up, `candidates/head-cap-idc-seat/`) was not adopted: Shawn kept the 14 mm jumper housings and the released V1.8 head set is a different design (face plate with direct camera screws, windowless lower shell, cap with the Pi rails 1 mm higher; see `../README.md` "Current state" and `guide/print/world/v18-sources.json`). The numbers below remain valid for the idc-seat candidate only.

Date: 2026-10-10. Frame: robot frame in mm, x forward, y left, z up. Cap-on is the populated cap lowered straight down by [0, 0, 40]. Criterion: at least 2 mm for rigid items and at least 1 mm for wires, along the whole descent and in the final pose. Every deciding number below is an exact triangle-mesh distance (manifold3d `min_gap`) against an exact convex sweep, unless it is marked as sampled or static.

## Recommendation

Do not print V1.7, and do not use single female jumper sleeves on any cap. Print the candidate cap once:

- Print file: `/Users/xiangzheng/code/robotics/microduck-sim/guide/print/candidates/head-cap-idc-seat/head_cap-idc-seat-print.stl` (sha256 73290fe9...), with the moved Bambu support blocker `/Users/xiangzheng/code/robotics/microduck-sim/guide/print/candidates/head-cap-idc-seat/pi-positive-y-upper-hole-support-blocker-idc-seat.stl` (sha256 5a97cab0...). World and STL-frame copies sit in the same folder (`head_cap-idc-seat-world.stl` f7eb675f..., `head_cap-idc-seat-stlframe.stl` 252ffe66...).
- Connect the Pi with one 2x20 IDC ribbon socket whose installed height, ribbon included, is at most 11.0 mm above the header plastic. The ribbon must leave the socket on the pin-1 row side (the inner row, away from the PCB edge), lie flat and turn up the board. Splice the robot wires to the ribbon conductors the way the guide already splices jumper halves (twist, solder, heat shrink); nothing is soldered to the Pi.
- The socket must be bought, which needs Shawn's approval. Preferred: 3M 89140-0101 (DigiKey MKC40A-ND, 10.5 mm REF tall) pressed onto a 40-way 1.27 mm 28 AWG flat cable in a bench vise, so Shawn controls the exit side. Alternative: Samtec IDSD-20-D-03.20-G cable assembly (DigiKey 612-IDSD-20-D-03.20-G-ND, 9.27 mm REF, pre-made, non-returnable; check on the Samtec drawing that the cable leaves sideways before ordering).

The candidate (called V1.8 below) is the printed V1.6 shell with the Pi seat moved 3.3 mm back and 2.0 mm up, the +y rail trimmed to x >= 54.5, and a stiffening web on that rail's neck. Its deciding margins with an 11.0 mm socket: socket to camera clamp screws 2.313 mm, socket to the head_bottom floor 2.564 mm, Pi solder tails to jaw_support 2.394 mm, +y rail to jaw_support 2.2 mm, ribbon exit band 2.344 mm. With a 10.6 mm socket the front margin is 2.707 mm and the floor 2.63 mm.

## Why nothing smaller works

- **Single sleeves fail at every seat position.** The front limit (pins 5 and 35 against camera clamp screws 3 and 1) grows about 1 mm per mm the Pi moves back: 0.513 mm at L = 14.25 with the V1.7 seat (dx 4.6), so 2 mm needs dx of about 6.1. The rear limit (Pi solder tails against jaw_support) is 5.694 - dx, so 2 mm needs dx <= 3.69. No dx satisfies both. Sources: `jumper-final.json`, `idc-study-a.json`, `idc-study-b.json`.
- **The edge row sits on the floor.** At dz 0 the edge-row pins 2 to 14 clear head_bottom by only 0.63 mm, whatever the connector sits on them. Clearing 2 mm needs the Pi raised at least 1.4 mm (floor gap 0.632 + dz for an IDC socket at H 10.6). Source: `jumper-final.json`, `idc-study-a.json`.
- **Quick prints do not help.** With the camera retainer and its three clamp screws removed from the V1.7 model, the edge row is still limited to L <= 5.70 for 2 mm (floor), and the best nominal-wire 1 mm limit at pin 14 is 12.2 mm, below every real sleeve. Source: `sleeve-sweep-dx4.6-no-retainer-screws.json`.
- **Assembly order cannot help.** The cap only goes on straight down: 0 of 68 approach directions are clean (`../approach-search.json`, step cap-on), and every tilted swing hits face_panel (50.45 to 76.27 mm3) and jaw_support (36.25 to 41.53 mm3) (`../cap-swing.json`). The sleeves ride on the Pi inside the cap, so they must be on before cap-on. For V1.7 no straight or offset path keeps sleeves 2 mm clear or wires 1 mm clear (`path-check-dx4.6-L14.0.json`); for V1.6 even touching sleeves have no path (`path-check-dx0.0-L14.0.json`).
- **Shorter or right-angle crimp housings do not help.** 2x20 crimp housings use the same 2.54 mm terminals as single sleeves (13.85 to 14.2 mm), and the edge row is floor-limited regardless of length. Right-angle parts grow toward the floor or the screws.
- **The amplifier pins do not change any verdict.** The worst jumper pins are 2 (floor) and 5 (front), neither of which drives the amplifier, so results with and without pins 4, 12, 14, 35 and 40 are identical. An IDC socket covers all 40 pins with one body and a full-width ribbon, so the pin set does not matter there either.

## Per-option margins

Pins are physical Pi numbers (see the row finding below). Realistic single-sleeve length L is 13.85 to 14.25 mm; 15.24 mm is the long outlier.

**V1.6 printed cap, single sleeves (dx 0).** Fails. At L = 13.85 to 15.24 all used pins except 40 collide (`jumper-final.json`). At L = 14.0 the sleeves are too long by 1.20 mm (pin 2), 1.65 (1), 1.93 (4), 2.38 (3), 2.84 (10, 12), 3.20 (14), 3.30 (9), 3.45 (6, 8) and 3.91 mm (5, 35); add 0.25 mm at L = 14.25 (`sleeve-sweep-dx0.json`). Pin 40 clears by only 0.61 mm. The largest touch-free length is 10.09 mm (pins 5, 35). The edge row cannot meet 2 mm at any length above 5.94 mm. Every wire model collides.

**V1.7 released cap, single sleeves (dx 4.6).** Does not collide at L <= 14.25 (smallest gap 0.513 mm, pins 5 and 35, camera clamp screws 3 and 1) but fails 2 mm at 12 of 13 pins. Worst gaps: 0.654 mm at L = 13.85 (pin 2, floor), 0.63 at 14.0, 0.513 at 14.25, contact at 15.24. Only pin 1 passes (3.088 at 13.85, 2.732 at 14.25). Wires: with the best bend direction, pins 5, 6, 8, 9, 35 and others hit at both 13.85 and 14.25 for all three wire models. V1.7 also fails 2 mm at the rear on its own: Pi solder tails 1.094 mm (`idc-study-a.json`) and the +y rail 0.5 mm (`descent-rails.json`) from jaw_support.

**V1.8 candidate, single sleeves.** Fails (pins 5 and 35 touch the clamp screws already at L = 13.85). The candidate is for an IDC socket only.

**V1.6 or V1.7 with an IDC socket.** Fails. V1.6 (dx 0): the front gap at H 10.6 is -0.593 mm (collision); a 9.27 mm Samtec body clears by 0.72 mm but its ribbon exit collides. V1.7: the floor gap is 0.632 mm. Source: `idc-study-a.json`, `idc-fold.json`.

**V1.8 candidate with an IDC socket (recommended).** Swept socket body against fixed parts, by height H (`verify-v18-dx3.3-dz2.0.json`, `idc-study-chosen.json`):

- H 9.27 (Samtec): head_bottom 2.849, clamp screws 4.017.
- H 10.6 (3M about 10.5): head_bottom 2.63, clamp screws 2.707, camera_retainer 3.047.
- H 11.0: clamp screws 2.313, head_bottom 2.564.
- H 11.79 (TE 1658622-9): clamp screws 1.535, fails.
- Largest height meeting 2 mm: 11.312 mm; largest touch-free height 13.346 mm.
- Ribbon exit band, full 50.8 mm ribbon width, leaving the pin-1 side 5.5 to 8.5 mm above the mating face and running 14 mm up the board: 2.344 mm (clamp screws 2 and 3; flexible criterion 1 mm) (`idc-study-chosen-fullribbon.json`). If the ribbon instead leaves the edge side and is folded back over the socket, its rising band comes within 0.601 mm of clamp screw 2 at H 9.27 and touches the camera board at H 10.6 (`idc-fold.json`), so the exit side matters.

## V1.8 candidate verification

All numbers are for the published candidate (world sha256 f7eb675f...).

- **Descent of the moved Pi group** (exact convex sweeps): solder tails 2.394 mm to jaw_support, header base 4.004 to head_bottom, PCB 4.207, Pi screw heads 5.665.
- **Descent of the changed cap material** (rails and web, sampled every 0.25 mm, true minimum at most 0.125 mm lower): +y rail 2.2 mm to jaw_support, 3.9 to motor15; -y rail 5.117 to head_bottom; no excess overlap (`descent-rails.json`). The minimum is in the seated pose. `verify-v18` also lists 1.001 mm to face_panel for the added material; that comes from 188 zero-volume slivers on the unchanged shell (re-exported vertices differ in the last digits), total volume 0.000000 mm3 (`probe-added.json`, `descent-rails.json`).
- **Cap shell.** Unchanged from the printed V1.6: the only seated overlap is its bottom rim in head_bottom's seat (63.026 mm3, identical for V1.6 and V1.8, `shell-overlap.json`); outside the edit boxes the XOR volume is 3.6e-13 mm3; the camera notch region is identical; the print pose keeps the same 104.39 mm2 bed contact and bounds.
- **Static stack-ups** (parts that ride together, no relative motion): socket to the E-pi-01/02 screw heads 1.09 mm and to the CSI connector conservative hull 1.378 mm (`verify-v18`). Pi components to the cap at least 1.602 mm, solder tails 0.4 mm and header base 1.6 mm to the rail bosses; these Pi-to-cap spacings are identical in V1.6, V1.7 and V1.8 (`static-pi.json`).
- **Screw seats** (`verify-v18`, C section): E-pi-01, 03 and 04 keep 4.4 mm of rail along the axis, so M2 x 6 engages fully. E-pi-02 keeps 2.5 to 2.82 mm, so it stays M2 x 4 as the guide already says (2.46 mm engagement, tip inside the rail, 3.928 mm to motor15). An M2 x 6 there would stand about 2 mm out of the trimmed rail back and pass the jaw_support face at less than 0.5 mm during cap-on.
- **+y rail neck.** The trim leaves the column above the E-pi-02 boss only 0.88 mm thick, and the boss hangs from that column while its screw is driven. The candidate fills the empty space between the column and the PCB back with a web (y 27.4 to 30.6, z 121.5 to 136, front face 0.8 mm behind the PCB back plane, 57 mm3, taper overhang 8.5 degrees). Thinnest section: V1.6 2.03 x 3.2 mm (section modulus 3.47 mm3 about the screw axis), V1.7 1.28 x 3.2 (2.19), V1.8 2.42 x 3.2 (4.13) (`rail-neck.json`, `measurements.json` plusYRailNeck). The web keeps x >= 54.5, so its descent clearance is the rail's 2.2 mm.
- **Cables** (0.5 mm voxel paths with exact readback, thresholds 2.91 mm to cap and fixed parts, 1.25 mm to the Pi class; `routes-v18-dx3.3-dz2.0.json`): bundle_head 3.31 / 1.14 mm (V1.7 3.83 / 1.14), head_i2s 3.17 / 0.98 (V1.7 4.56 / 1.0), head_csi 4.88 / 2.27 (V1.7 4.88 / 2.3), all feasible at the voxel thresholds with a 10.6 mm socket. The exact Pi-class minima of bundle_head (1.14 mm) and head_i2s (0.98 mm) are where the wires pass over the top edge of the Pi board near the roof (z about 146.6), as in V1.7 (1.14 and 1.0 mm at z about 144.7); a wire resting on a board that rides in the same cap is a static contact, not a descent clearance. The 200 mm CSI ribbon spans 28.95 mm straight.
- **Moved rails stay inside the cap:** added material outside the V1.6 cap hull and outside the community shell hull is 0.0 mm3; the rails are clipped 0.1 mm under the outer roof as in V1.6 (52.6 and 52.4 mm3 removed above the roof line).
- **Other side effects:** microSD side gap along +y at least 6.92 mm; roof gap above the Pi USB edge 3.89 mm (no USB plug is used inside the head).

## Connector data

Single sleeves (all fail): Amphenol Mini-PV 65039-036LF 13.85 +-0.13 mm; Harwin M20-1060100 14.00 +-0.20; Pololu 1900 / generic Dupont 14.00 +-0.25; TE Mod IV 14.2; Molex SL, C-Grid III and TE MTE 15.24. Wire OD 0.89 to 1.30 mm (Alpha Wire 422807, 3048, 3049). All three wire bend models used here are tighter than the NASA workmanship minimums, so the jumper wire results are optimistic.

IDC 2x20 sockets: 3M 89140-0101 (DigiKey MKC40A-ND) 10.5 mm REF, body 6.05 mm plus a 1.5 mm centre bump on the pin-1 side, needs at least 5.84 mm of post. Samtec IDSD-20-D-03.20-G (DigiKey 612-IDSD-20-D-03.20-G-ND) 9.27 mm REF, 5.08 mm wide, insertion depth 5.59 to 6.22 mm, non-returnable. Excluded: TE AMP-LATCH Novo 1658622-9 (11.79 mm), Wurth WR-BHD 61204023021 (strain relief, about 16 mm), Amphenol FCI 71600-040LF (the code was read as including a strain relief; 35-week lead time). Adafruit 1988 and generic FC-40 cables only after a caliper check. URLs are in `measurements.json` connectorData (accessed 2026-10-10).

## Physical checks for Shawn

1. Approve one purchase (3M 89140-0101 plus 40-way 1.27 mm 28 AWG flat cable, or the Samtec IDSD assembly). Nothing has been ordered.
2. With calipers, measure the installed socket from its mating face to the highest point of the cover and ribbon: at most 11.0 mm, ideally at most 10.6 mm. Fit no strain-relief clip.
3. The ribbon leaves on the pin-1 row side, which on the Pi is the inner row (away from the board edge), and turns up the board. Pin 1 is the inner-row pin at the microSD (+y) end; the red stripe goes there.
4. Measure the Pi header pins above the black plastic: 5.84 to 6.2 mm (CAD 5.96). Press the socket fully home so it sits flat on the plastic.
5. After printing, check that the +y rail web printed solid, then drive M2 x 4 into the lower +y corner (E-pi-02) first and M2 x 6 into the other three, as the guide already says.
6. Before closing the head, lower the cap by hand once and watch the socket pass the three camera clamp screws.

## Findings outside the brief

- **Row numbering.** In the CAD and in guide-data's per-pin envelopes, pin 1 sits 2.23 mm from the PCB edge and pin 2 4.77 mm, so the odd row is on the edge. A real Pi has the even row on the edge. `guide/content/steps.py` (step gpio) already describes the real layout. All per-pin results here use the real rows (`inspect-geometry.json`).
- **V1.7 rear clearances** fail 2 mm independently of connectors: solder tails 1.094 mm and the +y rail 0.5 mm to jaw_support.
- **If V1.8 is adopted,** the guide sources need a follow-up outside this folder: fasteners.json Pi seats (shift [+1.3, 0, +2.0] from V1.7), the gpio and cap steps for the IDC socket, the print manifest, and the per-pin envelopes.

## Limits

- Socket heights are REF values from drawings; the exit band height (5.5 to 8.5 mm above the mating face) is inferred from the drawings, and the ribbon beyond its first 14 mm and the splices are not modelled.
- The Pi header pin length is the CAD 5.96 mm; the socket is assumed to seat on the header plastic.
- Cable routes are voxel paths (0.5 mm) with an exact distance readback; real wires and the ribbon are flexible and can sit anywhere in their corridor.
- The neck comparison is a section comparison, not a load test. The candidate print has not been sliced on the printer here; the moved support blocker and the unchanged print pose follow the V1.6 release.
- The rail descent minimum is sampled (0.25 mm steps, at most 0.125 mm lower); all other descent numbers are exact sweeps.
- Fixed-part geometry is the guide source export at its current revision (`measurements.json` sources, with sha256).

## Files and reproduction

Results: `measurements.json` (collects everything with source hashes and run records), plus the per-job JSON files in this folder. Scripts: `scripts/` (shared helpers in `cs_lib.py`). Every geometry job ran through the bounded runner; run records are in `runs/`.

```
cd /Users/xiangzheng/code/robotics/microduck-sim/guide/content/interference-audit/cap-settle
R="python3 /Users/xiangzheng/code/robotics/microduck-sim/build-pack-20260913/redesign-20260913/head-redesign-20261008/run_bounded_cad.py --max-mib 1536 --wait-lock-seconds 60 --seconds 900"
PY=/tmp/microduck-cad-venv/bin/python
OUTDIR=/Users/xiangzheng/code/robotics/microduck-sim/guide/print/candidates/head-cap-idc-seat
C=$OUTDIR/head_cap-idc-seat-world.stl
DX=3.3 DZ=2.0 X_TRIM=54.5 NECK_WEB=1 NECK_CLEAR=0.8 $R --report runs/run-build18web.json -- $PY scripts/build_v18.py $OUTDIR
DX=3.3 DZ=2.0 X_TRIM=54.5 HS=9.27,10.6,11.0,11.79 $R --report runs/run-verify18.json -- $PY scripts/verify_v18.py $C
DX=3.3 DZ=2.0 CAND=$C $R --report runs/run-route18.json -- $PY scripts/route_v18.py
$R --report runs/run-descentrails.json -- $PY scripts/descent_rails.py $C
DX=3.3 DZ=2.0 $R --report runs/run-staticpi.json -- $PY scripts/static_pi.py $C
$R --report runs/run-railneck.json -- $PY scripts/rail_neck.py $C
VERSIONS=V1.6:0:0,V1.7:4.6:0,V1.8:3.3:2.0 $R --report runs/run-jumpfin.json -- $PY scripts/jumper_final.py
CASES=3.3:2.0 HS=9.27,10.6,11.0 TAG=-chosen-fullribbon EXIT_FULL=1 $R --report runs/run-idcfull.json -- $PY scripts/idc_study.py
python3 scripts/make_measurements.py
```
