"""Enhance the existing electrical ledger without changing its nets or print parts."""
from pathlib import Path
import json,copy,hashlib
G=Path(__file__).resolve().parent;P=G/'wiring-guide-data.json';baseline=G/'wiring-current-sources/electrical-ledger-before-ui-repair.json'
if not baseline.exists():baseline.write_bytes(P.read_bytes())
w=json.loads(baseline.read_text());con=w['connections'];by={c['id']:c for c in con}
groups=[{'id':'left-leg','title':'左腿 · 五个电机','description':'ID6→7→8→9→10 数据链；F4给6/7，F5给8/9。ID10供电在躯干共享F3，不是腿内串供。','connectionIds':['data-12','data-13','data-14','data-15','motor-F4','motor-F5']},{'id':'right-leg','title':'右腿 · 五个电机','description':'ID5→4→3→2→1 数据链；F2给3/4，F1给1/2。ID5供电在躯干共享F3。','connectionIds':['data-07','data-08','data-09','data-10','motor-F2','motor-F1']},{'id':'head','title':'头部、颈部与相机','description':'Pi物理针脚供电，USB接OpenRB；CSI同时供相机电源和数据。','connectionIds':[c['id'] for c in con if c['id'] in ['motor-F6','motor-F7','motor-F8','data-01','data-02','data-03','data-04','data-05','pi-5v-2','pi-5v-4','pi-gnd-6','pi-gnd-14','pi-otg','openrb-usb','camera-ribbon'] or c['id'].startswith('audio-') or c['id']=='speaker']},{'id':'torso-power','title':'躯干电源与保险支路','description':'墙充→5991→输入保险→XT30→DFR1202；F3分别给两髋ID5/10。底部是十一保险托，不是电池。','connectionIds':['charger-usb','input-fuse','input-return','regulator-input','star-output','motor-main','pi-fuse','audio-fuse','motor-F3','data-06']},{'id':'data','title':'跨腿数据、IMU与公共地','description':'1→6必须沿右腿上行、经躯干、沿左腿下行；不要在两踝间悬挂短线。','connectionIds':['data-11','openrb-ground','imu-vin','imu-sda','imu-scl','imu-gnd']}]
assert set(x for g in groups for x in g['connectionIds'])==set(by)
for c in con:
 cid=c['id'];c['groupIds']=[g['id'] for g in groups if cid in g['connectionIds']];c['moduleId']=c['groupIds'][0];c['lengthEvidence']={'text':c['wire'],'kind':'existing design target or purchased nominal length; not a measured free flexible span','source':'design-contract.json / motor-harness-reach.json','physicalLengthConfirmed':False}
 prep=[f"准备这一路：{c['from']} → {c['to']}。",f"线材/数量：本连接所列导体各1根；{c['wire']}。",'断开墙充与XT30，再操作接头。']
 assemble=[f"按标记接 {c['from']} 到 {c['to']}；压住插头壳体直插，焊接端先完成绝缘和应变卸载。"]
 check=['核对两端信号/极性；插头完全就座，导体和焊点无裸露。','确认剩余线长不被关节、螺丝或盖壳夹住，再固定线束。']
 if cid.startswith('data-'):
  prep=[f"准备1根 Robot Cable-X3P；{c['wire']}。",'使用JST EHR-3三针壳；源端仅保留3 DATA，1 GND/2 VDD按现分支方案隔离；接收端1/2接该电机独立电源尾线。','先读电机ID标签；ID是计划编号，不代表电机已写入。']
  assemble=[f"先将接收端插进 {c['to']} 的空闲JST-EH口，再沿所属连杆整理余线，最后插入 {c['from']} 的空闲口。",'电机两个插口电气并联，无固定IN/OUT；按已贴线标签区分来线和去线，勿把两端都接到同一台电机。']
  check=['逐端确认3 DATA连续，而相邻供电分支的2 VDD不互通；不能插回未经改线的三芯直通线旁路分支保险。','扭矩关闭时慢慢活动相关关节，确认线在转轴外侧自然弯曲、不绷紧，也不进入髋/膝夹缝。']
  if cid=='data-11':assemble[0]='从ID1沿右腿向上，经固定躯干，再沿左腿向下到ID6。采用400mm成品总长设计目标（180mm原线加约220mm），不是踝到踝直连。'
  c['connectorType']='jst-eh-3';c['lengthEvidence']['source']='motor-harness-reach.json; official XL330 bundled Robot Cable-X3P180mm'
 elif cid.startswith('motor-F'):
  prep=[f"准备 {c['wire']}；每台电机各有5V、GND两根尾线。",f"从 {c['from']} 给 {c['to']}，保留原厂JST-EH压接端。"]
  assemble=['先在无电状态做好支路的绝缘分叉：保险输出只接各电机2 VDD，公共地只接各电机1 GND。','再将含该电机DATA来线的三针接收插头直插到电机；另一插口作为下一段DATA出线。']
  check=['每台电机各自取电，不让两台电机电流经同一小插头串接。','移除对应保险后，该组VDD应隔离；GND保持公共连接，3 DATA仍按数据链连接。']
  if cid=='motor-F3':assemble.insert(0,'F3是跨侧共享支路：分别给右髋ID5、左髋ID10；不是两个髋之间的串联电源线。')
 elif cid.startswith('pi-5v-') or cid.startswith('pi-gnd-'):
  pin=int(cid.rsplit('-',1)[1]);signal='5 V' if '5v' in cid else 'GND';prep=[f"准备1根 {c['wire']}；这一根只接Pi物理{pin}脚 {signal}。",'找到实板1脚标记，按物理针号数，不按GPIO编号数。']
  assemble=[f"将这根母压接端固定在对应物理{pin}脚位置，沿排针方向直插，不能跨一行/错一格。",'四根供电线是一组：F9输出分别到2/4，公共地分别到6/14；Pi PWR IN口保持空置。']
  check=[f"确认这根落在物理{pin}脚；2/4是5V，6/14是地，绝不能将5V插到1脚3.3V。",'断电测量5V与GND无短接；插好后轻拉绝缘线确认端子锁住。']
 elif cid=='camera-ribbon':
  prep=['准备用户照片确认的 Standard–Mini 200mm排线1根，15触点端接Camera Module3，22触点端接Pi Zero。','相机电源与数据都由这一条CSI排线传输；不另接5V/GND电源线。']
  assemble=['先打开相机和Pi的锁扣，按实际触点面方向将两端加固段平直插到底，再分别扣紧锁片。','保持两端直段平整，用自然缓弯整理全部余线，然后观察合盖；模型橙线是摆放例子，不是要求复制的固定折线。']
  check=['两个锁扣均闭合，端面平齐，未斜插；轻放余线后，盖壳不夹排线。','当前完整200mm数字样例已通过几何、自交与合盖检查；实际图像、供电和对焦仍需上机检查。']
  c['physical_cable_identification_confirmed']=True;c['lengthEvidence']={'text':'200 mm nominal total','kind':'manufacturer nominal + user photo exact Standard-Mini identity','physicalLengthConfirmed':False};c['notes']=['CSI carries camera power and data; no independent camera supply.','Flexible placement example, not a rigid folding template.']
 elif cid in ['pi-otg','openrb-usb']:
  prep=[f"准备1根 {c['wire']}。",'SC0727标称80mm与4472标称152mm是整件长度，不等于可弯曲线段长度。']
  assemble=['先在未合盖且接口可达时插Pi标USB的Micro-B口（不是PWR IN），另一端接USB-A母头。' if cid=='pi-otg' else '把4472的USB-A公头插入SC0727母头；USB-C端从后服务口直插OpenRB。','先让插头通过对应开口，再整理余线；不要两端都固定以后才试图穿壳。']
  check=['两端插妥、接头周围有拔插空间；无牵拉PCB、挤压线尾或夹盖。','这是Pi USB主机到OpenRB的数据/逻辑电源连接，不给15个电机经USB串供电。']
 elif cid.startswith('imu-'):
  prep=[f"本步骤对应4397四芯线的一芯：{c['pins'][0]['signal']}，{c['from']} → {c['to']}。",'4397成品标称150mm；旧250mm是接长目标，不是已购成品长度。保留JST-SH四针整头，不逐芯强插。']
  assemble=['先按VIN/GND/SDA/SCL核对四芯顺序，整只JST-SH插入BNO085 STEMMA QT口。',f"再将本芯Pi母端接 {c['from']}；颈部留自然余量，不绷跨转轴。"]
 elif cid=='speaker':
  prep=['准备两根头内多股线；MAX98357A接端子，另一端焊扬声器两焊盘，长度按实际头内路径留余量。']
  assemble=['功放speaker+接扬声器标记+焊盘；speaker−接另一焊盘；固定线后再安装扬声器压盖。','两根扬声器输出都不能接公共地。']
  check=['螺钉端子夹住导体，焊盘绝缘并有应变卸载；线不穿过扬声器/压盖接触面。','扬声器8Ω/1W，初次测试从低音量开始。']
 c['tutorial']={'prepare':prep,'assemble':assemble,'check':check};c['assemblyOrder']={'powerDisconnected':True,'connectorBeforeClosure':cid.startswith(('pi-','imu-','audio-')) or cid in ['camera-ribbon','speaker'],'sequence':assemble}
for st in w['steps']:
 st['connections']=[copy.deepcopy(by[cid]) for cid in st['connectionIds']]
 if st['id']=='camera':st['actions']=by['camera-ribbon']['tutorial']['assemble'];st['check']=by['camera-ribbon']['tutorial']['check'][0]
 if st['id']=='pi-usb':st['check']='供电母端分别接物理2/4与6/14；当前头部显示采用V1.4实际Pi姿态，接收空间不是实物验证。'
w['groups']=groups;w['currentPowerSource']='wall charger; PB1033MI deferred, not in V1.4';w['geometryStatus']='Current head scene overlay; source-backed Pi pin frames; unknown connector poses explicitly unverified.'
w['repairSource']={'baselineSha256':hashlib.sha256(baseline.read_bytes()).hexdigest(),'scriptSha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'electricalTopologyChanged':False}
P.write_text(json.dumps(w,ensure_ascii=False,indent=2)+'\n');print('51 connections',len(con),'groups',[(g['id'],len(g['connectionIds']))for g in groups])
