"""Full CAFM simulation step."""

from forces.driving import compute_driving
from forces.repulsion import compute_repulsion
from forces.wall import compute_wall_repulsion
from forces.avoidance import compute_avoidance

def cafm_step(state, config, walls):
    """Compute total force and return it (no integration)."""
    F = compute_driving(state, config.v0_mean, config.tau, config.mass)
    F += compute_repulsion(state, config.A, config.B, config.K, config.kappa, config.r_ped)
    F += compute_wall_repulsion(state, walls, config.A_wall, config.B_wall,
                                config.K, config.kappa, config.r_ped)
    if config.avoidance_enabled:
        F += compute_avoidance(state, config.R_safety, config.R_danger, config.f_adm)
    return F