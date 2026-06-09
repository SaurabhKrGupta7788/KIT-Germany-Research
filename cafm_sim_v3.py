# """
# CAFM Pedestrian Simulation — v3
# =================================
# Implements the Collision-Avoidance Force Model (Yang et al., 2024)
# built on top of the Social Force Model (Helbing & Molnar, 1995/1998).

# v3 CHANGE: Corridor geometry now matches Yang et al. 2024 EXACTLY.
#   - Full corridor: 26m long, 3m wide          (Section 3.1, p.5)
#   - Waiting areas: 0–6m (left), 20–26m (right)
#   - Buffer zones:  6–8m (left), 18–20m (right)
#   - Measurement area: 8–18m (central 10m)     (Fig. 2, p.5)
#   - Metrics (crossing time, order param) computed ONLY inside
#     the 10m measurement zone, matching UAV camera coverage.

# References
# ----------
# Helbing & Molnar (1998): arXiv:cond-mat/9805244
# Yang et al. (2024): Physica A 642, 129762  [Section 3.1, Fig. 2, Table 1-3]
# """

# import numpy as np
# from dataclasses import dataclass
# from typing import Optional


# # ─────────────────────────────────────────────
# #  Corridor geometry constants (Yang 2024, p.5)
# # ─────────────────────────────────────────────
# #
# #  |← 6m waiting →|← 2m buffer →|←── 10m measurement ──→|← 2m buffer →|← 6m waiting →|
# #  0               6              8                        18             20              26
# #
# CORRIDOR_TOTAL   = 26.0
# CORRIDOR_WIDTH   =  3.0
# WAITING_LEFT_X   = (0.0,  6.0)
# BUFFER_LEFT_X    = (6.0,  8.0)
# MEASURE_X        = (8.0, 18.0)    # ← metrics computed here only
# BUFFER_RIGHT_X   = (18.0, 20.0)
# WAITING_RIGHT_X  = (20.0, 26.0)


# # ─────────────────────────────────────────────
# #  Parameter container
# # ─────────────────────────────────────────────

# @dataclass
# class SimParams:
#     """All tuneable parameters for one CAFM simulation run.

#     Geometry matches Yang et al. 2024, Fig. 2, Section 3.1.

#     Physical / SFM parameters
#     -------------------------
#     n_major   : pedestrians walking left→right  [Yang Table 1]
#     n_minor   : pedestrians walking right→left  [Yang Table 1]
#     v0_mean   : desired speed mean  [m/s]       [Yang Table 3: 1.21 m/s]
#     v0_std    : desired speed std   [m/s]
#     tau       : relaxation time     [s]          [Yang Table 3: 0.5]
#     mass      : pedestrian mass     [kg]         [Yang Table 3: 80]
#     A         : social repulsion strength [N]    [Yang Table 3: 20]
#     B         : social repulsion range    [m]    [Yang Table 3: 0.08]
#     K         : normal contact stiffness  [N/m]  [Yang Table 3: 1000]
#     kappa     : tangential friction [N·s/m]      [Yang Table 3: 1000]
#     r_ped     : pedestrian radius   [m]          [Yang Table 3: 0.3]

#     CAFM avoidance parameters
#     -------------------------
#     R_safety  : avoidance trigger distance [m]   [Yang Table 3: 1.22]
#     R_danger  : danger distance            [m]   [Yang Table 3: 0.61]
#     f_adm     : max avoidance force        [N]   [Yang Section 2.2: 38800]

#     Simulation control
#     ------------------
#     dt        : time step [s]
#     t_max     : max simulation time [s]
#     noise_std : velocity fluctuation std [m/s]
#     seed      : random seed
#     """
#     # crowd composition  [Yang Table 1]
#     n_major: int   = 18
#     n_minor: int   = 18

#     # desired speed  [Yang Table 3, Section 3.1]
#     v0_mean: float = 1.21
#     v0_std:  float = 0.20

#     # SFM force params  [Yang Table 3, p.9]
#     tau:   float = 0.50
#     mass:  float = 80.0
#     A:     float = 20.0
#     B:     float = 0.08
#     K:     float = 1000.0
#     kappa: float = 1000.0
#     r_ped: float = 0.30

#     # CAFM avoidance params  [Yang Table 3 + Section 2.2, p.4]
#     R_safety: float = 1.22
#     R_danger: float = 0.61
#     f_adm:    float = 38800.0

#     # simulation control
#     dt:        float = 0.05
#     t_max:     float = 60.0    # raised: 26m corridor needs more time
#     noise_std: float = 0.05
#     seed: Optional[int] = 42


# # ─────────────────────────────────────────────
# #  Agent state
# # ─────────────────────────────────────────────

# class AgentState:
#     def __init__(self, pos, vel, v0, direction):
#         self.pos       = pos.copy().astype(float)
#         self.vel       = vel.copy().astype(float)
#         self.v0        = v0.copy().astype(float)
#         self.direction = direction.copy().astype(float)
#         self.N         = len(pos)

#     @property
#     def desired_vel(self):
#         e = np.zeros((self.N, 2))
#         e[:, 0] = self.direction
#         return e * self.v0[:, None]


# # ─────────────────────────────────────────────
# #  Force components
# # ─────────────────────────────────────────────

# def driving_force(state, p):
#     """Yang eq.(1): F0_i = m*(v0*e - v)/tau"""
#     return p.mass * (state.desired_vel - state.vel) / p.tau


# def _g(x):
#     return np.maximum(x, 0.0)


# def pedestrian_repulsion(state, p):
#     """Yang eq.(5): psychological + physical contact between all pairs."""
#     N     = state.N
#     F     = np.zeros((N, 2))
#     pos   = state.pos
#     vel   = state.vel
#     r_sum = 2 * p.r_ped

#     for i in range(N):
#         diff      = pos[i] - pos
#         diff[i]   = 1e-9
#         dist      = np.linalg.norm(diff, axis=1)
#         overlap   = r_sum - dist
#         n_ij      = diff / dist[:, None]
#         t_ij      = np.column_stack([-n_ij[:, 1], n_ij[:, 0]])
#         dv        = vel - vel[i]
#         dv_t      = np.einsum('ij,ij->i', dv, t_ij)
#         f_psy     = p.A * np.exp(overlap / p.B)
#         f_phys_n  = p.K     * _g(overlap)
#         f_phys_t  = p.kappa * _g(overlap) * dv_t
#         mask      = np.ones(N, bool); mask[i] = False
#         F[i]     += np.sum(
#             (f_psy[mask] + f_phys_n[mask])[:, None] * n_ij[mask]
#             + f_phys_t[mask, None] * t_ij[mask], axis=0)
#     return F


# def wall_repulsion(state, p):
#     """
#     Yang eq.(6): wall repulsion — normal (psy + elastic) + tangential friction.

#     FIX v2: friction term now correctly applied to F[:,0] (x-direction).
#     FIX v3: overlap formula uses agent centre distance to wall directly.
#       overlap = r_ped - d_iw  where d_iw = y (bottom) or corridor_wid-y (top)
#     """
#     F  = np.zeros((state.N, 2))
#     y  = state.pos[:, 1]
#     vx = state.vel[:, 0]

#     # bottom wall (y=0): d_iw = y
#     ov_b  = p.r_ped - y
#     F[:, 1] += p.A * np.exp(ov_b / p.B) + p.K * _g(ov_b)
#     F[:, 0] -= p.kappa * _g(ov_b) * vx

#     # top wall (y=W): d_iw = W - y
#     ov_t  = p.r_ped - (CORRIDOR_WIDTH - y)
#     F[:, 1] -= p.A * np.exp(ov_t / p.B) + p.K * _g(ov_t)
#     F[:, 0] -= p.kappa * _g(ov_t) * vx

#     return F


# def cafm_avoidance_force(state, p):
#     """
#     Yang eq.(7-9): CAFM avoidance force.

#     FIX v2: R_obstacle is j's DANGER VECTOR ENDPOINT (Eq.8), not raw pos_j.
#       R_obstacle = (v_j/|v_j|) * R_safety*0.5 + pos_j
#     This is predictive — i avoids where j's danger zone reaches, not just
#     where j stands. See Fig.1(c) p.3 and Eq.8 p.4, Yang 2024.
#     """
#     F   = np.zeros((state.N, 2))
#     pos = state.pos
#     vel = state.vel
#     d   = state.direction

#     for i in range(state.N):
#         counter_mask = (d != d[i])
#         if not np.any(counter_mask):
#             continue
#         cidx  = np.where(counter_mask)[0]
#         cpos  = pos[cidx]
#         cvel  = vel[cidx]
#         dists = np.linalg.norm(pos[i] - cpos, axis=1)
#         j_loc = np.argmin(dists)
#         dist_ij = dists[j_loc]

#         if not (p.R_danger < dist_ij < p.R_safety):
#             continue

#         # R_safety endpoint of i  (Eq.7)
#         speed_i   = np.linalg.norm(vel[i]) + 1e-9
#         R_saf_i   = (vel[i] / speed_i) * p.R_safety + pos[i]

#         # R_obstacle = danger endpoint of j  (Eq.8)
#         speed_j   = np.linalg.norm(cvel[j_loc]) + 1e-9
#         R_obs     = (cvel[j_loc] / speed_j) * (p.R_safety * 0.5) + cpos[j_loc]

#         # avoidance direction (Eq.9)
#         vec       = R_saf_i - R_obs
#         norm_vec  = np.linalg.norm(vec) + 1e-9
#         F[i]     += (vec / norm_vec) * p.f_adm

#     return F


# # ─────────────────────────────────────────────
# #  Euler integrator
# # ─────────────────────────────────────────────

# def integrate(state, F_total, p, rng):
#     acc        = F_total / p.mass
#     noise      = rng.normal(0, p.noise_std, size=state.vel.shape)
#     state.vel += acc * p.dt + noise

#     # speed clamp: v_max = 1.3 * v0  (Helbing 1998, p.7)
#     v_max    = 1.3 * state.v0
#     speed    = np.linalg.norm(state.vel, axis=1)
#     too_fast = speed > v_max
#     state.vel[too_fast] = (state.vel[too_fast]
#                            / speed[too_fast, None]
#                            * v_max[too_fast, None])

#     state.pos += state.vel * p.dt

#     # wall boundary: reflect + damp y-velocity
#     bot = state.pos[:, 1] < p.r_ped
#     top = state.pos[:, 1] > CORRIDOR_WIDTH - p.r_ped
#     state.vel[bot | top, 1] *= -0.5
#     state.pos[:, 1] = np.clip(state.pos[:, 1], p.r_ped, CORRIDOR_WIDTH - p.r_ped)


# # ─────────────────────────────────────────────
# #  Order parameter — measurement zone only
# #  Yang eq.(12-13), Section 4.3, p.9
# # ─────────────────────────────────────────────

# def order_parameter(state, p, n_rows=15):
#     """
#     Computed only for agents currently inside the 10m measurement zone.
#     Yang divides into 15 rows of 0.2m width (3m / 15 = 0.2m).
#     """
#     mx_lo, mx_hi = MEASURE_X
#     in_zone = (state.pos[:, 0] >= mx_lo) & (state.pos[:, 0] < mx_hi)
#     if not np.any(in_zone):
#         return np.nan                         # no agents in zone yet

#     row_w    = CORRIDOR_WIDTH / n_rows
#     phi_list = []
#     for j in range(n_rows):
#         y_lo   = j * row_w
#         y_hi   = y_lo + row_w
#         in_row = in_zone & (state.pos[:, 1] >= y_lo) & (state.pos[:, 1] < y_hi)
#         if not np.any(in_row):
#             continue
#         n_L = np.sum(state.direction[in_row] > 0)
#         n_R = np.sum(state.direction[in_row] < 0)
#         tot = n_L + n_R
#         if tot == 0:
#             continue
#         phi_list.append(((n_L - n_R) / tot) ** 2)

#     return float(np.mean(phi_list)) if phi_list else 0.0


# # ─────────────────────────────────────────────
# #  Initialiser — matches Yang Fig.2 exactly
# # ─────────────────────────────────────────────

# def init_agents(p, rng):
#     """
#     Spawn major flow in LEFT waiting area  (x: 0.5 – 5.5m)
#     Spawn minor flow in RIGHT waiting area (x: 20.5 – 25.5m)
#     Both groups walk toward opposite ends through the full 26m corridor.
#     Matches Yang et al. 2024, Fig.2 and Section 3.1.
#     """
#     def place_group(n, x_lo, x_hi, direction):
#         pos = np.zeros((n, 2))
#         vel = np.zeros((n, 2))
#         v0  = np.clip(rng.normal(p.v0_mean, p.v0_std, n),
#                       p.v0_mean * 0.5, p.v0_mean * 1.5)
#         for k in range(n):
#             for _ in range(500):
#                 xt = rng.uniform(x_lo, x_hi)
#                 yt = rng.uniform(p.r_ped + 0.05, CORRIDOR_WIDTH - p.r_ped - 0.05)
#                 if k == 0:
#                     break
#                 if np.all(np.linalg.norm(pos[:k] - [xt, yt], axis=1)
#                           > 2 * p.r_ped + 0.05):
#                     break
#             pos[k] = [xt, yt]
#             vel[k] = [direction * v0[k], 0.0]
#         return pos, vel, v0

#     # major: waiting area left side (x: 0.5–5.5)
#     pM, vM, v0M = place_group(p.n_major, 0.5, 5.5,  +1.0)
#     # minor: waiting area right side (x: 20.5–25.5)
#     pm, vm, v0m = place_group(p.n_minor, 20.5, 25.5, -1.0)

#     pos = np.vstack([pM, pm])
#     vel = np.vstack([vM, vm])
#     v0  = np.concatenate([v0M, v0m])
#     direction = np.concatenate([np.ones(p.n_major), -np.ones(p.n_minor)])
#     return AgentState(pos, vel, v0, direction)


# # ─────────────────────────────────────────────
# #  Main simulation runner
# # ─────────────────────────────────────────────

# def run_simulation(p: SimParams) -> dict:
#     """
#     Run one CAFM simulation.

#     Crossing time = time agent spends traversing the 10m measurement zone.
#     This matches Yang et al. 2024 individual crossing time (Fig.6).

#     Returns scalar dict for GP training: (params → outputs).
#     """
#     rng   = np.random.default_rng(p.seed)
#     state = init_agents(p, rng)
#     N     = state.N

#     mx_lo, mx_hi = MEASURE_X          # 8.0 to 18.0

#     # track when each agent ENTERS and EXITS the measurement zone
#     entry_time  = {}   # agent_idx → time entered measurement zone
#     cross_times = []   # completed crossing durations [s]

#     phi_history   = []
#     speed_history = []

#     n_steps = int(p.t_max / p.dt)

#     for step in range(n_steps):
#         t = step * p.dt

#         F  = driving_force(state, p)
#         F += pedestrian_repulsion(state, p)
#         F += wall_repulsion(state, p)
#         F += cafm_avoidance_force(state, p)
#         integrate(state, F, p, rng)

#         # ── measurement zone entry / exit tracking ──
#         # FIXED: use proper entry_time dict, no placeholder set
#         for i in range(N):
#             x = state.pos[i, 0]
#             d = state.direction[i]
#             in_zone = (mx_lo <= x <= mx_hi)

#             if i not in entry_time and in_zone:
#                 entry_time[i] = t                     # just entered

#             if i in entry_time and i not in [c[0] for c in []] :
#                 # check if agent has EXITED zone on the correct side
#                 exited = (d > 0 and x > mx_hi) or (d < 0 and x < mx_lo)
#                 if exited and i in entry_time:
#                     cross_times.append(t - entry_time[i])
#                     del entry_time[i]                  # prevent re-counting

#         # metrics inside measurement zone only
#         phi = order_parameter(state, p)
#         if not np.isnan(phi):
#             phi_history.append(phi)
#         speed_history.append(np.mean(np.linalg.norm(state.vel, axis=1)))

#     # ── aggregate ──
#     n_crossed = len(cross_times)
#     return {
#         "mean_crossing_time" : float(np.mean(cross_times)) if cross_times else p.t_max,
#         "flow_rate"          : n_crossed / p.t_max,
#         "order_param_mean"   : float(np.mean(phi_history))   if phi_history   else 0.0,
#         "order_param_final"  : float(phi_history[-1])         if phi_history   else 0.0,
#         "mean_speed"         : float(np.mean(speed_history))  if speed_history else 0.0,
#         "completion_ratio"   : n_crossed / N,
#     }


# # ─────────────────────────────────────────────
# #  Validation run
# # ─────────────────────────────────────────────

# if __name__ == "__main__":
#     configs = [("6:0", 36, 0), ("5:1", 30, 6), ("4:2", 24, 12), ("3:3", 18, 18)]

#     print("CAFM v3 — Yang et al. 2024 exact geometry (26m corridor, 10m measurement zone)")
#     print("=" * 75)
#     print(f"{'Ratio':<6} {'Cross.Time':>12} {'FlowRate':>10} {'Order Φ':>10} "
#           f"{'Speed':>8} {'n_crossed/N':>12}")
#     print("-" * 70)

#     # Paper reference (Yang Fig.6, approximate from plot, CAFM model results)
#     # crossing time: 6:0~7-9s, 5:1~8-10s, 4:2~8-10s, 3:3~10-13s
#     paper_ct = [(7,9), (8,10), (8,10), (10,13)]

#     for (label, maj, minor), ct_ref in zip(configs, paper_ct):
#         p = SimParams(n_major=maj, n_minor=minor, seed=42)
#         r = run_simulation(p)
#         ct_ok = "✓" if ct_ref[0] <= r['mean_crossing_time'] <= ct_ref[1] else "~"
#         print(f"{label:<6} {r['mean_crossing_time']:>12.3f} {r['flow_rate']:>10.3f} "
#               f"{r['order_param_mean']:>10.4f} {r['mean_speed']:>8.4f} "
#               f"{r['completion_ratio']:>10.3f}   {ct_ok}")

#     print()
#     print("Geometry used:")
#     print(f"  Full corridor : {CORRIDOR_TOTAL}m × {CORRIDOR_WIDTH}m")
#     print(f"  Waiting zones : left {WAITING_LEFT_X}, right {WAITING_RIGHT_X}")
#     print(f"  Buffer zones  : left {BUFFER_LEFT_X}, right {BUFFER_RIGHT_X}")
#     print(f"  Measurement   : {MEASURE_X}  ← metrics computed here only")






"""
CAFM Pedestrian Simulation — v5
=================================
Implements the Collision-Avoidance Force Model (Yang et al., 2024)
built on top of the Social Force Model (Helbing & Molnar, 1995/1998).

v3 CHANGE: Corridor geometry now matches Yang et al. 2024 EXACTLY.
v4 CHANGE: flow_rate uses actual observation window, not t_max.
v5 CHANGES (bug fixes found by paper cross-check):


References
----------
Helbing & Molnar (1998): arXiv:cond-mat/9805244
Yang et al. (2024): Physica A 642, 129762  [Section 3.1, Fig. 2, Table 1-3]
"""

import numpy as np
from dataclasses import dataclass
from typing import Optional


# ─────────────────────────────────────────────
#  Corridor geometry constants (Yang 2024, p.5)
# ─────────────────────────────────────────────
#
#  |← 6m waiting →|← 2m buffer →|←── 10m measurement ──→|← 2m buffer →|← 6m waiting →|
#  0               6              8                        18             20              26
#
CORRIDOR_TOTAL   = 26.0
CORRIDOR_WIDTH   =  3.0
WAITING_LEFT_X   = (0.0,  6.0)
BUFFER_LEFT_X    = (6.0,  8.0)
MEASURE_X        = (8.0, 18.0)    # ← metrics computed here only
BUFFER_RIGHT_X   = (18.0, 20.0)
WAITING_RIGHT_X  = (20.0, 26.0)


# ─────────────────────────────────────────────
#  Parameter container
# ─────────────────────────────────────────────

@dataclass
class SimParams:
    """All tuneable parameters for one CAFM simulation run.

    Geometry matches Yang et al. 2024, Fig. 2, Section 3.1.

    Physical / SFM parameters
    -------------------------
    n_major   : pedestrians walking left→right  [Yang Table 1]
    n_minor   : pedestrians walking right→left  [Yang Table 1]
    v0_mean   : desired speed mean  [m/s]       [Yang Table 3: 1.21 m/s]
    v0_std    : desired speed std   [m/s]
    tau       : relaxation time     [s]          [Yang Table 3: 0.5]
    mass      : pedestrian mass     [kg]         [Yang Table 3: 80]
    A         : social repulsion strength [N]    [Yang Table 3: 20]
    B         : social repulsion range    [m]    [Yang Table 3: 0.08]
    K         : normal contact stiffness  [N/m]  [Yang Table 3: 1000]
    kappa     : tangential friction [N·s/m]      [Yang Table 3: 1000]
    r_ped     : pedestrian radius   [m]          [Yang Table 3: 0.3]

    CAFM avoidance parameters
    -------------------------
    R_safety  : avoidance trigger distance [m]   [Yang Table 3: 1.22]
    R_danger  : danger distance [m] = R_safety*0.5  [Yang Table 3: 0.61]
                ALWAYS keep R_danger = R_safety * 0.5  (Yang Eq.8, Section 2.2)
    f_adm     : max avoidance force [N]          [Yang Section 2.2: 38800]

    Simulation control
    ------------------
    dt        : time step [s]
    t_max     : max simulation time [s]
    noise_std : velocity fluctuation std [m/s]
    seed      : random seed
    """
    # crowd composition  [Yang Table 1]
    n_major: int   = 18
    n_minor: int   = 18

    # desired speed  [Yang Table 3, Section 3.1]
    v0_mean: float = 1.21
    v0_std:  float = 0.20

    # SFM force params  [Yang Table 3, p.9]
    tau:   float = 0.50
    mass:  float = 80.0
    A:     float = 20.0
    B:     float = 0.08
    K:     float = 1000.0
    kappa: float = 1000.0
    r_ped: float = 0.30

    # CAFM avoidance params  [Yang Table 3 + Section 2.2, p.4]
    R_safety: float = 1.22
    R_danger: float = 0.61   # must equal R_safety * 0.5
    f_adm:    float = 38800.0

    # simulation control
    dt:        float = 0.05
    t_max:     float = 80.0
    noise_std: float = 0.05
    seed: Optional[int] = 42


# ─────────────────────────────────────────────
#  Agent state
# ─────────────────────────────────────────────

class AgentState:
    def __init__(self, pos, vel, v0, direction):
        self.pos       = pos.copy().astype(float)
        self.vel       = vel.copy().astype(float)
        self.v0        = v0.copy().astype(float)
        self.direction = direction.copy().astype(float)
        self.N         = len(pos)

    @property
    def desired_vel(self):
        e = np.zeros((self.N, 2))
        e[:, 0] = self.direction
        return e * self.v0[:, None]


# ─────────────────────────────────────────────
#  Force components
# ─────────────────────────────────────────────

def driving_force(state, p):
    """Yang eq.(1): F0_i = m*(v0*e - v)/tau"""
    return p.mass * (state.desired_vel - state.vel) / p.tau


def _g(x):
    return np.maximum(x, 0.0)


def pedestrian_repulsion(state, p):
    """
    Yang eq.(5): psychological + physical contact between all pairs.

    BUG 1 FIX (v5): diff[i] is now set to [1, 0] instead of scalar 1e-9.
      With 1e-9: dist[i] ≈ 0 → overlap[i] ≈ r_sum (large positive) →
      exp(overlap/B) explodes for the self-entry, corrupting n_ij and
      f_psy arrays even though mask[i]=False excludes it from the final
      sum. Setting diff[i]=[1,0] gives dist[i]=1.0, overlap[i]<0
      (well below contact), making all self-entry values inert before
      the mask is even applied.
    """
    N     = state.N
    F     = np.zeros((N, 2))
    pos   = state.pos
    vel   = state.vel
    r_sum = 2 * p.r_ped

    for i in range(N):
        diff      = pos[i] - pos          # shape (N,2): pos_i - pos_j
        diff[i]   = np.array([1.0, 0.0]) # FIX v5: unit dummy — dist=1, overlap<0
        dist      = np.linalg.norm(diff, axis=1)
        overlap   = r_sum - dist
        n_ij      = diff / dist[:, None]
        t_ij      = np.column_stack([-n_ij[:, 1], n_ij[:, 0]])
        dv        = vel - vel[i]           # v_j - v_i  (Yang Eq.4)
        dv_t      = np.einsum('ij,ij->i', dv, t_ij)
        f_psy     = p.A * np.exp(overlap / p.B)
        f_phys_n  = p.K     * _g(overlap)
        f_phys_t  = p.kappa * _g(overlap) * dv_t
        mask      = np.ones(N, bool); mask[i] = False
        F[i]     += np.sum(
            (f_psy[mask] + f_phys_n[mask])[:, None] * n_ij[mask]
            + f_phys_t[mask, None] * t_ij[mask], axis=0)
    return F


def wall_repulsion(state, p):
    """
    Yang eq.(6): wall repulsion — normal (psy + elastic) + tangential friction.
    overlap = r_ped - d_iw  where d_iw = y (bottom) or W-y (top).
    """
    F  = np.zeros((state.N, 2))
    y  = state.pos[:, 1]
    vx = state.vel[:, 0]

    # bottom wall (y=0): normal pushes in +y, friction opposes vx
    ov_b  = p.r_ped - y
    F[:, 1] += p.A * np.exp(ov_b / p.B) + p.K * _g(ov_b)
    F[:, 0] -= p.kappa * _g(ov_b) * vx

    # top wall (y=W): normal pushes in -y, friction opposes vx
    ov_t  = p.r_ped - (CORRIDOR_WIDTH - y)
    F[:, 1] -= p.A * np.exp(ov_t / p.B) + p.K * _g(ov_t)
    F[:, 0] -= p.kappa * _g(ov_t) * vx

    return F


def cafm_avoidance_force(state, p):
    """
    Yang eq.(7-9): CAFM avoidance force.

    BUG 2 FIX (v5): R_danger consistency.
      Condition check AND R_obs computation now both use p.R_danger.
      Previously the condition used p.R_danger but R_obs was computed
      with p.R_safety*0.5. These are equal at default params but diverge
      when R_safety is swept in LHS without updating R_danger.
      Yang Eq.(8): |R_danger| = r = R*0.5 = R_safety*0.5 = p.R_danger.
      So R_obs endpoint = (v_j/|v_j|)*p.R_danger + pos_j.

    Only the nearest counterflow pedestrian is checked per Yang Section 2.2.
    """
    F   = np.zeros((state.N, 2))
    pos = state.pos
    vel = state.vel
    d   = state.direction

    for i in range(state.N):
        counter_mask = (d != d[i])
        if not np.any(counter_mask):
            continue
        cidx    = np.where(counter_mask)[0]
        cpos    = pos[cidx]
        cvel    = vel[cidx]
        dists   = np.linalg.norm(pos[i] - cpos, axis=1)
        j_loc   = np.argmin(dists)
        dist_ij = dists[j_loc]

        # collision avoidance active only in (R_danger, R_safety) band
        if not (p.R_danger < dist_ij < p.R_safety):
            continue

        # R_safety endpoint of i  (Eq.7): tip of i's safety vector
        speed_i = np.linalg.norm(vel[i]) + 1e-9
        R_saf_i = (vel[i] / speed_i) * p.R_safety + pos[i]

        # R_obstacle = danger endpoint of j  (Eq.8)
        # FIX v5: use p.R_danger (not p.R_safety*0.5) for consistency
        speed_j = np.linalg.norm(cvel[j_loc]) + 1e-9
        R_obs   = (cvel[j_loc] / speed_j) * p.R_danger + cpos[j_loc]

        # avoidance direction = R_safety_i - R_obstacle_j  (Eq.9)
        vec      = R_saf_i - R_obs
        norm_vec = np.linalg.norm(vec) + 1e-9
        F[i]    += (vec / norm_vec) * p.f_adm

    return F


# ─────────────────────────────────────────────
#  Euler integrator
# ─────────────────────────────────────────────

def integrate(state, F_total, p, rng):
    acc        = F_total / p.mass
    noise      = rng.normal(0, p.noise_std, size=state.vel.shape)
    state.vel += acc * p.dt + noise

    # speed clamp: v_max = 1.3 * v0  (Helbing 1998, p.7)
    v_max    = 1.3 * state.v0
    speed    = np.linalg.norm(state.vel, axis=1)
    too_fast = speed > v_max
    state.vel[too_fast] = (state.vel[too_fast]
                           / speed[too_fast, None]
                           * v_max[too_fast, None])

    state.pos += state.vel * p.dt

    # wall boundary: reflect + damp y-velocity
    bot = state.pos[:, 1] < p.r_ped
    top = state.pos[:, 1] > CORRIDOR_WIDTH - p.r_ped
    state.vel[bot | top, 1] *= -0.5
    state.pos[:, 1] = np.clip(state.pos[:, 1], p.r_ped, CORRIDOR_WIDTH - p.r_ped)


# ─────────────────────────────────────────────
#  Order parameter — measurement zone only
#  Yang eq.(12-13), Section 4.3, p.9
# ─────────────────────────────────────────────

def order_parameter(state, p, n_rows=15):
    """
    Computed only for agents inside the 10m measurement zone.
    Yang Eq.(13): Φ = (1/N)*ΣΦ_j  where N = n_rows = 15 (ALL rows).

    BUG 3 FIX (v5): divide by n_rows (15), not len(phi_list).
      Previous code used np.mean(phi_list) which divided by the number
      of OCCUPIED rows only → inflated Φ when few agents in zone.
      Yang Eq.(13) explicitly divides by the total number of rows N=15.
      Empty rows contribute Φ_j = 0 and must be included in denominator.
    """
    mx_lo, mx_hi = MEASURE_X
    in_zone = (state.pos[:, 0] >= mx_lo) & (state.pos[:, 0] < mx_hi)
    if not np.any(in_zone):
        return np.nan

    row_w    = CORRIDOR_WIDTH / n_rows   # 3/15 = 0.2m per row
    phi_rows = []                        # one entry per row (0.0 if empty)
    for j in range(n_rows):
        y_lo   = j * row_w
        y_hi   = y_lo + row_w
        in_row = in_zone & (state.pos[:, 1] >= y_lo) & (state.pos[:, 1] < y_hi)
        if not np.any(in_row):
            phi_rows.append(0.0)         # FIX v5: empty row → Φ_j = 0
            continue
        n_L = np.sum(state.direction[in_row] > 0)
        n_R = np.sum(state.direction[in_row] < 0)
        tot = n_L + n_R
        phi_rows.append(((n_L - n_R) / tot) ** 2 if tot > 0 else 0.0)

    # FIX v5: divide by n_rows (15), matching Yang Eq.(13)
    return float(np.sum(phi_rows) / n_rows)


# ─────────────────────────────────────────────
#  Initialiser — matches Yang Fig.2 exactly
# ─────────────────────────────────────────────

def init_agents(p, rng):
    """
    Spawn major flow in LEFT waiting area  (x: 0.5–5.5m)
    Spawn minor flow in RIGHT waiting area (x: 20.5–25.5m)
    Matches Yang et al. 2024, Fig.2 and Section 3.1.
    """
    def place_group(n, x_lo, x_hi, direction):
        pos = np.zeros((n, 2))
        vel = np.zeros((n, 2))
        v0  = np.clip(rng.normal(p.v0_mean, p.v0_std, n),
                      p.v0_mean * 0.5, p.v0_mean * 1.5)
        for k in range(n):
            for _ in range(500):
                xt = rng.uniform(x_lo, x_hi)
                yt = rng.uniform(p.r_ped + 0.05, CORRIDOR_WIDTH - p.r_ped - 0.05)
                if k == 0:
                    break
                if np.all(np.linalg.norm(pos[:k] - [xt, yt], axis=1)
                          > 2 * p.r_ped + 0.05):
                    break
            pos[k] = [xt, yt]
            vel[k] = [direction * v0[k], 0.0]
        return pos, vel, v0

    pM, vM, v0M = place_group(p.n_major, 0.5, 5.5,  +1.0)
    pm, vm, v0m = place_group(p.n_minor, 20.5, 25.5, -1.0)

    pos = np.vstack([pM, pm])
    vel = np.vstack([vM, vm])
    v0  = np.concatenate([v0M, v0m])
    direction = np.concatenate([np.ones(p.n_major), -np.ones(p.n_minor)])
    return AgentState(pos, vel, v0, direction)


# ─────────────────────────────────────────────
#  Main simulation runner
# ─────────────────────────────────────────────

def run_simulation(p: SimParams) -> dict:
    """
    Run one CAFM simulation.

    Crossing time = time each agent spends inside the 10m measurement zone.
    Matches Yang et al. 2024 individual crossing time (Fig.6).

    flow_rate = n_crossed / max(t_last_exit - t_first_entry, mean_ct)
      Physically correct throughput using actual observation window.
      Floor at mean_ct prevents explosion in unidirectional tight clusters.

    Returns scalar dict for GP training.
    """
    rng   = np.random.default_rng(p.seed)
    state = init_agents(p, rng)
    N     = state.N

    mx_lo, mx_hi = MEASURE_X

    entry_time    = {}
    cross_times   = []
    t_first_entry = None
    t_last_exit   = None
    phi_history   = []
    speed_history = []

    n_steps = int(p.t_max / p.dt)

    for step in range(n_steps):
        F  = driving_force(state, p)
        F += pedestrian_repulsion(state, p)
        F += wall_repulsion(state, p)
        F += cafm_avoidance_force(state, p)
        integrate(state, F, p, rng)

        # t evaluated AFTER integrate: positions and time are consistent
        t = (step + 1) * p.dt

        for i in range(N):
            x       = state.pos[i, 0]
            d       = state.direction[i]
            in_zone = (mx_lo <= x <= mx_hi)

            if i not in entry_time and in_zone:
                entry_time[i] = t
                if t_first_entry is None:
                    t_first_entry = t

            if i in entry_time:
                exited = (d > 0 and x > mx_hi) or (d < 0 and x < mx_lo)
                if exited:
                    cross_times.append(t - entry_time[i])
                    del entry_time[i]
                    t_last_exit = t

        phi = order_parameter(state, p)
        if not np.isnan(phi):
            phi_history.append(phi)
        speed_history.append(np.mean(np.linalg.norm(state.vel, axis=1)))

    n_crossed = len(cross_times)

    if n_crossed > 0 and t_last_exit is not None and t_first_entry is not None:
        mean_ct    = float(np.mean(cross_times))
        obs_window = max(t_last_exit - t_first_entry, mean_ct)
        flow_rate  = n_crossed / obs_window
    else:
        flow_rate  = 0.0

    return {
        "mean_crossing_time" : float(np.mean(cross_times)) if cross_times else p.t_max,
        "flow_rate"          : flow_rate,
        "order_param_mean"   : float(np.mean(phi_history))  if phi_history  else 0.0,
        "order_param_final"  : float(phi_history[-1])        if phi_history  else 0.0,
        "mean_speed"         : float(np.mean(speed_history)) if speed_history else 0.0,
        "completion_ratio"   : n_crossed / N,
    }


# ─────────────────────────────────────────────
#  Validation run
# ─────────────────────────────────────────────

if __name__ == "__main__":
    configs = [("6:0", 36, 0), ("5:1", 30, 6), ("4:2", 24, 12), ("3:3", 18, 18)]

    print("CAFM v5 — Yang et al. 2024 exact geometry")
    print("Bugs fixed: self-repulsion, R_danger consistency, order_param denominator")
    print("=" * 75)
    print(f"{'Ratio':<6} {'Cross.Time':>12} {'FlowRate':>10} {'Order Φ':>10} "
          f"{'Speed':>8} {'n/N':>8}")
    print("-" * 70)

    paper_ct = [(7,9), (8,10), (8,10), (10,13)]

    for (label, maj, minor), ct_ref in zip(configs, paper_ct):
        p = SimParams(n_major=maj, n_minor=minor, seed=42)
        r = run_simulation(p)
        ct_ok = "✓" if ct_ref[0] <= r['mean_crossing_time'] <= ct_ref[1] else "~"
        print(f"{label:<6} {r['mean_crossing_time']:>12.3f} {r['flow_rate']:>10.3f} "
              f"{r['order_param_mean']:>10.4f} {r['mean_speed']:>8.4f} "
              f"{r['completion_ratio']:>8.3f}   {ct_ok}")

    print()
    print("Geometry:")
    print(f"  Corridor : {CORRIDOR_TOTAL}m × {CORRIDOR_WIDTH}m")
    print(f"  Waiting  : left {WAITING_LEFT_X}, right {WAITING_RIGHT_X}")
    print(f"  Buffer   : left {BUFFER_LEFT_X}, right {BUFFER_RIGHT_X}")
    print(f"  Measure  : {MEASURE_X}")