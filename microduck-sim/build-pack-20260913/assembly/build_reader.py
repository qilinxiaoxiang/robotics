from pathlib import Path
import html,re,json
H=Path(__file__).resolve().parent
LINKS={'measurements-template.json':'../power/measurements-template.json','runtime-supervisor/README.md':'../power/runtime-supervisor/README.md','PRINT-LIST.md':'print-list.html','ASSEMBLY.md':'index.html','FIRST-ARTICLE.md':'first-article.html','../power/WIRING.md':'power-wiring.html','../power/FIRST-POWER-TEST.md':'first-power.html'}
def inline(s):
 s=html.escape(s)
 def link(m):
  label,url=m.groups();base,*anchor=url.split('#',1);url=LINKS.get(base,base)+(('#'+anchor[0]) if anchor else '')
  return f'<a href="{url}">{label}</a>'
 s=re.sub(r'\[([^\]]+)\]\(([^)]+)\)',link,s)
 s=re.sub(r'\*\*(.+?)\*\*',r'<strong>\1</strong>',s);s=re.sub(r'`([^`]+)`',r'<code>\1</code>',s);return s

def render(text):
 lines=text.splitlines();out=[];paragraph=[];mode=None;toc=[];hcount=0
 def flush():
  nonlocal mode
  if paragraph:out.append('<p>'+inline(' '.join(paragraph))+'</p>');paragraph.clear()
  if mode:out.append('</'+mode+'>');mode=None
 for line in lines:
  line=line.strip()
  if not line:flush();continue
  m=re.match(r'^(#{1,6})\s+(.+)',line)
  if m:
   flush();level=len(m[1]);hid='step-'+str(hcount);hcount+=1;slug=re.sub(r'[^\w\- ]','',m[2]).lower().replace(' ','-');out.append(f'<a id="{slug}"></a><h{level} id="{hid}">{inline(m[2])}</h{level}>')
   if level==2:toc.append((hid,m[2]))
   continue
  m=re.fullmatch(r'!\[([^\]]*)\]\(([^)]+)\)',line)
  if m:flush();out.append(f'<figure><a href="{html.escape(m[2])}" target="_blank"><img src="{html.escape(m[2])}" alt="{html.escape(m[1])}" loading="lazy"></a><figcaption>{html.escape(m[1])} · Open full-resolution figure</figcaption></figure>');continue
  m=re.match(r'^(?:([-*])\s+|(\d+)\.\s+)(.*)',line)
  if m:
   k='ul' if m[1] else 'ol'
   if mode!=k:flush();mode=k;out.append('<ol start="'+m[2]+'">' if k=='ol' else '<ul>')
   out.append('<li>'+inline(m[3])+'</li>');continue
  if mode:out.append('</'+mode+'>');mode=None
  paragraph.append(line)
 flush();return '\n'.join(out),toc
CSS='''*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:#f6f8fb;color:#19324a;font:18px/1.8 -apple-system,BlinkMacSystemFont,"PingFang SC",sans-serif}header{background:#fff;border-bottom:1px solid #dce4ec;padding:20px 5vw}header b{font-size:22px}nav{display:flex;gap:24px;flex-wrap:wrap;margin-top:8px}a{color:#176a9e;text-decoration:none}a:hover{text-decoration:underline}main{max-width:1240px;margin:auto;padding:35px 48px 80px;background:#fff}h1{font-size:42px;line-height:1.25;margin:18px 0 24px}h2{font-size:29px;line-height:1.4;padding-top:32px;margin-top:48px;border-top:1px solid #e0e7ee;scroll-margin-top:20px}h3{font-size:24px}p,li{max-width:1080px}p{margin:20px 0}strong{color:#173e60}li{padding:6px 0}code{background:#eef3f7;padding:2px 6px;font-size:.9em;border-radius:4px;overflow-wrap:anywhere}figure{margin:36px -20px;background:#f8fafc;border:1px solid #e2e8f0;border-radius:14px;overflow:hidden}figure img{display:block;width:100%;height:auto}figcaption{padding:12px 22px;font-size:15px;color:#566b80}.toc{padding:22px 28px;background:#eff5f9;border-radius:12px;margin:24px 0 36px}.toc summary{cursor:pointer;font-weight:650}.toc a{display:block;padding:6px 0}.note{font-size:15px;color:#667b8e;margin:0}footer{padding:30px 6vw;color:#65798c;font-size:15px}@media(max-width:700px){main{padding:22px}h1{font-size:30px}h2{font-size:25px}body{font-size:17px}figure{margin:24px 0}nav{gap:14px}}@media print{header,.toc{display:none}main{max-width:100%;padding:0}body{font-size:12pt}h2{break-after:avoid}figure{break-inside:avoid}a{color:inherit}}'''
for src,out in [(H/'ASSEMBLY.md','index.html'),(H/'PRINT-LIST.md','print-list.html'),(H/'FIRST-ARTICLE.md','first-article.html'),(H.parent/'power/WIRING.md','power-wiring.html'),(H.parent/'power/FIRST-POWER-TEST.md','first-power.html')]:
 body,toc=render(src.read_text());title=re.search(r'<h1[^>]*>(.*?)</h1>',body)[1];contents='<details class="toc"><summary>On this page</summary>'+''.join(f'<a href="#{i}">{html.escape(t)}</a>' for i,t in toc)+'</details>'
 pos=body.find('</h1>')+5;body=body[:pos]+contents+body[pos:]
 page=f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{title}</title><style>{CSS}</style></head><body><header><b>MicroDuck assembly manual</b><nav><a href="index.html">Assembly steps</a><a href="print-list.html">Prints and fasteners</a><a href="power-wiring.html">Wiring specification</a><a href="first-power.html">First power-up</a><a href="first-article.html">First-article record</a></nav></header><main>{body}</main><footer>2026-09-13 | Source CAD and slicer evidence | Physical printing, assembly and powered acceptance remain to be completed.</footer></body></html>'
 (H/out).write_text(page)
print('5 reader pages built')
