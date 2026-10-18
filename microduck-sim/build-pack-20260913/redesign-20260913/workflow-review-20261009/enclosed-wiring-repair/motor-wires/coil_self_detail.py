exec(__import__('pathlib').Path('hip_core.py').read_text().split('top=json')[0])
s=[]
for i in range(1,4):s.append(solid(trimesh.load_mesh(D/f'hip-coiled-right-wire-{i}.stl')))
for i in range(3):
 for j in range(i):
  c=s[i]^s[j];print(i+1,j+1,c.volume(),c.bounding_box())
