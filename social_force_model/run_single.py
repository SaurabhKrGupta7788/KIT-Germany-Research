"""Run a single CAFM simulation and save trajectory + metrics."""

import json
import numpy as np
from models.base import AgentState, integrate
from models.cafm import cafm_step
from geometry.corridor import build_corridor_walls
from utils.config import SimConfig, MEASURE_ZONE, CORRIDOR_WIDTH, CORRIDOR_TOTAL

def init_agents(config, rng):
    """Spawn agents as per Yang Fig.2."""
    def place_group(n, x_lo, x_hi, dir_):
        pos = np.zeros((n, 2))
        vel = np.zeros((n, 2))
        v0  = np.clip(rng.normal(config.v0_mean, config.v0_std, n),
                      config.v0_mean*0.5, config.v0_mean*1.5)
        for k in range(n):
            for _ in range(500):
                xt = rng.uniform(x_lo, x_hi)
                yt = rng.uniform(config.r_ped+0.05, CORRIDOR_WIDTH - config.r_ped - 0.05)
                if k == 0 or np.all(np.linalg.norm(pos[:k] - [xt, yt], axis=1) > 2*config.r_ped+0.05):
                    break
            pos[k] = [xt, yt]
            vel[k] = [dir_ * v0[k], 0.0]
        return pos, vel, v0

    posM, velM, v0M = place_group(config.n_major, 0.5, 5.5, +1.0)
    posm, velm, v0m = place_group(config.n_minor, 20.5, 25.5, -1.0)
    pos = np.vstack([posM, posm])
    vel = np.vstack([velM, velm])
    v0  = np.concatenate([v0M, v0m])
    direction = np.concatenate([np.ones(config.n_major), -np.ones(config.n_minor)])
    return AgentState(pos, vel, v0, direction)

def order_parameter(state, n_rows=15):
    """Yang Eq.(12-13)."""
    mx_lo, mx_hi = MEASURE_ZONE
    in_zone = (state.pos[:, 0] >= mx_lo) & (state.pos[:, 0] < mx_hi)
    if not np.any(in_zone):
        return np.nan
    row_w = CORRIDOR_WIDTH / n_rows
    phi_rows = []
    for j in range(n_rows):
        y_lo = j*row_w; y_hi = y_lo+row_w
        in_row = in_zone & (state.pos[:, 1] >= y_lo) & (state.pos[:, 1] < y_hi)
        if not np.any(in_row):
            phi_rows.append(0.0)
            continue
        nL = np.sum(state.direction[in_row] > 0)
        nR = np.sum(state.direction[in_row] < 0)
        tot = nL + nR
        phi_rows.append(((nL - nR)/tot)**2 if tot>0 else 0.0)
    return float(np.sum(phi_rows)/n_rows)

def run_simulation(config: SimConfig):
    rng = np.random.default_rng(config.seed)
    walls = build_corridor_walls()
    state = init_agents(config, rng)
    N = state.N

    mx_lo, mx_hi = MEASURE_ZONE

    entry_time = {}
    cross_times = []
    t_first_entry = None
    t_last_exit = None
    phi_history = []
    speed_history = []

    n_steps = int(config.t_max / config.dt)
    for step in range(n_steps):
        F = cafm_step(state, config, walls)
        integrate(state, F, config.dt, config.mass, config.noise_std, rng, v_max_factor=1.3)
        t = (step + 1) * config.dt

        for i in range(N):
            x = state.pos[i, 0]
            d = state.direction[i]
            in_zone = mx_lo <= x <= mx_hi
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

        phi = order_parameter(state)
        if not np.isnan(phi):
            phi_history.append(phi)
        speed_history.append(np.mean(np.linalg.norm(state.vel, axis=1)))

    n_crossed = len(cross_times)
    mean_ct = float(np.mean(cross_times)) if cross_times else config.t_max
    if n_crossed > 0 and t_last_exit is not None and t_first_entry is not None:
        obs_window = max(t_last_exit - t_first_entry, mean_ct)
        flow_rate = n_crossed / obs_window
    else:
        flow_rate = 0.0

    return {
        'mean_crossing_time': mean_ct,
        'flow_rate': flow_rate,
        'order_param_mean': np.mean(phi_history) if phi_history else 0.0,
        'order_param_final': phi_history[-1] if phi_history else 0.0,
        'mean_speed': np.mean(speed_history) if speed_history else 0.0,
        'completion_ratio': n_crossed / N,
        'trajectory': None  # optionally save full trajectory for later visualisation
    }

if __name__ == '__main__':
    configs = [
        ('6:0', 36, 0), ('5:1', 30, 6), ('4:2', 24, 12), ('3:3', 18, 18)
    ]
    paper_ct = [(7,9), (8,10), (8,10), (10,13)]
    for (label, maj, minor), ct_ref in zip(configs, paper_ct):
        cfg = SimConfig(n_major=maj, n_minor=minor, seed=42)
        res = run_simulation(cfg)
        ct_ok = '✓' if ct_ref[0] <= res['mean_crossing_time'] <= ct_ref[1] else '~'
        print(f"{label}  crossing={res['mean_crossing_time']:.2f}s  "
              f"Φ={res['order_param_mean']:.3f}  speed={res['mean_speed']:.2f}  {ct_ok}")   