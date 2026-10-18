"""Audit complete native plates with bounded streaming footprint readback."""
import json,sys
from pathlib import Path
D=Path(__file__).resolve().parent
sys.path.insert(0,str(D.parent/'13-RELEASE-PIPELINE-20261009'))
import release_pipeline as rp
prep=rp.read(D/'run/preparation.json'); rows=[]
for row in prep['rows']:
    c,m=row['color'],row['machine']
    result=rp.read(D/'run/native'/f'{c}_{m}'/'result.json')
    assert result['preparation']==rp.ref(D/'run/preparation.json')
    archive=rp.bound(result['archive']);g,cfg,imgs=rp.native_payload(archive)
    first,fp=rp.first_layer(g,rp.bound(row['project']),m)
    assert len(first)==sum(p['quantity'] for p in prep['parts'] if p['color']==c)
    expected={p['key']+'_'+str(i+1) for p in prep['parts'] if p['color']==c for i in range(p['quantity'])}
    assert {p['name'] for p in first}==expected
    bb=list(fp['allLayerModelSupportBrimBounds'].values())
    extent=[min(b[0]for b in bb),min(b[1]for b in bb),max(b[2]for b in bb),max(b[3]for b in bb)]
    center=[(extent[0]+extent[2])/2,(extent[1]+extent[3])/2]
    rows.append(dict(color=c,machine=m,archive=rp.ref(archive),estimatedSeconds=rp.time_seconds(g,m),firstLayer=first,footprint=fp,completeExtent=extent,completeCenter=center))
    if m=='Bambu':(archive.parent/'plate-preview.png').write_bytes(imgs['Metadata/plate_1.png'])
    print(c,m,'seconds',rows[-1]['estimatedSeconds'],'first layers',[(x['name'],round(x['model_area_mm2'],2),x['modelIslands'])for x in first],'center',center,flush=True)
issues=[dict(color=r['color'],machine=r['machine'],pair=p)for r in rows for p in r['footprint']['pairs']if p['conservativeGapMm']<4]
rp.write(D/'run/first-layer-review.json',dict(passed=not issues,preparation=rp.ref(D/'run/preparation.json'),rows=rows,issues=issues))
assert not issues,issues
