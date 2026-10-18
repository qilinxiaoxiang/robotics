# Rejected connection proposal — retained failure evidence

This proposal was rejected on 2026-10-09. It is not an active design decision. The user requires a fully enclosed head and repair of known wire collisions. Mac control/policy ownership did not authorize changing the internal Pi-to-OpenRB cable to an external rear USB route. Continue from [the active workflow](../WORKFLOW.md). The text below records the failed proposal only.

# Roof restoration and wiring review

Problems P0, P5 and P6. Decision date: 2026-10-09.

This native CAD review preserves the original body proportions and DFR1202 at the original battery location. It adopts the already specified Mac-control / Pi-sensor division for packaging: the Mac connects directly to the OpenRB USB-C port through the existing rear service aperture. The Pi's upward-facing USB/data port is unused in this configuration. Its camera remains on CSI; audio and sensor signals remain on the header. Restoring the crown therefore does not have to accommodate the old upward SC0727 adapter.

The [OpenRB manual](https://emanual.robotis.com/docs/en/parts/controller/openrb-150/) documents the factory USB-to-DYNAMIXEL bridge. The project already uses this direct Mac connection for commissioning. This selection extends that packaging arrangement to the proposed operational split; it does not claim that the combined Pi runtime has been migrated. Pi-to-OpenRB USB remains a historical runtime dependency, not an active cable in this CAD configuration. One host must own the bus at a time. Motor power remains separately supplied from the converter; the USB lead is not a substitute for motor power.

The [official SC0727 description](https://www.raspberrypi.com/products/micro-usb-male-to-usb-a-female-cable/) provides interfaces and an 80 mm cable length, but not a requirement for a head aperture or the assumed connector mould dimensions previously used to cut it. Both pages were checked on 2026-10-09. Original community cap geometry is bound by hash in `roof/roof-restoration.json`.

The crown repair adds only the corresponding original curved-shell material. It retains internal posts, speaker mounting features and the rear OpenRB service aperture. No external crown cover or flat patch is added.

The viewer and Fusion file are a staged design review. They contain named wires/connector geometry with endpoint and assumption records. They do not authorize the legacy combined Pi walking runtime with its USB connection absent. Hardware motion, current capacity of revised power branches, real cable slack and loaded timing require their own evidence. No existing released print files are replaced by this review.

Decision-changing evidence: an accepted operational requirement for a Pi-owned motor bus, an actual connector/closure conflict, an inaccessible rear USB route, or failed Mac serial/sensor timing. Such evidence changes the connection or mounting locally; it does not justify reintroducing an unbounded crown opening from an unverified plug box.


