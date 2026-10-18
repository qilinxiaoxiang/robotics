# Face for the Radxa Camera 13M 214 (A7Z head)

The face panel now carries the Radxa Camera 13M 214 (Sony IMX214) in place of the Camera Module 3 Wide. Only the back of the white face changes. The front of the face is unchanged (ray-cast comparison on a 1 mm grid: 0.000 mm deviation). The black eye trim is the V1.8 part, byte for byte, so the trim already on the robot can stay.

`build_face_a7z.py` rebuilds every file here from `../world/` and `../release-V1.8/manifest-V1.8.json`. It runs in about 9 seconds through the bounded CAD runner (command in the script header). It does not slice or release anything.

## Files

- `face_panel_a7z.stl` and `face_panel_a7z-print.stl`: the white face, in the robot frame and in the V1.8 print pose (front on the bed, bosses up).
- `eye_trim_a7z.stl` and `eye_trim_a7z-print.stl`: the black trim, identical to `world/eye_trim.stl`, in the robot frame and in the V1.8 print pose.
- `camera_13m214.stl`: the purchased camera as boxes. It includes the PCB with its holes, the lens holder, a 1.5 mm layer for the back components, the FPC connector on the lens side and a ribbon stub that folds back at y 33.
- `checks.json`: every number quoted below.
- `render-back.png`, `render-section.png`, `render-ribbon.png`: the back view, sections through the lens axis, and the ribbon exit.

## What changed against V1.8

- **Removed from the face back:** the four bearing lands and the two locating pegs used by the CM3 (75.8 mm³).
- **Added to the face back:** four round bosses, 4.8 mm across and 2.3 mm tall (x 77.8 to 80.1), under the four camera corner holes at y −14.09 / 13.91 and z 117.11 / 145.11. Each boss has a blind 1.7 mm pilot that stops 1.2 mm behind the face front. The camera PCB rests on the four boss tops.
- **Kept on the face:** the two 2.2 mm holes above and below the eye at (y −0.18, z 120.6 and 141.6). They now take the two screws that hold the eye trim.
- **Eye trim:** unchanged. Its two V1.8 pilots now take the trim screws from the face back.
- **Camera position:** the lens axis stays on the eye axis at y −0.09, z 131.11. The face eye hole, the trim bore and the CM3 lens agree to within 0.01 mm. The PCB front is at x 77.8 and the PCB back at x 76.2. The lens front is at x 84.18, which is 3.12 mm behind the CM3 lens front.

**Why the lens sits 3.1 mm further back.** The FPC connector is on the lens side of this board, at the edge, next to the lens. Radxa's two product photos show this (`a7z-head/sources/camera-13m-214-view.png` and `camera-13m-214-cubie-a7z.png`). The connector therefore sits between the PCB and the face back, so the PCB front must stay 2.3 mm behind the face back: 2.0 mm for the connector box plus 0.3 mm of air. The lens holder is a fixed 6.38 mm tall, which puts the lens front at x 84.18.

## Screws

All screws are self-tapping, threading into 1.7 mm printed pilots. No tip reaches an outside surface.

- **Camera, 4 × M2 × 4.** Driven from behind through the four plated corner holes into the face bosses. Thread engagement is 2.4 mm. The tip ends at x 80.2, with 1.2 mm of face plate left in front of it. Each head sits on the PCB back pad (x 74.6 to 76.2), 0.1 mm clear of the board-space box.
- **Eye trim, 2 × M2 × 6.** Driven from the face back through the two 2.2 mm face holes into the V1.8 trim pilots (x 81.3 to 87.0). Thread engagement is 4.7 mm. The tip ends at x 86.1, with 3.3 mm of trim left in front of it. Each head sits on the face back (x 78.5 to 80.1), 0.7 mm in front of the camera PCB, and is covered by the PCB once the camera is on.

**The corner screws do not reach the requested 3.5 mm of thread.** The 28 × 28 corner holes are 19.8 mm from the lens axis. The trim's outer radius is 15 mm, so the corners land on the 1.3 mm face plate. In front of the PCB there is only boss 2.3 mm plus plate 1.3 mm, 3.6 mm in total. Leaving the 1.2 mm minimum wall in front of the tip gives 2.4 mm of thread. The PCB cannot move further back, because its back components already end 0.2 mm from the board space. Four screws at 2.4 mm should hold a camera of a few grams, but this is below the target.

The two holes on the lens centreline would land inside the trim, as the V1.8 screws did. They measure about 1.8 mm on the Radxa drawing, which is too small for M2. The design does not use them.

## Assembly order

1. **Trim.** Press the black eye trim into the face from the front, as in V1.8. Turn the face over and drive the two M2 × 6 from the back, through the holes above and below the eye, into the trim. Stop when each head touches the face.
2. **Ribbon onto the camera.** With the camera loose, open the connector latch on the lens side, insert the 31-pin end of the 150 mm ribbon and close the latch.
3. **Camera onto the face.** Lay the face front down. Set the camera lens-first into the eye, with the connector edge towards the robot's left (+Y). Seen from behind with the face top away from you, that is your left hand. The PCB lies on the four bosses and covers the two trim screw heads. Drive the four M2 × 4 into the bosses and stop when each head touches the pad.
4. **Ribbon route.** The ribbon leaves the connector between the PCB and the face and runs flat along the face back towards +Y. At about y 33, before the cap screw boss at y 35, it folds back towards the board. Its 12 mm band (z 125 to 137) has no face or trim feature in the way.
5. **Face onto the head.** Lower the face unit straight down into the lower shell as in step `face-on`, then lead the ribbon along the left wall. The V1.8 step said the right wall.

## Key checks (`checks.json`)

- **Optics.** The full 78.4° diagonal cone, taken from a 1.0 mm pupil at the lens front, is not clipped. The nearest material is the trim bore lip at x 87.4, which is 2.77 mm off the cone surface: 3.57 mm radially, or 18.3° of spare angle. The face, cap, lower shell and jaw are each 12.5 mm or more away.
- **Image orientation.** With the connector edge on +Y, the image comes out turned 90°. Rotate it 90° clockwise, then confirm with one frame. In this orientation the 66.2° field is vertical.
- **Clearances in the installed pose.** No camera part overlaps any head part. The smallest gaps are:
  - Camera screw heads to the board space: 0.1 mm.
  - Back component layer to the board space: 0.2 mm.
  - Connector to the face back: 0.3 mm (designed).
  - Trim screw heads to the PCB: 0.7 mm.
  - Lens holder to the eye trim: 1.19 mm.
  - Ribbon fold to the cap boss: 1.65 mm.
  - PCB to the lower shell: 3.9 mm.
- **Face-on insertion.** Every rigid part was swept straight down from +40 mm. The minimum gaps are 3.5 mm to `head_bottom` (corner bosses) and 6.6 mm to `jaw_frame`.
- **Printability.** Both parts use the same print pose as V1.8. The face has 3.3 mm² of overhang steeper than 45°, against 7.9 mm² in V1.8. The boss wall is 1.55 mm and the pilot floor 1.2 mm.
- **Meshes.** All meshes are watertight. Volumes: face 4198.6 mm³ (V1.8 4130.0), trim 4213.1 mm³, camera model 3710.8 mm³.
- **Pre-existing overlap.** The face and `head_bottom` overlap by 0.154 mm³ in both V1.8 and A7Z. This is the existing seam and was not introduced here.

## Assumptions to confirm on the real board

- The connector is modelled 2.0 mm tall. Typical 0.3 mm flip-lock connectors are 0.9 to 1.2 mm, so the real gap should be larger.
- The pan-head screw head is modelled 1.6 mm tall.
- The back component layer is modelled 1.5 mm tall over the whole board, except 4 × 4 mm squares at the corner holes.
