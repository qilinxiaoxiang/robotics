#!/usr/bin/env python3
"""Check REQUIREMENTS.json and print the gap list: every requirement has Shawn's words, an acceptance and a known
status; every named test exists; a 'met' requirement has live evidence. Exit 1 on a malformed entry.

    python3 namecall-20261029/requirements_check.py
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MAC = os.path.dirname(HERE)
TEST_FILES = ["test_namecall_chain.py", "test_personfind.py", "test_ownkws.py"]
STATUS = ("gap", "partial", "built", "met")


def main():
    reqs = json.load(open(os.path.join(HERE, "REQUIREMENTS.json")))["requirements"]
    defined = set()
    for f in TEST_FILES:
        defined |= set(re.findall(r"^def (test_\w+)\(", open(os.path.join(MAC, f)).read(), re.M))
    bad = []
    for r in reqs:
        if not r.get("shawn") or not r.get("acceptance") or r.get("status") not in STATUS:
            bad.append(f"{r['id']}: needs Shawn's words, an acceptance and a status in {STATUS}")
        bad += [f"{r['id']}: test {t} not found" for t in r.get("tests", []) if t not in defined]
        if r.get("status") == "met" and not r.get("evidence"):
            bad.append(f"{r['id']}: met without live evidence")
    for s in STATUS[:3]:
        for r in (r for r in reqs if r.get("status") == s):
            print(f"[{s}] {r['id']} {r['title']}: {r.get('gap', '')}")
    print(f"{sum(r.get('status') == 'met' for r in reqs)}/{len(reqs)} met")
    for b in bad:
        print("ERROR", b)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
