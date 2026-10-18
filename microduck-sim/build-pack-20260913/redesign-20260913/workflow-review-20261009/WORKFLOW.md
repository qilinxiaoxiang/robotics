# MicroDuck: reproduce, adapt, print and fit

Current workflow, 9 October 2026. Advances P5 (serviceable hardware) and P6 (usable deployment); P0 requires evidence beyond a convincing animation. The user explicitly accepts staged prototype printing and physical adjustment. Detailed flexible-wire simulation is unnecessary for this build.

## 1. Fix the reference and the actual differences

Use the [AI-FanGe build](https://github.com/AI-FanGe/Microduck-build-tutorial) and its assembly video as the reference. Separate observed construction from inferred internal placement. The native fanhao375 XL330 v1.1 head has Zero 2 W and RobotHAT; it does not establish an OpenRB position. The earlier assistant-selected OpenRB pose is a design variable.

Preserve the original curved closed exterior, jaw, neck, body width and completed feet. The actual differences are the first-generation Pi Zero W with its existing top-side 40-pin header, eye camera, owned audio parts, and DFR1202 in the original battery region. Keep internal Pi-to-OpenRB USB. A change must solve one of these differences or a demonstrated obstruction.

## 2. Fit rigid parts and access in CAD

Use Fusion sections and interference tools on actual solids; use source mesh checks where unchanged parts have only mesh geometry. Keep boards, populated connectors, plugs and screw access in the same subassembly. Check the local conflict before moving a board or changing a print. Preserve editable feature sources and identify mesh-derived outputs honestly.

Check plug insertion and screwdriver approach before fixing mounts. Recalculate changed parts and affected neighbors. Photographs support routing and appearance; they do not provide hidden dimensions.

## 3. Specify ordinary wiring simply

For each connection, state its two endpoints, cable, insertion direction, available passage and the next cover that blocks access. Preconnect before installing that cover or board. Leave slack beside plugs and moving joints, keep cables out of seams and linkage pinch points, and check free movement by hand.

Show connector positions and insertion in the guide. Add a loose route illustration only when it explains a passage. Individual conductor solids, exact curve lengths and deformable-material simulations are optional and cannot hold up an otherwise useful prototype. Do not add physical tie frames to accommodate an artificial cable curve.

This follows the practical level in [Prusa's electronics assembly instructions](https://help.prusa3d.com/wp-content/uploads/generated/original-prusa-i3-mk3s-kit-assembly_1128_guide_174100_en_2026-05-06.pdf), steps 13–21 and 37–39: connect while accessible, follow channels, leave slack and inspect the closing cover. [Autodesk's harness segments](https://help.autodesk.com/cloudhelp/2024/ENU/Inventor-Help/files/GUID-60FCFDE3-6170-4C7A-881B-90D4CB1733E5.htm) provide a grouped representation when needed. Neither source qualifies this robot's physical fit.

## 4. Print a bounded, useful trial

State what the trial tests and any excluded unresolved interface. Release only changed geometry. Use a genuinely planar bed-contact face; check native slicing for supports, mounting holes and plate separation. Package one prefixed Bambu file and one Elegoo file per present color, named with actual sliced time.

Fit the printed pieces with the actual boards and plugs before final closure. If a problem appears, identify the interfering pair or pinched passage and change that local feature. Keep the failed evidence. A mounting trial does not establish that an unresolved USB plug fits, and a digital check does not establish powered operation.

## 5. Update the guide from the accepted assembly

Order operations as prepare parts and cables, insert or fasten while accessible, check the result, then close access. Animate rigid insertion where it helps. Use close-ups of the actual work area and show cable-before-cover actions in both assembly and wiring views.

Publish and verify the current guide on the Mac mini. Keep English-only ChatGPT.site publication for the agreed complete guide. The design verifier reports whole-design status; physical commissioning remains separate.

## Current results and remaining work

- The live leg guide uses eight local connections with connector and channel instructions. Six artificial rectangular tie frames and prescribed rigid wire loops are withdrawn. Original leg parts remain.
- The three-piece Orange head mounting trial contains the closed curved cap with integral mounts, speaker cradle and retaining ring. The owned straight USB-C housing still conflicts with full closure; the short internal USB lead is unresolved. GPIO leads need a physical no-pinch check. The trial instructions retain these limitations.
- Complete populated-head closure, powered USB operation, whole-robot commissioning and final English publication are not accepted yet.

Detailed earlier studies remain in [the archived workflow](WORKFLOW-before-print-and-fit-20261009.md). Superseded routes and local passes are diagnostic history, not current prototype requirements.
