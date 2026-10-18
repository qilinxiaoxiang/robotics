from pathlib import Path
import json,numpy as np
import conditional_u_route as c
D=Path(__file__).resolve().parent
front=35.9

def route(lowY,left=53.5,top=37.2886208,r=3.,lead=1.):
 wp=np.array([c.cam-[0,5,0],[c.cam[0],front,c.end_z],[70.8,front,c.end_z],[66,top,c.end_z],[left,top,c.end_z],[left,lowY,c.end_z],[left+6,lowY,c.end_z],[left+6,c.pi[1]+r+lead,c.end_z],[c.pi[0],c.pi[1]+r+lead,c.end_z],c.pi-[0,4.4,0]])
 wp[-1,2]=c.end_z;cuts=[]
 for i in range(1,len(wp)-1):
  u=wp[i]-wp[i-1];u/=np.linalg.norm(u);v=wp[i+1]-wp[i];v/=np.linalg.norm(v);theta=np.arccos(np.clip(u@v,-1,1));d=r*np.tan(theta/2);axis=np.cross(u,v);axis/=np.linalg.norm(axis);a=wp[i]-u*d;b=wp[i]+v*d;center=a+np.cross(axis,u)*r;cuts.append((a,b,center,axis,theta,d))
 for i in range(len(wp)-1):assert np.linalg.norm(wp[i+1]-wp[i])+1e-6>=(cuts[i-1][5] if i else 0)+(cuts[i][5] if i<len(cuts) else 0)
 pts=[wp[0]];total=0.;prev=wp[0]
 for a,b,center,axis,theta,d in cuts:
  le=np.linalg.norm(a-prev)
  if le>1e-7:pts.extend(np.linspace(prev,a,max(1,int(np.ceil(le/.1)))+1)[1:])
  total+=le;va=a-center
  for ang in np.linspace(0,theta,max(2,int(np.ceil(r*theta/.1)))+1)[1:]:pts.append(center+va*np.cos(ang)+np.cross(axis,va)*np.sin(ang))
  total+=r*theta;prev=b
 le=np.linalg.norm(wp[-1]-prev);pts.extend(np.linspace(prev,wp[-1],max(1,int(np.ceil(le/.1)))+1)[1:]);return np.array(pts),total+le,wp
c.route=route
if __name__=='__main__':
 rows=[]
 for width in [11.5,8.,5.]:
  for lead in [.5,1.,1.5]:
   top=c.pi[1]+3+lead+.3+.5
   r=c.make(top=top,width=width,lead=lead);st=c.self_test(r[4],r[3]);row={**r[-1],'selfCheck':st};rows.append(row);print(json.dumps({k:row[k] for k in ['middleWidthMm','outsidePiStraightLeadMm','intersectionsMm3']}|{'gap':st['minimumNonlocalSolidGapMm'],'selfPairs':len(st['nonadjacentCellIntersections'])}),flush=True)
   if not row['intersectionsMm3'] and not st['nonadjacentCellIntersections']:
    tag=f'w{width:g}-lead{lead:g}';r[1].export(D/f'conditional-S-{tag}-world.stl');(D/f'conditional-S-{tag}-centerline.json').write_text(json.dumps({'points':r[2].tolist(),'row':row},indent=2)+'\n')
 (D/'s-bend-lead-search.json').write_text(json.dumps({'scope':'Finite S-bend amendment; assumed body dimensions, no physical certification.','rows':rows},indent=2)+'\n')
