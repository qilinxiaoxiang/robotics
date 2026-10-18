# Option "hidden screw": one M2 x 10 from the cap back, both ears removed

**What changes.** Both ears go from the cap and both frame bosses and webs go from the frame, so nothing leaves the box
outline (outline check 0.0 mm). One M2 x 10 (stock) now holds the cap at the bottom. Screws: 16 (two cap M2 x 6 and
one 5991 M2 x 6 replaced by one M2 x 10). STLs: `../options/frame_hidden-world.stl`, `../options/lid_hidden-world.stl`,
`../options/screw_hidden-world.stl`.

**How it holds.** The 5991's upper +Y mounting hole is at (y +11.37, z -16.67), right behind the cap. Its own M2 x 6 is
left out. Instead a 5.6 mm column inside the cap runs from the cap back to x -55.1, just behind the USB-C socket. A
4.4 mm driver hole goes down the column to a 1.0 mm floor at x -56.1. The M2 x 10 sits on that floor, passes the
column floor, a 3.5 mm air gap and the 5991 PCB, and bites 3.9 mm into the existing 5991 boss (pilot to x -45.3,
unchanged). The column stops 3.5 mm short of the PCB on purpose, so the cap always seats on the rim first and the
screw then pulls the cap onto the rim. That screw stops the drop and the pull-out at the narrow tier; the top teeth do
the rest, as now.

**-Y complement: window hook.** The -Y lower corner is 27 mm from the screw, so it gets the same hook as the "delete"
option, in the top edge of the 5991 terminal window: a 1.2 mm tab at z -21.26..-20.06 with a 1.0 mm tooth that the lift
puts into a 1.1 x 1.2 mm notch in the frame. The terminal wires cross that wall at x -62.4 and -54.6, clear of the tab
at x -60.3..-57.4.

**Fitting.** Same path as now: slide the cap forward 1.2 mm low, lift 1.2 mm, then drive the M2 x 10 through the round
hole in the cap back (PH0/PH1 driver, shaft up to 4 mm). Before the cap goes on, the 5991 is held by its other three
screws.

**Clearances.** Column to the USB-C socket 0.2 mm while sliding low, 0.3 mm fitted; to the middle XL4015 1.6 mm; screw
to the USB-C socket 1.6 mm; every wire keeps 0.37 mm from the cap as released (the +Y wires stay above z -3.8).

**Print.** Cap rear face down: the column and its bore stand vertical; the floor at the top of the bore bridges about
1 mm around the 2.3 mm hole. The driver hole opens on the bed face. The frame loses only material.

**Cost.** A visible 4.4 mm round hole on the cap back beside the step (lower +Y view), one bottom screw instead of two,
and the 5991 corner at that hole is located by the screw shank but no longer clamped.
