"""Pure-standard-library constant-length rolling-U geometry.

This defines a kinematic *candidate*, not a cable mechanics or clearance proof.
Angles are radians. The radial basis and joint axis are an orthonormal triad.
Two equal-radius arcs occupy parallel planes. A semicircle travels at half the
joint angle, joining opposite tangents. Its ideal length is exactly independent
of q: 2*R*C + pi*d/2. No per-pose optimizer or family switching is used.
"""
import math

def add(a,b):return [x+y for x,y in zip(a,b)]
def scale(a,s):return [x*s for x in a]
def cross(a,b):return [a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]
def dot(a,b):return sum(x*y for x,y in zip(a,b))
def length(a):return math.sqrt(dot(a,a))
def unit(a):return scale(a,1/length(a))
def distance(a,b):return length([x-y for x,y in zip(a,b)])
def linspace(a,b,n):return [a+(b-a)*i/n for i in range(n+1)]
def rolling_loop(center,axis,radial,radius,separation,neutral_half_angle,q,step=.5):
 axis=unit(axis);radial=unit(radial);assert abs(dot(axis,radial))<1e-10
 e2=cross(axis,radial);R=radius;d=separation;C=neutral_half_angle
 assert R>0 and d>0 and C>abs(q)/2, 'Both arc spans must stay positive'
 assert C+abs(q)/2<2*math.pi, 'Do not let an individual arc complete a full turn'
 theta=C+q/2
 def polar(t):return add(scale(radial,math.cos(t)),scale(e2,math.sin(t)))
 def point(t,z):return add(center,add(scale(polar(t),R),scale(axis,z)))
 first=linspace(0,theta,max(2,math.ceil(R*theta/step)))
 last=linspace(theta,q,max(2,math.ceil(R*(theta-q)/step)))
 tangent=add(scale(radial,-math.sin(theta)),scale(e2,math.cos(theta)))
 join_center=point(theta,d/2)
 # At u=0: lower arc tangent +e_theta. At u=pi: upper arc -e_theta.
 bend=[add(join_center,add(scale(axis,-d/2*math.cos(u)),scale(tangent,d/2*math.sin(u)))) for u in linspace(0,math.pi,max(2,math.ceil(math.pi*d/2/step)))]
 points=[point(t,0) for t in first]+bend[1:]+[point(t,d) for t in last[1:]]
 return {'points':points,'analyticLengthMm':2*R*C+math.pi*d/2,'polylineLengthMm':sum(distance(a,b) for a,b in zip(points,points[1:])),'minimumCenterlineRadiusMm':min(R,d/2),'arcAnglesRadians':[theta,theta-q],'lowerAnchor':point(0,0),'upperAnchor':point(q,d),'joiningUAngleRadians':theta,'startTangent':e2,'endTangent':scale(add(scale(radial,-math.sin(q)),scale(e2,math.cos(q))),-1)}

def self_test():
 rows=[]
 for deg in range(-170,171,5):
  q=math.radians(deg);r=rolling_loop([0,0,0],[0,0,1],[1,0,0],18,24,math.radians(95),q,.25)
  assert abs(r['analyticLengthMm']-(36*math.radians(95)+12*math.pi))<1e-10
  assert 0<=r['analyticLengthMm']-r['polylineLengthMm']<.01
  assert distance(r['upperAnchor'],[18*math.cos(q),18*math.sin(q),24])<1e-10
  assert r['minimumCenterlineRadiusMm']==12
  rows.append(r['polylineLengthMm'])
 return {'testedAngles':69,'analyticLengthMm':36*math.radians(95)+12*math.pi,'minimumCenterlineRadiusMm':12,'maxChordApproximationLossMm':36*math.radians(95)+12*math.pi-min(rows),'clearanceTested':False,'selfIntersectionTested':False,'fatigueTested':False}
if __name__=='__main__':
 import json
 print(json.dumps(self_test(),indent=2))

def planar_rolling_loop(center,axis,radial,inner_radius,radial_separation,neutral_angle,q,step=.5):
 """Concentric planar rolling loop, avoiding the two-level loop's axial tower.

 Equal straight radial span across a semicircle; U-bend travels by
 outer/(inner+outer) * q. This is a position/length family, not a built guide.
 """
 axis=unit(axis);radial=unit(radial);assert abs(dot(axis,radial))<1e-10
 e2=cross(axis,radial);ri=inner_radius;ro=ri+radial_separation;h=radial_separation/2;C=neutral_angle
 theta=C+ro/(ri+ro)*q
 assert 0<theta<2*math.pi and 0<theta-q<2*math.pi
 def polar(t):return add(scale(radial,math.cos(t)),scale(e2,math.sin(t)))
 def point(t,r):return add(center,scale(polar(t),r))
 tangent=add(scale(radial,-math.sin(theta)),scale(e2,math.cos(theta)))
 join_center=point(theta,(ri+ro)/2)
 bend=[add(join_center,add(scale(polar(theta),-h*math.cos(u)),scale(tangent,h*math.sin(u)))) for u in linspace(0,math.pi,max(2,math.ceil(math.pi*h/step)))]
 points=[point(t,ri) for t in linspace(0,theta,max(2,math.ceil(ri*theta/step)))]+bend[1:]+[point(t,ro) for t in linspace(theta,q,max(2,math.ceil(ro*(theta-q)/step)))[1:]]
 return {'points':points,'analyticLengthMm':(ri+ro)*C+math.pi*h,'polylineLengthMm':sum(distance(a,b) for a,b in zip(points,points[1:])),'minimumCenterlineRadiusMm':min(ri,h),'arcAnglesRadians':[theta,theta-q],'lowerAnchor':point(0,ri),'upperAnchor':point(q,ro),'joiningUAngleRadians':theta}
