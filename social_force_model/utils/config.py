"""All parameters (geometry, physical, CAFM) bundled into SimConfig."""

from dataclasses import dataclass

# ── Fixed geometry (Yang 2024, Fig.2) ──
CORRIDOR_TOTAL   = 26.0
CORRIDOR_WIDTH   =  3.0
WAITING_LEFT     = (0.0, 6.0)
BUFFER_LEFT      = (6.0, 8.0)
MEASURE_ZONE     = (8.0, 18.0)
BUFFER_RIGHT     = (18.0, 20.0)
WAITING_RIGHT    = (20.0, 26.0)

@dataclass
class SimConfig:
    """All tuneable AND fixed parameters for a CAFM simulation.

    Defaults match Yang et al. 2024 Table 3 and Section 2.2.
    """
    # ── crowd composition ──
    n_major: int   = 18
    n_minor: int   = 18
    v0_mean: float = 1.21
    v0_std:  float = 0.20

    # ── SFM physical parameters (Yang Table 3) ──
    mass:     float = 80.0
    tau:      float = 0.50
    A:        float = 20.0      # social repulsion strength [N]
    B:        float = 0.08      # repulsion range [m]
    K:        float = 1000.0    # normal contact stiffness [N/m]
    kappa:    float = 1000.0    # tangential friction [N·s/m]
    r_ped:    float = 0.30      # body radius [m]

    # ── wall repulsion (optional; tuneable if needed) ──
    A_wall:   float = 10.0
    B_wall:   float = 0.2

    # ── CAFM avoidance (Yang Section 2.2) ──
    avoidance_enabled: bool = True
    R_safety:  float = 1.22
    R_danger:  float = 0.61   # = R_safety * 0.5
    f_adm:     float = 38800.0

    # ── simulation control ──
    dt:        float = 0.05
    t_max:     float = 80.0
    noise_std: float = 0.05
    seed:      int   = 42

    # speed limit factor (Helbing 1998)
    v_max_factor: float = 1.3