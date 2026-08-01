"""Corridor walls and nearest‑point utilities."""

import numpy as np
from scipy.spatial import cKDTree
from utils.config import CORRIDOR_WIDTH

class Wall:
    """Straight vertical/horizontal wall segment."""
    def __init__(self, x1, y1, x2, y2):
        self.p1 = np.array([x1, y1], dtype=float)
        self.p2 = np.array([x2, y2], dtype=float)
        self.dir = self.p2 - self.p1
        self.length = np.linalg.norm(self.dir)
        # normal pointing away from wall (to the interior)
        self.normal = np.array([-self.dir[1], self.dir[0]]) / self.length

    def nearest(self, pos):
        """Return (distance, unit_normal_pointing_away_from_wall)."""
        v = pos - self.p1
        t = np.dot(v, self.dir) / (self.length ** 2)
        t = np.clip(t, 0.0, 1.0)
        closest = self.p1 + t * self.dir
        diff = pos - closest
        dist = np.linalg.norm(diff)
        if dist < 1e-12:
            return dist, self.normal  # avoid division by zero
        return dist, diff / dist

def build_corridor_walls():
    """Return list of Wall objects for the 26 m straight corridor."""
    # bottom wall (y=0) from x=0 to x=26
    bottom = Wall(0.0, 0.0, 26.0, 0.0)
    # top wall (y=3)
    top    = Wall(0.0, 3.0, 26.0, 3.0)
    return [bottom, top]