# Internal USB interface — bounded negative result

This is a reversible engineering study of Pi → SC0727 → Adafruit4472 → the proposed torso OpenRB. It does not adopt that relocation, change printed parts, change joint limits, or replace the internal link with a Mac cable.

The native line/arc sweeps and receiving boxes are inspectable STEP/STL files. `candidate.json` retains their path primitives. `usb-interface-disposition.json` binds the source geometry, manufacturer drawing and all local results.

## Deciding evidence

- The first rear-neck arrangement requires 72.836 mm of flexible SC0727 wire and exactly 102.500 mm of flexible4472 wire. It fails the head floor and places the USB-A coupling against the USB-C mould. The known failures are retained; this is not a proposed assembly path.
- A head-fixed USB-A coupling avoids requiring the short SC0727 to span the moving neck. However, the original rigid-body baseline includes a collision-free neck-pitch−90° sample. In that sample, any cable tail inside the existing head and above its98.679 mm floor has worldX≥92.258 mm. The torso USB-C flexible tail hasX=−26.270 mm. Even the X-only separation is118.528 mm, exceeding the4472 nominal flexible length102.5 mm by16.028 mm before any bend or slack. This rejects a head-fixed coupling over that tested domain, independently of curve fitting.
- The checked full coupling receiving box,47.9×20×12 mm atX[-11,9],Y[-24,23.9],Z[137,149], intersects the original curved shell by1622.148 mm³. The25 mm SC female length and transverse receiving dimensions are assumptions, not measured manufacturer dimensions. This does not establish that a smaller actual female mould is impossible to fit. The4472 mould-and-relief axial length22.9 mm is from its drawing; metal insertion cannot be subtracted again from that plastic length.

The SC0727 official80 mm length lacks an endpoint definition. Treating all80 mm as flexible wire is not supported. The stock-length issue remains distinct from collision-free routing.

## Scope and stopping point

The result does not prove every intermediate or freely moving coupling topology impossible, and it does not certify that all XML angles are physically usable. It shows why the local positive controller-carrier assembly is insufficient to adopt the whole relocation with the presently specified head-fixed USB coupling. A different proven intermediate coupling, a different cable, or a physically established working range would be a separate decision. None is selected here.

Current Pi and amplifier+Y13 geometry were used. Original uncut body shells conservatively replace the proposed cut-only U-notch for screening; nonzero shell intersections are retained rather than claimed as actual modified-shell collisions. Body motion, changed FFC/audio routing and complete whole-harness acceptance are not inferred. Small named endpoint contacts are recorded separately from the large obstruction failures; no broad collision exemption was used.

All current geometry workers have exited. Successful bounded checks used approximately272–384 MiB. A shell STEP tessellation exceeded the512 MiB guard and was terminated, with no budget increase; the conservative original-shell screen avoids requiring that export. No Fusion UI or released files were changed.
