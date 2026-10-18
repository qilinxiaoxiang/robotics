# Head wire route after the hands-on finding of 2026-10-14

Study folder, read-only on the guide sources. Nothing here is a print file or a guide change. Problem advanced: P5/P6
(wiring that survives the trained head motion). The decision for Shawn is at the end (section d).

**Shawn's observation (as built, evening of 2026-10-14):** eight wires come up from below (2 Pi power, 2 UART, 4 IMU).
Bringing them in on the right (-Y) side of the neck is awkward and fights head roll. He now brings them in at the
left-rear of the neck through the triangular pocket there. The lower orange clip inside the head looks wrong: the
bundle comes up and then folds back down. None of the four V1.9 clips is fitted today. The amplifier wires are still
to come.

**Short answer.** The pocket Shawn found is the widest way into the head (6.30 mm free, against 4.41 mm for the
designed slot); the 2026-10-12 route study measured it and set it aside only because the ID11-to-ID13 servo cable
already runs through it. The fold at the head clip has no jaw or clearance purpose: it is left over from fixing the
clip to the only free screw on the jaw-support base plate and then routing around the amplifier. The real cost of the
left-rear route is wire slack at the two pitch joints, because the as-built run is about 15 mm behind the pitch axes
where the designed clips sit on them: 36 mm of slack over the walking range instead of 19 mm. A third option keeps the
two lower clips on the axes and crosses behind the bracket into the pocket; its numbers are in section b.

Files: `clearances.json` (every number quoted here), `renders/compare_rearleft.png`, `renders/compare_top.png`,
`renders/compare_right.png` (release route in red, left-rear route in green, amplifier jumpers purple, head roll -25 /
0 / +25), `scratch/` (scripts, per-run logs, bounded-runner reports).

## a. The designed route, and why it goes right and folds down

**The route as released (V1.9, `guide/print/ext-v19/route-v19.json`, 33 points, 305.7 mm from the pack notch to the
gather point in front of the Pi header).**

1. The eight wires gather over the notch in the pack plate at the top-rear corner of the torso (-16, 3, 41).
2. They cross the torso top to the right (-Y) side and lie in the **torso clip** under S12-horn-025, on the right shell
   at (22.6 to 27.6, -23.9, 36). That screw is on the neck-pitch axis.
3. Straight up the right side of the neck into the **bracket clip** under S11-horn-040, on the -Y plate of the head-pitch
   bracket at (26, -21.1, 79.7 to 85.2). That screw is on the head-pitch axis.
4. Up the bracket plate to (26, -22.3, 95), then one free span across the yaw and roll joints to the right side of the
   floor opening of the lower head shell at (30, -27, 105).
5. Up the **-Y slot**, 4.41 mm wide between the head yaw link (a yaw-body part) and the jaw-support wall (a head part),
   to z 136.
6. Over the top of the jaw-support cross wall (wall top z 130.3), then **down into the head clip** channel (x 45.6 to
   52.6, y -25.3 to -18.1, z 115 to 124) under H-jaw_support-03, out of its +Y window at z 118.
7. **Back up** behind the Pi to z 137, across the head from y -17.5 to y +15, up to the **cap clip** over the Pi top edge at
   (62.6 to 68.5, 18, 148), down the front face of the Pi at (75, 25.5) to the gather point (77, 27.5, 115.5), and
   fan to pins 1, 2, 3, 5, 6, 8, 9, 10.

Guide text: `guide/content/steps.py` overview line 208, bracket clip 918 to 920, head clip 1064 to 1066, bundle run
1221 to 1256, cap clip 1179.

**Why the right side.** The neck-route study of 2026-10-12 (`guide/extension-20261012-neck-audio/neck-route/README.md`)
searched every way into the closed head. It found two: the -Y slot (4.41 mm at rest) and the +Y pocket behind the jaw
servo (6.30 mm, `corridors.json` entry-1, narrowest at (13.85, 12.65, 127.3) between the yaw link, ID15 and the jaw
support). It chose the -Y side for two reasons: the two lower clips could sit under existing screws that lie exactly on
the neck-pitch and head-pitch axes on that side, which makes the pitch joints cost almost no slack; and the +Y pocket
is already used by the ID11-to-ID13 servo cable (its route B, "not recommended"). So the designed route takes the
narrower of the two gaps on purpose, for the sake of the clip positions.

**Why it folds down through the head clip.** The head clip is the only anchor of the bundle on the head body. It had
to go under an existing screw, and the only free screw head on the jaw support is H-jaw_support-03 on the base plate at
z 113. So the clip channel sits at z 115 to 124, 12 to 20 mm below the slot top. The first in-head route (A2) went slot,
down to this clip, and forward over the Pi top edge to the header. When the amplifier took that space on 2026-10-13,
route A3 kept the clip and rerouted the stretch after it "back up behind the Pi, under the amplifier housings". That is
the fold: from the slot top (z 136) the bundle now drops 20 mm into the clip and climbs 20 mm out again. The detour
measures 56.3 mm where the straight line is 20.8 mm. What the fold does and does not do:

- It is **not** for jaw clearance. With the jaw swept 0 to 40 degrees at rest, the nearest the jaw comes to any
  head-fixed span of the designed route is 5.7 mm (at the fan in front of the header), and the head-clip stretch itself
  is more than 6 mm from it. The jaw pose-cap table (`guide/firmware/pi/jaw_pose_caps.json`) does not involve wires.
- It is **not** for the roll or yaw motion: all of it is on the head body.
- It **is** the head-body anchor. With it, the yaw and roll span ends at the floor opening, and the 17 mm of extra wire
  that a 40 mm cap lift needs (taut lower bound, `route-v19-motion.json`) lies behind the Pi rather than being pulled up
  through the slot. The A3 notes say "it turns back up there, so the clip holds the bend".

So the anchor is a real function; the shape is an artefact of the screw position plus the amplifier reroute. The same
anchor can be had without the fold (section c).

**The roll finding, reproduced on the model.** The slot is bounded by a yaw-body part on one side and a head part on
the other, so head roll closes it on one side. For the 1.7 mm group radius the release study assumed, the designed slot
leaves 0.2 mm at rest, squeezes the group from +2.5 degrees of roll on (against the yaw link) and from -5 degrees on
(the bracket-to-floor span against the ID13 case and the floor edge). The recorded walking frames use roll -21.4 to
+11.2 degrees. Numbers: `clearances.json` routes.designed.rollTable.

**Two guide inconsistencies met on the way.** The bundle step asks for spiral wrap of up to 5 mm outside diameter from
the pack notch to the head; a 5 mm wrap cannot pass a 4.41 mm slot, and the route study said the wires must go through
as a flat group. And the same step says "pitch, yaw and roll the head by hand ... never goes tight or rubs a horn",
which the roll numbers above contradict for the slot. Neither is changed here.

## b. The left-rear entry on the same geometry

**What the pocket is.** Looking down into the open head, behind ID15 and left of the neck: the free space between the
+Y face of the head yaw link (y 9.5, a yaw-body part), the rear face of ID15 (x 16.6, head) and the diagonal face of the
jaw support's left-rear block (head). The floor opening runs under it as a strip 3.5 mm wide at the floor plate
(y 9.5 to 13) that widens above the plate. Free width at rest: 6.9 mm under the floor beside the rear-left corner of the
pitch bracket at (13.6, 13, 98.8), 6.30 mm at the narrowest point inside at (13.85, 12.65, 127.3), 8.4 mm above z 131.
The ID11-to-ID13 servo cable comes down through the same pocket (centreline (13.8, 12.2, 127.3), the X3P cable is
about 3 mm across), which leaves about 3.3 mm for the eight wires: they must lie around it as a flat or loose group, not
in spiral wrap. That is the same condition the designed slot imposes.

**The route modelled** (`scratch/routes_candidates.json`, route `leftrear`, 212.9 mm from the pack notch to the gather
point): pack notch (-16, 3, 41); over the torso top at (-6, 10, 45); up the rear-left corner of the neck at (11, 13.5),
6 mm behind the ID12 and ID11 cases, from z 52 to z 90; past the rear-left corner of the bracket at (13.5, 13.5, 99); up
the +Y strip of the floor opening at (13.8, 12.7) from z 110 to the pocket at z 127; out of the pocket at (15, 16, 131);
forward over ID15 at y 19 (z 133.5 at x 22, z 135.5 at x 44), 4.5 mm beside the head-fixed ID15-to-ID14 servo cable;
then the release route's own approach to the cap clip, over the Pi top edge, down the Pi front to the gather point. The
in-head part from the pocket to the cap clip is a single rising run with no fold.

**Clearances** (model and conventions in `clearances.json`; negative means the 1.7 mm group is squeezed):

- *Head roll (the point of the exercise).* At rest the pocket leaves 1.5 mm around the group (slot: 0.2 mm). Rolling
  the crown to the right (negative roll) closes the pocket as it closes the slot: squeezed from -7.5 degrees on
  (slot: -5), -1.8 mm at -25. Rolling to the left (positive) the pocket stays open to +20 degrees (slot: squeezed from
  +2.5). Over the recorded walking roll range (-21.4 to +11.2) both routes get squeezed at the right-roll end; the
  pocket has 1.3 mm more room everywhere and is free over the whole left-roll side. Neither route is free over the
  full roll range as a 3.4 mm group; single wires lying side by side are what both gaps really take.
- *Head yaw.* Slack over the full +-170 sweep 26.5 mm (designed 38.8); over the hand-turning range with roll, +-80
  and +-25, 18.4 mm (designed 30.7). The pocket is closer to the yaw axis than the slot.
- *Pitch, the cost.* The run is 15 mm behind the neck-pitch and head-pitch axes instead of on them. Slack needed over
  the policy box 35.9 mm (designed 18.5), over the walking-frame box 35.9 mm (designed 19.4), over the beak-pickup set
  60.1 mm (designed 12.8), over the single-joint MJCF sweeps 33.0 mm (designed 38.8). The two spans that pay are pack
  notch to neck rear (9.5 mm over the policy box, 33 mm at neck pitch -90) and neck rear to bracket corner (18.4 mm
  over the policy box, 22.6 mm at head pitch +90). That slack has to be stowed as a loop behind the neck, where the
  designed route needs none.
- *Jaw.* Jaw sweep 0 to 40 degrees at rest: nearest head-fixed span 5.7 mm from the jaw. Over the pose sets
  the jaw reaches the neck run only in the extreme pickup posture (neck -90, head pitch +90, jaw 40), where it reaches
  the designed route too (-1.65 against -1.83) and where the jaw already hits the neck parts without any wires.
- *Speaker collar, retainer and amplifier posts.* The forward run passes at y 19, outside the retainer (y up to 17.8)
  and the amplifier (y up to 8.9). Clearances at rest for the 1.7 mm group: amplifier 8.8 mm, speaker retainer 9.3 mm,
  speaker 11.7 mm, speaker tape 14.0 mm, Pi board 1.9 mm (at the cap clip, as designed), camera board 6.4 mm. The
  tight spots are at the pocket exit: 0.5 mm to the jaw-support block and 0.9 mm over the top of ID15, so the run must
  rise as it leaves the pocket (the modelled line is a lower bound on how high it should go). The ID15-to-ID14 servo
  cable is 4.5 mm away; the ID11-to-ID13 cable shares the pocket (see above).
- *Yaw link and ID13 in the pocket.* Beyond the hand range (yaw -130 and more) the strip under the floor runs into the
  ID13 case, as the designed route's span does at -160.

**Bundle length.** 212.9 mm against 305.7 mm at rest from the pack notch to the gather point (93 mm less); with the
slack each needs over the walking box the left-rear route is still about 70 mm shorter per wire. The 56 mm in-head
detour is gone. The IMU lead (394 mm) and the two jumper chains (423 and 500 mm) have margin either way.

**Cap lift** (plugging the header with the cap held 40 mm up, step "cap-on"). Designed: 17 mm extra between the head
clip and the cap clip. Left-rear with no head anchor: 18.5 mm, pulled up through the pocket from the neck slack. With
a head anchor at x 22 on the ID15-to-ID14 cable (section c): 21.6 mm between that anchor and the cap clip.

**Hybrid: lower clips kept, cross behind the bracket** (`routes_candidates.json` route `hybrid`, 279.1 mm). Torso and
bracket clips as released on the -Y axes; from the top of the bracket clip the group goes round the back of the
bracket at (15, -14, 92) and (13.5, 2, 97), beside the ID11-to-ID13 cable, into the pocket and on as the left-rear
route. Slack: policy box 14.1 mm, walking box 14.9 mm, beak pickup 7.3 mm, MJCF sweeps
16.1 mm, yaw sweep 16.1 mm, roll with yaw 16.2 mm. Roll at rest 0.47 mm, squeezed from -7.5 degrees, free on
the positive side. Jaw sweep at rest 5.7 mm. It buys back the pitch slack at the price of an S-bend behind the
bracket that runs along the servo cable and crosses the yaw axis.

## c. Clips, retention and the amplifier wires

- **Torso clip (right shell).** Not used by the left-rear route; the bundle no longer crosses to the right. Used by the
  hybrid.
- **Bracket clip (-Y bracket plate).** Same.
- **Head clip (jaw-support base plate).** Not used by either; it is the fold. The designed route itself can lose it
  (option C below) if its anchor function is replaced.
- **Cap clip (over the Pi top edge, under E-pi-04).** Still useful for every route: it holds the crossing of the Pi
  top edge at y 18 and keeps the bundle off the Pi header area; the left-rear route arrives at the same point from
  behind.
- **New retention needed: one head-body anchor between the pocket and the cap clip.** Without it the yaw/roll motion
  and the cap lift pull the whole run through the pocket. The geometry does not force a printed part: the ID15-to-ID14
  servo cable is fixed to the head at both ends and runs at y 11 to 12, z 133, right beside the forward run; one small
  cable tie (or 25 mm of spiral wrap over both) at x 20 to 30 binds the eight wires to it. That is an inference, not
  tested on the robot. A printed tab would need a free screw head on the +Y side of the jaw support, and there is none:
  H-jaw_support-01 (6.6, 19) and -02 (49.1, 9.35) sit under the support's blocks. The design rule in the bundle step
  ("do not tie it to any neck link") is kept: the tie is head to head.
- **Below the head, left-rear route.** One tie at the pack notch as designed; the run up the back of the neck is free
  and needs its pitch slack as a loop behind ID11.
- **The five amplifier wires** (purple in the renders). From the amplifier's right-angle header the housings point
  forward along x 42 to 56.5 at z 143.8, y -7.6 to +7.6; the jumpers go over the Pi top edge at x 61 to 65 and down the
  Pi front to pins 4, 12, 34, 35 and 40. The two speaker leads go from the speaker to the amplifier terminal under the
  roof. All of this is on the cap side above z 137 and is the same for every route. In the designed route the bundle
  runs directly under the amplifier housings on its way back up; in the left-rear route it approaches at y 19, outside
  them, so the two groups meet only at the Pi top edge where the pin-4 and pin-12 jumpers (y 9 to 16 there) lie beside
  the bundle (y 18). Lay the jumpers on top of the bundle at the edge, as the cap step already says.

## d. Decision set for Shawn

**Option A. Left-rear route as built, no lower clips.** Pack notch tie, free run up the back-left of the neck, pocket,
forward over ID15, tie to the ID15-to-ID14 cable, cap clip. Shortest wires (about 90 mm less), no fold, no clips to
print or fit, 1.3 mm more room than the slot under roll and free on the left-roll side, better yaw numbers. Costs:
36 mm of pitch slack to stow behind the neck (designed 19), the loop is visible, the pocket is shared with the
ID11-to-ID13 cable, and the only anchors are a tie and the cap clip.

**Option B. Hybrid.** Torso and bracket clips on the -Y axes as released, cross behind the bracket, then as A. Pitch
slack back to 14.9 mm over the walking box with A's roll and yaw behaviour and no fold. Costs: two clips to fit
plus their longer screws, an S-bend behind the bracket beside the servo cable, 66 mm more wire than A.

**Option C. Designed route without the head clip.** Keep the -Y slot and both lower clips; from the slot top go
straight behind the Pi to the cap clip (the 20.8 mm line instead of the 56.3 mm fold), anchored with the same tie to
the ID15-to-ID14 cable. Keeps the lowest pitch slack (19 mm over the walking box) and the released guide below the head. Costs: the 4.41 mm
slot stays, with its roll squeeze from +2.5 and -5 degrees, which is the thing Shawn felt on the robot; the servo
cable on the right side still shares the bracket plate.

Not proposed: any new printed part, a wider slot, or a change to the jaw limit.

## Method and sources

- Geometry: current audit solids of every guide part (`guide/content/interference-audit` cache, robot frame mm), the
  V1.9 clips and cap-side parts, MuJoCo kinematics from `robot_allcollisions.xml` (`neck-route/nr_lib.py`). Joint
  ranges read from the MJCF: neck pitch -90 to +60, head pitch +-90, yaw +-170, roll +-25 degrees. Walking frame
  ranges from `route-v19-motion.json`. Roll sign: positive tilts the crown to the robot's left (+Y).
- Model: the taut straight-span model of `neck-route/motion.py` (points ride on their bodies; clearance is the exact
  distance from the span centreline to parts on other bodies minus 1.7 mm). On the designed route it reproduces the
  release numbers of `ext-v19/checks/route-v19-motion.json` to the decimal. A negative value on a span whose two ends
  ride on different bodies is the taut-line artefact the release accepted; a negative value on a head-to-head span is
  a real squeeze.
- Pose sets: policy box (162), beak pickup (54), each joint over its MJCF range (164), yaw sweep (35), roll sweep
  -25 to +25 by 2.5 degrees (21), roll with yaw +-80 (25), walking-frame box (81), jaw sweep 0 to 40 (9).
- Jobs ran through `run_bounded_cad.py` (reports in `scratch/runs/`), each under five minutes, after the V1.15
  release jobs. The jaw pose-cap study was not rerun.
- Inferences, not measured on the robot: the 1.7 mm group radius, the cable-tie anchor, the as-built point positions
  of Shawn's route (modelled from the free corridor, not from a photo).
