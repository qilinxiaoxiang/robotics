from pathlib import Path
import json,hashlib,base64,sys,math
import numpy as np,trimesh,manifold3d as mf
D=Path(__file__).resolve().parent;R=D.parent.parent;SIM=R.parents[1];C=R/'head-redesign-20261008/usb-access/usb-repair/robot-source-cache';A=SIM/'hardware-design-20260912/whole-robot-20260912/assembly';sys.path.insert(0,str(A));from assembly_fk import fk
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def man(m):return mf.Manifold(mf.Mesh(np.asarray(m.vertices,dtype=np.float32),np.asarray(m.faces,dtype=np.uint32)))
def tri(s):
 m=s.to_mesh();return trimesh.Trimesh(np.asarray(m.vert_properties)[:,:3],np.asarray(m.tri_verts),process=True)
def box(lo,hi):return mf.Manifold.cube(np.subtract(hi,lo).tolist()).translate(lo)
def load(k):
 d=json.loads((C/(k+'.json')).read_text());p=np.frombuffer(base64.b64decode(d['positionB64']),'<f4').reshape(-1,3);return d,p
# This open-bottom refinement is an illustration only. Do not overwrite the
# failed candidate's source meshes or make an accepted print release.
m=trimesh.load(D/'pb1033mi-backpack-world.stl',force='mesh');s=man(m)
s-=box([-98,-27,-60],[-64,27,-56.35])
# Retire the low receiver bay in this illustration; full receiver moves close
# to the cable end on exterior rear. Retention design is explicitly pending.
s-=box([-62.99,-12.3,-54],[-49,12.3,-21.5])
preview=tri(s);preview.export(D/'open-bottom-illustration-world.stl')
pd=tri(box([-113.1,-10.15,-3.65],[-103,10.15,25.45]));pd.export(D/'near-exit-5991-illustration-world.stl')
# Bend points show natural slack, not a prescribed manufactured wire length.
points=[[-91,-27,25.45],[-91,-27,35],[-95,-22,43],[-105,-10,44],[-113,0,38],[-114.5,0,30],[-108,0,25.45]]
segments=[]
for a,b in zip(points,points[1:]):
 a=np.array(a);b=np.array(b);v=b-a;t=trimesh.geometry.align_vectors([0,0,1],v);t[:3,3]=(a+b)/2;segments.append(trimesh.creation.cylinder(radius=1.5,height=np.linalg.norm(v),sections=12,transform=t))
trimesh.util.concatenate(segments).export(D/'charging-cable-illustration-world.stl')
# Projection uses source mesh vertices, convex silhouette only. Label it clearly.
def hull(pts):
 p=sorted(set((round(float(x),4),round(float(z),4)) for x,z in pts))
 def cross(o,a,b):return(a[0]-o[0])*(b[1]-o[1])-(a[1]-o[1])*(b[0]-o[0])
 lo=[];hi=[]
 for a in p:
  while len(lo)>1 and cross(lo[-2],lo[-1],a)<=0:lo.pop()
  lo.append(a)
 for a in reversed(p):
  while len(hi)>1 and cross(hi[-2],hi[-1],a)<=0:hi.pop()
  hi.append(a)
 return lo[:-1]+hi[:-1]
def xy(x,z):return 420+2.5*x,450-2.5*z
def polygon(v,color,opacity=1):
 p=' '.join('%.2f,%.2f'%xy(x,z) for x,z in hull(v[:,[0,2]]));return f'<polygon points="{p}" fill="{color}" opacity="{opacity}" stroke="#354454" stroke-width="0.7"/>'
svg=['<svg xmlns="http://www.w3.org/2000/svg" width="1050" height="850" viewBox="0 0 1050 850"><rect width="1050" height="850" fill="#fafafa"/><g font-family="Arial,sans-serif">', '<text x="28" y="35" font-size="24">PB1033MI 背托：未通过的空间候选</text>', '<text x="28" y="62" font-size="15">侧视源轮廓投影；充电线仅示意自然余量。不是打印放行图。</text>']
for k in ['head_cap','head_bottom','neck_pitch','shell_left','shell_right','power_support','hip','thigh','lower','foot']:
 try:d,v=load(k);svg.append(polygon(v,'#dce3e8',.7))
 except FileNotFoundError:pass
svg.append(polygon(preview.vertices,'#303842',.8));bank=trimesh.load(D/'pb1033mi-reference-world.stl',force='mesh');svg.append(polygon(bank.vertices,'#81c6e8',.9));svg.append(polygon(pd.vertices,'#64be9b',1))
bas=fk()[0];poses=fk({'left_hip_pitch':math.pi/6})[0];d,v=load('lower');t=poses[d['body']]@np.linalg.inv(bas[d['body']]);v=v@t[:3,:3].T+t[:3,3];svg.append(polygon(v,'#e2766f',.45))
path=' '.join(('M' if i==0 else 'L')+'%.2f %.2f'%xy(p[0],p[2]) for i,p in enumerate(points));svg.append(f'<path d="{path}" fill="none" stroke="#e08a13" stroke-width="5" stroke-linejoin="round"/>')
texts=[('蓝：80.9 × 65.9 × 26 mm 充电宝',105),('黑：边缘承托，底端中央 54 mm 开放',138),('绿：唯一 5991 放到自带线出口附近',171),('橙：自带 USB-C → 5991（长度待实物摆线）',204),('红：髋俯仰 +30°，原机器人此姿态无所测源碰撞',250),('现低背托与小腿相交 17.18 mm³',278),('电池后移 20 mm，仍有 6 条源基线清楚姿态的新碰撞',306),('不能据此限制原关节范围或直接打印',334),('两端不做窄插头孔；底部 USB-C/A 均保留开放入口',390),('备用：底部 USB-C 另接线到同一 5991',418),('墙充与充电宝二选一；ISET 配置也须相应切换',446),('5991 的托/绑带最终固定未完成，绿色只是接收位置',474),('完整范围：左右 yaw/roll/pitch 各13点 + 27组合/侧',540),('去重133姿态：32有源碰撞，101未发现这些源碰撞',568),('无实物承重、重心、动态步态或供电验收',596)]
for txt,y in texts:svg.append(f'<text x="520" y="{y}" font-size="15" fill="#293845">{txt}</text>')
svg.append('</g></svg>');(D/'pb1033mi-backpack-side-view.svg').write_text('\n'.join(svg))
base=json.loads((D/'source-leg-motion-domain.json').read_text());blocked={r['state'] for r in base['intersections']};negative=json.loads((D/'negative-low-backpack-motion.json').read_text());alts=json.loads((D/'finite-pose-alternatives.json').read_text());report={'status':'not accepted; not in print package','printedPartRelease':False,'physicalAccepted':False,'motion':{'poses':133,'sourceBlocked':len(blocked),'sourceClear':133-len(blocked),'originalCandidateClearDomainFailures':sum(r['state'] not in blocked for r in negative['failures']),'alternativesClearDomainFailures':{k:sum(r['state'] not in blocked and r['obstacle']==k for r in alts['failures']) for k in alts['bounds']}},'openEndIllustration':{'centralBottomOpeningWidthMm':54,'noPlugSpecificHoles':True,'loadOnOuterEdgeFeet':True,'dynamicRecheck':False},'chargingCable':{'illustrationOnly':True,'pointsMm':points,'polylineLengthMm':sum(math.dist(a,b) for a,b in zip(points,points[1:])),'radiusMm':1.5,'stockLengthNotPublished':True,'wireNotCollisionVerified':True,'contactsAndMouldingsNotDimensionallyVerified':True,'alternative':'bottom USB-C optional separate lead to same single5991; no parallel supply','receiverMountPending':True},'sourceHashes':{str(p):sha(p) for p in [Path(__file__),D/'negative-low-backpack-motion.json',D/'finite-pose-alternatives.json',D/'source-leg-motion-domain.json',D/'open-bottom-illustration-world.stl',D/'near-exit-5991-illustration-world.stl',D/'charging-cable-illustration-world.stl',D/'pb1033mi-backpack-side-view.svg']}}
(D/'mechanical-disposition.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report['motion']));print('illustration body',len(preview.split()),'watertight',preview.is_watertight)
