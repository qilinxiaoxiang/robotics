exec(open(__file__.replace('probe_keeper2.py','probe.py')).read().split('for i,m')[0])
K=S^box([-100,-100,0],[150,-20.1,250]);main=S-box([-100,-100,0],[150,-19.9,250]);slot=box([20.8,-42,90],[31.4,-34,118.6146]);bar=box([15.0,-39.7,113.4],[37.2,-30.9,115.4])-cylinder_y(5.25,-50,-30)
receivers=box([15,-39.7,115.6],[20.7,-30.9,121.8])+box([31.5,-39.7,115.6],[37.2,-30.9,121.8]);upper=((K-slot)-bar)+receivers;lower=(K^slot)+bar
for name,m in [('upper',upper),('lower',lower)]:
 print('PART',name,m.volume(),len(m.decompose()),flush=True)
 for v in [[0,0,32],[0,0,-32]]:
  print(name,v,samples({name:m},{'main':main,'motor':M,**J},v,step=.5)['peakContactsMm3'],flush=True)
# Distinguish trim required to lower cap from retaining the complete axial seat.
lowersweepobstacle=(J['jaw_frame']+J['lower_pad']).minkowski_sum(box([-.15,-.15,-.15],[.15,.15,32.15]));cut=lower^lowersweepobstacle
print('LOWER_TRIM',cut.volume(),cut.bounding_box(),flush=True)
