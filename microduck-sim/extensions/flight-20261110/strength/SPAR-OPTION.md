# Carbon spar option for the wing root

Geometry: commit `1b392541` (the same STL hashes as `README.md`), cad/ unchanged. Hand calculations: `spar_calcs.py`. Corridor scan: `spar_clearance.py`. Numbers are in `results.json → spar_option`.

## Conclusion

The spar can carry the loads, but on its own it does not fix the root.

**The spar:** two roll-wrapped 12 × 10 mm carbon tubes.
- One tube runs at x −106, z 27 and the other at x −106, z 63 (guide frame), |y| ≤ 145.
- Each is a 500 mm stock tube cut to 290 mm. A 250 mm tube is too short: it would end at y 125, before the outer saddle at y 135. No 290 to 300 mm stock was confirmed in this size.
- Each nacelle rides on two closed printed rings, at y 85 and y 135.
- Two rings at y ±20 tie the spars to the centre.
- Tube SF per case:
  - Peak thrust (×1.5): 2.8
  - 15.6 g landing: 2.1
  - Lift by one nacelle: 1.9
  - 10 g fore-aft: 17
  - 10 g sideways: 12
  - Topple strike, 131 N at the nacelle end: 2.3
- Mass: 28 g of tube, plus about 25 to 30 g of printed rings and centre tie.
- Cost: about USD 12 per 500 mm tube. That price comes from a listing for the nearest size (10 × 8 × 500 mm, Uxcell) and an eBay listing for 12 × 10. I did not confirm an Amazon listing for 12 × 10 × 500.

**Why the root still fails:**
- A straight spar fits in only one place: behind the battery backpack and the FC stack. Through the nacelles it would pass a fan, the trunk or the head sweep.
- From there, the load has to come forward to the centre plate. The backpack (|y| < 32, back to x −80, up to z 43), the backpack plugs, the protected saddle rear window and the FC stack (y < −35.5) block every path except the tops of the wing arms at |y| 25 to 33. That is the root band again.
- The spar removes the side bending in the band: fore-aft 10 g bending goes from SF 0.61 to 1.9, sideways 10 g from 0.88 to 1.4.
- It cannot remove the pitch moment, because the fans sit ahead of the duck. That moment is what breaks the band in normal use. Landing torsion stays at SF 0.9 in the hand model, the same as today; today's FEA puts it at about 0.55.
- So the spar only helps if the layout changes so a tie can reach the centre plate below the band. That needs the FC stack moved off the right side, and the backpack top and its plugs redesigned.

**The topple:** the spar itself survives it at SF 2.3. The four M2 post screws into the OpenRB pack still carry the same 290 N as today (SF 0.39). That load depends only on the strike and where the posts are, not on what sits between them. No spar makes the topple survivable. The duck has to be kept upright: in the sim, holding the fans at 40 to 50 % until the feet have settled does this.

## Where a straight spar fits

`spar_clearance.py` scans every line parallel to y, at 1 mm steps in x and z. For each line it finds the nearest point on:
- the as-built world parts, with the backpack shifted as in `cad/check_parts.py`;
- the pack's bought-part dummies (fans, batteries and leads, FC/ESC stack, harness, MTF-01, capacitor, A7Z link);
- the pose clouds of the legs and head (stand, 50 % random, pickup scan, full head yaw, 1046 logged bend poses).

The printed pack parts do not count as obstacles, because in this option they become saddles. Map: `out/spar_clearance.png` (local only).

- **Lines that clear everything by the tube radius + 1 mm, at nacelle height (z 20 to 65): only x ≤ −98.** That is behind the backpack (x −80) and the FC stack (x −102 at y < −35.5).
- **Above the nacelles (z ≥ 75):** x ≤ −80 is free. But a spar there would hang the nacelles from struts more than 30 mm tall.
- **Through the middle web between the fans (x ≈ −12):** blocked by the trunk and saddle.
- **Ahead of the chest (x 58):** blocked by the head in the pickup scan poses (distance 0).
- **The existing 4 mm root slot (x −48.45, z 29.6):** touches the backpack frame (0.1 mm) and runs into the rear fan at y 97. It cannot reach the nacelles.
- **Chosen lines, at x −106:** distance from the spar axis to the nearest obstacle (for a 12 mm tube, subtract 6 mm to get the gap):
  - FC stack: 13.4
  - Other dummies (harness, MTF-01, capacitor, A7Z link): 14.5 at z 27, 16.0 at z 63
  - Duck at rest: 25.8
  - Fans: 26 to 33
  - Head sweep: 28.5 at z 63, 39.1 at z 27
  - Legs: ≥ 36

## What the spar collides with, and what has to change

- **Nothing in the current layout touches the two lines.**
- **The nacelles end at x −88.3.** Each needs a rear hanger about 18 mm long carrying two closed rings around the spars. The present clamp screws stay as they are.
- **The centre tie has no clear path:**
  - The backpack sits flush on the centre plate at x −48.5, from z −44 to 43, across |y| < 32.
  - The backpack plugs sit on top of it, at z 43 to 48.5.
  - The saddle rear window is protected: x −59 to −44, z 47.8 to 58, |y| < 30.
  - The FC stack starts at y −35.5.
  - The tie can only land on the wing arm tops at |y| 25 to 33, which puts it back on the root band.
- **A rear fall:** the spar ends and rings, 18 mm behind the nacelles, become the first contact.

## Load cases and results

The six cases are the ones in `README.md`, with the nacelle loads of `hand_calcs.CASES` on each side. The trays stay on the wing plate. Carbon allowables are the low end of the Easy Composites CFP pultrusion TDS (rev. 2024-09-20): flexural 250 to 400 MPa, compressive 200 to 320 MPa, short-beam shear 30 to 40 MPa. Design values are bending 200 MPa (the compression face governs) and shear 30 MPa. Roll-wrapped tubes are stronger in torsion than pultrusions, so these values are conservative. The tube is a plain beam, so FEA would add nothing to the tube result: the uncertainty is the material data.

- **Two spars or one.** The fans sit 57 to 128 mm ahead of the spar line, so each nacelle puts 2.5 to 3.6 N·m of pitch torque on it.
  - A single round tube can only hold that by clamp friction, which needs 1700 to 2400 N of clamping. M2 screws in PLA cannot give that.
  - Two tubes spaced 36 mm in z carry the torque as a pair of opposite fore-aft forces.
  - A single 10 × 10 square box holds it by its shape, at SF 1.4 to 1.9.
  - So two round spars are needed.
- **Tube SF per candidate.** Spar mass is for 290 mm per tube; the numbers are thrust / landing / lift / fore-aft / sideways / topple.
  - 2 × 12 × 10 round (28 g): 2.76 / 2.11 / 1.94 / 17.3 / 11.8 / 2.34
  - 2 × 10 × 8 round (23 g): 1.82 / 1.39 / 1.28 / 11.4 / 7.8 / 1.54
  - 2 × 8 × 6 round (18 g): 1.08 / 0.83 / 0.76 / 6.8 / 4.6 / 0.92
  - 2 × 4 mm rod (10 g): 0.20 / 0.15 / 0.14 / 1.2 / 0.84 / 0.17
  - 1 × 10 × 10 × 8 square box (15 g): 1.94 / 1.49 / 1.36 / 10.4 / 9.8 / 1.67. Its torque goes into the PLA saddle corners.
  - 1 × 10 × 8 round (12 g): 1.39 / 1.06 / 0.97 / 6.1 / 5.8 / 0.99. It needs a friction clamp the screws cannot give.
- **What governs the tube.** Most of the bending comes from the pitch couple running along each spar to the centre rings at y ±20. Widening the rings to ±28 is the most the FC stack allows. That cuts the lever by about 10 % and raises the lift case of 12 × 10 to about 2.15.
- **Loads in the printed rings (2 × 12 × 10):**
  - Nacelle rings carry up to 52 N (lift).
  - Centre rings carry 71 N (thrust), 93 N (landing), 339 N (lift by one nacelle) and 284 N (topple).
  - Bearing is at most 2.8 MPa, SF ≥ 9 across layers.
  - If the load went into a two-part saddle with a cap, the two M2 cap screws would take up to 339 N, SF 0.71. That is why the saddles are closed rings, with the tube slid in from the end and one M2 pinch screw for axial location. A ring with a 3 mm wall then carries 339 N as hoop tension of 5.7 MPa, SF 3.1 across layers.
  - Sideways 10 g puts 42 N along the spar, about 5 N per ring, which the pinch screws hold by friction.
- **The nacelles hung from the rear.** They carry both fans as a cantilever from x −106. The joined halves at x −80, −60 and −36 stay at 0.1 to 3.3 MPa, SF ≥ 9.7.
- **The root band with the tie on the arm tops** (hand model, today's value in brackets):
  - Thrust, torsion: 2.8 (2.8)
  - Landing, torsion: 0.90 (0.90)
  - Lift, torsion: 6.7 (1.3)
  - Fore-aft, bending: 1.9 (0.61)
  - Sideways, bending: 1.4 (0.88)
  - Topple, torsion: 0.20 (0.49). The yaw moment becomes a force couple across the two tie points, so the topple gets worse.
  - None of these hand values is within 30 % of SF 2 except fore-aft (1.9). The governing landing case fails clearly, so I did not run FEA. Today's FEA shows the band's open-section torsion is about 2.5 × worse than the hand model.
- **Pack posts:** unchanged from today, because the resultant at the posts does not depend on the structure in between. Fore-aft SF 2.0, landing 3.1, topple 0.39.

## What would make the spar worth it

A tie that reaches the centre plate inside |y| < 20, below the band. That means:
- moving the FC/ESC stack off the right side behind the backpack;
- giving the backpack top a pass-through for two webs from x −106 to the centre plate top, clear of the plugs and below the saddle window;
- or mounting the backpack on the tie instead of on the centre plate.

That is a layout change, not a part change. Until it happens, the root fix stays the one in `README.md`.

## Reproduce

1. Push to the Mac mini: `zsh cad/mini_sync.sh push`
2. Scan the corridor there, about 1 minute: `zsh cad/mini_sync.sh run '$PY strength/spar_clearance.py'`
3. Copy the results back: `rsync 'mac-mini:code/flight-cad-mirror/robotics/microduck-sim/extensions/flight-20261110/strength/out/spar_clearance*' strength/out/`
4. Run the hand calculations, a few seconds: `/tmp/microduck-cad-venv/bin/python strength/spar_calcs.py`
5. Merge into `results.json`: `/tmp/microduck-cad-venv/bin/python strength/build_results.py`
