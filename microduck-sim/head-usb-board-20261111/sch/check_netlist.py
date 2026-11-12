#!/usr/bin/env python3
"""Check a generated or Fusion-exported .sch against netlist.py. Run: python3 check_netlist.py FILE.sch
Fails when a pin is on another net than netlist.py says, a part or pin is missing or extra, a net has one pin only,
or a chip pin that the datasheet does not allow open is open."""
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import netlist as NL

MAY_BE_OPEN = {  # (kind, pin name without number): reason from the datasheet
    "CH334F": {"RESET#", "PSELF", "OVCUR#", "PWREN#", "NC", "NC2", "DP3", "DM3", "DP4", "DM4", "LED1", "LED2", "LED3", "LED4"},
    "MAX98357A": {"GAIN_SLOT", "NC"},
    "AP2112K-3.3": {"NC"},
}


def main(path):
    want = {}
    fails = []
    for members in NL.GROUPS.values():
        for ref, kind, value, conn in members:
            for pin, net in conn.items():
                name = pin.split("_", 1)[1] if pin[0].isdigit() and "_" in pin else pin
                if net is None:
                    if not (name.startswith("GPIO") or name in MAY_BE_OPEN.get(kind, ())):
                        fails.append(f"{ref}.{pin} ({kind}) is open and not on the allowed-open list")
                else:
                    want[(ref, pin)] = net
    got = {}
    root = ET.parse(path).getroot()
    for net in root.iter("net"):
        for pr in net.iter("pinref"):
            got[(pr.get("part"), pr.get("pin"))] = net.get("name")
    parts = {p.get("name") for p in root.iter("part")}
    refs = {m[0] for ms in NL.GROUPS.values() for m in ms}
    for r in sorted(refs ^ parts):
        fails.append(f"part {r}: in {'netlist only' if r in refs else 'file only'}")
    for k in sorted(set(want) | set(got)):
        if want.get(k) != got.get(k):
            fails.append(f"{k[0]}.{k[1]}: netlist {want.get(k)}, file {got.get(k)}")
    count = {}
    for net in want.values():
        count[net] = count.get(net, 0) + 1
    for net, n in sorted(count.items()):
        if n < 2:
            fails.append(f"net {net}: only one pin")
    for f in fails:
        print("FAIL", f)
    print(f"{'FAIL' if fails else 'PASS'}: {len(parts)} parts, {len(want)} connected pins, {len(count)} nets")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
