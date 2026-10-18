# Independent diagram review

VERDICT: PASS

BLOCKERS: None.

POLISH: None required.

GATES: A:ok B:ok C:ok D:ok

The independent reviewer viewed both refreshed images on 2026-09-13: `architecture.png` and the actual Chrome delivery screenshot `handbook-browser-preview.png`. This pass applies to their rendered content and delivery visibility; it does not certify physical hardware operation.

## Confirmed corrections

- The Pi card now says **“Board + card: borrow first”** in both images. It states the sourcing requirement without claiming the board or boot card has already been obtained.
- The Mac-to-Pi path is explicitly labeled **“Wi-Fi commands”**, with a separate return path for frames/logs.
- The power receiver title is **“5991 USB power receiver”** and fits inside its card.

## Rendered-image checks

- The full power path and the complete information path remain visible in two labeled zones. The diagram identifies one shared robot supply, the sensor power path through Pi, and the audio branch. The Mac is identified as the existing computer.
- The diagram covers the charger, receiver, onboard converter, Pi, camera/IMU, Mac, audio, controller, all 15 servos and the future bank interface. The subtitle explicitly retains the remaining visual-software work.
- Mac↔Pi and Pi↔OpenRB show the correct two-way information flow. **The OpenRB↔15-servos link has clear arrowheads at both ends in both reviewed images.**
- The camera/IMU and audio cards align with Pi; the servo card aligns with OpenRB. Connectors have visible lines, clear arrowheads and readable labels. No line crossings, card overlap, text occlusion, overflow, clipping or unintended wrapping were observed.
- The actual handbook screenshot displays the whole refreshed diagram, including the final future-bank text. It contains no broken image, alternative-text placeholder or mismatched older revision.

## Reviewed image identity

- `architecture.png`: SHA-256 `fa61e8685ce948716c4117391baa5001ab861a08747818edd987f80f3dbe9965`.
- `handbook-browser-preview.png`: SHA-256 `b11da463fd52a4b4494b41e7951d3f18e03fa0b05fa71b3c4b51870b43213729`.
