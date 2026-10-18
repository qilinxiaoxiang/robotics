from pathlib import Path
import json,hashlib,struct,re
D=Path(__file__).resolve().parent;R=D.parent.parent
svg=(D/'pb1033mi-backpack-side-view.svg').read_text()
svg=re.sub(r'<path id="(?:bottom|wall)-route"[^>]+/>','',svg)
svg=re.sub(r'<g id="output-wiring">.*?</g>','',svg,flags=re.S)
svg=svg.replace('id="builtin-route" ','')
# Use the true original curved shell silhouette rather than the older guide's
# modified cap. Standard-library binary STL read, no CAD process or boolean.
p=R/'head-redesign-20261008/curved-head/community-curved-head-world.stl';b=p.read_bytes();n=struct.unpack_from('<I',b,80)[0];pts=[]
for i in range(n):
 vals=struct.unpack_from('<12fH',b,84+50*i)
 pts.extend((round(vals[j],4),round(vals[j+2],4)) for j in [3,6,9])
def hull(pts):
 ps=sorted(set(pts));lo=[];hi=[]
 def cross(o,a,b):return(a[0]-o[0])*(b[1]-o[1])-(a[1]-o[1])*(b[0]-o[0])
 for a in ps:
  while len(lo)>1 and cross(lo[-2],lo[-1],a)<=0:lo.pop()
  lo.append(a)
 for a in reversed(ps):
  while len(hi)>1 and cross(hi[-2],hi[-1],a)<=0:hi.pop()
  hi.append(a)
 return lo[:-1]+hi[:-1]
points=' '.join(f'{420+2.5*x:.2f},{450-2.5*z:.2f}' for x,z in hull(pts));svg=re.sub(r'<polygon[^>]+/>',f'<polygon points="{points}" fill="#dce3e8" opacity=".7" stroke="#354454" stroke-width=".7"/>',svg,count=1)
svg=svg.replace('stroke="#e08a13"','id="builtin-route" stroke="#e08a13"')
# Diagrams show cable topology and endpoint access, not a certified exact shape.
extra='<path id="bottom-route" style="display:none" d="M 215 589 L 215 613 Q 215 640 177 638 Q 102 638 102 585 L 102 377 Q 102 350 124 365 L 150 386" fill="none" stroke="#9168c5" stroke-width="5" stroke-linecap="round"/>'
wall='<path id="wall-route" style="display:none" d="M 36 310 Q 120 310 133 350 L 150 386" fill="none" stroke="#357fbc" stroke-width="5" stroke-linecap="round"/>'
output='<g id="output-wiring"><rect x="321.25" y="447.5" width="20" height="75" fill="#41958c" stroke="#1d5953"/><path d="M 150 459 L 150 478 L 275 480 L 321 480" fill="none" stroke="#b83642" stroke-width="4" stroke-dasharray="7 3"/><path d="M 150 465 L 150 484 L 275 486 L 321 486" fill="none" stroke="#292f37" stroke-width="3" stroke-dasharray="7 3"/><rect x="265" y="470" width="20" height="25" rx="3" fill="#e8bb41" stroke="#715519"/><text x="245" y="513" font-size="13">XT30</text><text x="340" y="510" font-size="13">DFR1202</text><text x="65" y="555" font-size="13" fill="#a12d35">正负输出线从电池侧面绕行</text><text x="65" y="573" font-size="12">虚线为侧视投影，不代表穿过电池</text><text x="520" y="650" font-size="15">5991 输出 → 现有 XT30 → 现有 DFR1202</text><text x="520" y="677" font-size="14">插头位置和线束弯形是示意，未通过净距核验。</text></g>'
svg=svg.replace('</g></svg>',extra+wall+output+'</g></svg>')
(D/'pb1033mi-backpack-side-view.svg').write_text(svg)
html='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>充电宝背托评估 · 未纳入 V1.4</title><style>body{margin:0;background:#f4f6f8;color:#223242;font:16px/1.65 system-ui,sans-serif}main{max-width:1100px;margin:auto;padding:24px}h1{font-size:27px;margin:8px 0}.card{background:white;padding:20px;border:1px solid #d7dfe6;border-radius:12px;margin:16px 0}.status{color:#a43421;font-weight:650}button{font:inherit;padding:8px 15px;border:1px solid #bbc8d2;border-radius:8px;background:#fff;margin:4px;cursor:pointer}button[aria-pressed=true]{background:#223e50;color:#fff}.scene{overflow:auto}.scene svg{width:100%;min-width:850px;height:auto}a{color:#125ca0}.small{font-size:14px;color:#526371}</style><main><a href="LEFT-LEG.html">返回装配教程</a> · <a href="REPRINT-PLAN.html">打印清单</a><h1>充电宝背托：接口已留开，摆腿冲突未解决</h1><p class="status">这是 PB1033MI 试验候选，不是已通过打印件；不在 V1.4 黑盘中。</p><div class="card"><p>现有腿、髋关节位置和 DFR1202 保留。充电宝上下两端都开放：自带线从一端出来，另一端的 USB-C / USB-A 可接额外线。托底只承托外缘，不围着未知插头尺寸开窄孔。</p><button aria-pressed="true" data-mode="builtin">自带 USB-C 线</button><button aria-pressed="false" data-mode="bottom">底端备用 USB-C 线</button><button aria-pressed="false" data-mode="wall">墙充线</button><p id="mode-note">自带线接唯一的 5991；5991 靠近出线端，线留自然余量；输出正负线经现有 XT30 接 DFR1202。图中线长及弯形仅为示意，未当成实物尺寸。</p><div class="scene">'''+svg+'''</div></div><div class="card"><strong>为什么暂不把托放进打印包</strong><p>同样的 133 个有限腿部姿态中，32 个已与原机器人结构冲突，分别保留；其余 101 个姿态内，这个低位背托仍有新增碰撞。左髋向后俯仰 30° 时，小腿碰托约 17.18 mm³。电池后移 20 mm 后仍有 6 条新增碰撞记录，不能用原机极端姿态的限制来掩盖。</p><p>上移 40 mm、后移 10 mm 加上移 25 mm 的有限比较也未通过。继续放大托或限制腿的自由度，都没有被这里的结果认可。</p></div><div class="card"><strong>同一个接口，供电配置也要对应切换</strong><p>充电宝试验：5991 的 ISET 闭合，请求 20 V / 1.25 A。墙充方案：按现供电文档采用 ISET 开路 / 3.25 A。两路二选一，不并联，也不增加第二块 5991。</p><p class="small">绿色框采用官方 5991 完整 29.1 × 20.3 × 10.1 mm 接收尺寸；最终固定、绑带路径、实际插头和整根线净距尚未验收。图中的电源线属于装配示意，不能把示意线路当成已验证实物线长。整机重心、负载、供电和运动仍需实际调试。</p></div></main><script>const notes={builtin:'自带线接唯一的 5991；5991 靠近出线端，线留自然余量；输出正负线经现有 XT30 接 DFR1202。图中线长及弯形仅为示意，未当成实物尺寸。',bottom:'底端 USB-C 备用线绕过外缘托脚，再接同一 5991。底端中央保持大开口；这根额外线的库存和长度未在此确认。',wall:'拔下充电宝线，用墙充线接同一 5991；同时按供电说明切换 ISET。不得两路并联。'};document.querySelectorAll('button[data-mode]').forEach(b=>b.onclick=()=>{document.querySelectorAll('button[data-mode]').forEach(x=>x.setAttribute('aria-pressed',x===b));for(const m of ['builtin','bottom','wall'])document.getElementById(m+'-route').style.display=m===b.dataset.mode?'':'none';document.getElementById('mode-note').textContent=notes[b.dataset.mode]});</script></html>'''
(D/'POWER-REVIEW.html').write_text(html)
r=json.loads((D/'mechanical-disposition.json').read_text());r['sourceHashes'][str(p)]=hashlib.sha256(p.read_bytes()).hexdigest()
for f in ['pb1033mi-backpack-side-view.svg','POWER-REVIEW.html']:
 r['sourceHashes'][str(D/f)]=hashlib.sha256((D/f).read_bytes()).hexdigest()
(D/'mechanical-disposition.json').write_text(json.dumps(r,indent=2)+'\n')
print('HTML',hashlib.sha256((D/'POWER-REVIEW.html').read_bytes()).hexdigest());print('report',hashlib.sha256((D/'mechanical-disposition.json').read_bytes()).hexdigest())
