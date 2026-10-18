# Motor-wire repair: use the installed native CAD workflow

Verified 2026-10-09. Research and source-receipt review only; no route, robot geometry, Fusion document, or released file changed. Custom optimizer work is paused.

## Decision applicable now

Use the installed **Autodesk Fusion**, starting with one complete failed local station, **motor4 → motor3**, before repeating the method elsewhere. Preserve the registered connector frames and current original leg spacing. Inspect the motor, plate and thigh with section planes to establish a genuinely open corridor; then create a native editable 3D sketch with explicit axial connector leads, tangent lines/arcs and a stated bend-radius parameter. Sweep the complete receiving diameter and connector housings into separate named components. Measure native route length and account for stock excess separately. Do not continue exporting visually smooth but uneditable paths through the same occupied waypoints.

This is Autodesk's existing connector-to-connector method: enable 3D sketch, include actual connector geometry, constrain endpoint lines and spline tangency, then create Pipe. It does not discover a collision-free route automatically. [Autodesk pipe/hose between fittings](https://www.autodesk.com/support/technical/article/caas/sfdcarticles/sfdcarticles/Create-a-pipe-or-hose-between-two-fittings-in-Fusion.html)

For this station, current interference occurs at the motor3 rear/bottom channel, plate and thigh lip. Section locations around world Y = −43, −66.5 and −70 mm are useful diagnostic locations, not preapproved cable waypoints. Resolve that actual corridor before mirroring it to motor8. The failure does not establish a need to replace these printed parts.

## Tool availability and limits

The local inventory found `~/Applications/Autodesk Fusion.app` on this Apple Silicon Mac. No Inventor, SOLIDWORKS or Windows virtual-machine application was found in `/Applications` or `~/Applications`; no harness add-in was found in the inspected Fusion API AddIns directory. This is a limited inventory, not a license audit. The Fusion bundle's 2705.1.30 string is a launcher/bundle version, not a verified CAD-engine version.

The latest located Autodesk employee reply, dated January 2026, gives no ETA for a dedicated Fusion wire-harness tool and identifies Inventor as Autodesk's existing harness application. Therefore do not promise a hidden Fusion harness module or automatic bend/stock-length management. [Autodesk support discussion](https://forums.autodesk.com/t5/fusion-electronics-forum/wire-harness-tool/td-p/13226419)

Fusion's interference API explicitly accepts BRep bodies and component occurrences. The current imported STL scene must not be treated as checked merely because a BRep interference command returns no results. Use valid native solids or a verified **local** conversion. For mesh-only pairs, Fusion's Mesh Combine → Intersect on duplicate bodies, with Keep Tools, provides a native overlap operation; retain source geometry. Do not subtract collisions from either physical part to manufacture a pass. [Interference API](https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/fusion_Design_createInterferenceInput.htm), [Mesh Combine](https://help.autodesk.com/cloudhelp/ENU/Fusion-Mesh/files/MESH-COMBINE.htm), [body-type limitations](https://help.autodesk.com/cloudhelp/ENU/Fusion-Assemble/files/GUID-C1AB4941-D7AD-4D27-A035-2FA9208635B6.htm)

Native sketch curves expose length, and circular arcs have measurable radius; the API's curve-length unit is centimetres. These support explicit dimensional checks, but do not replace the actual cable specification. Motion Study animates assembly joints and Contact Sets prevent rigid components passing through one another. Neither establishes constant-length flexible-wire deformation or bend fatigue. Check plug insertion, prewired closure and joint service allowance separately. [SketchCurve API](https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/fusion_SketchCurve.htm), [Motion Study](https://help.autodesk.com/cloudhelp/ENU/Fusion-Assemble/files/GUID-1B0EEBBF-3923-47E3-BB58-E5955D9EA738.htm), [Contact Sets](https://help.autodesk.com/cloudhelp/ENU/Fusion-Assemble/files/ASM-CONTACT-SETS.htm)

## What dedicated industry applications add

**Inventor Cable & Harness** manages connectors, wires, cable segments and routed harness subassemblies. Assigned minimum bend radii can be checked actively after route edits and positional changes. Its documentation explicitly excludes some cases, including junctions and splices; reports can still be produced with violations. It is not installed here and has no native macOS version. This is a reference for the required checks, not a request to buy or install it. [Harness creation](https://help.autodesk.com/cloudhelp/2024/ENU/Inventor-Help/files/GUID-AF02C388-3094-44EC-ADA6-B75BA0560823.htm), [bend checking](https://help.autodesk.com/cloudhelp/2025/ENU/Inventor-Help/files/GUID-F85EED4E-1A50-4A15-ACD7-B58DB6208064.htm), [Mac limitation](https://www.autodesk.com/support/technical/article/caas/sfdcarticles/sfdcarticles/Can-I-install-Autodesk-Inventor-on-a-Mac.html)

**SOLIDWORKS Electrical/Routing** uses connector connection points, routing paths and cable libraries with diameter and minimum bend radius. Its automatic routing operates on supplied routing paths; it is not evidence that arbitrary sealed geometry can be routed automatically. It is not installed here. [Route Cables](https://help.solidworks.com/2025/English/swelec/r_swelec_routing_cables.htm?id=4a27ff52753e4517a2a17f6a288822b5), [cable/wire library dimensions](https://help.solidworks.com/2024/english/SolidWorks/sldpiping/c_maintaining_library_files.htm?format=P&value=)

## Actual causes of the eleven failed routes

The accompanying JSON binds every existing route receipt by SHA-256 and records the maximum intersection of an individual conductor/body, with its actual intersection bounds. Values below are not sums across conductors.

- **OpenRB → 15:** down-and-forward corridor crosses motor13, jaw support and yaw link, up to 5.927 mm³; a separate roof-feature contact is 0.527 mm³. The OpenRB socket is registered from actual connector geometry; the corridor is the failure.
- **15 → 14:** bridge passes through the speaker (33.668 mm³), and rear descent crosses cap (23.564 mm³) and bottom. A separate conservative motor14 plug box contacts the bottom; exact mating-profile detail remains necessary before declaring the real plug impossible.
- **14 → 13:** local upper turn clips jaw support and yaw-link tops, 0.470 and 0.444 mm³.
- **13 → 11:** negative-Y descent crosses a structural support arm (15.673 mm³), bottom and jaw frame rather than an established neck opening.
- **5 → 4:** rear vertical route occupies the existing converter insert (42.730 mm³) and power support. It is not an empty rear corridor.
- **4 → 3:** the chosen channel traverses motor3 (28.359 mm³), plate and thigh lip; rounding does not remove those crossings.
- **2 → 1:** knee exit crosses thigh lip and ankle-side turn crosses the lower-link rear bar, up to 2.304 mm³.
- **1 → 6:** both ankle turns cross ankles, inner rings and lower links, up to 13.487 mm³. The middle cross-leg span is not the main problem.
- **6 → 7:** mirrored thigh-lip and lower-link rear-bar crossings, up to 2.307 mm³.
- **8 → 9:** mirrored motor8, plate and thigh-lip crossings, up to 28.360 mm³.
- **9 → 10:** mirrored converter insert and support crossings, up to 41.607 mm³.

The generator used a corner-trim heuristic (`min(2.5, adjacentLength × 0.3)`) rather than enforcing a specified bend radius. Its reported minimum centreline radius reaches **0.066 mm**, smaller than the modeled conductor radius of 0.75 mm. A watertight swept mesh is therefore not proof of a physically admissible wire. Replacing the earlier overshooting curves fixed some errors but left invalid straight corridors and overly sharp turns.

The four remaining routes have neutral static receipts without source-mesh intersections; they are **not complete harness passes**. Their stock spare length, specified minimum bend radius, connector insertion, electrical pin order and moving-joint service allowance remain unaccepted. The 1.5 mm conductor diameter is a receiving assumption, not newly verified purchased-wire diameter.

## Immediate acceptance target

Deliver one editable Fusion local route whose connector axes, full housing, diameter, explicit bend dimensions and total length are inspectable, with actual local interference results and the required pre-insertion/cover order. Only then repeat the same native method. Do not declare all eleven routes repaired, prescribe structural reprints, or claim physical wiring validation from this research brief.
