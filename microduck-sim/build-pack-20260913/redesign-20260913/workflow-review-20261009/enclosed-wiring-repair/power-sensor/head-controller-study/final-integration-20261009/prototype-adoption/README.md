# Head fit prototype: three Orange pieces

The trial set contains one integrated head cap, one speaker cradle and one speaker keeper. Use `head-cap-prototype-print.stl` and the two existing speaker print meshes referenced in `prototype-adoption.json`. All three are Orange to preserve the V1.4 color grouping.

The cap replaces confirmed stock ID4 and the V1.4 cap. It combines the original closed curved shell with four controller posts, two Pi side rails, two speaker posts and two repaired amplifier posts. They are integral features, not additional loose print pieces. The two speaker pieces are additions relative to the 89-piece stock and changed ear versions relative to V1.4. The old audio carrier stock44 is separate; this inventory does not declare it retired. Completed legs, original jaw and unchanged parts stay in use.

The combined cap reads back as one watertight body. Its outer bounds match the source shell and source material was retained. The old flat tips of the two Pi roof posts protruded locally; only those tips were shortened to remain under the source roof. The inherited V1.4 broad side-face orientation has 162.13mm² of contact within 0.02mm of the bed. The final shell is a mesh Boolean result; original cap STEP, six mounting STEP files and the source feature scripts remain available. No full-head native conversion or new slicing was performed here.

## Bench assembly

1. Keep the cap detached. Place keeper, speaker and cradle; connect the speaker wires while accessible. Use two M2.5×8 TAP screws through the cage.
2. Preconnect amplifier leads, then attach the matching moved amplifier with two M2.5×8 TAP screws.
3. Preplug the controller cables while accessible and mount OpenRB with four M2×6 TAP screws.
4. Fit the Pi to its two integral rails using four M2×6 TAP screws. Retain its existing 40-pin header. Plug the ordinary female leads before fitting the face, and arrange their flexible exits without pressure.
5. Trial-fit cap and face gently. Check all plugs, the camera ribbon and wire slack. Stop if closing presses a plug or wire; this is the intended physical fit trial.

These new mount interfaces use eight M2×6 TAP and four M2.5×8 TAP screws. Their remaining stock count is not asserted. Existing shell attachment screws remain; no M2×5 is introduced.

## Two open fit checks

**USB:** both ends of the finished replacement cable are unselected. The owned 4472 straight C receiver conflicts with this closed shell. A short direct Micro-B→USB-C connection is the requirement; an unconfirmed USB-A coupling chain is unnecessary. Many C-to-Micro cables specify C as host and Micro as device, so identical plug shapes do not establish the required Pi-host/OpenRB-device direction. No purchase or fine-pitch connector modification is authorized by this document.

**GPIO:** the ordinary female housings passed their rigid subset check. The pin 2/4/6/14 wire-exit centers are at X 78.746; the face inner plane is X 80.099, giving a 1.35mm projected X gap. Odd-row exits have about 1.79mm. These are not minimum 3D distances or bend allowances. Rotating a normal housing changes its latch side, not the axial exit. The finite modeled first bends failed; natural wire arrangement must be checked during the trial. No cutting of Pi pins or SMT socket substitution is prescribed.

This package supports printing and physical fitting. It does not prove complete populated closure, working USB, whole-robot wiring or physical commissioning.
