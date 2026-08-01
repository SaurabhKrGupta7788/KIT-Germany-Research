"""Agent state container and Euler integrator."""

import numpy as np

class AgentState:
    __slots__ = ('pos', 'vel', 'v0', 'direction', 'N')
    def __init__(self, pos, vel, v0, direction):
        self.pos = pos.astype(float)
        self.vel = vel.astype(float)
        self.v0  = v0.astype(float)
        self.direction = direction.astype(float)   # +1 (L→R) or -1 (R→L)
        self.N = len(pos)

def integrate(state, F_total, dt, mass, noise_std, rng, v_max_factor=1.3):
    acc = F_total / mass
    noise = rng.normal(0, noise_std, size=state.vel.shape)
    state.vel += acc * dt + noise

    # speed clamp
    v_max = v_max_factor * state.v0
    speed = np.linalg.norm(state.vel, axis=1)
    too_fast = speed > v_max
    state.vel[too_fast] = (state.vel[too_fast] / speed[too_fast, None] * v_max[too_fast, None])

    state.pos += state.vel * dt

    # keep inside walls (hard boundary)
    state.pos[:, 1] = np.clip(state.pos[:, 1], 0.3, 2.7)   # assumes r_ped=0.3