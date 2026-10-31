"""Check microduck-sim/FAULTS.json: a fault seen twice or more needs a confirmed cause or a test that has run or is
queued with its named blocker, and a fault that disables a function stays failing until that function is shown to come
back by itself after an induced fault (rule recurring-fault-cause-first.md). Exit 1 on any failure."""
import json
import os
import sys

PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "FAULTS.json")


def problems(fault):
    out = []
    n = len(fault.get("occurrences", []))
    tests = fault.get("tests", [])
    if n >= 2 and fault.get("cause", {}).get("status") != "confirmed":
        live = [t for t in tests if t.get("status") in ("run", "running")
                or (t.get("status") == "queued" and t.get("blocker"))]
        if not live:
            out.append(f"seen {n} times, cause not confirmed, and no test run or queued with a named blocker")
        else:
            out.append(f"seen {n} times, cause not confirmed; open tests: "
                       + "; ".join(f"{t['id']} ({t['status']}, blocker: {t.get('blocker', '-')})" for t in live))
    rec = fault.get("recovery", {})
    if fault.get("required_recovery") and not (rec.get("self_recovers") is True
                                               and rec.get("verified_by_induced_fault") is True):
        out.append("the lost function does not yet come back by itself after an induced fault")
    return out


def main():
    faults = json.load(open(PATH))["faults"]
    failed = False
    for name, fault in faults.items():
        p = problems(fault)
        failed |= bool(p)
        print(f"{name}: {'OPEN' if p else 'OK'}" + "".join(f"\n  - {x}" for x in p))
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
