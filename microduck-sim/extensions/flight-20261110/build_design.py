"""Build the flying-duck design pages, Chinese and English, from one set of facts and one 3D view.

    /tmp/microduck-cad-venv/bin/python export_pack_meshes.py     # released CAD meshes -> pack_meshes.json
    python3 build_design.py                                       # -> flying-duck-design.html, flying-duck-design-en.html

Inputs: design-template.html (zh), design-template-en.html (en), design-view.js (3D view), duck_poses.json (duck meshes and
poses, export_duck_poses.py), pack_meshes.json, three.js from microduck-simulator; every number comes from design_facts.py.
The build fails if a {{key}} is left unfilled or the pack meshes are not the released FlightPack-D1 geometry.
"""
import json
import re
from pathlib import Path

from design_facts import facts

H = Path(__file__).resolve().parent
three = (H.parents[1] / "microduck-simulator/app/node_modules/three/build/three.module.min.js").read_text()
assert "</script" not in three.lower()
view = H.joinpath("design-view.js").read_text()
assert "</script" not in view.lower()
mesh = H.joinpath("duck_poses.json").read_text()
pack_txt = H.joinpath("pack_meshes.json").read_text()
pack = json.loads(pack_txt)
release = json.loads(H.joinpath("cad/slices/release-FlightPack-D1/STATUS.json").read_text())["geometry"]
for p in pack["parts"]:
    if p["id"] in release:
        assert p["sha12"] == release[p["id"]], f'{p["id"]}: pack_meshes.json is not the released geometry; rerun export_pack_meshes.py'
assert {p["id"] for p in pack["parts"]} >= set(release), "a released part is missing from pack_meshes.json"

STATUS = {
    "zh": {"ordered": "已下单，还没到", "carted": "在购物车里，没下单", "unticked": "在购物车里没勾选，没买", "removed": "不买",
           "roboclub": "从 RoboClub 拿，还没拿到", "inhand": "已到手"},
    "en": {"ordered": "ordered, not arrived", "carted": "in the cart, not ordered", "unticked": "in the cart but unticked, not bought",
           "removed": "not buying", "roboclub": "from RoboClub stock, not collected yet", "inhand": "in hand"},
}
F = facts()
CSS = re.search(r"<style>.*?</style>", H.joinpath("design-template.html").read_text(), re.S).group(0)   # one stylesheet, both pages
for lang, tpl, out in (("zh", "design-template.html", "flying-duck-design.html"), ("en", "design-template-en.html", "flying-duck-design-en.html")):
    if not H.joinpath(tpl).exists():
        print("skip", tpl, "(no template)")
        continue
    src = H.joinpath(tpl).read_text()
    def fill(m):
        k = m.group(1)
        v = F[k]
        return STATUS[lang][v] if k.startswith("st_") else v
    html = re.sub(r"\{\{(\w+)\}\}", fill, src)
    assert "{{" not in html, f"{tpl}: unfilled placeholder"
    html = html.replace("__CSS__", CSS).replace("__MESH__", mesh).replace("__PACK__", pack_txt).replace("__VIEW__", view).replace("__THREE__", three)
    H.joinpath(out).write_text(html)
    print(out, len(html), "keys used", len(set(re.findall(r"\{\{(\w+)\}\}", src))))
