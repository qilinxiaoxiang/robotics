# Native local station: motor4–3 and motor8–9

The failed rearward route crossed the orange thigh back wall and the knee motor. Sections of the unchanged source geometry identify an existing route along the knee motor's lower edge, returning toward the open edge before continuing to the hip. The new route changes wires only.

## Current geometric result

- Three separate Ø1.5 mm receiving conductors, each 180.000 mm centreline length, at each station. This is nominal-stock accommodation, not a measured stock-length tolerance.
- Exact circular arcs: R2 mm inside the restricted connector/cover region, R4 mm around the exterior service loop. The local receiving assumption is explicit; an actual cable minimum radius is not claimed.
- Registered connector-axis departure and arrival, tangent line/arc transitions. No Catmull-Rom or fitted interpolating spline.
- Both stations independently checked against the unchanged source obstacle inventory. AABB-disjoint objects are culled; all eight nearby solid obstacles per strand are checked without deleting the thigh, plate or motor. Zero intersections for the six conductors and six within-station conductor pairs.
- Minimum measured receiving-mesh clearance is 0.5405 mm to the knee motor and 0.9395 mm to the thigh. This is a digital neutral-pose result.
- Forty-eight conservative nearby fastener boxes also clear. These include long shaft and head/seat allowances, not an omission of the retained hardware.
- The first exterior detour failed against the hip and thigh, and had conductor overlaps; `local-route-negative-outer.json` retains that negative case. The previous frozen route has about 28.36 mm³ maximum conductor intersection with motor3/motor8.

## Fusion execution

Root owns the Fusion UI. Execute `FusionLocalMotorRoute.py` through the existing Python.Run route. It creates a new document. It imports the registered manufacturer STEP for the two motors, complete catalogue receiving housings, and six unchanged local printed/ring mesh references. The meshes stay explicitly labelled as meshes; they are not silently certified by a native BRep-only interference query.

The script creates named editable 3D line/arc sketches, tangent constraints where supported, radius annotations and circular Sweep bodies. It checks native curve endpoints, lengths and radii against the source-bound candidate. Native creation failures produce `FAILED_NOT_ACCEPTED` in `fusion-native-readback.json`; no mesh fallback replaces a failed Sweep. Successful creation exports a local F3D review document. That creation is not automatically full wiring acceptance.

`local-route.json` is the right station; `mirror-route.json` is the independently checked left station. The latter reverses the mirrored path to match actual motor8→9 endpoints. A metadata correction to its non-operative control-point list is recorded in `mirror-metadata-correction.json`; operative primitives and STL hashes were unchanged.

## Assembly and remaining limits

Pre-seat the knee plug before enclosing it behind the orange thigh. Existing source registration demonstrates that the post-closure straight plug approach is obstructed; the black plate is not the offending cover. The whole new prewired motor/lead installation has not yet been checked, so the earlier housing-only insertion result is not promoted to whole-harness acceptance.

The exterior service loop now accounts for the full nominal length, but its retention is not qualified. The current exact receiving route occupies world X up to 49.63 mm, Y −68.56…−24.74 mm on the right (mirrored on the left), Z −34.86…−8.74 mm. Do not present a free loop as a fixed installed route, invent a stock tie or anchor, or add a new printed bracket without reviewing that specific attachment. Native review can examine a reversible tie to an existing leg structure; its wrap path and joint allowance still need checking.

No new print geometry, robot width, electrical topology, published guide or physical machine was changed. Whole-harness acceptance remains false pending retention, insertion/closure, applicable joint motion and actual stock bend/diameter/terminal confirmation.
