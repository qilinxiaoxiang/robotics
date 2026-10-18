# Assembly guide review method

Problem **P5 / P6**: an assembly guide must preserve a physically possible route to each joint and keep screws and connectors accessible until their work is complete. A final CAD pose, a smooth animation, or complete screw counts cannot establish those properties. A measured collision, blocked tool corridor, missed cable opening, or actual fit result changes the assembly decision.

Verified primary sources on **2026-10-08**: the [ROBOTIS OMX assembly guide](https://docs.robotis.com/docs/systems/omx/quick_start_guide/assembly_guide/), its [leader data](https://docs.robotis.com/interactive/omx/models/leader.json) and [follower data](https://docs.robotis.com/interactive/omx/models/follower.json), both revision `v025-materials-v027`, and the guide's [viewer implementation](https://docs.robotis.com/interactive/omx/assets/index-BtI3oHfa.js). The observations below describe the official page's published instructions and data. They do not establish that every official animation is collision-free.

## 1. Preserve access by choosing the assembly order

The official follower's optional-camera sequence provides a concrete example. Labels `camera-prep-v013 → 60 → 61 → 59 → 62` prepare the bracket separately, place the camera, secure its four screws while the bracket is off the robot, insert the complete module along the locating-peg axis, and finally secure the three bracket screws. Its `motionSource` explicitly identifies an authored web subassembly; retained source-film frames are references rather than the revised execution order. This is evidence for preassembly while access is open, not a reason to copy video frame order blindly. [Follower data](https://docs.robotis.com/interactive/omx/models/follower.json)

The same guide seats the drive jaw, fastens its two faces, and only then adds the opposing jaw. It pairs each opposing-jaw cap immediately with its retaining screw: labels `51a → 53 → 54 → 51b → 52a → 56 → 52b → 55`. This separates placing a loose component, retaining it, and closing access to it. [Follower data](https://docs.robotis.com/interactive/omx/models/follower.json)

For each local operation, record the actual parts present, the complete moving subassembly, the required screw or connector operation, its approach axis, and the next part that closes access. Add an explicit dependency from the access-dependent operation to that closure. A loose nested part needs a stated temporary support or retention action. Whole-module insertion must move all its retained parts and hardware together.

Review the dependency chain across build sections as well as inside each section. Head-electronics, camera, wiring, and final head closure share access even when separate tabs present them. Both legs need independent checks against their actual source poses; a mirrored label does not prove mirrored clearance.

Include joint pose in that state. When two steps appear to block each other, test whether opening an existing joint creates access without removing parts. Carry every attached component through the same rotation and check the entire angular path. In this review, opening the jaw and attached lower pad by 30° cleared the two front cap-screw shafts, while the fixed upper pad still blocked them. The resulting dependency is to leave the upper pad off, hold the jaw open for closure, and install the upper pad through the open mouth afterward. This measured access result does not establish the separate route used to install the jaw assembly.

## 2. Give every step a preparation, motion, and check

The official viewer has three phases: Prepare, Assemble, and Check. It provides work-face, reverse-face, assembly, and cable-end views. Fastener location numbers identify seated positions rather than specifying tightening order. Some underside views use a translucent base and explicitly describe that transparency as explanatory. [Viewer implementation](https://docs.robotis.com/interactive/omx/assets/index-BtI3oHfa.js), [leader data, label 05](https://docs.robotis.com/interactive/omx/models/leader.json)

Apply those distinctions locally:

- **Prepare:** identify the specific piece and fasteners, the reference orientation, and what must remain loose or open.
- **Assemble:** show a physically evaluated motion or explicitly show a static preparation/fit check when motion is unresolved. Keep already joined pieces rigidly together. The camera must expose the mating face without concealing surrounding obstacles.
- **Check:** give an observable result: seated faces, retained washer, engaged locating feature, every required screw installed, connector shoulders seated, or remaining joint freedom. Check completion before the access-closing step.

An exploded diagram is an identification aid. It must not be presented as an insertion path unless that path has been checked. Transparency and isolation improve inspection; the collision test still includes the actual obstacles present at that operation.

## 3. Evaluate the entire path and the tool corridor

This section is the local acceptance method derived from the reported failures, rather than a claim about ROBOTIS's internal validation process.

1. Bind the test to the actual source meshes, generated operation IDs, rendered transforms, and guide revision. Define the moving and stationary sets from the operation's cumulative state, including parts introduced in earlier sections where relevant.
2. Sample all segments and orientation changes from the initial prepared pose through the final seat. Test each moving solid against every applicable stationary solid. Preserve pairwise collision volumes and the first blocked frame. A valid start or final pose cannot accept the interior of a path.
3. Model the driver approach separately from the screw's final location. Use the actual outward screw axis and declared shaft diameter, length, and head-seat offset. Record handle/finger limitations separately. Check both sides of machine screws, including access to hold a nut. A screw visible through transparent geometry may still be impossible to tighten.
4. Specify allowable mating contacts per pair and stage. Do not globally ignore a part because its final fit includes contact, or subtract final overlap from every intermediate frame: either can hide traversal through that part. Preserve unresolved source interference as a fit checkpoint.
5. Run a negative control that restores the reported wrong sign, omits a member from the moving group, or restores closure before internal fastening. The test must fail for the original defect and pass for the corrected supported motion/order. A script that writes a report and exits successfully for collisions is an investigation, not an acceptance check.
6. Rebuild the actual entrypoint and inspect start, intermediate, and final states there, including pause and the slider. Verify that completion does not teleport to a prohibited seated state and that switching views preserves the same assembly state.

Audit the obstacle inventory itself. Start from the complete source assembly and subtract only components absent at the declared operation; record every exclusion and its dependency. A hand-picked list of "head parts" omitted the neck yaw fork in the 8 October curved-head investigation. Independent whole-source checking then found approximately 0.034 mm³ controller, 368.215 mm³ speaker and 63.616 mm³ amplifier intersections. The layout was withdrawn, repacked and retested against all retained structural source parts. An exclusion cannot be justified by a viewer hiding the object. Preserve that failed report as a regression case.

Also verify the shape being preserved against the actual original mesh, not the most recent redesign. A nearly unchanged bounding box hid a curved-to-rectangular cap conversion. Boolean added/removed volume and reference overlays exposed it. Shading checks should preserve every vertex and triangle; they cannot substitute for recovering the correct geometry.

Finite sampling reports sampled clearance at a stated interval. It does not establish continuous clearance, compliant insertion, or real printed fit. Digital acceptance and physical commissioning remain separate, and an unresolved path must remain visibly incomplete.

## 4. Route the cable before closing the route

The leader's labels `wiring-03-v022` and `wiring-04-v022` require the free plug to pass through three named openings, A (entry), B (middle), and C (exit), before both plugs are seated. Other TTL steps specify the endpoints and nominal cable length, keyed straight insertion, seated plugs, and a service loop clear of the joint. The follower converter steps additionally describe pushing the plug housing until its shoulder meets the socket mouth and avoiding pulling on the wires. [Leader data](https://docs.robotis.com/interactive/omx/models/leader.json), [follower data](https://docs.robotis.com/interactive/omx/models/follower.json)

The source data distinguishes nominal cable length from rendered free-centerline length and marks the latter as visual routing rather than a cut-length drawing. Its cable endpoint records include connector orientation, and route records identify the frame and opening coordinates. Adopt that specificity; a curve connecting two labels does not demonstrate that a connector can pass through the frame.

For each local cable, show the connector identity and orientation, endpoint pin/function, free-end threading order, intermediate openings or clips, slack near moving joints, and the closure deadline. Check the connector body against openings, not only the wire centerline. Seat connectors with power disconnected. Before closure, inspect the actual route at relevant joint limits for tension, rubbing, pinching, and obstruction of fasteners. Recheck continuity and polarity using the existing electrical procedure before power commissioning.

Keep locally distinct electrical nets distinct in the illustration. ROBOTIS's TTL cabling example teaches presentation and access sequencing; it does not replace MicroDuck's fused power-group, DATA-chain, or camera/IMU pin assignments.

### Flexible placement and conservative obstacle models

Treat a flexible cable route as one feasible placement, with hand-arranged slack and flat reinforced ends. It is not a rigid installation template. A search over a few fixed bends can reject that search family; it cannot establish that a printed enclosure must change. First locate the reported contact and distinguish actual solid geometry from a conservative receiving box. Refine only the implicated component region, preserve unknown dimensions explicitly, and keep the original failed check.

The 8 October head repair illustrates this distinction. A full-board component block produced 14.052 mm³ of reported overlap. Individual source-drawn component footprints reduced this to 1.599 mm³ under retained conservative height assumptions. A small local transition then cleared those same conservative receivers while preserving the complete 200 mm material length and both connector frames. The unchanged first 75 mm reused its source-bound results; only the altered material and affected closure pairs needed new checks. No additional printed part or board relocation was required. The final evidence is `../head-redesign-20261008/camera-ribbon-repair/fixed-pose-local-bend/full-ribbon-acceptance.json`.

Use swept bounding volumes to prove separation before expensive intersection tests. The final route needed detailed cap checking for only one of 148 moving entities. Inspect actual pinching, connector access, terminal straightness and slack storage; report assumed bend limits separately from measured physical endurance. Freeze the print package after these design checks, then reuse unchanged native plate exports rather than slicing them again.

## 5. Close each finding with evidence

Record each finding with the operation ID, obstruction pair or blocked tool axis, original failing state, corrected order or motion, quantitative readback, and fresh browser state from the user-facing guide. Include the full moving set and applicable earlier components so an isolated subassembly check cannot silently certify a later robot-level insertion.

Acceptance should report separate results for source identity, assembly dependencies, sampled part motion, tool access, cable route/closure dependencies, and visible behavior. Known geometry failures cannot be cleared by a disclaimer, while a documented physical checkpoint cannot be relabeled as an accepted rigid insertion.

The final handoff must identify any remaining physical fit or commissioning requirement. A digital assembly-guide review does not close the camera-guided pickup or learned-control project goal.

AI assistance was used to draft.

### Cross-module state and service corrections

A completed leg is a retained, off-robot subassembly until a later operation joins it to the torso. Do not equate “completed earlier” with “already fixed in final world coordinates.” Validate the intended moving subassembly and its fasteners against the parts physically present at that station. Conversely, limiting obstacles to `module.partKeys` misses power hardware that is already installed when the IMU arrives.

The 8 October follow-up tests both interpretations explicitly: moving the base between two fixed finished legs, and bringing each finished leg to a bench-built base. Both straight-route families fail around the closed torso rings. The resulting service sequence preserves each four-joint leg and temporarily releases only the two yaw-link case screws, one rear-center screw and four hip-yaw output screws per side. The small rear washer is removed before withdrawal. Install the power support last because fitting it earlier blocks the returning screwdriver corridors. These are source-bound service checks, not a claim that a closed ring can be forced over a larger captured end.

### Source dimensions before measurement requests

Resolve the exact purchased SKU and manufacturer revision before asking the owner to measure a component. The official Raspberry Pi PCN36 describes 16 mm and 11.5 mm bodies for the Standard–Mini camera cable; a hypothetical 5 mm ribbon cannot validate either. Standard–Standard and display-cable drawings are different products. Preserve absent specifications as absent, without transferring dimensions from a similar-looking product or naming an unobserved end-tab color.

### Availability is part of assembly acceptance

Keep the existing complete guide usable while revising a head candidate. A successful HEAD response is insufficient: the previous 3-second socket timeout returned HTTP200 but truncated a 31.9 MB body. Exercise a paused large response, compare full bytes, and open a non-head module in the user's Chrome after deployment. Use a distinct body-idle timeout and revalidated content caching; do not replace the user's Mac mini entry with a local file preview.

## Fastener and cable lessons — 8 October 2026

A washer is a real part with an insertion path and a receiving recess. A first screen that excluded the entire receiving lower link incorrectly accepted an OD5 washer. Including that link rejects it. Restrict intentional contact exclusions to the threaded receiver volume; keep its surrounding printed seat and walls in the obstacle set. For an OD4 alternative, distinguish unconstrained hole play from physically admissible flat seating; preserve the off-center collision as a negative control. A thickness calculation alone is insufficient.

The revised 1 mm seats are fresh-build geometry, not a disassembly procedure for the user's already force-fitted ankle. Existing-leg repair needs its own complete-leg sequence, retained screws and tool paths. The user confirmed M2×6; the exact eight positions come from the per-ID source rather than another user question. Stock availability is separate from a manufacturer dimension drawing.

The speaker's original line crossed the controller. Reorienting the amplifier and relieving the keeper yields a bounded static route, but prewired installation, terminal bodies, leads exiting GPIO sockets and joint slack remain independent checks. The guide's 51 illustrative electrical curves are not a mechanical route certificate. A connector receiver assumption cannot silently become a purchased connector dimension.
