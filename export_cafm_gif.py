import numpy as np
import matplotlib
matplotlib.use('Agg') # Headless backend for saving
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

# Import from the existing files
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from cafm_visualisation import build_sim, AGENT_RADIUS, ARROW_SCALE, dynamic_integrate, dynamic_cafm_avoidance_force, dynamic_wall_repulsion
from cafm_sim_v3 import driving_force, pedestrian_repulsion, order_parameter

def create_cafm_gif(output_filename="cafm_simulation.gif", frames=150, fps=20, n_major=10, n_minor=4):
    print(f"Generating CAFM simulation animation: {output_filename}")
    p, rng, state = build_sim(n_major, n_minor, 26.0, 3.0)
    N = state.N

    fig, ax = plt.subplots(figsize=(10, 4), facecolor='#1a1a2e')
    ax.set_facecolor('#0f0f1a')
    ax.set_aspect('equal')
    ax.set_xlim(0, 26.0)
    ax.set_ylim(0, 3.0)
    ax.axis('off') # Hide axes for clean presentation
    
    # Draw static boundaries
    ax.axhline(0, color='#556677', lw=2.0, zorder=1)
    ax.axhline(3.0, color='#556677', lw=2.0, zorder=1)
    ax.axvline(8.0, color='#22cc66', lw=1.2, ls='--', alpha=0.7, zorder=2)
    ax.axvline(18.0, color='#22cc66', lw=1.2, ls='--', alpha=0.7, zorder=2)

    circles = []
    arrows = []
    for i in range(N):
        col = '#4488ff' if state.direction[i] > 0 else '#ff4444'
        c = plt.Circle((state.pos[i, 0], state.pos[i, 1]), AGENT_RADIUS, color=col, alpha=0.85, zorder=5)
        ax.add_patch(c)
        circles.append(c)
        a = ax.annotate('', xy=(state.pos[i,0], state.pos[i,1]), xytext=(state.pos[i,0], state.pos[i,1]),
                        arrowprops=dict(arrowstyle='->', color=col, lw=1.2, alpha=0.6), zorder=6)
        arrows.append(a)

    def update(frame):
        # 3 steps per frame to speed up visuals
        for _ in range(3):
            F  = driving_force(state, p)
            F += pedestrian_repulsion(state, p)
            F += dynamic_wall_repulsion(state, p)
            F += dynamic_cafm_avoidance_force(state, p) 
            dynamic_integrate(state, F, p, rng)
            
        speeds = np.linalg.norm(state.vel, axis=1)
        for i in range(N):
            x, y = state.pos[i]
            vx, vy = state.vel[i]
            spd = speeds[i]
            circles[i].center = (x, y)
            
            if spd > 0.05:
                tip_x = x + (vx / spd) * ARROW_SCALE
                tip_y = y + (vy / spd) * ARROW_SCALE * 0.6
                arrows[i].xy = (tip_x, tip_y)
                arrows[i].set_position((x, y))
                arrows[i].set_alpha(min(1.0, spd / p.v0_mean))
            else:
                arrows[i].set_alpha(0.0)
                
        return circles + arrows

    anim = FuncAnimation(fig, update, frames=frames, interval=1000/fps, blit=False)
    anim.save(output_filename, writer='pillow', fps=fps, dpi=72)
    print(f"Saved {output_filename} successfully.")

if __name__ == '__main__':
    create_cafm_gif()
