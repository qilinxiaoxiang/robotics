#!/usr/bin/env python3
"""Investigate existing OpenRB nut entry and a minimal cap-mouth relief candidate.

Writes this report and an explicitly separate candidate STL. No canonical guide, mesh, print project,
PCB or assembled hardware is changed.
"""
from pathlib import Path
import base64,hashlib,heapq,itertools,json,time
import numpy as np
import trimesh
import manifold3d as mf
HERE=Path(__file__).resolve().parent
GUIDE=HERE.parent/'leg-guide-20261006'

def main():
    blob=(GUIDE/'full-build-data.json').read_bytes();data=json.loads(blob);parts={p['key']:p for p in data['parts']};ss={};identity={}
    def solid(k):
        if k not in ss:
            p=parts[k];vb=base64.b64decode(p['positionB64']);ib=base64.b64decode(p['indexB64'])
            m=trimesh.Trimesh(np.frombuffer(vb,'<f4').reshape(-1,3),np.frombuffer(ib,'<u4').reshape(-1,3),process=True)
            ss[k]=mf.Manifold(mf.Mesh(np.asarray(m.vertices,np.float32),np.asarray(m.faces,np.uint32)))
            assert ss[k].status()==mf.Error.NoError,k
            identity[k]={'verticesSha256':hashlib.sha256(vb).hexdigest(),'trianglesSha256':hashlib.sha256(ib).hexdigest(),'boundsMm':m.bounds.tolist(),'sourceTransformWorld':p['sourceTransformWorld']}
        return ss[k]
    cap=solid('head_cap');keys=['nut_E-openrb-01','nut_E-openrb-03'];controls=['nut_E-openrb-02','nut_E-openrb-04']
    originals=[]
    for k in keys+controls:
        rows=[]
        for z in np.linspace(12,0,241):
            inter=solid(k).translate([0,0,z])^cap;v=max(0.,float(inter.volume()))
            rows.append({'translationMm':[0,0,float(z)],'overlapMm3':v,'intersectionBoundsMm':list(inter.bounding_box()) if v>1e-9 else None})
        originals.append({'key':k,'maxOverlapMm3':max(r['overlapMm3'] for r in rows),'finalOverlapMm3':rows[-1]['overlapMm3'],'samples':rows})
    # Bounded two-axis pose search. A successful result is checked against the
    # complete cap after planning. A failed finite search is not impossibility.
    k=keys[0];center=np.array(parts[k]['center']);nut0=solid(k).translate(-center)
    clip=mf.Manifold.cube([20,20,20],center=True).translate(center+[0,0,2]);obstacle=cap^clip
    searches=[]
    for plane,tilt_axis in [('XZ',1),('YZ',0)]:
        start_time=time.monotonic();cache={};parents={};best_cost={};edge_cache={}
        step=.05;angle_step=2.;max_h=40;max_z=80;max_angle=30;start=(0,0,0);goal=None;expanded=0
        def transform(state):
            horizontal,z,angle=state;offset=np.zeros(3);offset[0 if plane=='XZ' else 1]=horizontal*step;offset[2]=z*step
            degrees=np.zeros(3);degrees[tilt_axis]=angle*angle_step
            return nut0.rotate(degrees).translate(center+offset)
        def free(state):
            if state not in cache:
                b=transform(state);bounds=b.bounding_box()
                assert all(center[i]-10-1e-6<=bounds[i] and bounds[i+3]<=center[i]+10+(2 if i==2 else 0)+1e-6 for i in range(3))
                cache[state]=max(0.,float((b^obstacle).volume()))<1e-8
            return cache[state]
        def edge_free(a,b):
            pair=(a,b)
            if pair not in edge_cache:
                edge_cache[pair]=all(free(tuple(np.array(a)+(np.array(b)-a)*f)) for f in [.25,.5,.75,1])
            return edge_cache[pair]
        heap=[(4.,0.,start)];best_cost[start]=0.;free(start)
        directions=list(itertools.product([-1,0,1],repeat=3));directions.remove((0,0,0))
        while heap and expanded<12000 and time.monotonic()-start_time<75:
            _,cost,state=heapq.heappop(heap)
            if cost>best_cost[state]+1e-9:continue
            expanded+=1
            if state[1]>=max_z:goal=state;break
            for dh,dz,da in directions:
                nxt=(state[0]+dh,state[1]+dz,state[2]+da)
                if abs(nxt[0])>max_h or not 0<=nxt[1]<=max_z or abs(nxt[2])>max_angle:continue
                nc=cost+np.linalg.norm([dh*step,dz*step,da*.08])
                if nc>=best_cost.get(nxt,float('inf')):continue
                if not free(nxt) or not edge_free(state,nxt):continue
                best_cost[nxt]=nc;parents[nxt]=state;heapq.heappush(heap,(nc+(max_z-nxt[1])*step,nc,nxt))
        path=[]
        if goal:
            curr=goal
            while curr!=start:path.append(curr);curr=parents[curr]
            path.append(start);path.reverse()
            for a,b in zip(path,path[1:]):
                for f in np.linspace(0,1,9):
                    state=tuple(np.array(a)+(np.array(b)-a)*f)
                    assert max(0.,float((transform(state)^cap).volume()))<1e-8
        searches.append({'nutKey':k,'plane':plane,'tiltAxis':'XYZ'[tilt_axis],'translationGridMm':step,'rotationGridDegrees':angle_step,'edgeTranslationSpacingMmMaximum':step/4,'edgeAngleSpacingDegreesMaximum':angle_step/4,'horizontalRangeMm':[-2,2],'zOffsetRangeMm':[0,4],'angleRangeDegrees':[-60,60],'expandedStates':expanded,'testedConfigurations':len(cache),'elapsedSeconds':time.monotonic()-start_time,'found':bool(goal),'pathStates':path,'searchExhausted':not heap,'boundedResult':'validated sampled existing route' if goal else 'no route in this finite pose grid; not proof that all hand-tilt paths are impossible'})
        print('search',plane,searches[-1],flush=True)
    # Minimum axial roof relief: preserve the entire actual nut pocket and seat.
    # Remove only above the seated nut top +0.20mm. Hex mouth AF4.3 gives the
    # nominal AF4 nut0.15mm clearance at each flat; dimensions still need real fit.
    proposed=cap;cutters=[];specs=[]
    for k in keys:
        p=parts[k];c=np.array(p['center']);af=4.3;bottom=float(np.nextafter(np.float32(p['bounds'][1][2]+.2),np.float32(np.inf)));top=bottom+2.
        mesh=trimesh.creation.cylinder(radius=af/np.sqrt(3),height=top-bottom,sections=6)
        mesh.apply_translation([c[0],c[1],(bottom+top)/2])
        cutter=mf.Manifold(mf.Mesh(np.asarray(mesh.vertices,np.float32),np.asarray(mesh.faces,np.uint32)))
        cutters.append(cutter);proposed=proposed-cutter
        specs.append({'nutKey':k,'worldHexCenterXYMm':c[:2].tolist(),'hexAcrossFlatsMm':af,'nominalNutAcrossFlatsMm':4.,'radialFlatClearanceMm':.15,'worldCutZMm':[float(bottom),float(top)],'nutSeatAndPocketProtectedBelowWorldZMm':float(bottom),'bodyFrameNutCenterMm':(np.linalg.inv(np.array(parts['head_cap']['sourceTransformWorld']))@np.r_[c,1])[:3].tolist(),'bodyFrameHexVerticesYZMm':[[float(c[1]+af/np.sqrt(3)*np.sin(a)),float(-48.75-af/np.sqrt(3)*np.cos(a))] for a in np.arange(6)*np.pi/3],'bodyFrameCutAxis':'+X','bodyFrameCutRangeXMm':[float(bottom-115.6146),float(top-115.6146)]})
    cutter_union=cutters[0]+cutters[1]
    removed=cap^cutter_union
    subtraction_residual=abs(float((cap-proposed).volume())-float(removed.volume()))
    assert subtraction_residual<1e-5
    routes=[]
    for k in keys+controls:
        rows=[]
        for z in np.linspace(12,0,241):
            inter=solid(k).translate([0,0,z])^proposed
            rows.append({'translationMm':[0,0,float(z)],'overlapMm3':max(0.,float(inter.volume()))})
        peak=max(r['overlapMm3'] for r in rows)
        assert peak<1e-8,(k,peak)
        routes.append({'key':k,'maxOverlapMm3':peak,'samples':rows})
    # All geometry at/below the actual seated nuts remains identical. Do not
    # mistake smaller removed volume for a load/strength certification.
    protected_limit=min(x['nutSeatAndPocketProtectedBelowWorldZMm'] for x in specs)
    protect=mf.Manifold.cube([300,300,300]).translate([-100,-150,protected_limit-300])
    protected_removed=max(0.,float((removed^protect).volume()))
    assert protected_removed<1e-8
    assert proposed.status()==mf.Error.NoError and proposed.num_tri()>0
    candidate_mesh=proposed.to_mesh()
    candidate=trimesh.Trimesh(np.array(candidate_mesh.vert_properties)[:,:3],np.array(candidate_mesh.tri_verts),process=False)
    candidate.apply_transform(np.linalg.inv(np.array(parts['head_cap']['sourceTransformWorld'])))
    candidate_path=HERE/'head-cap-openrb-nut-mouth-candidate-body.stl'
    candidate.export(candidate_path)
    readback=trimesh.load_mesh(candidate_path,process=True).apply_transform(np.array(parts['head_cap']['sourceTransformWorld']))
    readback_solid=mf.Manifold(mf.Mesh(np.asarray(readback.vertices,np.float32),np.asarray(readback.faces,np.uint32)))
    assert readback_solid.status()==mf.Error.NoError and readback.is_watertight
    readback_peaks={}
    for key in keys+controls:
        peak=max(max(0.,float((solid(key).translate([0,0,z])^readback_solid).volume())) for z in np.linspace(12,0,241))
        assert peak<1e-8,(key,'exported STL entry',peak)
        readback_peaks[key]=peak
    report={'problemIds':['P5','P6'],'checked':'2026-10-08','sourceDataSha256':hashlib.sha256(blob).hexdigest(),'scriptSha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'sourceMeshIdentity':identity,'originalStraightEntries':originals,'boundedPoseSearch':searches,
      'recommendedCandidate':{'name':'Relieve only the two OpenRB roof-mouth corners above the existing nut pockets','baselineCapUnchangedOnDisk':True,'candidateMeshWritten':True,'candidateMeshPath':str(candidate_path),'candidateMeshSha256':hashlib.sha256(candidate_path.read_bytes()).hexdigest(),'candidateMeshFrame':'Original head-cap body coordinates (jaw_soft), NOT world frame','cuts':specs,'removedVolumeMm3':float(removed.volume()),'booleanDifferenceResidualMm3':subtraction_residual,'booleanNumericalConsistencyToleranceMm3':1e-5,'removedBoundsMm':list(removed.bounding_box()),'protectedNutPocketAndSeatRemovedVolumeMm3':protected_removed,'allFourAxialNutEntries':routes,'candidateManifoldStatus':str(proposed.status()),'candidateBodies':len(proposed.decompose()),'exportedStlReadback':{'watertight':bool(readback.is_watertight),'manifoldStatus':str(readback_solid.status()),'axialEntryPeakOverlapMm3':readback_peaks,'samplesPerNut':241,'sampleSpacingMm':.05},'mechanicalBoundary':'Preserves the complete original nut pocket, bearing floor, PCB posts and screw-axis registration by leaving all material at/below the nut top+0.20mm unchanged. Roof local stiffness, measured print clearance and actual hardware fit have not been verified.'},
      'materialEvidence':{'source':'../PRINTING/README.md and ../printing/10-SURFACE-QUALITY-20261006/README.md','documentedProfiles':'Ordinary PLA; X1 Carbon0.4mm Bambu PLA Basic and Elegoo retained PLA profiles. This identifies prepared jobs, not the actual cap material batch or strength.','physicalMaterialVerified':False,'forceRecommendation':'Do not specify a press force or use PCB bending as an assembly method. No measured force/strain/material data support forced seating. Load nuts into the detached cap before mounting the board; use a clearance route or revised opening.'},
      'recommendation':'Use the bounded roof-mouth relief if an existing clear manual path is not physically demonstrated. It permits the same straight axial entry as the two already-clear rear nuts while preserving the original capture pocket and bearing seat. Do not demand elastic PCB deformation. Integrate the two specified cuts into the new cap design and recheck against its new camera/eye geometry before release.',
      'physicalFitVerified':False,'safetyBoundary':'Digital candidate only. No print, machining, hardware force, fastener substitution or canonical assembly change was performed.'}
    (HERE/'nut-fit-investigation.json').write_text(json.dumps(report,indent=2)+'\n')
    print('NUT_FIT_INVESTIGATION_PASS','removed',removed.volume(),'protected_removed',protected_removed,flush=True)
    return report
if __name__=='__main__':main()
