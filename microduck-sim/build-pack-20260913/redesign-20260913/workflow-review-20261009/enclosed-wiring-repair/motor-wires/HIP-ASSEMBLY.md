# Hip motor cables — current original body

This local revision replaces the failed neutral paths for motor 5→4 and motor 10→9. The active topology is `active-topology.json`. It does not reconnect the two feet. No printed part, servo ID or connector selection changes.

Each route contains three receiving conductors, each with 180 mm of modeled flexible material. The spare is represented in the existing rear-of-motor cavity, rather than discarded or stretched through the converter. Endpoint straight segments and R2 tangent entry bends lead into a compact loose coil. The conductor diameter of 1.5 mm and bending radii are receiving assumptions, not a manufacturer fatigue specification. Do not wind or clamp the actual lead to an exact rigid helix merely to reproduce the drawing.

## Installation sequence

1. Keep the already assembled foot and ankle together. Work at the open hip/torso station. If the right torso cover is already fitted, remove that cover only to expose the motor-5 outlet; do not pull the inserted plug sideways through the cover.
2. Before the right torso cover closes, plug the motor-5 socket-14 end axially. Its complete receiving housing collides with `shell_right` during the 15 mm axial approach when that cover is in place. This is a source-geometry result, not an inference from a bounding box.
3. Lead the three conductors toward the rear/inner edge of the motor, then down the existing channel. The channel's narrow local section is 2 mm across: the modeled Ø1.5 mm receiving conductor has approximately 0.2405 mm surface clearance after the conservative polygon allowance. Keep the conductors side by side, not stacked through this section. The final geometry does not cut or enlarge this passage.
4. Arrange the spare gently in the rear pocket while the cover is open. The displayed coil is a collision-free neutral receiving shape. A loose ordinary tie may collect the spare; do not tighten it into a rigid spring or bind a moving link to the stationary torso. No new printed clip is required by this local routing result. Tie placement and inventory are not certified by the current mesh receipt.
5. Plug the motor-4 socket-13 end along its axis. For the other branch, use motor-10 socket-14 and motor-9 socket-14. Current source-printed surrounds do not block the other three 15 mm axial housing approaches; this does not certify finger access or detailed latch mating.
6. Before closing the cover, move the actual joint through its intended travel by hand with power off and adjust the loose service section once. The two connectors must remain seated, the cable must not be drawn taut, and no section may enter a closing seam. This physical adjustment is required; the neutral CAD curve is not a fixed-shape motion model.

## Digital evidence and limits

`hip-fusion-manifest.json` gives ten world-coordinate meshes: six full-length conductors and four complete receiving connector housings. `hip-valid-source-static.json` binds all near original obstacles and substitutes the twelve valid manufacturer solids per servo for invalid aggregate motor meshes. It finds no neutral overlap. Own-socket contact is a mating interface and is not certified by a rectangular receiving housing.

`hip-centerline-audit.json` checks nonlocal single-wire segment distances and the local curvature samples; each wire is self-clear. The two full route reports also check all three wire-to-wire pairs and the adjacent previously cleared knee route. The smallest nonlocal single-wire surface-distance lower bound is 1.322 mm. `hip-plug-access.json` records the exact right-cover closure dependency.

A 0.25 mm lateral shift of the narrow passage was explicitly rejected: it crossed the opposite torso-base lip. The centered source route is retained. Neutral clearance is established; complete flexible motion, installed material tolerances, latch operation and fatigue life are not claimed.
