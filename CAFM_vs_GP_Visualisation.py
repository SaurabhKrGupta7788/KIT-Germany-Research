"""
CAFM vs GP Digital Twin Dashboard
=============================================
Top: Real-time Microscopic CAFM Simulation
Bottom: Macroscopic Metrics (Live CAFM vs Instant GP Prediction)
"""

import numpy as np
import matplotlib
matplotlib.use('TkAgg') 
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from matplotlib.widgets import Slider, Button
import sys, os
from dataclasses import dataclass

sys.path.insert(0, os.path.dirname(__file__))
from cafm_sim_v3 import SimParams, AgentState, driving_force, pedestrian_repulsion, cafm_avoidance_force

# ── config ──────────────────────────────────
STEPS_PER_FRAME = 3        
FIG_W, FIG_H    = 16, 10.0  # Larger canvas for split screen
AGENT_RADIUS    = 0.28     
ARROW_SCALE     = 0.5      
# ────────────────────────────────────────────

@dataclass
class DynamicSimParams(SimParams):
    corridor_length: float = 26.0
    corridor_width: float = 3.0

# ── 1. GP SURROGATE PREDICTOR (THE AI BRAIN) ──
def get_gp_predictions(v0, tau, A, R_safety, density, flow_ratio):
    """
    [RADHA'S NOTE]: This is where your GPyTorch model connects!
    For now, I am using a dummy heuristic so the visualizer runs without crashing.
    To make it real, load your `scaler_X`, `scaler_Y`, and `model_list` here and return:
    gp_mean, gp_std
    """
    # DUMMY HEURISTICS (Replace with: model_list(X_tensor))
    ct_mean = 8.0 + (density * 12.0)
    flow_mean = 0.5 + (density * 1.5) - (flow_ratio * 0.5)
    order_mean = 0.4 if flow_ratio == 0 else 0.15 + (density * 0.2)
    speed_mean = v0 - (density * 0.5)
    
    # Return structure: [Crossing Time, Flow Rate, Order Param, Mean Speed]
    gp_means = np.array([ct_mean, flow_mean, order_mean, speed_mean])
    gp_stds = np.array([1.5, 0.15, 0.05, 0.08]) # Dummy uncertainty
    return gp_means, gp_stds


# ── 2. DYNAMIC PHYSICS OVERRIDES ─────────────────
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


# ── 3. MAIN DIGITAL TWIN VISUALIZER ────────────────────────────

def build_sim(n_major, n_minor, length, width, seed=42):
    p   = DynamicSimParams(n_major=n_major, n_minor=n_minor, 
                           corridor_length=length, corridor_width=width, seed=seed)
    rng = np.random.default_rng(seed)
    state = dynamic_init_agents(p, rng)
    return p, rng, state

def run_viz():
    n_maj_start, n_min_start = 18, 18
    p, rng, state = build_sim(n_maj_start, n_min_start, 26.0, 3.0)
    N = state.N

    entry_time  = {}
    cross_times = []
    step_count  = [0]
    is_paused   = False

    fig = plt.figure(figsize=(FIG_W, FIG_H), facecolor='#1a1a2e')
    fig.canvas.manager.set_window_title('CAFM vs GP Digital Twin Dashboard')

    # TOP HALF: The CAFM Microscopic Visualizer
    ax_sim = fig.add_axes([0.02, 0.55, 0.72, 0.40])
    ax_sim.set_facecolor('#0f0f1a')
    ax_sim.set_aspect('equal')
    ax_sim.set_title("Real-Time CAFM Microscopic Simulator", color='white', pad=10)
    ax_sim.tick_params(colors='#aaaaaa', labelsize=8)
    for spine in ax_sim.spines.values(): spine.set_edgecolor('#333355')

    geom_elements = []

    def draw_geometry(length, width):
        for el in geom_elements: el.remove()
        geom_elements.clear()
        l1 = ax_sim.axhline(0, color='#556677', lw=2.0, zorder=1)
        l2 = ax_sim.axhline(width, color='#556677', lw=2.0, zorder=1)
        m1 = ax_sim.axvline(8.0, color='#22cc66', lw=1.2, ls='--', alpha=0.7, zorder=2)
        m2 = ax_sim.axvline(length - 8.0, color='#22cc66', lw=1.2, ls='--', alpha=0.7, zorder=2)
        m3 = ax_sim.axvspan(8.0, length - 8.0, alpha=0.04, color='#22cc66', zorder=0)
        t5 = ax_sim.text(8.2, width + 0.1, 'Measurement Zone', color='#22cc66', fontsize=7, alpha=0.8)
        geom_elements.extend([l1, l2, m1, m2, m3, t5])
        ax_sim.set_xlim(-0.5, length + 0.5)
        ax_sim.set_ylim(-0.5, max(5.0, width + 1.0))

    draw_geometry(p.corridor_length, p.corridor_width)

    major_color, minor_color = '#4488ff', '#ff4444'
    circles, arrows  = [], []

    def build_patches():
        for c in circles: c.remove()
        for a in arrows: a.remove()
        circles.clear(); arrows.clear()
        for i in range(state.N):
            col = major_color if state.direction[i] > 0 else minor_color
            c = plt.Circle((state.pos[i, 0], state.pos[i, 1]), AGENT_RADIUS, color=col, alpha=0.85, zorder=5)
            ax_sim.add_patch(c)
            circles.append(c)
            a = ax_sim.annotate('', xy=(0,0), xytext=(0,0), arrowprops=dict(arrowstyle='->', color=col, lw=1.2, alpha=0.6), zorder=6)
            arrows.append(a)

    build_patches()

    # BOTTOM HALF: 4 Macroscopic Graphs (CAFM vs GP)
    metric_names = ["Crossing Time (s)", "Flow Rate (ped/s)", "Order Param", "Mean Speed (m/s)"]
    axes_graphs = [fig.add_axes([0.05 + i*0.23, 0.15, 0.20, 0.30]) for i in range(4)]
    
    lines_cafm = []
    lines_gp = []
    bands_gp = []
    data_hists = [[], [], [], []]

    for i, ax in enumerate(axes_graphs):
        ax.set_facecolor('#111122')
        ax.set_title(metric_names[i], color='#aaaaaa', fontsize=10)
        ax.tick_params(colors='#666677', labelsize=8)
        line_c, = ax.plot([], [], color='#22cc66', lw=2, label="Live CAFM")
        line_g = ax.axhline(-100, color='#4488ff', lw=2, ls='--', label="GP Predict")
        lines_cafm.append(line_c)
        lines_gp.append(line_g)
        bands_gp.append(None) # Placeholder for fill_between
        if i == 0: ax.legend(loc='upper right', fontsize=7, facecolor='#222233', edgecolor='none', labelcolor='white')

    # ── INTERACTIVE CONTROLS ─────────────────────────
    ax_slider_maj = fig.add_axes([0.80, 0.85, 0.15, 0.02], facecolor='#222233')
    ax_slider_min = fig.add_axes([0.80, 0.80, 0.15, 0.02], facecolor='#222233')
    ax_btn_reset  = fig.add_axes([0.80, 0.65, 0.07, 0.05])
    ax_btn_pause  = fig.add_axes([0.88, 0.65, 0.07, 0.05])

    fig.s_maj = Slider(ax_slider_maj, 'Major', 0, 40, valinit=n_maj_start, valstep=1, color=major_color)
    fig.s_min = Slider(ax_slider_min, 'Minor', 0, 40, valinit=n_min_start, valstep=1, color=minor_color)
    for s in [fig.s_maj, fig.s_min]:
        s.label.set_color('#aaaaaa'); s.valtext.set_color('#ffffff')

    fig.btn_reset = Button(ax_btn_reset, 'UPDATE', color='#334455', hovercolor='#446688')
    fig.btn_reset.label.set_color('#ffffff')
    fig.btn_pause = Button(ax_btn_pause, 'PAUSE', color='#884444', hovercolor='#aa5555')
    fig.btn_pause.label.set_color('#ffffff')

    def update_gp_lines():
        # Convert sliders to GP inputs
        n_maj = int(fig.s_maj.val)
        n_min = int(fig.s_min.val)
        total_ped = n_maj + n_min
        
        density = total_ped / (10.0 * p.corridor_width) if total_ped > 0 else 0
        flow_ratio = n_min / total_ped if total_ped > 0 else 0
        
        # Ask the GP!
        gp_means, gp_stds = get_gp_predictions(p.v0_mean, p.tau, p.A, p.R_safety, density, flow_ratio)
        
        for i, ax in enumerate(axes_graphs):
            lines_gp[i].set_ydata([gp_means[i], gp_means[i]])
            
            # Remove old band
            if bands_gp[i] is not None:
                bands_gp[i].remove()
            
            # Draw new Epistemic Uncertainty band
            bands_gp[i] = ax.fill_between([0, 10000], 
                                          gp_means[i] - 2*gp_stds[i], 
                                          gp_means[i] + 2*gp_stds[i], 
                                          color='#4488ff', alpha=0.2)
            
            # Dynamically adjust y-limits to fit both GP and CAFM
            ax.set_ylim(max(0, gp_means[i] - 4*gp_stds[i]), gp_means[i] + 4*gp_stds[i])
            ax.set_xlim(0, max(50, len(data_hists[0])))

    def reset_sim(event):
        nonlocal p, rng, state, N, entry_time, cross_times, step_count, data_hists, is_paused
        
        p, rng, state = build_sim(int(fig.s_maj.val), int(fig.s_min.val), 26.0, 3.0)
        N = state.N
        entry_time.clear(); cross_times.clear(); step_count[0] = 0
        data_hists = [[], [], [], []]
        
        for line in lines_cafm: line.set_data([], [])
        
        is_paused = False
        fig.btn_pause.label.set_text('PAUSE'); fig.btn_pause.color = '#884444'
        
        draw_geometry(p.corridor_length, p.corridor_width)
        build_patches()
        update_gp_lines()

    def toggle_pause(event):
        nonlocal is_paused
        is_paused = not is_paused
        fig.btn_pause.label.set_text('RESUME' if is_paused else 'PAUSE')
        fig.btn_pause.color = '#448844' if is_paused else '#884444'
        fig.canvas.draw_idle()

    fig.btn_reset.on_clicked(reset_sim)
    fig.btn_pause.on_clicked(toggle_pause)

    # Initialize GP lines on startup
    update_gp_lines()

    # ── animation update ────────────────────────────
    def update(frame):
        t = step_count[0] * p.dt

        if not is_paused:
            for _ in range(STEPS_PER_FRAME):
                if state.N > 0:
                    F  = driving_force(state, p)
                    F += pedestrian_repulsion(state, p)
                    F += dynamic_wall_repulsion(state, p)
                    F += cafm_avoidance_force(state, p)
                    dynamic_integrate(state, F, p, rng)
                step_count[0] += 1
                t = step_count[0] * p.dt

                mx_lo, mx_hi = 8.0, p.corridor_length - 8.0
                for i in range(state.N):
                    x = state.pos[i, 0]
                    d = state.direction[i]
                    in_z = mx_lo <= x <= mx_hi
                    if i not in entry_time and in_z:
                        entry_time[i] = t
                    if i in entry_time:
                        if (d > 0 and x > mx_hi) or (d < 0 and x < mx_lo):
                            cross_times.append(t - entry_time[i])
                            del entry_time[i]

            # Update Microscopic Animation
            speeds = np.linalg.norm(state.vel, axis=1) if state.N > 0 else []
            mx_lo, mx_hi = 8.0, p.corridor_length - 8.0
            
            for i in range(state.N):
                x, y = state.pos[i]
                vx, vy = state.vel[i]
                spd = speeds[i]

                circles[i].center = (x, y)
                in_z = mx_lo <= x <= mx_hi
                circles[i].set_alpha(0.5 if not in_z else 0.92)

                if spd > 0.05:
                    arrows[i].xy = (x + (vx/spd)*ARROW_SCALE, y + (vy/spd)*ARROW_SCALE*0.6)
                    arrows[i].set_position((x, y))
                    arrows[i].set_alpha(min(1.0, spd / p.v0_mean))
                else:
                    arrows[i].set_alpha(0.0)

            # Update Macroscopic Graphs
            mean_ct = float(np.mean(cross_times)) if cross_times else 0.0
            flow_r = len(cross_times) / t if t > 0 else 0.0
            phi = dynamic_order_parameter(state, p)
            mean_spd = float(np.mean(speeds)) if state.N > 0 else 0.0

            if not np.isnan(phi):
                data_hists[0].append(mean_ct)
                data_hists[1].append(flow_r)
                data_hists[2].append(phi)
                data_hists[3].append(mean_spd)

                x_data = range(len(data_hists[0]))
                for idx, line in enumerate(lines_cafm):
                    line.set_data(x_data, data_hists[idx])
                    # Auto-scroll X axis if it gets too long
                    if len(x_data) > axes_graphs[idx].get_xlim()[1]:
                        axes_graphs[idx].set_xlim(0, len(x_data) + 100)

        return circles + arrows + lines_cafm

    anim = FuncAnimation(fig, update, interval=40, blit=False, cache_frame_data=False)
    plt.show()

if __name__ == '__main__':
    run_viz()