# Final integration gaps
Four concrete items remain; this is a read-only snapshot, not a new acceptance framework.

## I1 · Current head connections still inherit the removed star-fed motor topology and old board poses.
- Saved effective bundle has17 head/unaccepted connections after excluding the3 inlet rows now handled by the new input adapter.
- data-02..data-05 show only pin3 DATA for15→14→13→11→12; their old separate fused motor feeds were removed.
- data-01 correctly says source GND/VDD isolated; the receiving head-zone supply and return are not yet adopted.

**Smallest fix:** Freeze one complete head layout; replace the four internal head motor links with three-conductor keyed EH links, add the receiving motor15 zone power termination and actual logic distribution/J4/USB/CSI/I2S endpoints, then project the same connectors and closure prerequisites into the head tutorial. Preserve OpenRB→15 DATA-only boundary.

**Readback:** One source-bound head inventory contains all active rigid plugs, flexible cable examples and branch contacts; tutorial net continuity matches the three-zone design and the same populated closure.

## I2 · The moving neck and IMU middle extensions are not yet joined to actual head endpoints.
- neck-open-interface-manifest.json is intentionally integrationReady=false; neutral3-conductor routes end at Z98, not a connector.
- IMU four150mm leads have only17.5/19.5/21.5/23.5mm nominal remaining after local routes and19.25mm connector reserve.
- There is no accepted physical placement for the eight individually insulated extension splice joints.

**Smallest fix:** Use the existing three Z98 interfaces, retain the four original SH/female lead ends and extend each in the middle. Assign four lower and four head-side insulated splice locations to supported sections, keep splices out of flex zones, and check the adopted neck range with actual moving head endpoints. Do not reinstate the rejected11-wire rigid loop or cut new neck slots as an assumption.

**Readback:** Continuous net and material-length ledger to actual pins, no unexplained150mm full-head reach, explicit slack/retention and closure order for the final head.

## I3 · The available native print package still belongs to V1.4, not the pending closed-head/body installation revision.
- dual-printer/delivery-index.json is RELEASED V1.4,11 types/13 pieces/8 files.
- incremental-audit-V1.4.json states Pi2mm spacers unchanged and head_cap same as V1.3.
- cloud-share/build.py lines9–18 checks version/index/ZIP hashes but does not bind head-page geometry or assembly geometry to those printer files.

**Smallest fix:** After the final mechanical source freeze, compare only the adopted changed printable parts with recorded stock; reuse unchanged native files and slice only genuinely changed color plates for both machines. Write a release record binding accepted head/body geometry hashes, part-to-plate list, native readback and index. Require that record when building the website.

**Readback:** Exactly one Bambu and one Elegoo file per included color, zhengxia_ names and native time/thumbnail/first-layer/functional-hole readback; release record proves the same geometry is displayed. No whole-baseline reslice or new physical acceptance requirement.

## I4 · Effective sources and public outputs need one final coherent rebuild, with a few active stale electrical labels removed.
- Saved LEFT-LEG bundle lacked inputWiringAdapter at review time; its loader issue was reported and leg_paths fixed it without changing receipts (6 tests passed).
- viewer.js:95 still says fuses remain part of later power system. wiring3d.js:82 still gives the legacy OpenRB schematic a GND wire and fused-branch label; :95/:198 name the retired fuse carrier.
- Effective WIRING.single_source still says external5A fuse; SPATIAL.assertionsPassed still says15 motors get assigned fused VDD.
- Saved cloud dist has no CJK text, but it is an older artifact and still has an ANKLE-REDESIGN.html link whose target is absent. This is not a live-site claim.

**Smallest fix:** Apply the attached small semantic patch after coordination, call the input adapter after body→IMU→DATA, finish head projection, rebuild assembly and explicit power page, then run the existing cloud builder once from the same final release and verify the deployed pages. Do not publish a mixture of current source and old saved bundles.

**Readback:** Current adapter hashes are in the bundle; every selected active connection resolves to actual geometry/tutorial; relative page/source links exist; English scan covers HTML and both compressed payloads; live main/head/power/download views match the release.

## Deliberately excluded
- Built-in OpenRB500mA USB protection is real and must not be scrubbed as if it were the withdrawn external fuse array.
- Old site_content.power_page is no longer called by build.py; its historical bank/fuse prose is not an active page source.
- The450mA value in the effective tutorial is explicitly an unimplemented engineering proposal for supported current modes, not a manufacturer rating or proof of physical current limitation. This requires accurate commissioning wording, not a new print blockade.
- Legacy rooftop/head text is labeled historical and filtered from the public module list. The accepted replacement head still needs to be supplied; deleting history is not a geometry repair.
- No rerun of already passed body/leg geometry is needed solely for these integration issues.
- Root has already fixed data-group old cross-ankle description and IMU naming/reprint/motion captions; do not duplicate those requests.

`proposed-semantic-cleanup.patch` is reviewable and has not been applied.
