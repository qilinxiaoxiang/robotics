# Removable MicroDuck ankle side: digital prototype

Problems P5/P6, checked 2026-10-07. This branch changes only candidate ankle parts. It does not overwrite the accepted robot, change motor addresses, send a print job, purchase hardware or energize a motor.

## Chosen mechanism

Keep the existing lower link, XL330, yellow foot, metal rear washer and original motor/foot fasteners. Replace each orange one-piece ankle with an orange base and a removable orange side; replace its black printed sleeve. Six replacement printed parts cover both legs. The base is derived from community66/64: the motor-output holes and foot interface keep their original locations. Two outer portions of the old passive side remain with the base, outside local |X|=11mm, providing support without crossing the20mm-wide lower/motor package's top-entry path.

The removable side closes along the shaft direction. Two straight tongues descend into open-top slots. Their nominal2.0/2.2mm widths leave0.1mm lateral clearance per side; matching flat faces set the other lateral position. This is a positional register, not an elastic snap latch. Two existing black **M2×8 TAP**, packet **PHS_M2X08_TAP_K**, pull those faces together. Their axes run transversely through raised side pillars; all newly added mounting material begins at localZ1.65mm, beyond the lower link's maximumZ1.3mm. The fasteners and their driver corridors avoid the existing foot. Machine-thread screws cannot substitute for these TAP pilots.

The old small printed part is a plain sleeve, not a modelled ball bearing. The replacement has OD14.6mm, ID10.4mm, width2.8mm and0.2mm entry chamfers. It can slide at both interfaces and is axially captured by the lower flange and the original side lip. It is not glued or claimed to be fixed to the link.

## Why this option

Increasing the sleeve bore alone removes the inner interference but leaves the original fork blocking the preassembled link/motor. The original top-entry route has about78.8mm³ peak material intersection in the finite replay, and its9.65mm sleeve overlaps the10mm boss by about14.96mm³ in the final pose.

An initial split with axial screws below the joint was rejected: the new mounts and screw heads entered the retained yellow foot. The independent negative fixture is retained as `independent-foot-rejection-v5.json`; those obsolete parts are not the current manufacturing STL. The selected raised transverse mounting uses the old outer support geometry and keeps new hardware outside both the lower-link axial slab and the foot's upper envelope. It also avoids large outboard wings.

## Assembly order

1. Fit the existing lower link to the bare motor on the bench. Install its two original M2×10 TAP case screws.
2. Place the original0.5mm metal rear washer, then retain it with the original M2.6×8 TAP rear screw.
3. Slide the new black sleeve over the lower-link boss.
4. With the orange removable side off, bring this complete package into the open base from above.
5. Start the four original M2×4 TAP output screws loosely.
6. Slide the removable side down its two open-top guides. Confirm complete seating without force.
7. Install its two black M2×8 TAP screws. Seat evenly, then finish the original output screws and check the case/rear retainers.
8. Reuse the original foot and its M2×6 TAP retaining screw. The main guide supplies its detailed original interface instructions.

The preview preserves the actual washer mesh as `washer6`/`washer1` and shows placing it separately from the printed sleeve. No simulated robot-motion command is issued. Fasteners drawn as cylinders are installation envelopes, not an explicit thread model.

## Screw stack and access

Candidate shaft coordinates are localX±12, Z4.5. The head bearing plane isY6; the M2×8 tip isY−2. The cap has4mm clamped thickness, followed by0.5mm of open register channel before actual base pilot entryY1.5. Thread entry is therefore3.5mm. The blindØ1.6 pilot ends atY−2.5, leaving0.5mm ahead of the tip and2mm of back wall toY−4.5. The cap clearance isØ2.3.

The rectangular host gives at least1.2mm nominal lateral wall outside the pilot; about1.0mm remains after a2mm outside thread. This is not a four-wall, reliable locking-torque or load-capacity certification. Use hand snug assembly and measure actual printed pilot fit before a load trial. The modeled head envelope isØ4×1.72; the driver corridor isØ3.5 and15mm long. Actual head/driver clearance and continuous annular head-seat/pilot material are checked in `geometry-evidence.json`, and independently in the verification report.

## Fit tradeoff

The actual source boss is approximately9.985–10.006mm, and the source pocket approximately14.980–15.006mm. The new sleeve's nominal inner diametral clearance is about0.4mm; its outer diametral clearance remains about0.4mm. Combined support-side radial float is therefore approximately0.4mm. This favours assembly over minimal backlash; it is not an FFF tolerance guarantee or a stiffness measurement. Bore10.2 and10.3mm would reduce play but provide less allowance for an undersized printed hole; these are analysed dimension alternatives, not extra interchangeable files hidden in the package.

Thirty-two source rays find the negative axial stop atZ−1.698005 and the positive lip atZ1.499932. With a2.8mm-wide sleeve, nominal axial endplay is approximately0.397937mm,0.2mm more than the old3mm sleeve. The chamfer leaves a narrow flat end-contact band near the original lip; wear and axial retention under real loads need inspection. A sleeve that moves smoothly on the bench is not proof of loaded joint performance.

## Digital checks and limits

The own finite geometry check replays the blocked original route, tests121 complete-package approach positions,49 sleeve and side-closure positions,129 retained-foot approach positions, the new head/driver/seat/pilot envelopes and every integer degree from−90 to+90 for **added material and hardware**. New sleeve/boss overlap is zero. The left package approach is zero; the right retains the original0.00093mm-thick source mating-face contact, with about0.137mm³ volume, so it is not labelled a strict zero-intersection route.

The small residuals below1e−5mm³ in differences between the source and exported manufacturing meshes are float serialization/Boolean residuals, not a claimed physical clearance. Original ankle/foot contact of about0.195/0.288mm³ is preserved, while the new mounts and heads do not add a material obstruction.

The source simulation specifies±90°, but the original assembled foot/body already hits the properly separated stationary motor case near the extremes. Independent source sampling finds clear poses through±70° and collisions by±75°. This prototype does not certify a full±90° joint or change the controller limits. The new geometry is compared against the original at those poses; output horn and case must be assigned to the correct moving and stationary groups.

Print-facing checks are in the independent print review. The selected base trial puts left local+X/right local−X against the bed; the sleeve uses an axial end. The removable side has **no accepted print orientation**: its +Z-down trial leaves a broad surface floating4.1mm, while sideways choices create bearing-ceiling tradeoffs. It is **not print-ready** and needs a native slicing/support and actual finish check before manufacturing. The raised pillar/tab planes are now at localZ7.1; old flat-Z3 or circular-peg claims do not apply. The original base's inner motor mating face is opposite its exterior output screw seats, so both cannot be upward in one orientation. Small transverse pilots/clearances also need actual printed hole and support-removal checks. No physical surface finish, fit, thread strength or bending stiffness is verified.

## Geometry and CAD identity

`candidate-manifest.json` and `preview-data.json` bind the manufacturing STL, unchanged source3MF, manufacturer STEP, original FK XML, per-source mesh payloads and transforms. Local candidate coordinates use the exact motor shaft line; their world matrices reproduce the original assembled pose. The original source geometry is tessellated. The editable generator preserves that imported geometry instead of inventing analytic source surfaces. Exported STEP files, when listed in `cad-export.json`, are checked closed faceted BREP models of the current STL. Any numerical welding used for STEP sewing is documented there; the manufacturing STL remains unchanged.

Digital prototype acceptance remains separate from printed assembly, calibration, ground contact, wiring, electrical commissioning and camera-guided pickup.

A strict connected-solid readback found a four-triangle zero-volume CSG skin on the left side. Float32 STL serialization gave it a tiny apparent volume of4.6871e−7mm³. The generator now removes only sub1e−5mm³ disconnected components and records this in `evidence/mesh-component-cleanup.json`; the final printed-part outputs retain exactly one solid each. This cleanup changes no intentional dimension.
