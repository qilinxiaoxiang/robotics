# V1.4 incremental print delivery

User decision, 2026-10-08: use the existing external wall-charger power configuration. Onboard battery work is deferred; no battery tray is included or required for this release.

The current user package is `zhengxia_MicroDuck_V1.4_8-files.zip`: exactly eight ready-to-print files, four colors with one alternative for each of Bambu X1 Carbon and Elegoo Centauri Carbon. Print one machine file per color, not all eight. Use the machine, nozzle and plate specified in the matching file.

11 part types / 13 pieces: six replacements and seven additions against the 89-piece previously printed stock. Unchanged stock is not duplicated. The neck bracket has integral 1 mm screw seats; four separate neck washers are removed. Three Pi 2 mm spacers remain. The unaccepted PB1033MI carrier is excluded.

`dual-printer/delivery-index.json` is RELEASED and binds filenames, actual native slice time, hashes and final first-layer/hole acceptance. `incremental-audit/incremental-audit-V1.4.json` binds the stock comparison. The earlier V1.3 package remains historical and contains more source files and separate neck washers.

Physical fit and power commissioning remain open. Source head shape and already assembled legs are retained. Printed bed contact and supports have been checked in each final native output; this does not establish whole-robot assembly or dynamic acceptance.

Archive SHA256: 231f92c5c1e8d92305580f59dca1d264861d77f2538e6782ebdf7064c2e721c0
