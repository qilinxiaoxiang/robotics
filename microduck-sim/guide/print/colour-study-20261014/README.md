# MicroDuck colour study (2026-10-14)

Renders only. No CAD, print file or guide changed, and no print gate ran.

**Recommendation: option E.** Print the side shells and the head cap in white and keep the legs as they are. E is the only option that changes no part outside the V2.0 reprint set, so it adds no reprint beyond what V2.0 already needs. Open `renders/compare-all.png` first.

## Compare sheets

- `renders/compare-all.png`: all five options in rows of front 3/4, rear 3/4 and right side.
- `renders/compare-front34.png`, `renders/compare-rear34.png`, `renders/compare-side.png`: one view per sheet.
- `renders/option-A.png` to `renders/option-E.png`: the three views of one option.

## As built

The robot today is mostly orange. Shells, thighs, hip brackets, ankle brackets, neck links, rear pack and head cap are orange. The beak (lower head shell and jaw frame) and both feet are yellow. Every structural link and ring, the eye trim and the head-pitch bracket are black, and so are the 15 XL330 servos, which make up the largest dark area. The face panel is the only white part.

The converter box (frame and lid) is released orange in V1.11 but has not been printed. Until it is, the V1.8 black pack cover closes the back. `colour_as_built.json` gives the colour, source quote and slicer grams for each part.

Where the facts come from:

- **Stock parts:** the 10/1 batch. Original plate 1 was printed orange and plate 5 black (`build-pack-20260913/redesign-20260913/printing/COLOR-PLAN.md`). The other 61 instances went into four single-colour jobs (`04-FOUR-COLOR-20260929/color-layout.json`). The part to file to plate mapping is in `color-analysis-20260929/original-current-colors.json`.
- **Our prints:** the `color` field in `release-V1.6-final/final-V1.6.json` and in `release-V1.8`, `release-V1.9` and `release-V1.11` `scripts/rows.json`. The guide viewer colours are display colours, so this study does not use them.
- **Grams:** `object_grams.py` sums each object's extrusion in the released Elegoo G-code and scales the sum to the slicer header total. The output is `object_grams.json`.
- **Filament on hand:** no parts sheet, manifest or memory file records it. Every release has printed all four colours at the club, so all four exist there. The quantities are unknown.

## Options and reprint cost

All costs are in white PLA. `reprint_cost.json` has the full list. Under any option, the old orange parts become spares.

- **A, as built:** nothing to reprint.
- **B, white side shells and thighs:** 4 parts, 38.65 g. These are the left shell (14.51 g), the right shell (14.20 g) and both thigh bodies (4.97 g each).
  - Each thigh holds the hip-pitch and knee servos ("two motor seats", `full-build-data-current.json`). Replacing the thighs means taking both legs apart.
- **C, white shells, thighs and head cap:** 5 parts, 84.61 g. This is B plus the head cap (45.96 g, V1.9 cap).
- **D, white head cap only:** 1 part, 45.96 g. The cap comes off with three screws.
- **E, white shells and head cap, legs as built:** 3 parts, 74.67 g. The shells come off as described in the guide's torso chapter.

How the cost relates to V2.0 and future prints:

- **V2.0 overlap:** `v20-source/` already revises both shells (screw to the pack, filled tunnels) and the head cap (M2 pilots). Once V2.0 is released, those three parts are reprinted anyway.
  - Their colour costs nothing extra in D and E.
  - B and C add only the two thighs, but those require the legs to come apart.
- **Future prints:** the converter box is unprinted, so its colour is free in every option. It stays orange here.

## Why E

- **Contrast:** in A, the white face is a single patch on an orange robot. E adds white at the two places a viewer looks: the head and the torso.
  - The black eye trim on a white face and cap still reads clearly.
  - The yellow beak stands out more against white than against orange.
  - The orange hips, ankles and rear box frame the white torso, and the black servos separate the colour blocks.
- **Dirt:** white shows scuffs and finger grime. E keeps white off the parts that hit the floor in falls (thighs, ankles, feet) and off the box Shawn opens. The shells and cap do get handled when he lifts the robot, so E is not grime-free.
  - B and C put white on the thighs, at knee height, where falls scuff first.
- **The face:** with an orange cap (A, B), the white face reads as a separate visor. With a white cap (C, D, E), it blends into the head. The eye then becomes the only face feature, which suits a duck.
  - If Shawn prefers the visor look, B is the version to choose.
- **Print count:** E is one White plate of three parts, all already in the V2.0 set, with no leg work. D is the cheapest trial of white on the head, but on its own it leaves the body all orange.

## Method

- **Renderer:** `render_colour.py` extends `../back-plate/layout-D-20261014/render_scene.py` with three spec keys: recolour MJCF meshes, hide MJCF meshes, and attach a mesh to a body.
  - Same model, HOME pose with feet flat, and free camera.
  - Each option took 3 to 8 s under `run_bounded_cad.py`.
- **Head:** the community head shells are replaced by the printed head STLs: `world/head_cap.stl` (V1.9), `head_bottom.stl`, `jaw_frame.stl`, `face_panel.stl`, `eye_trim.stl` and `camera_board.stl`. They are attached to the `jaw_soft` body at its q0 pose.
  - At q0, the community head meshes and these STLs have the same trunk-frame bounds to within 0.1 mm, except where V1.8 changed the shape. So the attached head follows the neck and head joints to HOME.
- **Rest of the robot:** the legs, neck and torso use the community MJCF meshes, which are the stock prints. The converter box and boards are the layout F world STLs.
- **Removed placeholders:** `render_scene.py` drops the `power_support` and `np_f970` placeholders by geom name, but those geoms have no name, so they stay in its renders. Here they are dropped by mesh name.
- **Colours:** swatches are plain PLA approximations. The floor and sky are the model's defaults.
- **Not rendered:** wires, the IMU and the small V1.9 clips are left out.

## Rebuild

```
python3 build_colour_json.py          # colour_as_built.json (needs object_grams.json)
python3 object_grams.py <gcode...>    # object_grams.json (inputs listed in that file)
python3 make_specs.py                 # spec-A..E.json
python3 run_bounded_cad.py ... -- ~/.venvs/microduck-dyn/bin/python render_colour.py spec-X.json
./compose_sheets.sh                   # renders/compare-*.png, renders/option-*.png
python3 reprint_cost.py               # reprint_cost.json
```
