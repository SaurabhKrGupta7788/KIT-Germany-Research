"""Driving force: Yang Eq.(1)"""

import numpy as np

def compute_driving(state, v0_mean, tau, mass):
    """F0_i = m * (v0*e_i - v_i) / tau"""
    desired = np.zeros_like(state.vel)
    desired[:, 0] = state.direction * state.v0
    return mass * (desired - state.vel) / tau