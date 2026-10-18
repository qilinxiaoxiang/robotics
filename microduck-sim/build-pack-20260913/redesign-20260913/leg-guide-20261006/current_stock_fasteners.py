"""Current user-stock instructions; preserves the immutable geometry evidence input.

The historical integral-seat proposal remains verified evidence, but is not the
V1.3 printing choice. No printed mesh is generated or changed here.
"""
import copy
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
REVISION='v1.4-integral-neck-existing-legs-m2x6'

def apply_current_stock_fasteners(base, effective):
    result=copy.deepcopy(effective)
    originals={p['key']:p for p in base['parts']}
    for i,p in enumerate(result['parts']):
        if p['key'] in ('lower','right_lower'):
            result['parts'][i]=copy.deepcopy(originals[p['key']])
    old={c['id']:c for c in base['screws']}
    knee=('S07-horn-','S02-horn-')
    knee_note=('保留已完成的腿。你已确认膝部装的是 M2×6 TAP；原件栈厚 2.8 mm，名义进入 3.2 mm，高于厂家 3 mm 上限。这不证明已经损伤，也不能把原件直接配 6 mm 当作已验收。不要为本次头部增量包拆开已压入的脚踝。既有小外径金属垫片方案只有条件几何验证，尚非已完成的实物修复；M2×4 只有 1.2 mm 进入深度，不能直接替代。')
    neck_note=('V1.4：更换黑色颈俯仰U架（原community28）为四处一体加厚1 mm的版本，使用四颗M2×6 TAP，不再加独立垫圈。名义进入2.10044 mm，距3 mm孔深上限余0.89956 mm。四处孔已在新模型清通；这是颈支架，不是黄色头底壳。')
    imu_note=('两颗 M2×6 TAP 作顶压螺丝；尖端接触导轨即停，头部保留1.8 mm间隙，不拧到贴平，不加垫片或螺母。M2×4在尖端接触前已头部到底，不能夹紧。无需重打夹座。')
    for c in result['screws']:
        cid=c['id']
        if cid.startswith(knee) and old[cid].get('length_mm')==5:
            saved=copy.deepcopy(old[cid]);c.clear();c.update(saved)
            c.update(spec='M2 x 6 TAP',length_mm=6,engagement_mm=[3.2,3.2],penetration_mm=[3.2,3.2],passed=False)
            c['fastenerRevision']={'id':REVISION,'kind':'user-confirmed-installed-knee','notice':knee_note,'physicalRepairAccepted':False,'stockStatus':'already installed; not a new purchase requirement'}
            c['evidence']='User-confirmed installed length; 3.2 mm nominal entry is not accepted against the 3 mm maximum.'
        elif cid.startswith('S13-horn-') and old[cid].get('length_mm')==5:
            c['fastenerRevision']={'id':REVISION,'kind':'integral-neck-seat','notice':neck_note,'requiresRevisedPart':'neck_pitch','physicalFitVerified':False}
            c['evidence']=neck_note
        elif cid.startswith('E-imu_clamp-'):
            c['fastenerRevision']={'id':REVISION,'kind':'pressure-screw','notice':imu_note,'headStandOffAtContactMm':1.8,'requiresRevisedPart':None}
            c['evidence']=imu_note
    texts={'left-leg-10':knee_note,'right-leg-10':knee_note,'neck-04':neck_note+' 在独立台架上完成这四颗，再装到ID11。','imu-02':imu_note}
    for module in result['modules']:
        for op in module['operations']:
            if op['id'] in texts:op['text']=texts[op['id']]
    # Recompute the current BOM; do not retain the historical M2x5 aggregate.
    totals={}
    for c in result['screws']:totals[c['spec']]=totals.get(c['spec'],0)+c.get('quantity',1)
    result['screwTotals']=totals
    paths=[ROOT.parent/'fastener-review-20261008/fastener-choice-report.json',ROOT.parent/'fastener-review-20261008/neck_pitch-m2x6-seat-world.stl']
    for p in result['parts']:
        if p['key']=='neck_pitch':p['fastenerRevision']['notice']=neck_note
    result['fastenerRevision']={'id':REVISION,'partKeys':['neck_pitch'],'screwIds':[c['id'] for c in result['screws'] if c.get('fastenerRevision')],'physicalFitVerified':False,'historicalProposalId':effective['fastenerRevision']['id'],'evidenceHashes':{str(p.relative_to(ROOT.parent)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},'scope':'Current V1.4 integral neck and existing legs. Reuses verified neck geometry. Existing knee condition remains unresolved; no forced dismantling. Head 3D remains the labeled legacy reference.'}
    return result
