from pathlib import Path
import json
import conditional_u_route as c
D=Path(__file__).resolve().parent
rows=[]
for width in [11.5,8.,5.]:
 for lead in [.5,1.,1.5]:
  for gap in [.3,.5]:
   top=c.pi[1]+3+lead+.3+gap;r=c.make(top=top,width=width,lead=lead);st=c.self_test(r[4],r[3]);row={**r[-1],'targetInterRibbonGapMm':gap,'selfCheck':st};rows.append(row);print(json.dumps({k:row[k] for k in ['middleWidthMm','outsidePiStraightLeadMm','topYmm','intersectionsMm3']}|{'gap':st['minimumNonlocalSolidGapMm'],'selfPairs':len(st['nonadjacentCellIntersections'])}),flush=True)
   if not r[-1]['intersectionsMm3'] and not st['nonadjacentCellIntersections'] and st['minimumNonlocalSolidGapMm']>=.29:
    tag=f"w{width:g}-lead{lead:g}-gap{gap:g}";r[1].export(D/f'conditional-{tag}-world.stl');(D/f'conditional-{tag}-centerline.json').write_text(json.dumps({'points':r[2].tolist(),'row':row},indent=2)+'\n')
(D/'conditional-lead-search.json').write_text(json.dumps({'scope':'Finite thinner-middle-body sensitivity. All dimensions/R3 remain receiving assumptions, not actualSC1892 certification. Same200mm length and all final obstacles.','rows':rows},indent=2)+'\n')
