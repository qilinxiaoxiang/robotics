"""Measure local deposited-bead overlap and two-sided finite native anchors.

A source probe need not sit on a support stripe centre. Local evidence requires
at least0.10mm lateral deposited-bead overlap. Otherwise only a real connected
native path to >=0.40mm supported bead on EACH end can justify a <=4mm slow span.
"""
import heapq
import numpy as np
from shapely.geometry import LineString,Point
from shapely.ops import unary_union

def local_native_anchor(layers,model,point,configured_gap,normal_layer):
    top=model['z'];bottom=model['bottom'];current=layers[top];index=model['native_segment_index']
    first=current['p0'][index];last=current['p1'][index];step=last-first;den=float(step@step)
    t=0.0 if den<1e-15 else float(np.clip((np.array(point[:2])-first)@step/den,0,1));q=first+step*t
    region_low=q-6;region_high=q+6;polygons=[];support_levels=[];model_levels=[]
    for z,layer in layers.items():
        gap=bottom-z
        if gap<-.025 or gap>configured_gap+normal_layer+.05:continue
        for i,kind in enumerate(layer['kind']):
            support='support interface' in kind.lower();self_model='support' not in kind.lower() and gap<=.075
            if not (support or self_model):continue
            u=layer['p0'][i];v=layer['p1'][i];half=float(layer['w'][i])/2
            if np.any(np.maximum(u,v)+half<region_low) or np.any(np.minimum(u,v)-half>region_high):continue
            polygons.append(LineString([u,v]).buffer(half,resolution=16))
            (support_levels if support else model_levels).append(float(z))
    if not polygons:return dict(direct_model_bead_overlap=False,two_sided_bounded_span=False,anchor_footprints_present=False)
    anchors=unary_union(polygons);distance=float(anchors.distance(Point(q)));overlap=float(model['width']/2-distance)
    result=dict(native_model_centerline_xy_mm=q.tolist(),distance_to_actual_anchor_footprint_mm=distance,
                lateral_model_bead_overlap_mm=overlap,minimum_required_overlap_mm=.10,
                actual_interface_top_levels_mm=sorted(set(support_levels)),actual_previous_model_top_levels_mm=sorted(set(model_levels)),
                direct_model_bead_overlap=overlap>=.10-1e-6,two_sided_bounded_span=False,anchor_footprints_present=True)
    if result['direct_model_bead_overlap']:return result
    if model['speed_mm_s']>30.01 or float(np.linalg.norm(step))>4.:return result
    # Actual same-layer segment endpoints form a graph. Rounded native0.001mm
    # coordinates unify only native-connected endpoints, never a spatial guess.
    key=lambda xy:tuple(np.round(xy,3));graph={};edges={}
    for i,kind in enumerate(current['kind']):
        if 'support' in kind.lower():continue
        u=current['p0'][i];v=current['p1'][i]
        if np.any(np.maximum(u,v)<region_low) or np.any(np.minimum(u,v)>region_high):continue
        k0=key(u);k1=key(v);length=float(np.linalg.norm(v-u))
        if k0==k1 or length<1e-6:continue
        edges[i]=(u,v,length,float(current['w'][i]));graph.setdefault(k0,[]).append((k1,i));graph.setdefault(k1,[]).append((k0,i))
    def find_anchor(start,blocked):
        queue=[(0.,0,start,blocked,0.,None,[])];serial=0;visited={}
        while queue:
            distance_so_far,_,node,previous,run,run_start,trace=heapq.heappop(queue)
            if distance_so_far>1.5:continue
            for target,edge_index in graph.get(node,[]):
                if target==previous or edge_index==index or edge_index in trace:continue
                u,v,length,width=edges[edge_index]
                if key(v)==node:u,v=v,u
                intervals=max(1,int(np.ceil(length/.025)));ds=length/intervals
                continuing=run;begin=run_start
                for j in range(1,intervals+1):
                    pos=u+(v-u)*(j/intervals);supported=anchors.distance(Point(pos))<=width/2-.10+1e-6
                    if supported:
                        if continuing==0:begin=distance_so_far+(j-1)*ds
                        continuing+=ds
                        if continuing-ds>=.40:
                            return dict(unsupported_prefix_upper_bound_mm=float(begin),supported_anchor_run_lower_bound_mm=float(continuing-ds),
                                        required_supported_anchor_run_mm=.40,native_connected_segment_indices=trace+[edge_index],
                                        sampled_spacing_upper_bound_mm=.025)
                    else:continuing=0.;begin=None
                newdist=distance_so_far+length
                state=(target,node,round(continuing,3))
                if newdist<visited.get(state,float('inf')):
                    visited[state]=newdist;serial+=1;heapq.heappush(queue,(newdist,serial,target,node,continuing,begin,trace+[edge_index]))
        return None
    left=find_anchor(key(first),key(last));right=find_anchor(key(last),key(first))
    result['connected_end_anchors']=[left,right]
    if left and right:
        span=float(np.linalg.norm(step))+left['unsupported_prefix_upper_bound_mm']+right['unsupported_prefix_upper_bound_mm']
        result.update(native_unanchored_span_upper_bound_mm=span,span_speed_mm_s=model['speed_mm_s'],
                      two_sided_bounded_span=span<=4.+1e-6)
    return result
