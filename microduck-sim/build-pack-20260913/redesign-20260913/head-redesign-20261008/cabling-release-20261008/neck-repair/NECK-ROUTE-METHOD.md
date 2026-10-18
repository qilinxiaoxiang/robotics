# Neck harness: continuous material paths

P5/P6 route acceptance must describe the same physical cable through joint motion. A route existing separately at every sampled pose does not show that the cable can move between those shapes.

The rejected shortest-arc family illustrates this: head yaw changes from −45.001° to −44.999°, but its direction-conditioning arc endpoint jumps64.0016mm. The normalized cross product changes sign when the tangents are antiparallel. All sampled self checks can miss this branch switch. See `short-family-continuity-failure.json`; source-bound negative regression is `check_short_family_continuity.py`.

Track fixed material arclength coordinates from one connector to the other. Check both position and tangent changes at neighboring angular poses, including analytical singular angles and paths between grid samples. Preserve connector identities and total length. Reordering point samples, relabeling segments or assigning a new shortest-rotation branch does not count as cable motion. Report interpolation/chord error separately from actual length change. A whole bundle centerline is a receiving-space model, not proof that each constituent wire has adequate length or can slide through a clamp.

The next family integrates an explicitly continuous unit tangent: joint angles gradually return to zero while a fixed135° turn is applied. Its55mm transition has exact analytical arclength and no antiparallel shortest-arc branch. At the previous singular angle, material-point displacement is0.00373mm for0.002° rather than64mm. This is a targeted algebraic repair; `continuous-tangent-preparation.json` remains unaccepted until self, obstacle and full angular-path checks complete.

Resource rule: load one source obstacle per guarded worker, at most two light workers under the shared guard. Input solids, output Boolean status, closed-mesh readback, source hashes and expected pose×obstacle coverage remain mandatory. Preserve every native-rigid-blocked value separately; neither those states nor unexecuted pairs are passes.

Keep previous failure artifacts. The raised shortest-arc candidate completed2740/2790 source-subset pairs, then stopped at native-clear pose158 with1.3825mm³ intersection against the neck-pitch ring. Its full-motion acceptance also fails the continuous-path regression. Neither increasing its length nor completing unrelated static pairs resolves that evidence.
