"""
CAFM Real-Time Visualiser — Interactive Geometry Edition v3 (Physics Patched)
===========================================================================
Runs the exact Python CAFM simulation (cafm_sim_v3/v5) and shows
a matplotlib animation of pedestrian movement in real time.

Features:
  - Exact CAFM physics with LATERAL SIDESTEPPING fix.
  - LIVE CONTROLS: Sliders for Major Flow, Minor Flow, 
                   Corridor Length, and Corridor Width.
  - Pause/Resume button for parameter and vector analysis.
  - Dynamic boundaries: walls and measurement zones scale instantly.
"""

import numpy as np
import matplotlib
matplotlib.use('TkAgg') 
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.animation import FuncAnimation
from matplotlib.widgets import Slider, Button
import argparse, sys, os
from dataclasses import dataclass

sys.path.insert(0, os.path.dirname(__file__))

# Import forces that don't depend on geometry bounds
from cafm_sim_v3 import (
    SimParams, AgentState, 
    driving_force, pedestrian_repulsion
)

# ── config ──────────────────────────────────
STEPS_PER_FRAME = 3        
FIG_W, FIG_H    = 14, 6.0  # Taller for extra slider row
AGENT_RADIUS    = 0.28     
ARROW_SCALE     = 0.5      
# ────────────────────────────────────────────

@dataclass
class DynamicSimParams(SimParams):
    """Extends the base parameters to include dynamic geometry."""
    corridor_length: float = 26.0
    corridor_width: float = 3.0

# ── DYNAMIC PHYSICS OVERRIDES ─────────────────

def dynamic_wall_repulsion(state, p):
    F  = np.zeros((state.N, 2))
    y  = state.pos[:, 1]
    vx = state.vel[:, 0]

    ov_b = p.r_ped - y
    F[:, 1] += p.A * np.exp(ov_b / p.B) + p.K * np.maximum(ov_b, 0.0)
    F[:, 0] -= p.kappa * np.maximum(ov_b, 0.0) * vx

    ov_t = p.r_ped - (p.corridor_width - y)
    F[:, 1] -= p.A * np.exp(ov_t / p.B) + p.K * np.maximum(ov_t, 0.0)
    F[:, 0] -= p.kappa * np.maximum(ov_t, 0.0) * vx
    return F

def dynamic_cafm_avoidance_force(state, p):
    """
    Fixed Avoidance Logic:
    Includes orthogonal sidestepping and proportional force scaling
    to prevent unnatural backward bouncing.
    """
    F   = np.zeros((state.N, 2))
    pos = state.pos
    vel = state.vel
    d   = state.direction

    for i in range(state.N):
        counter_mask = (d != d[i])
        if not np.any(counter_mask): continue
        
        cidx    = np.where(counter_mask)[0]
        cpos    = pos[cidx]
        cvel    = vel[cidx]
        
        # Find the absolute closest counterflow pedestrian
        dists   = np.linalg.norm(pos[i] - cpos, axis=1)
        j_loc   = np.argmin(dists)
        dist_ij = dists[j_loc]

        # Only trigger if they breach the safety radius, but haven't crashed past danger
        if not (p.R_danger < dist_ij < p.R_safety): continue

        # Calculate the predicted danger endpoint of the obstacle
        speed_j = np.linalg.norm(cvel[j_loc]) + 1e-9
        R_obs   = (cvel[j_loc] / speed_j) * p.R_danger + cpos[j_loc]
        
        # Base repulsion vector: Points from the obstacle to my current position
        vec = pos[i] - R_obs
        
        # --- 1. LATERAL SIDESTEPPING FIX ---
        # Find the perpendicular direction to my current velocity
        speed_i = np.linalg.norm(vel[i]) + 1e-9
        v_dir = vel[i] / speed_i
        n_perp = np.array([-v_dir[1], v_dir[0]]) 
        
        # Ensure we sidestep in the direction that already has more clearance
        if np.dot(vec, n_perp) < 0:
            n_perp = -n_perp
            
        # Blend the backward repulsion with a strong lateral sidestep
        avoid_dir = vec + (n_perp * 1.5)
        norm_dir = np.linalg.norm(avoid_dir) + 1e-9
        avoid_dir = avoid_dir / norm_dir

        # --- 2. PROPORTIONAL FORCE SCALING FIX ---
        # Force scales linearly from 0 (at R_safety edge) to MAX (at R_danger edge)
        overlap_ratio = (p.R_safety - dist_ij) / (p.R_safety - p.R_danger)
        
        # Realistic max avoidance force (approx 3x body weight to sharply step aside)
        realistic_f_adm = 450.0 
        
        F[i] += avoid_dir * (realistic_f_adm * overlap_ratio)

    return F

def dynamic_integrate(state, F_total, p, rng):
    acc = F_total / p.mass
    noise = rng.normal(0, p.noise_std, size=state.vel.shape)
    state.vel += acc * p.dt + noise

    v_max = 1.3 * state.v0
    speed = np.linalg.norm(state.vel, axis=1)
    too_fast = speed > v_max
    state.vel[too_fast] = (state.vel[too_fast] / speed[too_fast, None] * v_max[too_fast, None])

    state.pos += state.vel * p.dt

    bot = state.pos[:, 1] < p.r_ped
    top = state.pos[:, 1] > p.corridor_width - p.r_ped
    state.vel[bot | top, 1] *= -0.5
    state.pos[:, 1] = np.clip(state.pos[:, 1], p.r_ped, p.corridor_width - p.r_ped)

def dynamic_order_parameter(state, p, n_rows=15):
    mx_lo, mx_hi = 8.0, p.corridor_length - 8.0
    in_zone = (state.pos[:, 0] >= mx_lo) & (state.pos[:, 0] < mx_hi)
    if not np.any(in_zone): return np.nan

    row_w = p.corridor_width / n_rows
    phi_rows = []
    for j in range(n_rows):
        y_lo = j * row_w
        y_hi = y_lo + row_w
        in_row = in_zone & (state.pos[:, 1] >= y_lo) & (state.pos[:, 1] < y_hi)
        if not np.any(in_row):
            phi_rows.append(0.0)
            continue
        n_L = np.sum(state.direction[in_row] > 0)
        n_R = np.sum(state.direction[in_row] < 0)
        tot = n_L + n_R
        phi_rows.append(((n_L - n_R) / tot) ** 2 if tot > 0 else 0.0)
    return float(np.sum(phi_rows) / n_rows)

def dynamic_init_agents(p, rng):
    def place_group(n, x_lo, x_hi, direction):
        pos = np.zeros((n, 2))
        vel = np.zeros((n, 2))
        v0  = np.clip(rng.normal(p.v0_mean, p.v0_std, n), p.v0_mean * 0.5, p.v0_mean * 1.5)
        for k in range(n):
            for _ in range(500):
                xt = rng.uniform(x_lo, x_hi)
                yt = rng.uniform(p.r_ped + 0.05, p.corridor_width - p.r_ped - 0.05)
                if k == 0: break
                if np.all(np.linalg.norm(pos[:k] - [xt, yt], axis=1) > 2 * p.r_ped + 0.05): break
            pos[k] = [xt, yt]
            vel[k] = [direction * v0[k], 0.0]
        return pos, vel, v0

    pM, vM, v0M = place_group(p.n_major, 0.5, 5.5, +1.0)
    pm, vm, v0m = place_group(p.n_minor, p.corridor_length - 5.5, p.corridor_length - 0.5, -1.0)

    pos = np.vstack([pM, pm]) if p.n_major and p.n_minor else (pM if p.n_major else pm) if p.n_major or p.n_minor else np.zeros((0,2))
    vel = np.vstack([vM, vm]) if p.n_major and p.n_minor else (vM if p.n_major else vm) if p.n_major or p.n_minor else np.zeros((0,2))
    v0  = np.concatenate([v0M, v0m])
    direction = np.concatenate([np.ones(p.n_major), -np.ones(p.n_minor)])
    return AgentState(pos, vel, v0, direction)

# ── MAIN VISUALIZER ────────────────────────────

def parse_ratio(s):
    a, b = s.split(':')
    return int(a) * 2, int(b) * 2

def build_sim(n_major, n_minor, length, width, seed=42):
    p   = DynamicSimParams(n_major=n_major, n_minor=n_minor, 
                           corridor_length=length, corridor_width=width, seed=seed)
    rng = np.random.default_rng(seed)
    state = dynamic_init_agents(p, rng)
    return p, rng, state

def run_viz(ratio_str='3:3'):
    n_maj_start, n_min_start = parse_ratio(ratio_str)
    p, rng, state = build_sim(n_maj_start, n_min_start, 26.0, 3.0)
    N = state.N

    entry_time  = {}
    cross_times = []
    step_count  = [0]
    is_paused   = False

    fig = plt.figure(figsize=(FIG_W, FIG_H), facecolor='#1a1a2e')
    fig.canvas.manager.set_window_title('CAFM Interactive Simulator')

    ax = fig.add_axes([0.02, 0.25, 0.72, 0.65])
    ax.set_facecolor('#0f0f1a')
    ax.set_aspect('equal')
    ax.set_xlabel('x (m)', color='#aaaaaa', fontsize=9)
    ax.set_ylabel('y (m)', color='#aaaaaa', fontsize=9)
    ax.tick_params(colors='#aaaaaa', labelsize=8)
    for spine in ax.spines.values(): spine.set_edgecolor('#333355')

    geom_elements = []

    def draw_geometry(length, width):
        for el in geom_elements: el.remove()
        geom_elements.clear()

        l1 = ax.axhline(0, color='#556677', lw=2.0, zorder=1)
        l2 = ax.axhline(width, color='#556677', lw=2.0, zorder=1)
        
        b1 = ax.axvspan(6.0, 8.0, alpha=0.15, color='#445566', zorder=0)
        b2 = ax.axvspan(length - 8.0, length - 6.0, alpha=0.15, color='#445566', zorder=0)
        
        m1 = ax.axvline(8.0, color='#22cc66', lw=1.2, ls='--', alpha=0.7, zorder=2)
        m2 = ax.axvline(length - 8.0, color='#22cc66', lw=1.2, ls='--', alpha=0.7, zorder=2)
        m3 = ax.axvspan(8.0, length - 8.0, alpha=0.04, color='#22cc66', zorder=0)

        t1 = ax.text(3.0, width + 0.1, 'waiting', color='#888899', fontsize=7)
        t2 = ax.text(length - 4.0, width + 0.1, 'waiting', color='#888899', fontsize=7)
        t3 = ax.text(6.5, width + 0.1, 'buf', color='#667788', fontsize=6)
        t4 = ax.text(length - 7.5, width + 0.1, 'buf', color='#667788', fontsize=6)
        t5 = ax.text(8.2, width + 0.1, 'measurement zone', color='#22cc66', fontsize=7, alpha=0.8)

        geom_elements.extend([l1, l2, b1, b2, m1, m2, m3, t1, t2, t3, t4, t5])
        ax.set_xlim(-0.5, length + 0.5)
        ax.set_ylim(-0.5, max(5.0, width + 1.0))

    draw_geometry(p.corridor_length, p.corridor_width)

    major_color = '#4488ff'
    minor_color = '#ff4444'

    circles = []
    arrows  = []

    def build_patches():
        for c in circles: c.remove()
        for a in arrows: a.remove()
        circles.clear()
        arrows.clear()
        
        for i in range(N):
            col = major_color if state.direction[i] > 0 else minor_color
            c = plt.Circle((state.pos[i, 0], state.pos[i, 1]),
                            AGENT_RADIUS, color=col, alpha=0.85, zorder=5)
            ax.add_patch(c)
            circles.append(c)

            a = ax.annotate('', xy=(state.pos[i,0], state.pos[i,1]),
                            xytext=(state.pos[i,0], state.pos[i,1]),
                            arrowprops=dict(arrowstyle='->', color=col, lw=1.2, alpha=0.6),
                            zorder=6)
            arrows.append(a)

    build_patches()

    # ── stats panel (right 15%) ──────────────────────
    ax_stats = fig.add_axes([0.76, 0.25, 0.22, 0.65])
    ax_stats.set_facecolor('#111122')
    ax_stats.axis('off')

    stat_labels = {
        'title'   : ax_stats.text(0.5, 0.95, 'Live Statistics', ha='center', va='top', fontsize=11, color='#ccccff', fontweight='bold'),
        'time'    : ax_stats.text(0.1, 0.82, 't = 0.00 s', fontsize=9, color='#aaddff'),
        'speed'   : ax_stats.text(0.1, 0.72, 'speed = — m/s', fontsize=9, color='#aaddff'),
        'phi'     : ax_stats.text(0.1, 0.62, 'Φ = —', fontsize=9, color='#aaddff'),
        'crossed' : ax_stats.text(0.1, 0.52, 'crossed = 0', fontsize=9, color='#aaddff'),
        'inzone'  : ax_stats.text(0.1, 0.42, 'in zone = 0', fontsize=9, color='#22cc66'),
        'params'  : ax_stats.text(0.1, 0.25, f'v₀ = {p.v0_mean} m/s\nRsaf = {p.R_safety} m\nN = {N}', fontsize=8, color='#778899', va='top', linespacing=1.6),
    }

    ax_sp = fig.add_axes([0.76, 0.06, 0.22, 0.12])
    ax_sp.set_facecolor('#111122')
    ax_sp.tick_params(colors='#666677', labelsize=6)
    ax_sp.set_ylabel('v̄', color='#666677', fontsize=7)
    for sp in ax_sp.spines.values(): sp.set_edgecolor('#333344')
    speed_hist   = []
    speed_line,  = ax_sp.plot([], [], color='#4488ff', lw=0.8)
    ax_sp.set_ylim(0, 1.8)

    # ── INTERACTIVE CONTROLS ─────────────────────────
    ax_slider_maj = fig.add_axes([0.25, 0.14, 0.20, 0.03], facecolor='#222233')
    ax_slider_min = fig.add_axes([0.52, 0.14, 0.20, 0.03], facecolor='#222233')
    ax_slider_len = fig.add_axes([0.25, 0.06, 0.20, 0.03], facecolor='#222233')
    ax_slider_wid = fig.add_axes([0.52, 0.06, 0.20, 0.03], facecolor='#222233')
    
    ax_btn_reset  = fig.add_axes([0.02, 0.08, 0.08, 0.06])
    ax_btn_pause  = fig.add_axes([0.12, 0.08, 0.08, 0.06])

    fig.s_maj = Slider(ax_slider_maj, 'Major (→)', 0, 40, valinit=n_maj_start, valstep=1, color=major_color)
    fig.s_min = Slider(ax_slider_min, 'Minor (←)', 0, 40, valinit=n_min_start, valstep=1, color=minor_color)
    fig.s_len = Slider(ax_slider_len, 'Length (m)', 20.0, 50.0, valinit=26.0, valstep=1.0, color='#888899')
    fig.s_wid = Slider(ax_slider_wid, 'Width (m)', 2.0, 10.0, valinit=3.0, valstep=0.5, color='#888899')
    
    for s in [fig.s_maj, fig.s_min, fig.s_len, fig.s_wid]:
        s.label.set_color('#aaaaaa'); s.valtext.set_color('#ffffff')

    fig.btn_reset = Button(ax_btn_reset, 'RESET', color='#334455', hovercolor='#446688')
    fig.btn_reset.label.set_color('#ffffff'); fig.btn_reset.label.set_fontweight('bold')

    fig.btn_pause = Button(ax_btn_pause, 'PAUSE', color='#884444', hovercolor='#aa5555')
    fig.btn_pause.label.set_color('#ffffff'); fig.btn_pause.label.set_fontweight('bold')

    def reset_sim(event):
        nonlocal p, rng, state, N, entry_time, cross_times, step_count, speed_hist, is_paused
        
        p, rng, state = build_sim(int(fig.s_maj.val), int(fig.s_min.val), 
                                  float(fig.s_len.val), float(fig.s_wid.val))
        N = state.N
        entry_time.clear(); cross_times.clear(); step_count[0] = 0; speed_hist.clear(); speed_line.set_data([], [])
        
        is_paused = False
        fig.btn_pause.label.set_text('PAUSE')
        fig.btn_pause.color = '#884444'
        
        draw_geometry(p.corridor_length, p.corridor_width)
        stat_labels['params'].set_text(f'v₀ = {p.v0_mean} m/s\nRsaf = {p.R_safety} m\nN = {N}')
        build_patches()

    def toggle_pause(event):
        nonlocal is_paused
        is_paused = not is_paused
        if is_paused:
            fig.btn_pause.label.set_text('RESUME')
            fig.btn_pause.color = '#448844' 
        else:
            fig.btn_pause.label.set_text('PAUSE')
            fig.btn_pause.color = '#884444' 
        fig.canvas.draw_idle()

    fig.btn_reset.on_clicked(reset_sim)
    fig.btn_pause.on_clicked(toggle_pause)

    # ── animation update ────────────────────────────
    def update(frame):
        t = step_count[0] * p.dt

        if not is_paused:
            for _ in range(STEPS_PER_FRAME):
                if N > 0:
                    F  = driving_force(state, p)
                    F += pedestrian_repulsion(state, p)
                    F += dynamic_wall_repulsion(state, p)
                    # THIS LINE IS NOW USING THE UPDATED AVOIDANCE LOGIC
                    F += dynamic_cafm_avoidance_force(state, p) 
                    dynamic_integrate(state, F, p, rng)
                step_count[0] += 1
                t = step_count[0] * p.dt

                mx_lo, mx_hi = 8.0, p.corridor_length - 8.0
                for i in range(N):
                    x = state.pos[i, 0]
                    d = state.direction[i]
                    in_z = mx_lo <= x <= mx_hi
                    if i not in entry_time and in_z:
                        entry_time[i] = t
                    if i in entry_time:
                        exited = (d > 0 and x > mx_hi) or (d < 0 and x < mx_lo)
                        if exited:
                            cross_times.append(t - entry_time[i])
                            del entry_time[i]

        speeds = np.linalg.norm(state.vel, axis=1) if N > 0 else []
        in_zone_count = 0
        mx_lo, mx_hi = 8.0, p.corridor_length - 8.0

        for i in range(N):
            x, y = state.pos[i]
            vx, vy = state.vel[i]
            spd = speeds[i]

            circles[i].center = (x, y)
            in_z = mx_lo <= x <= mx_hi
            if in_z: in_zone_count += 1

            base_col = major_color if state.direction[i] > 0 else minor_color
            circles[i].set_alpha(0.5 if not in_z else 0.92)
            circles[i].set_facecolor(base_col)

            if spd > 0.05:
                tip_x = x + (vx / spd) * ARROW_SCALE
                tip_y = y + (vy / spd) * ARROW_SCALE * 0.6
                arrows[i].xy = (tip_x, tip_y)
                arrows[i].set_position((x, y))
                arrows[i].set_alpha(min(1.0, spd / p.v0_mean))
            else:
                arrows[i].xy = (x, y)
                arrows[i].set_position((x, y))
                arrows[i].set_alpha(0.0)

        if not is_paused:
            mean_spd = float(np.mean(speeds)) if N > 0 else 0.0
            phi      = dynamic_order_parameter(state, p) if N > 0 else np.nan
            phi_str  = f'{phi:.3f}' if not np.isnan(phi) else '—'

            speed_hist.append(mean_spd)
            if len(speed_hist) > 200: speed_hist.pop(0)
            speed_line.set_data(range(len(speed_hist)), speed_hist)
            ax_sp.set_xlim(0, max(200, len(speed_hist)))

            stat_labels['time'   ].set_text(f't = {t:.2f} s')
            stat_labels['speed'  ].set_text(f'speed = {mean_spd:.3f} m/s')
            stat_labels['phi'    ].set_text(f'Φ = {phi_str}')
            stat_labels['crossed'].set_text(f'crossed = {len(cross_times)}')
            stat_labels['inzone' ].set_text(f'in zone = {in_zone_count}')

        return circles + arrows + [speed_line]

    anim = FuncAnimation(fig, update, interval=40, blit=False, cache_frame_data=False)
    plt.subplots_adjust(bottom=0.25) 
    plt.show()
    return anim 

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='CAFM pedestrian visualiser')
    parser.add_argument('--ratio', default='3:3', choices=['6:0','5:1','4:2','3:3'])
    args = parser.parse_args()
    running_anim = run_viz(args.ratio)