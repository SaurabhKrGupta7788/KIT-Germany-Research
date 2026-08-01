"""
CAFM Paper‑Faithful Visualiser (final)
======================================
Uses the EXACT physics from Yang et al. 2024 (forces/, models/).
Interactive sliders: Major flow, Minor flow, Corridor length, Corridor width.
No freeze, all variable references corrected.
"""

import numpy as np
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from matplotlib.widgets import Slider, Button
import argparse

from utils.config import SimConfig, CORRIDOR_TOTAL, CORRIDOR_WIDTH, MEASURE_ZONE
from models.base import AgentState, integrate
from models.cafm import cafm_step
from geometry.corridor import build_corridor_walls
from run_single import init_agents, order_parameter

# ── visual constants ────────────────────────
AGENT_RADIUS  = 0.28
ARROW_SCALE   = 0.5
STEPS_PER_FRAME = 3
FIG_W, FIG_H  = 14, 6.0

# ── build initial simulation ─────────────────
def build_sim(n_major, n_minor, length, width, seed=42):
    """Create config, state, RNG, walls for given parameters."""
    cfg = SimConfig(
        n_major=n_major,
        n_minor=n_minor,
        seed=seed,
        avoidance_enabled=True
    )
    rng = np.random.default_rng(seed)
    state = init_agents(cfg, rng)
    walls = build_corridor_walls()
    return cfg, rng, state, walls

# ── main visualiser function ─────────────────
def run_viz(ratio_str='3:3'):
    # parse ratio
    def parse_ratio(s):
        a, b = s.split(':')
        return int(a)*2, int(b)*2
    n_maj_start, n_min_start = parse_ratio(ratio_str)

    cfg, rng, state, walls = build_sim(n_maj_start, n_min_start,
                                       CORRIDOR_TOTAL, CORRIDOR_WIDTH)
    N = state.N

    entry_time  = {}
    cross_times = []
    step_count  = [0]
    is_paused   = False

    # ── figure layout ────────────────
    fig = plt.figure(figsize=(FIG_W, FIG_H), facecolor='#1a1a2e')
    fig.canvas.manager.set_window_title('CAFM Paper‑Faithful Simulator')

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
        # walls
        l1 = ax.axhline(0, color='#556677', lw=2.0, zorder=1)
        l2 = ax.axhline(width, color='#556677', lw=2.0, zorder=1)
        # buffers
        b1 = ax.axvspan(6.0, 8.0, alpha=0.15, color='#445566', zorder=0)
        b2 = ax.axvspan(length-8.0, length-6.0, alpha=0.15, color='#445566', zorder=0)
        # measurement zone
        m1 = ax.axvline(8.0, color='#22cc66', lw=1.2, ls='--', alpha=0.7, zorder=2)
        m2 = ax.axvline(length-8.0, color='#22cc66', lw=1.2, ls='--', alpha=0.7, zorder=2)
        m3 = ax.axvspan(8.0, length-8.0, alpha=0.04, color='#22cc66', zorder=0)
        # text labels
        t1 = ax.text(3.0, width+0.1, 'waiting', color='#888899', fontsize=7)
        t2 = ax.text(length-4.0, width+0.1, 'waiting', color='#888899', fontsize=7)
        t3 = ax.text(6.5, width+0.1, 'buf', color='#667788', fontsize=6)
        t4 = ax.text(length-7.5, width+0.1, 'buf', color='#667788', fontsize=6)
        t5 = ax.text(8.2, width+0.1, 'measurement zone', color='#22cc66', fontsize=7, alpha=0.8)

        geom_elements.extend([l1,l2,b1,b2,m1,m2,m3,t1,t2,t3,t4,t5])
        ax.set_xlim(-0.5, length+0.5)
        ax.set_ylim(-0.5, max(5.0, width+1.0))

    draw_geometry(CORRIDOR_TOTAL, CORRIDOR_WIDTH)

    major_color = '#4488ff'
    minor_color = '#ff4444'

    circles = []
    arrows  = []

    def build_patches():
        for c in circles: c.remove()
        for a in arrows: a.remove()
        circles.clear(); arrows.clear()
        for i in range(N):
            col = major_color if state.direction[i] > 0 else minor_color
            c = plt.Circle((state.pos[i,0], state.pos[i,1]),
                            AGENT_RADIUS, color=col, alpha=0.85, zorder=5)
            ax.add_patch(c)
            circles.append(c)
            a = ax.annotate('', xy=(state.pos[i,0], state.pos[i,1]),
                            xytext=(state.pos[i,0], state.pos[i,1]),
                            arrowprops=dict(arrowstyle='->', color=col, lw=1.2, alpha=0.6),
                            zorder=6)
            arrows.append(a)
    build_patches()

    # ── stats panel ────────────────────────
    ax_stats = fig.add_axes([0.76, 0.25, 0.22, 0.65])
    ax_stats.set_facecolor('#111122')
    ax_stats.axis('off')
    stat_labels = {
        'title'   : ax_stats.text(0.5, 0.95, 'Live Statistics', ha='center', va='top',
                                  fontsize=11, color='#ccccff', fontweight='bold'),
        'time'    : ax_stats.text(0.1, 0.82, 't = 0.00 s', fontsize=9, color='#aaddff'),
        'speed'   : ax_stats.text(0.1, 0.72, 'speed = — m/s', fontsize=9, color='#aaddff'),
        'phi'     : ax_stats.text(0.1, 0.62, 'Φ = —', fontsize=9, color='#aaddff'),
        'crossed' : ax_stats.text(0.1, 0.52, 'crossed = 0', fontsize=9, color='#aaddff'),
        'inzone'  : ax_stats.text(0.1, 0.42, 'in zone = 0', fontsize=9, color='#22cc66'),
        'params'  : ax_stats.text(0.1, 0.25,
                                  f'v₀ = {cfg.v0_mean} m/s\n'
                                  f'Rsaf = {cfg.R_safety} m\n'
                                  f'N = {N}', fontsize=8, color='#778899', va='top', linespacing=1.6),
    }

    # speed mini‑plot
    ax_sp = fig.add_axes([0.76, 0.06, 0.22, 0.12])
    ax_sp.set_facecolor('#111122')
    ax_sp.tick_params(colors='#666677', labelsize=6)
    ax_sp.set_ylabel('v̄', color='#666677', fontsize=7)
    for sp in ax_sp.spines.values(): sp.set_edgecolor('#333344')
    speed_hist   = []
    speed_line,  = ax_sp.plot([], [], color='#4488ff', lw=0.8)
    ax_sp.set_ylim(0, 1.8)

    # ── interactive sliders ────────────────
    ax_slider_maj = fig.add_axes([0.25, 0.14, 0.20, 0.03], facecolor='#222233')
    ax_slider_min = fig.add_axes([0.52, 0.14, 0.20, 0.03], facecolor='#222233')
    ax_slider_len = fig.add_axes([0.25, 0.06, 0.20, 0.03], facecolor='#222233')
    ax_slider_wid = fig.add_axes([0.52, 0.06, 0.20, 0.03], facecolor='#222233')
    ax_btn_reset  = fig.add_axes([0.02, 0.08, 0.08, 0.06])
    ax_btn_pause  = fig.add_axes([0.12, 0.08, 0.08, 0.06])

    fig.s_maj = Slider(ax_slider_maj, 'Major (→)', 0, 40, valinit=n_maj_start, valstep=1, color=major_color)
    fig.s_min = Slider(ax_slider_min, 'Minor (←)', 0, 40, valinit=n_min_start, valstep=1, color=minor_color)
    fig.s_len = Slider(ax_slider_len, 'Length (m)', 20.0, 50.0, valinit=CORRIDOR_TOTAL, valstep=1.0, color='#888899')
    fig.s_wid = Slider(ax_slider_wid, 'Width (m)', 2.0, 10.0, valinit=CORRIDOR_WIDTH, valstep=0.5, color='#888899')

    for s in [fig.s_maj, fig.s_min, fig.s_len, fig.s_wid]:
        s.label.set_color('#aaaaaa'); s.valtext.set_color('#ffffff')

    fig.btn_reset = Button(ax_btn_reset, 'RESET', color='#334455', hovercolor='#446688')
    fig.btn_reset.label.set_color('#ffffff'); fig.btn_reset.label.set_fontweight('bold')
    fig.btn_pause = Button(ax_btn_pause, 'PAUSE', color='#884444', hovercolor='#aa5555')
    fig.btn_pause.label.set_color('#ffffff'); fig.btn_pause.label.set_fontweight('bold')

    def reset_sim(event):
        nonlocal cfg, rng, state, walls, N, entry_time, cross_times, step_count, speed_hist, is_paused
        # build new simulation from slider values
        cfg, rng, state, walls = build_sim(int(fig.s_maj.val), int(fig.s_min.val),
                                           float(fig.s_len.val), float(fig.s_wid.val))
        N = state.N
        entry_time.clear(); cross_times.clear(); step_count[0] = 0; speed_hist.clear(); speed_line.set_data([], [])
        is_paused = False
        fig.btn_pause.label.set_text('PAUSE')
        fig.btn_pause.color = '#884444'
        # redraw geometry using slider values (not config attributes)
        draw_geometry(float(fig.s_len.val), float(fig.s_wid.val))
        stat_labels['params'].set_text(f'v₀ = {cfg.v0_mean} m/s\nRsaf = {cfg.R_safety} m\nN = {N}')
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

    # ── animation update ──────────────────
    def update(frame):
        nonlocal cfg, rng, state, walls, N, entry_time, cross_times, step_count, speed_hist, is_paused
        t = step_count[0] * cfg.dt

        if not is_paused:
            for _ in range(STEPS_PER_FRAME):
                if N > 0:
                    # ---- PAPER‑FAITHFUL FORCE CALL ----
                    F = cafm_step(state, cfg, walls)
                    integrate(state, F, cfg.dt, cfg.mass, cfg.noise_std, rng, cfg.v_max_factor)
                step_count[0] += 1
                t = step_count[0] * cfg.dt

                # crossing tracking
                mx_lo, mx_hi = MEASURE_ZONE
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

        speeds = np.linalg.norm(state.vel, axis=1) if N > 0 else np.zeros(1)
        in_zone_count = 0
        mx_lo, mx_hi = MEASURE_ZONE
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
                tip_x = x + (vx/spd) * ARROW_SCALE
                tip_y = y + (vy/spd) * ARROW_SCALE * 0.6
                arrows[i].xy = (tip_x, tip_y)
                arrows[i].set_position((x, y))
                arrows[i].set_alpha(min(1.0, spd/cfg.v0_mean))
            else:
                arrows[i].xy = (x, y)
                arrows[i].set_position((x, y))
                arrows[i].set_alpha(0.0)

        if not is_paused:
            mean_spd = float(np.mean(speeds)) if N > 0 else 0.0
            phi = order_parameter(state) if N > 0 else np.nan
            phi_str = f'{phi:.3f}' if not np.isnan(phi) else '—'
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
    plt.show()
    return anim

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Paper‑faithful CAFM visualiser')
    parser.add_argument('--ratio', default='3:3', choices=['6:0','5:1','4:2','3:3'])
    args = parser.parse_args()
    run_viz(args.ratio)