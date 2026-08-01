"""Pedestrian repulsion: Yang Eq.(5) with Bug1 fix."""

import numpy as np

def _g(x):
    return np.maximum(x, 0.0)

def compute_repulsion(state, A, B, K, kappa, r_ped):
    N = state.N
    pos = state.pos
    vel = state.vel
    F = np.zeros((N, 2))
    r_sum = 2 * r_ped

    for i in range(N):
        diff = pos[i] - pos                # (N,2)
        diff[i] = np.array([1.0, 0.0])    # self-term inert
        dist = np.linalg.norm(diff, axis=1)
        overlap = r_sum - dist
        n_ij = diff / dist[:, None]
        t_ij = np.column_stack([-n_ij[:, 1], n_ij[:, 0]])
        dv = vel - vel[i]                  # v_j - v_i
        dv_t = np.einsum('ij,ij->i', dv, t_ij)

        f_psy    = A * np.exp(overlap / B)
        f_phys_n = K * _g(overlap)
        f_phys_t = kappa * _g(overlap) * dv_t

        mask = np.ones(N, dtype=bool); mask[i] = False
        F[i] += np.sum(
            (f_psy[mask] + f_phys_n[mask])[:, None] * n_ij[mask] +
            f_phys_t[mask, None] * t_ij[mask], axis=0)
    return F