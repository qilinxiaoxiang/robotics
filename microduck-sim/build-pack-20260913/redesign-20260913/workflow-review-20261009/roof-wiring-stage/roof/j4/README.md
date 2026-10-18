# OpenRB J4 power-wire entry registration

`terminal-registration.json` registers the actual two terminal cavities from connected component 65 of the current OpenRB mesh lineage. It does not use the board bounding-box center. The native CAD terminal matches the independently identified STEP solid 47 bounds, without loading the STEP assembly.

In current guide/world millimetres:

- GND, schematic J4 pin 2: [58.758633787, -1.71, 144.575117815].
- VIN+, schematic J4 pin 1: [58.758633787, +1.79, 144.575117815].
- Both insertion axes: [-0.998629535, 0, -0.052335956]; outward is the opposite direction.

The datum is the outermost terminal lip plane, native Y=-33.89. Native section Y=-33.3 establishes rectangular cavity openings 2.6 by 3.96 mm, with 3.5 mm center spacing. A 1.6 mm diameter shaft spanning native Y=-34.49 to -31.89 has zero intersection in each cavity. The same shaft aimed at the divider instead intersects 2.310145 mm³, retained as a negative control. This verifies wire entry, not the final clamped conductor depth, strip length, screw torque or screwdriver access.

Polarity is tied to the [official terminal-power illustration](https://emanual.robotis.com/assets/images/parts/controller/openrb-150/openrb-150_power_terminal_vin.png), visually inspected by the parent task on 2026-10-09: GND is on the VIN(DXL) jumper side. The mesh jumper is on native negative X, which maps to negative world Y. This avoids assuming that image up/down is a world coordinate. Physical operation has not been tested.

`current-mesh-binding.json` confirms exact float32 vertex-set correspondence and equal triangle count between the registered source and the current original-body manifest OpenRB, with zero additional transform. Topology provenance remains the source lineage; vertex equality alone is not presented as independent topology equivalence.

The orthographic and four section PNGs are derived from the actual extracted terminal. Reproduce extraction, sections, entry and source-binding through the existing head resource guard, then run `assign_polarity.py` to apply the recorded official-image mapping. Highest sampled worker RSS was 351 MiB; no full STEP import was used. No geometry in the main assembly was changed.
