# Ankle insertion-path investigation

Problem P5. Checked 2026-10-07. This is a read-only investigation of the unchanged native source parts. No printing, resizing, source CAD changes, or physical assembly test was performed.

## Findings

The earlier order—attach the lower link to the knee, fasten its ankle motor, then bring the orange ankle over the preassembled link/motor/sleeve—does not have a clear straight top-insertion route. At the first tested contact, the small sleeve catches the ankle; the final assembled pose being clear externally does not mean the intervening path is clear.

Two smaller left-side bench operations do have clear sampled routes against the stated obstacles:

- Sleeve62 into empty ankle66: world translation `[0,+10,0]` to `[0,0,0]`, 41 poses at 0.25 mm; maximum material intersection 0 mm³. Insert from inside the fork toward the pocket, rather than through the outside retaining lip.
- Bare motor6 into ankle66 with the sleeve seated, lower link absent: world translation `[0,0,+30]` to zero, 121 poses at 0.25 mm; maximum intersection 0 mm³. Keep case/output screws absent or loose until closure and alignment are checked.

These are finite sampled partial routes. Other robot parts, fasteners and wires were not obstacles in these tests. A positive minimum separation or continuous collision-free certificate was not computed.

## Blocked old route

Moving the preassembled `lower`, `motor6`, and `smallring` together down from world Z +30 mm first exceeds the unchanged 0.02 mm³ collision criterion at world Z +16.48388672 mm. The first pair is `smallring--ankle`, with 0.020031899 mm³ of intersection. The contact offset was bracketed by 12 binary refinements after 0.25 mm sampling; bracket width is 0.000061035 mm.

The JSON animation stops at `stopAtT=0.4505350749`. Only an explicitly labelled contact preview may reach `contactAtT=0.4505371094`. Highlight the sleeve and ankle; do not animate this group through the obstruction to its nominal final pose.

At 3 mm top offset the sleeve/ankle intersection is about 77.89 mm³, while lower/ankle is about 5.47 mm³. Both axial directions and the other four cardinal translations also contain collisions in the bounded coarse scan. A 390-pose motor-last search over source-axis tilts and offsets found no complete connected route. This is a bounded negative result, not a proof that every possible compliant assembly motion is impossible.

## Closure requires a real fit checkpoint

The untouched sleeve has approximately 9.65 mm bore and the lower-link locating boss approximately 10 mm outer diameter. Their nominal final mesh intersection is 14.9585869 mm³. Consequently a strictly rigid, zero-interpenetration path containing all four unchanged parts cannot even terminate at this nominal final pose.

Real printed parts can deform and differ from nominal dimensions, so that result does not prove physical assembly impossible. It does mean the guide must not certify a smooth rigid closure animation. Prepare the ankle on the bench, seat the sleeve from inside, introduce the loose bare motor, then perform a gentle lower-link/peg/sleeve alignment and fit check. Only after that check should scheduled case, rear and output fasteners be tightened and the module attached to the knee. Do not force the sleeve through the retaining lip or use screw tightening to conceal an unresolved fit.

A split or deliberately compliant bracket could be investigated as a future design option, but neither source geometry nor dimensions were changed here; no redesign is asserted to be necessary or author-intended.

## Actual right-side checks

The actual right meshes were tested directly, rather than assuming the left mirrored route passes. Sleeve68 into ankle64, world Y −10 mm to zero, has 41 sampled poses and zero intersection. Bare motor1 world Z +30 mm to zero, against ankle64 and sleeve68, was sampled at 121 poses. It does **not** pass the unchanged strict 0.02 mm³ volume criterion: maximum intersection is 0.1372849 mm³, final intersection 0.1372744 mm³.

That final intersection is a mating-face slab with world Y extent only 0.000930786 mm and X/Z extents about 15.599 mm. This quantitatively distinguishes a thin nominal registration/contact discrepancy from the substantial entrance obstruction of the left preassembled sleeve. The attribution to source registration or numerical representation is an inference. Right bare-motor movement remains a source-contact preview and physical-fit checkpoint, not a certified collision-free insertion. No tolerance threshold or assembled source pose was changed.

## Geometry identity and animation data

`assembly-path-investigation.json` binds the latest left `leg-data.json` SHA and the native 3MF, motor STEP, original assembled XML and referenced assembly sources. `left_native_inputs` and `right_native_inputs` also bind each participating mesh's decoded position/index payload SHA and actual source transform. The full-build JSON file hash is intentionally not an input, because that file binds this report; binding individual immutable payloads avoids a circular identity dependency.

Each path includes world-millimetre translation, xyzw quaternion, pivot, fixed/moving keys, finite sampled intersection volumes, and viewer-ready animation frames. The blocked route includes stop/contact parameters and coloured-pair identifiers. All claims remain digital geometry findings; printed fit, roundness, surface finish, physical assembly and wiring are unverified.

## Rest-of-robot route

The canonical assembly handbook covers torso/legs, feet, neck/head/jaw, camera/IMU and harness routing. Use right motor IDs 1–5, left 6–10 and head/neck 11–15 with the current authoritative fastener schedule. IDs14/15 do not acquire invented case screws: peg/shell retention remains an explicit source-feature and dry-fit check. The right composite foot46 must use its measured native ankle64 registration, not a blind copy of left foot44 or a tutorial URDF from a different robot.

This investigation supplies mechanical ordering and partial insertion evidence only. The full-guide exporter owns remaining assembly coverage; wiring, electrical commissioning and completed physical assembly are separate acceptance scopes.
