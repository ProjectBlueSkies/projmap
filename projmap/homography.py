import numpy as np


def compute_homography(src, dst):
    """
    Compute 3x3 homography H such that dst_h ~ H @ src_h (homogeneous coords).
    src, dst: (4, 2) float arrays of corresponding 2D points.
    """
    A = []
    for (sx, sy), (dx, dy) in zip(src, dst):
        A.append([-sx, -sy, -1,   0,   0,  0, dx*sx, dx*sy, dx])
        A.append([  0,   0,  0, -sx, -sy, -1, dy*sx, dy*sy, dy])
    _, _, Vt = np.linalg.svd(np.array(A, dtype=np.float64))
    H = Vt[-1].reshape(3, 3)
    return H / H[2, 2]
