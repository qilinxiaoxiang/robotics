# M2×5 fastener revision — 8 October 2026

Problems P5/P6: remove the guide's unavailable 5 mm fastener requirement without bottoming out screws, accepting too little engagement, or reopening the user's completed legs. This package proposes exact per-position changes; it does not modify the canonical baseline or establish physical strength.

## Decisions

**ID13 head-yaw output: four M2×6 TAP screws with a revised neck-pitch bracket.** The original bracket puts the head 2.89956 mm from the horn face. M2×4 enters only 1.10044 mm; M2×6 enters 3.10044 mm. ROBOTIS limits the horn pilot depth to 3 mm. The existing project requires more than 1.6 mm entry, which is an engineering screening criterion rather than a manufacturer-specified minimum or strength result.

The candidate adds four integral, 1.0 mm tall head seats: outer diameter 5 mm, central clearance diameter 2.4 mm. M2×6 then enters 2.10044 mm, leaving 0.89956 mm to the manufacturer's maximum. The screw tips and the motor interface remain in their previous positions. `neck_pitch-m2x6-seat-world.stl` and `neck_pitch-m2x6-seat-source-frame.stl` correspond to guide part `neck_pitch`, community source ID 28, original stock `STL-Instances/plate-03/06_community-28.stl`.

The source bracket also contains a 0.200005 mm sacrificial membrane across each screw bore. A 2 mm shaft intersects about 0.627884 mm³ of membrane per hole. The replacement provides continuous Ø2.4 mm clearance through those same axes; it removes 11.4402 mm³ in total for the four membranes and local bore-wall clearance. It adds 42.6604 mm³ at the head seats. No unrelated wall or motor seat is cut.

**IMU clamp: two M2×6 TAP pressure screws, with no reprint.** These screws press their tips against the rail; their heads are intentionally above the holder. Keep the tips at Z=29.5 mm and raise the heads from Z=34.5 to 35.5 mm. The 6 mm version leaves a 1.8 mm head gap. Stop at tip contact; do not force the heads flush. M2×4 bottoms its head while the tip remains 0.2 mm above the rail, so it does not clamp. The old audit called the pilot material 4.2 mm; ray measurements of the actual source resolve 4.0 mm of plastic at Z=29.7…33.7, with a separate 0.2 mm air gap below it. The new metadata corrects that distinction.

**Eight knee-output screws: preserve the completed legs.** Their original 2.8 mm stack gives 1.2 mm entry with M2×4 and 3.2 mm with M2×6. Neither is accepted as a direct substitute. The optional `lower` and `right_lower` candidates add the same 1 mm seats so M2×6 retains the former 2.2 mm entry and 0.8 mm tip margin. They correspond to community source IDs 30 and 32. The user confirmed that M2×6 is already installed. That implies3.2mm nominal entry against the drawing's3mm maximum; it does not prove actual damage. The revised links are validated **for a new build**. Replacing already assembled lower links reopens captured ankle interfaces; no replacement sequence preserving those force-fitted interfaces has been validated. Do not interpret these candidates as an instruction to dismantle the completed legs.

**The earlier OD5 washer screen was incomplete and is superseded.** It omitted the printed lower link from its obstacles. With the host included, a DIN433 M2.5 washer (ID2.7 / OD5 / thickness0.5mm) intersects each recessed knee seat; this alternative is rejected. Do not substitute a generic kit washer.

A separate conditional review checks one SS304 small-OD washer per knee screw: ID2.20–2.34, OD3.64–4.00, thickness0.40–0.60mm, as specified for JC Fasteners B4D1002001 (the catalogue's NF-E25-513/514 variant, not generic DIN433 M2). These dimensions give nominal screw entry2.6–2.8mm. The washer must lie flat within the original recess: centered poses and an eccentricity envelope of0.10mm have a clear insertion path, while unconstrained0.17mm bore play can hit the recess and is explicitly rejected. This is a conditional geometry review, not current main-guide adoption. Washer stock, actual printed-seat fit, strength and torque remain unverified. If a washer cannot lie flat without forcing, do not tighten it or substitute a larger outside diameter. The user confirmed screw length only, not washer ownership.

There are 14 affected M2×5 positions in the current guide: twelve servo-output positions plus two IMU pressure screws. There is no M2.5×5 position in the current guide or integrated head candidate. M2.5×6 and M2.5×8 head hardware are different specifications and remain unchanged. M2 machine screws must not be treated as interchangeable with M2 tapping screws.

## Evidence and scope

The [manufacturer-authored X330 drawing](https://www.besttechnology.co.jp/modules/knowledge/gate.php/X330_dimension.pdf?way=attach&_noumb&refer=Dynamixel%20XL330-M077&openfile=X330_dimension.pdf), dated 28 May 2020 and rechecked 8 October 2026, identifies the output holes as Ø1.6, maximum depth 3 mm, for M2 tapping screws. The [official XL330 manual](https://emanual.robotis.com/docs/en/dxl/x/xl330-m288/#drawings) supplies the manufacturer's drawing entry. The [official OMX assembly model](https://docs.robotis.com/interactive/omx/models/leader.glb) contains PTS2_M2X4 and PTS2_M2X6. Their published head meshes measure approximately Ø3.49945 × 1.27274 mm; the checks use the larger Ø4 × 1.72 mm envelope. Published CAD is not an inspection of the actual kit fasteners.

`fastener-choice-report.json` records each ID, original stack, 4/6 mm arithmetic, head seat, pilot depth, tip margin, bore failure, individual insertion paths and tools. Head and shaft routes have 0.25 mm sampling; threads intentionally entering the target servo or printed IMU pilot are named receiver exclusions, not ignored external obstacles. Neck screws are fastened on the detached bracket, and knee screws on the leg bench before torso joining. `negative-knee-fastening-after-torso.json` preserves the blocked attempt to fasten knee screws after the power support is present.

`fastener-context-report.json` re-executes all 17 torso service part paths and 34 driver paths using complete revised geometry and retained screws, preserving the original strict, pair-specific contact limits. It also tests the new neck seats and four relocated heads against the actual curved-head replacements, electronics, receiving envelopes and retained structure. No source contact is globally subtracted.

The replacement solids are watertight single bodies. Source-frame STL files retain the original part coordinate frame and are geometry candidates, not sliced print jobs. Complete operational joint-range testing, print tolerances, torque, thread retention and strength remain unverified. Neither this supplement nor a passing baseline design verifier certifies physical commissioning.

## Rebuild and bind

Use the current CAD Python recorded in the hardware workflow:

1. Run `probe_seats.py` to build the three candidate parts.
2. Run `verify_fastener_choices.py` and `verify_fastener_context.py` against the unchanged baseline source.
3. Run `finalize_revision.py`. It rejects any changed evidence input and sets `fastener-patch-proposal.json` readiness only after both geometry gates pass.

The proposal binds the current base guide, all meshes, relevant sources and both reports. `proposalContentSha256` hashes canonical JSON after removing only `integrationReady` and `reportSha256`; the latter separately binds the final report bytes. Canonical JSON means UTF-8 `json.dumps` with sorted keys, compact separators and `ensure_ascii=True`. Re-running a geometry generator resets readiness, so an outdated proposal cannot silently ship.
