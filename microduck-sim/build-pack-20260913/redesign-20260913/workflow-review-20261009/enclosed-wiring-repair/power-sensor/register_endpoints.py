"""Register purchased BNO085 source ports, without a routing search or CAD preload."""
from pathlib import Path
import json,struct,hashlib,xml.etree.ElementTree as ET
D=Path(__file__).resolve().parent
src=D/'sources/bno085.stl';board=D/'sources/bno085.brd'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
# Existing IMU receiving envelope is X[-61,-53],Y[-14,14],Z[2.5,27.5].
# Define installation: PCB backside X=-53, component face outward (-X),
# board long axis along Y, board short axis along Z. Do not infer this from
# the old box: it is the now explicit installation orientation.
SOURCE_TO_WORLD=[[0,0,-1,-53],[1,0,0,-12.7],[0,-1,0,26.43],[0,0,0,1]]
def determinant3(T):return T[0][0]*(T[1][1]*T[2][2]-T[1][2]*T[2][1])-T[0][1]*(T[1][0]*T[2][2]-T[1][2]*T[2][0])+T[0][2]*(T[1][0]*T[2][1]-T[1][1]*T[2][0])
assert determinant3(SOURCE_TO_WORLD)==1
assert determinant3([[0,0,-1],[1,0,0],[0,1,0]])==-1 # Rejected historical reflection.
def world(q):x,y,z=q;return [-53-z,x-12.7,26.43-y]
b=bytearray(src.read_bytes());count=struct.unpack_from('<I',b,80)[0];lo=[float('inf')]*3;hi=[-float('inf')]*3
for i in range(count):
 off=84+50*i;v=struct.unpack_from('<12f',b,off);n=v[:3];newn=[-n[2],n[0],-n[1]];pts=[world(v[j:j+3]) for j in [3,6,9]]
 for p in pts:
  for k in range(3):lo[k]=min(lo[k],p[k]);hi[k]=max(hi[k],p[k])
 struct.pack_into('<12f',b,off,*newn,*pts[0],*pts[1],*pts[2])
out=D/'bno085-installed-reference-world.stl';out.write_bytes(b)
r=ET.parse(board).getroot();bd=r.find('.//board');nets={}
for s in bd.findall('./signals/signal'):
 for c in s.findall('contactref'):
  if c.get('element') in ['CONN3','CONN4']:nets[(c.get('element'),c.get('pad'))]=s.get('name')
ports=[]
for name,x,outward,sign in [('CONN4',.065,[0,-1,0],-1),('CONN3',25.335,[0,1,0],1)]:
 pins=[]
 for pin in range(1,5):
  y=11.43+sign*(-1.5+pin-1)
  pins.append({'number':pin,'net':nets[(name,str(pin))],'contactMouthProjectionWorldMm':world([x,y,3.535])})
 ports.append({'id':name,'connector':'JST SH 4-pin / STEMMA QT','mouthPlaneWorldMm':world([x,11.43,3.08]),'outwardAxis':outward,'insertionAxis':[-v for v in outward],'componentNormalWorld':[-1,0,0],'sourceCavitySectionMm':{'y':[9.23,13.63],'z':[2.03,4.13]},'sourceMouthXmm':x,'pins':pins,'evidence':'Official STL planar mouth wall and cavity section; EAGLE CONN3 R90 / CONN4 R270 pad/net mapping. Mated cable housing and installation path are separate checks.'})
report={'problemIds':['P0','P5','P6'],'sku':'Adafruit4754, received DigiKey1528-4754-ND','registrationStatus':'Manufacturer board-local port geometry and nets registered; explicit installed orientation defined inside existing receiving envelope. Holder engagement and mated plug clearance not yet checked.','sourceToWorld':SOURCE_TO_WORLD,'rotationDeterminant':determinant3(SOURCE_TO_WORLD),'supersedesInvalidMirroredRegistration':True,'actualOfficialModelBoundsWorldMm':[lo,hi],'existingReceivingBoundsMm':[[-61,-14,2.5],[-53,14,27.5]],'allSourceVerticesInsideOldReceivingBounds':all(lo[i]>=[-61,-14,2.5][i]-1e-5 and hi[i]<=[-53,14,27.5][i]+1e-5 for i in range(3)),'boardOutlineMm':[25.4,22.86],'fullComponentHeightMm':4.53,'ports':ports,'selectedForNextRoute':'CONN4 faces world negativeY, with both cable and enclosure present during future checks','sourceHashes':{str(p):sha(p) for p in [src,board,Path(__file__)]},'output':str(out),'outputSha256':sha(out),'physicalFitVerified':False}
(D/'bno085-endpoint-registration.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'bounds':[lo,hi],'ports':ports,'file':str(out)}))
