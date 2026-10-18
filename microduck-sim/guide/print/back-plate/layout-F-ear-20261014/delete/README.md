# Option "delete": remove the +Y ear, add a slot hook

**What changes.** The +Y ear at (y +23.8, z -33.6) goes from the cap, and its frame boss and web go from the frame. The
-Y ear (y -23.8, z -17.4) and both top tongues stay. Complement: a small slot hook on the +Y side (below). Screws: 17
(one M2 x 6 fewer). STLs: `../options/frame_delete-world.stl`, `../options/lid_delete-world.stl`; without the hook:
`*_delete_plain-world.stl`.

**Does the cap stay on with three fixings?** Yes. Seen as a rigid part, one screw plus the two toothed tongues pins it
completely: the screw stops it dropping, the teeth in their slots stop it pulling out and twisting. Turning the cap
about the -Y screw so the +Y tooth drops out would also slide both teeth sideways by 1.2 times the drop; the slots allow
0.2 mm sideways, so the +Y tooth can drop at most about 0.17 mm (about 0.35 mm with 0.2 mm print slop) against a
1.0 mm tooth. It stays lifted.

**What holds the +Y lower corner.** Only the stiffness of the 1.2 mm cap shell, spanning about 39 mm from the -Y screw.
The rim only stops the cap moving inward. Estimate for a 2 N outward push at the +Y bottom corner (y +15.6, z -36):
lower band of the cap as a 39.4 mm cantilever from the screw (back face strip 20 mm tall plus the 8 mm deep step
wall, I about 130 mm4, PLA E about 3 GPa) bends about 0.1 mm; the twist from the 20 mm offset, with the walls resisting
warping, adds about 0.15 mm; the narrow part itself adds about 0.01 mm. About 0.3 mm in all, plausibly 0.15 to 0.6 mm
given the crude model and the flexible ear flange. No wire presses there (the lowest +Y wire is at z -3.8 and every
wire keeps 0.37 mm from the cap), so in use the risk is not a load but the seam: nothing pulls that corner onto the
rim, so a cap printed with the usual 0.2 to 0.5 mm bow would show that bow as an open seam at the +Y bottom corner.

**Complement: slot hook.** The cap side wall continues 1.7 mm forward into the rear end of the USB-C slot (it already
closes that end), as a 1.2 mm tab just under the slot's top edge (z -18.36..-17.16) with a 1.0 mm tooth on top
(x -58.2..-57.4). The frame gets a 1.1 x 1.2 mm notch in the slot's top edge. The cap slides in 1.2 mm low, so the tooth
passes under the edge, and the final 1.2 mm lift puts the tooth into the notch. That holds the narrow tier's +Y side
in x at z -17, and the 19 mm below it is stiff (about 0.01 mm under 2 N). The tab stays inside the wall and 0.4 mm
behind the USB-C plug envelope; from outside it reads as the cap colour filling the slot's rear corner.

**Fitting.** Unchanged: slide the cap forward 1.2 mm low until it meets the rim, lift it 1.2 mm, drive the one M2 x 6
into the -Y ear.

**Print.** Frame: the notch roof is a 1.2 mm bridge (rim down). Cap: the tab stands 1.7 mm up from the rim (rear face
down) and its tooth overhangs 1.0 mm sideways, printable without support.

**Limit.** The -Y lug stays, 4.7 mm under the step.
