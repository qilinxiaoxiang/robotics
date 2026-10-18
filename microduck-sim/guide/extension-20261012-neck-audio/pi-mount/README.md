# MicroDuck Pi mount study (after a V1.8 Pi post snapped)

Problem IDs: P5 (head integration), P6 (build and assembly). Study date 2026-10-12. This is a measurement and options study. It contains no release print files, and V1.8 is unchanged. Coordinates are in the robot frame, in mm: x forward, y left, z up.

Owner report: while support was being removed from the printed V1.8 head cap, one Pi mounting post snapped off. The Pi still mounts on the other three holes.

## Verdict

Reinforce the existing rails (option A) and print them as part of the audio-extension head cap, which needs a reprint anyway.

- Option A keeps the same four Pi screws, the same Pi position and the same assembly steps. It adds no new parts.
- Each rail gets a web to the side wall, a ramp over the lower boss and a solid root at the roof. This lowers the bending stress per newton by about 7 to 10 times compared with V1.8.
- The rails no longer have ledges that need support in the slice, so nobody has to pry support off them.
- The exact manifold3d checks pass with zero failures. Every clearance is listed under "Option A" below.

A separate flat-printed bracket (option B) also passes the checks. It is not recommended: it adds 2 parts and 4 screws, still needs a cap reprint for its stubs, and its screw joint is the new weak point. Inserts, standoffs and glue (option C) do not fix the cause.

**Current build on three screws:** this is acceptable until the new cap is printed. When you push jumper housings onto the header, support the board from behind with a finger. Tighten the screws only until snug. Do not pry near the remaining posts, and check that the board does not rock. If the missing post is E-pi-02 (the +y lower one), also check that the free corner stays clear of jaw_support. The Pi had only about 1.09 mm of clearance to it.

## What is measurement and what is inference

- **Measured.** Section sizes, stresses per newton, clearances, overlaps and overhang areas come from the V1.8 and study meshes, using exact manifold3d booleans and beam statics.
  - Stress per newton is the bending stress that a 1 N force at a Pi screw would cause. It is geometry only and needs no material data.
- **Inference.** Every statement about PLA strength or breaking loads is inference. So is every claim about which post broke and why it broke during support removal. Each one is labelled where it appears.

## Why the V1.8 post broke

Each V1.8 Pi rail is a thin column that hangs from the roof. It is about 28 mm long, from z 116 to 144.3. Between its two screw bosses it is only 2.0 mm deep along the screw and 3.2 mm wide. The +y rail is trimmed to 1.23 × 3.2 mm at z 122.1.

The lower screws (E-pi-01, E-pi-02) sit at the free end of that column, about 20 mm from the roof.

- A 1 N push along the screw at a lower screw gives 9.26 MPa at z 138.4.
- A 1 N sideways push there gives 5.79 MPa.
- The upper screws sit about 2.5 mm from the roof and see only 0.19 to 0.26 MPa per N.

The cap prints roof-down, so each rail is built upward from the roof like a column. Its rail axis is 14.4° from the layer normal. That means 94% of the bending stress pulls the layers apart across their bond, which is the weakest direction of a print.

The two released slices differ near the rails. Both use PLA, 0.2 mm layers, tree support, a 30° threshold, and support allowed on the model.

- **Bambu slice.** It puts no support on the rails, only overhang walls. Its nearest support is under the roof's outside grooves, at z 147 to 150.
- **Elegoo slice.** It roots tree support on each rail's front face, under the lower boss ledge at z 121.5. That is 3.6 mm from E-pi-01 and E-pi-02. More support climbs to the upper boss ledge.

Inference:

- PLA's bond between layers is roughly 20 to 30 MPa. That puts the break near 2 to 3 N (about 0.2 to 0.3 kgf) of prying at a lower screw.
- Twisting off support that is rooted on the rail face can easily apply that much.
- The snapped post was most likely a lower one, because the upper bosses see only about 1/50 of that stress.

Owner answer, 2026-10-13: the broken post is the left one seen from the front. Seen from the front of the duck, the viewer's left is the duck's right (-y), so it is on the -y rail: E-pi-01 (lower boss) or E-pi-03 (upper). The stress figures above point to the lower boss, E-pi-01 (inference). Option A reinforces both rails, so the recommendation does not change.

Pictures:

- `png/v18-rail-sections.png`: section size and stress along each rail.
- `png/v18-rail-support.png`: support the slices placed around the rails.
- `png/V18-sections.png`: the V1.8 rails among their neighbours.

## What every option was checked against

Each option's solids went through the same exact checks:

- **Parts:**
  - the Pi with all 13 jumper housings and their wire exits;
  - the GPIO solder tails;
  - the CSI connector, the CSI ribbon (modelled as a 16 mm × 0.3 mm strip along its route) and the camera;
  - jaw_support and motor15.
- **Motions:**
  - head roll ±25°;
  - jaw 0 to 40°;
  - the 40 mm cap-on descent.
- **Layouts and keep-outs:**
  - the recommended audio layout (speaker, amplifier, housings and wires);
  - the head bundle tube;
  - the neck-route keep-outs: behind the Pi in the middle (x < 59.5, |y| < 25), everything below z 111.9, and the region just below the Pi header (x 59 to 78, |y| < 26, z 104 to 113).
- **Outside of the cap:** nothing may be added outside the V1.8 hull or in its outside grooves.

Every option leaves the keep-outs empty.

## Option A: reinforced integral rails (recommended)

**What changes.** Each rail gets three printed additions. All three are fused into the cap.

- **Web.** A web joins the rail to the side wall. It runs from the lower boss to 12 mm above the upper screw. Its back face is at u 8 (about x 49.5). On +y the back face steps back near the lower boss so it clears jaw_support.
- **Lower-boss ramp.** A 55° ramp above the lower boss replaces the flat ledge that the Elegoo slice supported.
- **Root block.** A solid block runs from the upper boss into the roof.

All four Ø1.7 pilots are re-cut. The added material is 2139 mm³ (about 2.7 g of PLA if solid; inference). Nothing is added outside the cap, and nothing is removed apart from the pilot re-cuts.

**Space checks (exact, zero failures):**

- **Pi:** sits flush on the same seat plane, with 0.004 mm to the pads.
- **jaw_support:** 0.5 mm statically and 0.45 mm during cap descent.
- **Other parts:** GPIO solder tails 1.19 mm (V1.8 rail: 0.4 mm); CSI connector 1.64 mm; motor15 2.15 mm during descent.
- **CSI ribbon strip:** 2.05 mm (V1.8 rail: 3.24 mm).
- **Head bundle:** 3.28 mm from the bundle centreline to the rail, for a 3 mm bundle radius (V1.8: 3.03 mm).
- **Sweeps:** head roll at least 8 mm; jaw 7.8 mm.
- **Audio layout:** the nearest part is the pin-40 housing, 4.31 mm away.

**Strength** (beam statics on the measured study geometry, side wall excluded, so this is conservative):

- **Along the rail, across layers:** 0.95 MPa per N (−y) and 1.28 MPa per N (+y) for a push along the screw. That is 9.6 and 7.1 times lower than V1.8's 9.14. Sideways it is 0.84 MPa per N, 6.8 times lower than V1.8's 5.71.
- **Through the web into the side wall, along layers:** 0.08 MPa per N (−y) and 0.67 MPa per N (+y).
- **Inference:** the lower posts should now take roughly 15 to 30 N before breaking, up from about 2 to 3 N.

**Print.** The cap prints with the same pose and slice settings.

- Rail faces that point down at less than 30° drop from 11.3 mm² per rail in V1.8 to 0.08 mm² per rail, so the rails need no support.
- The only remaining down-facing areas are the tops of the four pilot bores (6 to 8 mm² per rail). They bridge, as they do in V1.8.

**Screws.** These are unchanged:

- E-pi-01, E-pi-03 and E-pi-04: M2 × 6 TAP.
- E-pi-02: M2 × 4 TAP.

**Assembly order.** The same as V1.8:

1. Remove support from the rest of the cap without levering on the rails.
2. Seat the Pi on the four pads.
3. Start all four screws, then tighten them to snug.
4. Fit the jumper housings.

Picture: `png/A-sections.png`.

## Option B: separate flat-printed Pi brackets (checked, not recommended)

**What changes.**

- **Cap.** Both V1.8 rails and their bosses are removed (751 mm³). Two stubs are added (437 mm³). Each stub is a 3.5 mm deep block that hangs from the roof down to z 133.3. It sits behind the place where the rail was and fuses into the roof and side wall.
- **Brackets.** One bracket per side: about 906 mm³ on −y and 468 mm³ on +y. Each bracket carries the two Pi seat pads and both Pi pilots. Its upper part is a tongue that lies against the front of the stub.
- **Bracket width.** On +y the bracket stays at the V1.8 rail's inner face, |y| 27.4, to keep room for the head bundle.

**Space checks (exact, zero failures):**

- **jaw_support:** 0.91 mm statically and 0.37 mm during descent. That is tighter than option A.
- **Other parts:** GPIO solder tails 0.8 mm; motor15 2.07 mm.
- **CSI ribbon strip:** 2.12 mm.
- **Head bundle:** 3.7 to 4.1 mm from its centreline.
- **Sweeps:** jaw 7.2 mm; roll at least 8 mm.
- **Audio layout:** at least 4.2 mm away.

**Strength.**

- **Bracket body, along layers:** 3.5 MPa per N (−y) and 5.8 MPa per N (+y), measured at the bracket-screw row.
- **Cap stub just above its screw row, across layers:** 1.4 to 1.9 MPa per N.
- **Weak point:** at the screw row itself, the two Ø2.4 holes leave only thin strips of stub.
- **Inference:** a real design would need a deeper stub or staggered holes. The joint, rather than the bracket, would then set the strength.

**Print.**

- **Bracket.** It prints lying on its inner face, so its layers run along its length. It needs no support. The only down-facing areas are the tops of the horizontal Ø1.7 pilots, which bridge.
- **Cap.** The stub clearance holes add 8.8 mm² of bridged hole tops per side.

**Screws.**

- The four Pi screws keep their V1.8 specs and now thread into the brackets.
- 4 extra M2 × 6 TAP screws hold the brackets to the stubs, with about 2.5 mm of thread engagement each (inference: weaker than the Pi screws' 4.4 mm).
- The straight line behind each bracket-screw head is clear for only 17 to 25 mm before the cap's back wall, so this needs a stubby or angled screwdriver.

**Assembly order.**

1. Print the cap and the two brackets.
2. With the cap upside down on the bench, hold each bracket's tongue against its stub. Drive 2 screws per side from behind.
3. Seat the Pi on the bracket pads and drive E-pi-01 to E-pi-04.
4. Fit the jumper housings.

To replace a bracket later, remove that side's two Pi screws and two bracket screws.

**Carrying the amplifier on the bracket.** This was not pursued.

- The brackets sit beside the Pi at |y| 26 to 33. Behind them is the cap wall and the neck-route keep-out.
- The audio study's amplifier position already passes all checks.

**Why not B.** It needs 2 extra parts and 4 extra screws, and the cap still has to be reprinted for the stubs. Its jaw_support margin is tighter, and its clamp joint becomes the new weak point.

Picture: `png/B-sections.png`.

## Option C: other ideas (text only, not recommended)

- **Heat-set M2 inserts** (pressed in with the soldering iron).
  - They do not address the failure, which is the column bending across its layers rather than stripped threads.
  - An insert needs a hole of about 3.2 mm with 1.2 to 1.5 mm of wall around it, which means a boss 5.6 to 6.2 mm across. The +y lower boss is only about 2.9 mm deep.
  - The iron's heat would soften the thin column.
  - They would need machine-thread screws, but all E-pi screws are TAP.
- **M2.5 brass standoffs.**
  - The Pi holes accept M2.5, but a standoff needs a solid anchor behind the Pi. Behind the rails there is only the neck-route corridor and open space.
  - Anchoring to the old rails keeps the weak column.
  - They are a new purchase under the sourcing policy.
- **Gluing the snapped post back.**
  - The standing build rule allows glue only when the benefit is large, and never over screws.
  - A glued column also keeps the same weak 2 × 3.2 mm section.

## Connection methods for owner approval

Option A (recommended):

- **Rails to cap:** printed as one piece with the cap. The web, ramp and root block are fused into the side wall and roof, with no fastener.
- **Pi to rails:** four self-tapping M2 screws through the Pi's holes into Ø1.7 printed pilots, as in V1.8. They are M2 × 6 TAP at E-pi-01, E-pi-03 and E-pi-04, and M2 × 4 TAP at E-pi-02. The Pi rests on the four boss pads.

Option B (for comparison):

- **Stubs to cap:** printed as one piece with the cap.
- **Bracket to stub:** a lap joint. The bracket's tongue is pulled against the stub's front face by 2 self-tapping M2 × 6 screws per side. They are driven from behind through Ø2.4 holes in the stub into Ø1.7 blind pilots in the bracket.
- **Pi to brackets:** the same four screws as V1.8, now threading into the brackets.

## Open items

- **Mesh repair.** The study STL files come from exact manifold3d booleans, but trimesh reports them as not watertight because of degenerate triangles. Run a mesh repair before slicing.
- **Reslice check.** Reslice the option A cap in both Orange profiles and confirm that no support lands on the rails.
- **Print test.** Print one cap, mount the Pi and push the housings on. Then do a gentle pull test at the lower screws.
- **Owner confirmation.** Confirm which printer made the broken cap and which post snapped.
- **+y web clearance.** The +y web's back face passes 0.45 mm from jaw_support during cap descent. Check that face for elephant foot or a raised seam.

## Files

- **This file:** `/Users/xiangzheng/code/robotics/microduck-sim/guide/extension-20261012-neck-audio/pi-mount/README.md`
- **Summary data:** `pi-mount-study.json`.
- **V1.8 failure numbers:** `v18-failure.json`.
- **Neighbour distances of the V1.8 rails:** `neighbourhood.json`.
- **Option A:**
  - `A-build.json` and `A-parts.json`;
  - check results in `A-checks.json`;
  - solids `study-solids/A-head_cap-world.stl` (the full cap, built on the audio-extension cap), `A-added-world.stl`, `A-removed-world.stl` and `A-pi_screws_envelope-world.stl`.
- **Option B:**
  - `B-build.json` and `B-parts.json`;
  - check results in `B-checks.json`;
  - solids `study-solids/B-head_cap-world.stl`, `B-cap_added-world.stl`, `B-bracket-y-world.stl`, `B-bracket+y-world.stl`, `B-pi_screws_envelope-world.stl` and `B-bracket_screws_envelope-world.stl`.
- **Pictures:** `png/`.

**Rerun.** Run these from `scripts/` with `/tmp/microduck-cad-venv/bin/python`, in this order (each takes under 2 minutes):

1. `v18_failure.py`
2. `neighbourhood.py`
3. `build_a.py`
4. `check_options.py A`
5. `build_b.py`
6. `check_options.py B`
7. `render_options.py V18`, `render_options.py A`, `render_options.py B`

The scripts read the audio study's check library (`../audio/scripts`) and its extension cap. They read V1.8 files without writing to them.
