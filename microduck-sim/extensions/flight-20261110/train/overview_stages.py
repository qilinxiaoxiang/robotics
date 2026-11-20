"""Render the stage scoreboard of OVERVIEW.html from ../TRAIN-CONTRACT.json, so the page and the contract cannot
drift apart. Replaces what lies between <!--STAGES:BEGIN--> and <!--STAGES:END-->.

  python3 train/overview_stages.py          (light: reads one JSON, rewrites one block; fine on the MacBook)

Shows per line the goal in Chinese (goal_zh) and Shawn's first quoted words, and per stage its Chinese sheet
(sheet_zh: does, does_not, pass, kill, budget), status, attempts (prediction_zh / result_zh when present) and result.
"""
import html
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CONTRACT, PAGE = HERE.parent / "TRAIN-CONTRACT.json", HERE / "OVERVIEW.html"
BEGIN, END = "<!--STAGES:BEGIN-->", "<!--STAGES:END-->"
TAG = {"proposed": ("warn", "待你批"), "approved": ("run", "已批，未开跑"), "running": ("run", "进行中"),
       "passed": ("ok", "已过"), "killed": ("bad", "已放弃")}
VERDICT = {"running": "进行中", "pass": "过", "fail": "不过", "invalid": "作废"}


def e(s):
    return html.escape(str(s), quote=False)


def stage_html(st):
    z = st.get("sheet_zh") or {}
    cls, word = TAG[st["status"]]
    b = st.get("budget", {})
    used, failed = len(st.get("attempts", [])), sum(1 for a in st.get("attempts", []) if a.get("verdict") == "fail")
    out = [f'<div class="card stage" id="st-{e(st["id"])}"><b class="h"><span class="tag {cls}">{word}</span>{e(z.get("title", st["id"]))}</b>',
           f'<p><b>做什么：</b>{e(z.get("does", st["question"]))}</p>',
           f'<p><b>不做什么：</b>{e(z.get("does_not", ""))}</p>',
           f'<p><b>过关：</b>{e(z.get("pass", st["pass"]["threshold"]))}</p>',
           f'<p><b>放弃：</b>{e(z.get("kill", st["kill"]["condition"]))}</p>',
           f'<p><b>预算：</b>{e(z.get("budget", ""))} 已用 {used} 次，其中不过 {failed} 次（上限 {b.get("max_attempts", "?")} 次）。</p>']
    ap = st.get("approval")
    if ap:
        out.append(f'<p class="src">批准：{e(ap["by"])} {e(ap["date"])}，原话“{e(ap["words"])}”</p>')
    for a in st.get("attempts", []):
        out.append(f'<p class="att"><b>第 {a["n"]} 次（{e(a["started"][:16].replace("T", " "))}，{VERDICT.get(a.get("verdict"), a.get("verdict"))}）</b><br>'
                   f'开跑前的预测：{e(a.get("prediction_zh") or a.get("prediction", ""))}'
                   + (f'<br>结果：{e(a.get("result_zh") or a.get("result"))}' if a.get("result_zh") or a.get("result") else "") + "</p>")
    for r in st.get("route_reviews", []):
        out.append(f'<p class="att"><b>路线复盘（{e(r["date"])}，第 {r["after_attempt"]} 次之后）：</b>{e(r.get("finding_zh") or r["finding"])} 决定：{e(r["decision"])}</p>')
    res = st.get("result")
    if res:
        out.append(f'<p><b>结论（{e(res["date"])}）：</b>{e(res.get("number_zh") or res["number"])} <span class="src">{e(res["evidence"])}</span></p>')
    out.append("</div>")
    return "\n".join(out)


def main():
    c = json.loads(CONTRACT.read_text())
    parts = []
    for line in c["lines"]:
        q = line["owner_words"][0]
        parts.append(f'<h3>{e(line["id"])} 线：{e(line.get("goal_zh", line["goal"]))}</h3>')
        parts.append(f'<div class="q">“{e(q["quote"])}”（{e(q["date"])}）</div>')
        parts.extend(stage_html(st) for st in line["stages"])
    block = BEGIN + "\n" + "\n".join(parts) + "\n" + END
    page = PAGE.read_text()
    if BEGIN not in page or END not in page:
        sys.exit(f"{PAGE}: markers {BEGIN} / {END} not found")
    head, rest = page.split(BEGIN, 1)
    PAGE.write_text(head + block + rest.split(END, 1)[1])
    print(f"{PAGE.name}: {sum(len(l['stages']) for l in c['lines'])} stages rendered from {CONTRACT.name}")


if __name__ == "__main__":
    main()
