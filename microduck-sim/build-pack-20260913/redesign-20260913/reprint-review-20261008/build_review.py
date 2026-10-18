"""Build the source-bound replacement list; package only explicitly released meshes."""
from pathlib import Path
import base64, hashlib, html, json, zipfile

D=Path(__file__).resolve().parent
R=D.parent
G=R/'leg-guide-20261006'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
manifest=json.loads((D/'parts.json').read_text())
if manifest.get('localPrintDelivery'):
    current=manifest['localPrintDelivery']
    assert current['deliveryMode']=='local_mac_only'
    package_path=R/current['manifest']
    route_path=R/current['routeReport']
    assert sha(package_path)==current['manifestSha256'], 'Local package manifest changed'
    assert sha(route_path)==current['routeReportSha256'], 'Route evidence changed'
    package=json.loads(package_path.read_text())
    route=json.loads(route_path.read_text())
    assert package['version']==current['version']
    assert package['partKinds']==current['partKinds']==11
    assert package['quantity']==current['quantity']==16
    assert route['geometricCandidateAccepted'] and not route['physicalCommissioningAccepted']
    assert route['selfCoverage']['total']==4851 and route['selfCoverage']['overlaps']==0
    assert route['staticCoverage']['overlaps']==0 and route['closureCoverage']['intersections']==0
    assert sum(len(c['parts']) for c in current['colors'])==11
    assert sum(p['quantity'] for c in current['colors'] for p in c['parts'])==16
    esc=html.escape
    cards=[]
    for color in current['colors']:
        items=''.join(f"<li>{esc(p['name'])}<span>×{p['quantity']}</span></li>" for p in color['parts'])
        cards.append(f'''<article class="plate"><div class="color" style="background:{color['hex']}"></div><div class="platebody"><h3>{esc(color['name'])}<small>{len(color['parts'])}种 · {sum(p['quantity'] for p in color['parts'])}件</small></h3><ul>{items}</ul><p class="meta">{esc(color['printer'])}</p></div></article>''')
    retained=''.join(f'<li>{esc(s)}</li>' for s in current['retain'])
    steps=''.join(f'<li>{esc(s)}</li>' for s in current['assembly'])
    page=f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>MicroDuck V1.3 · 四色重打清单</title><style>*{{box-sizing:border-box}}body{{margin:0;background:#f3f5f0;color:#263f34;font:17px/1.7 system-ui,sans-serif}}main{{max-width:1000px;margin:auto;padding:32px 24px 60px}}a{{color:#23664e}}nav{{display:flex;gap:22px;flex-wrap:wrap;font-size:15px}}h1{{font-size:36px;line-height:1.25;margin:22px 0 12px}}h2{{font-size:24px;margin:32px 0 14px}}h3{{font-size:22px;margin:0 0 12px;display:flex;justify-content:space-between;align-items:center}}small,.meta,footer{{font-size:14px;color:#627065;font-weight:400}}.lead{{font-size:21px;margin:0 0 20px}}.status{{padding:18px 22px;background:#e2eedf;border:1px solid #b2c9ab;border-radius:12px}}.status p{{margin:6px 0}}.plates{{display:grid;grid-template-columns:1fr 1fr;gap:18px}}.plate{{background:#fff;border:1px solid #d2dbcf;border-radius:12px;overflow:hidden}}.color{{height:10px}}.platebody{{padding:20px}}.plate ul{{list-style:none;padding:0;margin:0}}.plate li{{display:flex;justify-content:space-between;margin:7px 0}}.plate .meta{{margin-bottom:0}}.local{{padding:18px 22px;background:#fff;border:1px solid #d2dbcf;border-radius:12px}}code{{font-size:14px;overflow-wrap:anywhere}}.note{{border-left:3px solid #b7894b;padding:8px 16px;background:#fff8ea}}li{{margin:10px 0}}footer{{margin-top:32px}}@media(max-width:650px){{main{{padding:22px 16px 44px}}h1{{font-size:29px}}.plates{{grid-template-columns:1fr}}}}</style><main><nav><a href="/LEFT-LEG.html">整机拼装与接线</a><a href="/HEAD-EYE-REVIEW.html">头部旧版3D参考</a></nav><p class="meta">MICRODUCK · {esc(current['date'])} · {esc(current['version'])}</p><h1>四色重打清单：11种，共16件</h1><p class="lead">打印文件已直接提供在你的Mac上。已装好的腿和原版下颚继续保留。</p><div class="status"><strong>完整200mm相机排线示例的几何检查已通过</strong><p>全长与两端位置保持，未发现自交或静态碰撞，装有电子件的头盖闭合检查通过。整理余线无需新增打印改件。</p><p class="meta">合盖检查包含0.25mm间隔采样。实物配合、自由转动、强度和上电仍需实装确认；数字检查不等于整机已经调通。</p></div><h2>按颜色取件</h2><div class="plates">{''.join(cards)}</div><h2>在Mac上打开打印包</h2><div class="local"><p>本机文件：<code>{esc(current['archiveName'])}</code>。解压后的Yellow、White、Orange、Black四个目录分别包含可编辑、已排盘的3MF、原生打印导出文件及源STL。</p><p>优先打开对应颜色的3MF；单独导入STL时，按3MF里的朝向摆放。黄色、白色使用Bambu导出，橙色、黑色使用Elegoo导出，具体机型见各颜色卡片。</p><p>本网页仅同步说明。打印ZIP、STL和3MF没有部署到Mac mini，也不从这里下载。详细装配顺序见包内<code>ASSEMBLY-REVIEW.txt</code>。</p></div><h2>哪些保留，哪些换回原版</h2><ul>{retained}</ul><h2>接两端 → 收余线 → 观察合盖</h2><ol>{steps}</ol><p class="note">上方整机拼装和头部3D链接继续可用。头部3D仍是旧版参考，其模型没有同步本次V1.3源文件；本次打印清单与装配说明以本机V1.3包为准。</p><footer>四盘已核对原生首层、支撑和功能孔。相机排线是柔性件，示例曲线不规定唯一折法。<br>AI assistance was used to draft.</footer></main></html>'''
    for target in (D/'REPRINT-PLAN.html',G/'REPRINT-PLAN.html'):
        target.write_text(page)
    print(json.dumps({'status':'LOCAL_PRINT_DELIVERY','version':current['version'],'partKinds':11,'quantity':16,'htmlSha256':sha(D/'REPRINT-PLAN.html'),'htmlBytes':len(page.encode()),'archiveGenerated':False}))
    raise SystemExit(0)

if manifest.get('releaseSuspended'):
    notice=manifest['releaseSuspended']
    items=''.join('<li>'+html.escape(s)+'</li>' for s in notice['corrections'])
    page=f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>MicroDuck · 重打清单核对中</title><style>body{{margin:0;background:#f3f5f0;color:#263f34;font:18px/1.75 system-ui,sans-serif}}main{{max-width:850px;margin:auto;padding:40px 24px}}a{{color:#23664e}}nav{{display:flex;gap:24px;flex-wrap:wrap}}h1{{line-height:1.3}}li{{margin:16px 0}}.notice{{padding:20px;background:#fff8e9;border-left:4px solid #ba8744}}footer{{font-size:14px;margin-top:40px}}</style><main><nav><a href="/LEFT-LEG.html">继续查看整机拼装和接线</a><a href="/HEAD-EYE-REVIEW.html">头部候选预览（尚未定稿）</a></nav><h1>重打清单正在按原仓库重新核对</h1><p class="notice">旧的分件下载已撤下。完整、按颜色分盘的打印包尚未完成；之前的候选清单不能作为本次打印清单。</p><ul>{items}</ul><p>原版基准：AI-FanGe / Microduck-build-tutorial，采用 Pi 与 OpenRB 的社区版本。新增相机和扬声器只做必要的局部适配。</p><p>已装好的腿、脚踝和脚掌继续保留。其他拼装页面保持可用。</p><footer>更新：{html.escape(notice['date'])}<br>AI assistance was used to draft.</footer></main></html>'''
    readme='本归档已暂停作为打印交付。\n旧候选STL已撤下；完整分色盘尚未完成。\n\n'+'\n'.join(notice['corrections'])+'\n'
    for target in (D/'REPRINT-PLAN.html',G/'REPRINT-PLAN.html'):target.write_text(page)
    with zipfile.ZipFile(D/'REPRINT-PARTS.zip','w',compression=zipfile.ZIP_DEFLATED) as z:z.writestr('NOT-A-PRINT-PACK.txt',readme)
    (G/'REPRINT-PARTS.zip').write_bytes((D/'REPRINT-PARTS.zip').read_bytes())
    (D/'suspended-release.json').write_text(json.dumps({'status':'SUSPENDED','manifestSha256':sha(D/'parts.json'),'htmlSha256':sha(D/'REPRINT-PLAN.html'),'zipSha256':sha(D/'REPRINT-PARTS.zip'),'releasedStlCount':0},indent=2)+'\n')
    print(json.dumps({'status':'SUSPENDED','releasedStlCount':0}));raise SystemExit(0)

import numpy as np
import trimesh
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
(D/'images').mkdir(exist_ok=True)
(D/'individual-parts').mkdir(exist_ok=True)
colors={'Yellow':'#e5ba54','Orange':'#f0a34b','White':'#e2e5df','Black':'#434b48'}
records=[]; cards=[]; released=[]
for part in manifest['parts']:
    src=R/part['source']; m=trimesh.load(src,force='mesh')
    if not m.is_watertight or not m.is_volume:
        raise ValueError('Invalid closed print mesh: '+part['name'])
    record={**part,'sourceSha256':sha(src),'dimensionsMm':m.extents.tolist(),'watertight':bool(m.is_watertight),'connectedBodies':len(m.split()),'volumeMm3':float(m.volume)}
    records.append(record)
    png=D/'images'/(part['id']+'.png'); stamp=png.with_suffix('.sha256')
    if not png.exists() or not stamp.exists() or stamp.read_text()!=record['sourceSha256']:
        vertices=m.vertices-m.bounds.mean(axis=0)
        fig=plt.figure(figsize=(4.5,3.2),dpi=130);ax=fig.add_subplot(111,projection='3d')
        faces=Poly3DCollection(vertices[m.faces],facecolors=colors[part['color']],linewidths=0,shade=True)
        ax.add_collection3d(faces);span=max(m.extents)*.54
        ax.set(xlim=(-span,span),ylim=(-span,span),zlim=(-span,span));ax.set_box_aspect((1,1,1));ax.view_init(elev=23,azim=-50);ax.set_axis_off();fig.subplots_adjust(0,0,1,1);fig.savefig(png,facecolor='#f1f4ef');plt.close(fig);stamp.write_text(record['sourceSha256'])
    ready=part['status']=='prototype'
    badge=('Optional alternative · fit prototype' if part.get('optional') else 'Geometry ready · fit prototype') if ready else 'Hold · dependency under review'
    if ready:
        name=f"{part['id']}_{'OPTIONAL_' if part.get('optional') else ''}{part['key']}_{part['color'].lower()}_qty{part['quantity']}.stl"
        target=D/'individual-parts'/name;target.write_bytes(src.read_bytes());record['file']=name;released.append(target)
    dims=' × '.join(f'{x:.1f}' for x in m.extents)
    img=base64.b64encode(png.read_bytes()).decode()
    cards.append(f'''<article class="part" data-part="{html.escape(part['key'])}" data-status="{part['status']}"><img src="data:image/png;base64,{img}" alt="Actual mesh of {html.escape(part['name'])}"><div class="body"><span class="badge {'ready' if ready else 'hold'}">{badge}</span><h3>{part['id']} · {html.escape(part['name'])}</h3><p class="meta">{part['color']} · quantity {part['quantity']} · {dims} mm</p><p><strong>Replaces:</strong> {html.escape(part['old'])}</p><p>{html.escape(part['reason'])}</p></div></article>''')
checks={'manifestSha256':sha(D/'parts.json'),'parts':records,'printedHardwareIncluded':False,'physicalFitVerified':False,'slicingAccepted':False,'releaseCount':len(released)}
(D/'geometry-manifest.json').write_text(json.dumps(checks,indent=2)+'\n')
readme=['# MicroDuck individual replacement parts — 8 October 2026','','The numbered files correspond to the online replacement list. Units: mm. Geometry retains the assembly world frame. These are individual STL geometry inputs, not sliced printer jobs. Select the matching printer/material and inspect orientation, supports and all functional seats in the native slicer before printing.','','Only parts marked “Geometry ready · fit prototype” are in the download. Held camera/audio parts are listed separately to prevent printing a design whose cable route can still change.','','## Individual parts','']
for p in records:
    readme.append(f"- **{p['id']} · {p['name']}** — {p['color']}, ×{p['quantity']}; replaces {p['old']}. {'Included as '+p['file'] if 'file' in p else 'Held; not in the print download.'} {p['reason']}")
readme+=['','## Retain existing parts','']+[f"- **{p['name']}** — {p['reason']}" for p in manifest['keepExisting']]
readme+=['','Physical fit and material strength remain unverified. Follow PRINTING/WORKFLOW.md for native slicing.','', 'AI assistance was used to draft.','']
(D/'README.md').write_text('\n'.join(readme))
if released:
    with zipfile.ZipFile(D/'REPRINT-PARTS.zip','w',compression=zipfile.ZIP_DEFLATED) as z:
        for p in released:z.write(p,'individual-parts/'+p.name)
        z.write(D/'README.md','README.md');z.write(D/'geometry-manifest.json','geometry-manifest.json')
    (G/'REPRINT-PARTS.zip').write_bytes((D/'REPRINT-PARTS.zip').read_bytes())
jaw=(D/'jaw-assembly-section.html').read_text()
software=(D/'software-section.html').read_text() if (D/'software-section.html').exists() else ''
fasteners=(D/'fastener-section.html').read_text() if (D/'fastener-section.html').exists() else ''
wiring=(D/'wiring-section.html').read_text() if (D/'wiring-section.html').exists() else ''
retained=''.join(f"<li><strong>{html.escape(p['name'])}.</strong> {html.escape(p['reason'])}</li>" for p in manifest['keepExisting'])
download=f'<a class="button" href="/REPRINT-PARTS.zip">Download {len(released)} individual prototype STL files</a>' if released else '<p>Replacement geometry is listed below; release depends on the remaining cable and fastener checks.</p>'
primary_count=sum(p['status']=='prototype' and not p.get('optional') for p in records)
optional_count=sum(p['status']=='prototype' and p.get('optional',False) for p in records)
held_count=sum(p['status']=='hold' for p in records)
page=f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>MicroDuck · Replacement parts and assembly corrections</title><style>*{{box-sizing:border-box}}body{{margin:0;background:#f3f5f0;color:#263f34;font:17px/1.6 system-ui,sans-serif}}main{{max-width:1180px;margin:auto;padding:32px 24px 80px}}a{{color:#23664e}}nav{{display:flex;gap:20px;flex-wrap:wrap}}h1{{font-size:38px;line-height:1.16;max-width:870px}}h2{{margin-top:40px}}h3{{margin:10px 0;font-size:20px;line-height:1.3}}.lead{{font-size:20px;max-width:850px}}.note{{padding:18px 22px;border-left:4px solid #ba8744;background:#fff8e9;margin:20px 0}}.parts{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:22px}}.part{{border:1px solid #cdd8cb;background:white;border-radius:14px;overflow:hidden}}.part img{{width:100%;height:240px;object-fit:contain;background:#f1f4ef}}.body{{padding:20px}}.part p{{margin:10px 0}}.badge{{font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:.6px}}.ready{{color:#267049}}.hold{{color:#8a601a}}.meta,footer{{font-size:14px;color:#596b60}}.button{{display:inline-block;background:#23664e;color:white;border-radius:8px;padding:10px 18px;text-decoration:none}}li{{margin:10px 0}}.step{{padding:16px 20px;margin:12px 0;background:white;border:1px solid #d5dfd3;border-radius:10px}}@media(max-width:650px){{.parts{{grid-template-columns:1fr}}h1{{font-size:30px}}main{{padding:20px 16px}}}}</style><main><nav><a href="/LEFT-LEG.html">Assembly and wiring guide</a><a href="/HEAD-EYE-REVIEW.html">Curved head · interactive review</a></nav><p class="meta">MICRODUCK · 8 OCTOBER 2026</p><h1>Replacement parts, screw changes and cable access</h1><p class="lead">Keep the completed legs. Replace only the named parts needed to make the remaining joints accessible and retain the curved duck head.</p>{download}<div class="note">STL files are individual geometry inputs. They are not printer-specific sliced jobs. Check the actual printer, material, first layer, supports and screw seats before printing. A passed digital assembly check does not establish printed strength.</div><nav><a href="#knee-repair">Screw corrections</a><a href="#jaw-station">Jaw assembly</a><a href="#cable-review">Cable checks</a></nav><p>{primary_count} primary prototype parts and {optional_count} optional lower-leg alternatives are available. {held_count} head/electronics-dependent parts remain held. The download labels optional alternatives explicitly.</p><h2>Parts to replace or add</h2><div class="parts">{''.join(cards)}</div><h2>Keep these existing parts</h2><ul>{retained}</ul>{fasteners}{jaw}{wiring}{software}<h2>Prepare → assemble → check</h2><p>Following the access-first structure of the <a href="https://docs.robotis.com/docs/systems/omx/quick_start_guide/assembly_guide/">ROBOTIS assembly guide</a>, each station must retain access for the next screw and connector before it closes.</p><div class="step"><strong>Prepare.</strong> Identify the exact part, fasteners and cable ends. State which joints are loose, which parts already move as a group, and the reference motor posture.</div><div class="step"><strong>Assemble.</strong> Show the whole retained group and the correct work face. Prewire and fasten internal modules while the cover is detached; route free connector ends through openings before latching both ends.</div><div class="step"><strong>Check.</strong> Confirm seated mating faces, retained washers, the specified screw depth, latched connectors and slack throughout the permitted joint travel. Close the next shell only after those checks.</div><footer>Actual source meshes shown. Electronics and screw-envelope meshes are excluded from the print list.<br>AI assistance was used to draft.</footer></main></html>'''
(D/'REPRINT-PLAN.html').write_text(page);(G/'REPRINT-PLAN.html').write_text(page)
print(json.dumps({'parts':len(records),'releasedPrototypeParts':len(released),'htmlBytes':len(page.encode())}))
