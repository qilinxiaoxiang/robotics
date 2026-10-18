# Current head viewer handoff

`HEAD-EYE-REVIEW.html` is self-contained: Three.js, controls and a gzip-compressed scene are inline. `scene.json` is the same scene without compression for the existing website integration. `viewer.js` is the small UI source; `viewer-manifest.json` binds source files and output hashes.

The viewer contains the restored source jaw/support/lower pad and retained mouth ring, speaker-pilot-fixed populated cap, current three-screw camera clamp, positive-x225 Pi shifted by its three 2 mm spacers, matching M2.5×8 screws, discrete 40-pin header, and the final complete200 mm local-S ribbon. The obsolete split jaw, old ribbon curves and filled 40-pin block are absent.

Default is the current assembled geometry. Internal view hides the cap/face/eye trim. Open-cap view lifts cap-mounted hardware40 mm. Optional blue receiving spaces are dimensional references, not physical component CAD. The orange ribbon is explicitly an adjustable flexible routing example, not a prescribed rigid folding shape. Physical commissioning and motor/runtime acceptance remain false.

Build performed only scene conversion, with no CAD boolean/optimization or new geometry design. Duplicate vertices were exactly indexed without deleting triangles. Final conversion7.58 s, peak373.23 MiB. Source/mesh selection and SHA256 checks passed; compiledJavaScript syntax passed. Live browser rendering is to be checked in the parent-owned existing website deployment.

Do not copy historical viewer-candidate wording as current acceptance; this handoff binds the final full-ribbon-acceptance.json. No Sites checkout or publishing action was performed by this branch.
