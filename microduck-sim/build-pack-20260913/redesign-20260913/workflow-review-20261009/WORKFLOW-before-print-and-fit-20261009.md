# MicroDuck: design, assemble, then publish

## Prototype scope accepted by the user — 9 October

The user now explicitly accepts a practical incremental print-and-fit prototype and subsequent local adjustment. Detailed flexible-wire CAD, material simulation and individual conductor collision certificates are not prerequisites. The guide may show only real sockets/plugs, insertion direction, available openings, slack placement and cable-before-cover order. Check populated rigid parts and access; confirm soft-wire movement and pinch-free closure during the physical trial. This supersedes earlier whole-flexible-harness release requirements for a prototype, but does not label a prototype as fully commissioned or accept known rigid overlaps. Whole-project verification remains separate.

For the practical wiring instructions, [Prusa’s electronics assembly guide](https://help.prusa3d.com/wp-content/uploads/generated/original-prusa-i3-mk3s-kit-assembly_1128_guide_174100_en_2026-05-06.pdf), steps 13–21 and 37–39, is a concrete model: connect inaccessible motors before mounting the box, follow existing passages, leave slack and check the cover for pinched wires. The project adopts that level of detail; optional spline work is not a delivery gate.


Review date: 2026-10-09. Problems P5 (serviceable hardware), P6 (reliable deployment), and P0 (evidence that distinguishes a useful design from a convincing animation).

## Replication first — 9 October correction

The active task is adaptation of AI-FanGe's working MicroDuck to the user's actual components. Use the upstream revision and real assembly media as the baseline. Preserve the original structure unless a required component or demonstrated rigid access problem needs a local change. The primary problems remain P5/P6; P0 requires checks that discriminate real assembly defects from representation errors.

The overnight leg routing failed this purpose: loose conductors became separate rectangular spring shapes, and six virtual cable-tie receiving frames appeared as physical hardware. Those retention frames are withdrawn. They are neither print parts nor mandatory bought hardware. Original hip, thigh, ankle and foot geometry stays intact.

Source correction: the native fanhao375 XL330 v1.1 head CAD contains Zero 2 W plus RobotHAT; FanGe documents OpenRB plus Pi over USB. The -3° OpenRB pose in `head-redesign-20261008/curved-head/build_curved_layout.py:56` is our own packing search result. Matching the curved shell never established a matching electronics package. The existing `NATIVE-CAD-PROVENANCE.md` already recorded this difference; subsequent work failed to honor it. Treat actual FanGe assembly media as the next discriminating source before new head geometry.

Use the following order for the current correction:

1. Compare upstream hardware/assembly with our actual differences: first-generation Zero W with soldered header, eye camera, owned audio parts, and converter in the original battery location. Record each adopted deviation and its physical reason.
2. Fit the complete rigid head package, including actual plugs, before choosing board mounts. Assistant-designed positions and mounts remain adjustable. New adapters and internal supports are proposals until justified by this whole-package comparison.
3. For each subassembly, connect sockets while accessible, arrange an ordinary flexible bundle with gentle spare length, then close covers. Model only the critical passages and connector departures with a few smooth control points. Reserve physical fit checks for actual cable behavior; exact per-strand curve length and deformation are not release prerequisites.
4. Review the changed subassembly against the original appearance and real assembly actions. Run targeted rigid collision, tool-access and pinch checks. Diagnostic volume contact does not justify a reprint; identify the actual physical conflict first.
5. Export the same adopted configuration to the guide. Show plugs, relevant parts and adjustable soft-wire paths; exclude withdrawn helpers. Release only adopted incremental geometry, and keep physical fit/powered commissioning explicitly separate.

Do not resume the prior coordinate-by-coordinate head routing or bespoke connector search without a baseline difference that makes it necessary. An illustrated cable is an installation arrangement, not a forming jig. A failed rigid-path model must trigger a representation review before another geometry iteration.

Primary method references checked 2026-10-09: [AI-FanGe build tutorial](https://github.com/AI-FanGe/Microduck-build-tutorial), [Autodesk harness segments](https://help.autodesk.com/cloudhelp/2024/ENU/Inventor-Help/files/GUID-60FCFDE3-6170-4C7A-881B-90D4CB1733E5.htm), and [cables routed as a group](https://help.autodesk.com/cloudhelp/2024/ENU/Inventor-Help/files/GUID-0D4F436F-5246-4433-B273-9FEBC9555357.htm). These support the representation and workflow; they do not validate this robot's physical build.

## Current review boundary

The latest user decision withdraws the central clamped battery and widened frame because of appearance and future beak pickup. Restore the original body and leg spacing, placing the existing DFR1202 at the original battery location. C and its alternative layouts are historical only. The former C-selection statements below are superseded by this boundary.

The original-body Fusion archive has been saved and reopened with 161 source-bound mesh references and exact placement checks. In that restored baseline, the existing converter support and insert remain; reverting C itself introduces no new printed geometry. The later body-controller carrier is a separate, unadopted layout study. Local static/approach evidence is in `original-body-converter/`.

The 9 October roof-and-wiring review was rejected: its rear shell remained open and 11 of 15 neutral motor routes collided. The archived mesh file and its saved-file readback are diagnostic evidence only. The substitution of external Mac-to-OpenRB USB was not authorized by the Mac-control requirement. Preserve the internal Pi-to-OpenRB connection while repairing enclosure and connector placement. Crown and rear closure are separate geometric requirements; a watertight shell mesh can still contain a designed opening.

Known visible defects must be repaired before another review handoff. A complete local result may be reviewed only when it is useful on its own and does not imply unfinished integration passed. User decisions concern genuine tradeoffs, not whether to correct an existing collision. The active print baseline remains 1.4; no rejected design can inherit its acceptance.

## Why the previous process caused rework

The project already uses STEP solids and CadQuery, but the final head viewer, historical whole-body model, electrical ledger and assembly operations have different owning files. The old wiring generator attached cables to bounding-box centres. Its motor records explicitly said connector orientation was unverified. The leg viewer traversed the global wiring list, and the forty leg assembly operations omitted cable-before-closure dependencies. These facts explain the demonstrated errors without treating every screen-space collision as a physical defect.

The repair is to bind interfaces and operations to the same assembly revision. Changing software alone cannot supply a missing plug, cover deadline or joint constraint.

Two subsequent checks exposed incomplete scope, not a reason to add more numerical gates. The local head inventory omitted the intended head-mounted OpenRB, so its 90-part pass did not qualify the new Pi/audio mounts. The complete controller is now included before joint packaging. Separately, neutral-clear 180 mm leg curves projected 30–36 mm beyond the thigh as unsupported flat loops. Those routes require a practical soft bundle with adjustable slack; fixed geometric loops and virtual retention frames are withdrawn under the replication correction above. The assembly page must consume the same preplug deadlines as the wiring page, at the operation that closes access.

## One source model, several outputs

### Constraint ownership for head packaging

Preserve the user's original curved exterior, closed crown/rear shell, eye-camera appearance and original jaw/neck mechanisms. Internal Pi, OpenRB, amplifier and speaker positions selected during this repair are design variables until the **complete** populated package, plugs and mounting sequence agree. A locally clear speaker or Pi pose is not a user-imposed fixed position. Revisit their joint arrangement before declaring a cable purchase necessary. Use actual available layer height and connector departures to select a compact, staggered arrangement; do not keep rotating one board around an arbitrary earlier mount.

Identify the exact current community assembly before importing CAD. The archived microduck.step is an older humanoid and must not be presented as the current duck. Use the current source-bound duck meshes and transforms for unchanged references; use manufacturer solids and native editable geometry for new parts. Give each replaced part a stable component ID, source revision and transform. Keep original geometry, adopted changes and proposed changes in distinct configurations. Model bought boards with their connectors and populated sides; use manufacturer solids where available. Record deliberately approximate envelopes as such.

Maintain four linked records:

- **Mechanical assembly:** component instances, joint axes and limits, closed-loop linkage constraints, fasteners, load paths and mass assumptions.
- **Electrical connections:** exact ports and pins, voltage, current allocation, conductor size, bought cable SKU, source protection and return path. A connection has an electrical purpose independent of its 3D shape.
- **Harness geometry:** plug bodies, insertion axes, accessible grip space, routing supports, moving-joint slack and closure constraints. Cable length includes terminations and slack; an arbitrary drawn curve is not evidence of reach.
- **Assembly operations:** parts present, movable subassembly, connector insertion, screw/tool access, next closure and observable completion condition.

Export printable solids and tutorial meshes from the chosen mechanical revision. Export tutorial steps from the operation records. Record source hashes with each export; stale geometry cannot inherit current acceptance.

## Tools and their responsibilities

The documented industrial pattern is integrated mechanical/electrical design, then local validation and revision. For example, the vendor-published Westwood Robotics account describes its use of SOLIDWORKS Design and Simulation to check concepts before manufacture; this is a reported customer practice, not an independent benchmark or proof that the company uses a particular harness module. Autodesk's Cable & Harness documentation gives the concrete sequence used here: pinned parts and wire definitions, placed/constrained components, route segments through available spaces, wires attached to named connectors, then drawings and reports. Sources below checked on 2026-10-09.

Before fixing a harness around a catalogue item, distinguish actual received stock from kit contents, planned borrowing and proposals. The current official OMX sequence uses both 100 mm and 180 mm leads; select a suitable available nominal length before designing spare-length storage. SC0727 is not confirmed on hand, so its assumed body and the resulting USB-A coupling cannot silently become mandatory design requirements.

Start from the exact upstream assembly and manufacturer parts. The XL330 v1.1 source has now been registered against the current head. Fusion imports its SLDPRT cap as one solid with 13,588 planar faces: this is a faceted solid, not recovered analytical surfaces or feature history. Its location and shape match the current reference within export precision. Keep that distinction in subsequent edits and acceptance; the historical humanoid STEP and FT-motor revisions are not substitutes. Source receipts are in `enclosed-wiring-repair/head-layout/native-cad-provenance.json` and `enclosed-wiring-repair/native-shell-readback.json`.

**Fusion** is installed and signed in. Use actual solid components, joints, section views and interference analysis for rigid packaging; use component-referenced 3D sketches and Pipe/Sweep for the small local harness. Inspect connector approach before routing; define a passage through available spaces and retention points, then construct the cable within it. Move a support point or board within the accepted architecture to resolve the offending pair, regenerate the dependent route and recheck it. Importing STL references into F3D does not convert them to exact solids. Fusion's solid interference tool cannot certify an assembly with only mesh bodies; verify participating bodies and coverage. Preserve unchanged mesh references and use the existing valid mesh intersection checks when necessary instead of blindly converting the whole robot.

**Inventor Cable & Harness** and **SOLIDWORKS Routing/Electrical 3D** document the dedicated workflow: electrical endpoints, connector orientation, route segments, wire diameter and length, bend checks, drawings and manufacture. Neither suite is currently installed. Their capabilities are a method reference, not capabilities we can claim Fusion has. Do not build a custom route optimizer or flexible-material simulator to duplicate a missing module. If native small-harness authoring cannot meet a concrete requirement, identify the specific capability gap before choosing another tool.

**CadQuery** remains useful for parameterized adapters, exact bought-part envelopes, local geometry checks and STEP exports. Use established CAD operations; no new full-robot mesh pipeline. **MuJoCo** checks reachable robot poses with the original linkage constraints; a joint animation does not simulate physical wire deformation.

For ordinary flexible cable, model a plausible route with real end directions, diameter, available length, spare-length space, bend allowance and strain relief. Check rigid interference, pinch and endpoint motion in the relevant robot poses. Do not require an invented exact deformation proof to unblock unrelated rigid parts, or treat one failed curve family as evidence that a standard ribbon cannot fit. A local physical fit check resolves cable behavior that the CAD model cannot establish. This does not waive visible collisions or change cable dimensions.

The HTML guide consumes the reviewed assembly and operations. It is not the design source. Its existing builder must reject known failed or incomplete requirements for the proposed review scope; an internal diagnostic export is never a user acceptance artifact. The baseline design verifier and the current review check remain distinct, with explicit source bindings.

## Review stages and exit evidence

### A. Power and packaging

Continue the selected external-charger configuration, original body and original leg spacing, with DFR1202 in the original battery region. The withdrawn PB1033MI layouts are archived comparison evidence, not an active design branch. Model the populated boards and rigid plugs first, including space for mating the USB-A connection; then route flexible leads. Adjust mounts within the selected installation region while preserving the exterior and intended connections. Relocating OpenRB from the head into the torso changes the cross-neck harness and remains a proposal under the prior user restriction; local fit alone cannot adopt that layout. Use verified manufacturer dimensions; where these are unavailable, state a photo-derived envelope and a practical fit margin instead of letting an arbitrary oversized box force a shell redesign. Count actual motor and logic loads and document the existing distribution interface. Remove the external fuse array from the preferred concept, while identifying how source/converter protection matches the selected branches. Never use another robot's absence of visible fuses as an electrical rating.

**Review artifact:** the complete enclosed local assembly, dimensioned views and actual connection diagram. Present choices only if there is a genuine architecture or purchase tradeoff. **Exit:** rigid packaging, connector approach and mounting are checked for the selected architecture. This is not physical commissioning or a print release.

### B. One complete leg, assembled and wired

Choose one leg as a vertical slice. First inventory every required socket, register it to the motor CAD, and identify its insertion direction, grip space and access-closing operation. Order connections from those deadlines and free-end threading dependencies; the most buried connector is not automatically first. Preconnect while the required approach is open, route slack through intended openings, secure the moving-joint loop, and only then close access. Keep the controller-side end accessible until joining the torso. Include screw-driving and connector removal corridors.

**Review artifact:** one leg's native assembly, a cable list, and prepare/assemble/check animation derived from the same operations. **Exit:** every required connector has a registered socket and a checked complete housing/grip approach in its actual assembly state; no required insertion occurs after its access-closing operation. A missing socket registration or unchecked plugged-subassembly approach blocks acceptance of the complete leg, even when the dependency-order test passes. Individual completed local checks may be retained with their source bindings; unresolved physical fit remains separate from digital acceptance. For already built legs, first establish whether direct insertion is possible. Only a demonstrated obstruction justifies a specific local opening and its supported removal sequence; never infer a panel removal or whole-leg teardown from a schematic.

### C. Integrate and check motion

The active motor connection graph is `enclosed-wiring-repair/motor-wires/active-topology.json`: two physical OpenRB outlets, one branch ending at ID 1 and a second descending from ID 10 to ID 6. The old ID 1–6 edge is withdrawn because it directly couples separate ankles with cable. The four OpenRB outlets share the same bus; this change does not increase the documented aggregate port current rating. The source socket frames and physical cable direction must follow this graph, not a numeric-ID chain.

Mirror and check the second leg independently. Integrate torso, head, power and audio. Route nearby motors locally; bring each subsystem's harness to an accessible torso junction. The head still needs a supply/return path and any actual control/data connections across the neck. Route these along the structure with retention and a service loop instead of an unsupported diagonal between part centres. Camera power and images use the same CSI ribbon from the Pi.

Check reachable joint extremes, plug loads, pinch points, lid closure, screwdriver access and charger/disconnect access. Validate only affected component pairs first. A flexible ribbon gets a plausible adjustable slack arrangement and a physical closure check; a restricted mathematical curve family must not force a new head shell.

**Exit:** complete interconnect coverage, reachable motion checks, and a recoverable installation/removal sequence. A digital pass still requires bench verification.

### D. Small prototype, then incremental printing

If a critical interface remains uncertain, print the local bracket, fit gauge or connector access coupon that answers it. Do not slice every colour while a change can still alter those parts. After the relevant fit is accepted, produce only changed/new parts, grouped by colour and printer, using real flat first layers and ordinary available fasteners. Keep `zhengxia_` prefixes and the existing two-machine handoff format.

**Exit:** each file has a named purpose, version and affected baseline part. Preserve unchanged stock. A staged print is justified by an explicit experiment, not by unfinished integration hidden behind a release label.

### E. Commission and publish the accepted state

Test actual supply negotiation, voltage at endpoints, startup/current transients, reset behaviour and thermal operation. Then validate motion and camera/control timing. Keep the trained-policy and visual-pickup acceptance separate. Publish English public pages and the Mac mini guide from the same accepted revision. Verify the original leg-cabling entry, phase changes, pause/scrub, reverse view and endpoint views in Chrome.

## Speed controls

Run independent head packaging, torso wiring and leg installation branches in parallel with one integrator. Within a leg, give one owner both sockets, all exiting wires and the shared passage of each motor. The eight in-leg links must be accounted for together; six individually clear links cannot establish complete-leg acceptance. Head layout changes must not block work on unchanged leg sockets and covers. Retain unchanged knee/ankle evidence by source identity. Start with dimensions, joints and local access before full collision calculations. Cache results by input hashes and affected pairs. A head translation does not rerun unrelated feet. Keep the existing memory guard for geometry jobs; do not retain every full-scene pose. Full design verification belongs at an adopted hardware-plan handoff; draft concepts need their own bounded checks and cannot be labelled design-accepted.

Measure iteration time, changed/reprinted part count, discovered-before-print versus discovered-at-assembly defects, and reopen operations required by the guide. Preserve the existing failures as negative tests: global wiring in a leg module; a cable plugged after cover closure; stale head geometry; unsupported pin orientation; unreachable joint sampling; slicing a still-changing part.

## Official tool references

Verified 2026-10-09:

- [Fusion assembly joints and constraints](https://help.autodesk.com/cloudhelp/ENU/Fusion-Assemble/files/GUID-8818AE31-958A-4A59-989B-9875A174C67A.htm)
- [Fusion interference analysis during motion](https://www.autodesk.com/support/technical/article/caas/sfdcarticles/sfdcarticles/How-to-visualize-collisions-during-motion-with-the-Interference-command-using-joints-in-Fusion.html)
- [FreeCAD solid, parametric and assembly features](https://www.freecad.org/features.php?lang=eng_EN)
- [SOLIDWORKS electrical endpoints](https://help.solidworks.com/2024/english/swelec/r_swelec_set_origin_destination_cables.htm?id=0.35.5.3.0)
- [Inventor bend-radius checks and limitations](https://help.autodesk.com/cloudhelp/2025/ENU/Inventor-Help/files/GUID-F85EED4E-1A50-4A15-ACD7-B58DB6208064.htm)
- [Fusion interference checks solid bodies](https://help.autodesk.com/cloudhelp/ENU/Fusion-Model/files/SLD-INSPECT-TOOLS.htm)
- [ROBOTIS OMX guide, leader cable step 53](https://docs.robotis.com/docs/systems/omx/quick_start_guide/assembly_guide?model=leader&step=53&view=3d)



- [Autodesk documented Cable & Harness workflow](https://help.autodesk.com/cloudhelp/2025/ENU/Inventor-Help/files/GUID-D90EF17B-D6CD-4782-B528-7B7F3F3CC7F5.htm)
- [Westwood Robotics customer account: integrated design and simulation](https://www.solidworks.com/customer-story/westwood-robotics-delivers-reliable-humanoid-systems-faster/)
