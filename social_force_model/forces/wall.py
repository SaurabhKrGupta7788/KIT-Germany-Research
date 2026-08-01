"""Wall repulsion: Yang Eq.(6) – CORRECTED friction sign to match paper."""

import numpy as np

def _g(x):
    return np.maximum(x, 0.0)

def compute_wall_repulsion(state, walls, A_wall=10.0, B_wall=0.2,
                           K=1000.0, kappa=1000.0, r_ped=0.3):
    """Force from all walls on every agent."""
    F = np.zeros((state.N, 2))
    if not walls:
        return F

    for wall in walls:
        for i in range(state.N):
            d, n = wall.nearest(state.pos[i])   # n points AWAY from wall
            overlap = r_ped - d
            if overlap <= 0 and d > 3.0:        # cutoff
                continue

            psy_n = A_wall * np.exp(-d / B_wall) * n   # negative? no, sign of n already correct
            # Eq.(6): psy part is A_wall * exp[(ri - diw)/B] * n_iw  (diw is distance)
            # Our overlap = r - d, so exp(overlap/B) is correct.
            psy  = A_wall * np.exp(overlap / B_wall) * n   # this is normal repulsion

            phys_n = K * _g(overlap) * n

            # tangential direction: for a vertical wall, n = (±1,0) or (0,±1).
            # We compute t = perpendicular
            if abs(n[0]) > 0.9:
                t = np.array([0.0, -np.sign(n[0])])   # vertical wall, t along y? Actually for bottom wall n=(0,1), t=(1,0) correct.
            else:
                t = np.array([-np.sign(n[1]), 0.0])    # horizontal wall
            v_t = np.dot(state.vel[i], t)
            # Paper Eq.(6): + μ g(ri - diw) (v_i · t_iw) t_iw
            phys_t = kappa * _g(overlap) * v_t * t

            F[i] += psy + phys_n + phys_t   # note the + sign, not -
    return F