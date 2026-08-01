"""CAFM collision avoidance force: Yang Eq.(7-9)."""

import numpy as np

def compute_avoidance(state, R_safety, R_danger, f_adm):
    F = np.zeros((state.N, 2))
    pos = state.pos
    vel = state.vel
    d = state.direction

    for i in range(state.N):
        counter_mask = (d != d[i])
        if not np.any(counter_mask):
            continue
        cidx = np.where(counter_mask)[0]
        cpos = pos[cidx]
        cvel = vel[cidx]
        dists = np.linalg.norm(pos[i] - cpos, axis=1)
        j_loc = np.argmin(dists)
        dist_ij = dists[j_loc]

        if not (R_danger < dist_ij < R_safety):
            continue

        speed_i = np.linalg.norm(vel[i]) + 1e-9
        R_saf_i = (vel[i] / speed_i) * R_safety + pos[i]

        speed_j = np.linalg.norm(cvel[j_loc]) + 1e-9
        R_obs = (cvel[j_loc] / speed_j) * R_danger + cpos[j_loc]

        vec = R_saf_i - R_obs
        norm_vec = np.linalg.norm(vec) + 1e-9
        F[i] += (vec / norm_vec) * f_adm

    return F