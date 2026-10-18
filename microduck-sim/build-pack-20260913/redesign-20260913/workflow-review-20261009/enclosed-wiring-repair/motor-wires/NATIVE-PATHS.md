# Native authoring inputs for six repaired leg cables

`leg-centerlines.json` is the authoring input. It contains 18 ordered conductor curves in millimetres, radius 0.75 mm, alongside `leg-local-manifest.json`'s independently checked receiving meshes. Import curves and make native circular Sweeps; do not convert the tube mesh triangles into faceted BReps.

Knee and ankle paths use `ordered-world-line-arc-v1`: line start/end and circular arc start/mid/end are already in traversal order and world coordinates. The left knee source was recorded 8→9; the exported authoring curve is explicitly reversed for the active 9→8 traversal. Reversal changes neither physical geometry nor electrical pin order. Use shared SketchPoints or merge consecutive ends, then `component.features.createPath(collection, False)`; check entity count and native length rather than assuming coordinate coincidence means topological connectivity. `FusionResumeMotorRoute.py` is the successful local API reference, not the initial failed `FusionLocalMotorRoute.py`.

Hip paths use `ordered-line-arc-analytic-helix-bezier-v1`. Their first line/arc primitives are followed by one smooth-pitch helix, one cubic Bezier and the last line. Apply `canonicalToWorld` to every point. This is a reflection in Y for the left route, so an arc normal transforms as a pseudovector; using start/mid/end avoids silently reversing an arc.

For the helix, let φ range from 0 to `sweepRadians` (L), δ=`pitchRampRadians`, h=`pitchMm`/(2π), r=`radiusMm`, c=`centerXY`, z₀=`startZMm`. The exact centreline is:

- x=cₓ+r cosφ; y=cᵧ−r sinφ; z=z₀−h I(φ).
- For 0≤φ<δ: I=φ/2−δ sin(πφ/δ)/(2π).
- For δ≤φ≤L−δ: I=φ−δ/2.
- For L−δ<φ≤L, put u=φ−(L−δ): I=L−1.5δ+u/2+δ sin(πu/δ)/(2π).

The raised-cosine pitch ramp gives a horizontal tangent at both ends. The cubic Bezier has four ordered control points and uses the ordinary Bernstein basis. These are editable analytic definitions, not hand-drawn curve guesses. Standard native CAD curve fitting may approximate the helix; record its approximation tolerance and actual total path length. Do not certify it by silently replacing a failed native Sweep with the checked STL. `worldSamples` provide a comparison/reference and a bounded curve-fit input, not permission to alter topology or overshoot into the housing.

The receiving STL's radius includes a small circumscribed polygon allowance; a native Ø1.5 mm circular Sweep lies within that receiving cross-section when its centreline is reproduced accurately. Any fitted native centreline must be compared against the bound before inheriting static clearance. The manufacturer's actual minimum bend radius, strand length tolerance and fatigue life remain unverified.
