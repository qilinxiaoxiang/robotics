"""Rotation of image regions between photo A (closed loop) and photo B (open loop): SIFT matches inside a box, RANSAC similarity."""
import cv2, numpy as np, math, sys
A = cv2.imread(sys.argv[1], 0); B = cv2.imread(sys.argv[2], 0)
sift = cv2.SIFT_create(20000)
def rot(name, boxA, boxB=None, exclude=()):
    boxB = boxB or boxA
    def kp(im, box):
        m = np.zeros_like(im); x0, y0, x1, y1 = box; m[y0:y1, x0:x1] = 255
        for ex in exclude: m[ex[1]:ex[3], ex[0]:ex[2]] = 0
        return sift.detectAndCompute(im, m)
    ka, da = kp(A, boxA); kb, db = kp(B, boxB)
    mt = cv2.BFMatcher().knnMatch(da, db, k=2)
    good = [m for m, n in mt if m.distance < 0.7 * n.distance]
    pa = np.float32([ka[m.queryIdx].pt for m in good]); pb = np.float32([kb[m.trainIdx].pt for m in good])
    M, inl = cv2.estimateAffinePartial2D(pa, pb, method=cv2.RANSAC, ransacReprojThreshold=2.0, maxIters=20000)
    ang = math.degrees(math.atan2(M[1, 0], M[0, 0])); sc = math.hypot(M[0, 0], M[1, 0])
    # bootstrap on inliers for spread
    idx = np.where(inl.ravel())[0]; rng = np.random.default_rng(0); angs = []
    for _ in range(200):
        s = rng.choice(idx, len(idx)); M2, _ = cv2.estimateAffinePartial2D(pa[s], pb[s], method=cv2.LMEDS)
        if M2 is not None: angs.append(math.degrees(math.atan2(M2[1, 0], M2[0, 0])))
    print(f"{name:28s} rot {ang:+.2f} deg (+- {np.std(angs):.2f})  scale {sc:.4f}  shift {M[0,2]:+.0f},{M[1,2]:+.0f}  inliers {len(idx)}/{len(good)}")
    return ang
bg = rot("background (camera)", (0, 0, 4032, 3024), exclude=[(1500, 0, 2900, 2900), (2900, 1500, 4032, 2500)])
tr = rot("trunk (shell + rear pack)", (1850, 1100, 2800, 1700))
ft = rot("feet + ankle brackets", (1800, 2300, 2500, 2800))
print(f"trunk minus camera {tr-bg:+.2f} deg;  feet minus camera {ft-bg:+.2f} deg  (image rotation A->B, + = counterclockwise in image coords with y down)")
print("--- segments (minus camera)")
th = rot("thigh cover (white triangle)", (1950, 1580, 2650, 2250), exclude=[(2550, 1700, 2900, 2300)])
sh = rot("shin / ankle servo body", (2050, 2150, 2500, 2480))
fo = rot("foot + bracket only", (1750, 2470, 2600, 2850))
for n, v in (("thigh", th), ("shin", sh), ("foot", fo)): print(f"  {n} minus camera {v-bg:+.2f}")
