"""
LHS Dataset Generator for CAFM GP Surrogate
=============================================
Generates structured training data for Gaussian Process regression.

Design
------
Input space  X : 6 parameters swept via Latin Hypercube Sampling
Output space y : 4 scalar simulation outputs (one per GP target)

Parameters swept (with physical justification):
  1. v0_mean    : desired speed          [0.80, 1.60] m/s
  2. tau        : relaxation time        [0.30, 0.80] s
  3. A          : social repulsion       [10.0, 40.0] N
  4. R_safety   : avoidance trigger      [0.80, 1.60] m
  5. density    : agents/m²              [0.10, 1.0] (controls n_major+n_minor)
  6. flow_ratio : minor/(major+minor)    [0.00, 0.50] (0=unidirectional, 0.5=balanced)

Fixed at Yang et al. 2024 Table 3 values:
  B, K, kappa, r_ped, mass, R_danger, f_adm

Outputs collected per run:
  mean_crossing_time, flow_rate, order_param_mean, mean_speed

References
----------
McKay et al. (1979): Latin Hypercube Sampling
Yang et al. (2024): Physica A 642, 129762
"""

import numpy as np
from scipy.stats import qmc
import time
import os
import sys

# add parent dir so we can import cafm_sim_v3
sys.path.insert(0, os.path.dirname(__file__))
from cafm_sim_v3 import SimParams, run_simulation, CORRIDOR_TOTAL, CORRIDOR_WIDTH

# ─────────────────────────────────────────────
#  Parameter bounds
# ─────────────────────────────────────────────

PARAM_NAMES = ["v0_mean", "tau", "A", "R_safety", "density", "flow_ratio"]

PARAM_BOUNDS = {
    #              lower    upper   unit / note
    "v0_mean"  : (0.80,    1.60),  # m/s
    "tau"      : (0.30,    0.80),  # s
    "A"        : (10.0,    40.0),  # N
    "R_safety" : (0.80,    1.60),  # m  (R_danger = R_safety * 0.5 always)
    "density"  : (0.10,    1.0),  # ped/m²  over corridor area
    "flow_ratio": (0.00,   0.50),  # fraction that are minor (counterflow)
}

OUTPUT_NAMES = [
    "mean_crossing_time",
    "flow_rate",
    "order_param_mean",
    "mean_speed",
]

# measurement zone area (Yang 2024: 10m x 3m)
MEASURE_AREA = 10.0 * CORRIDOR_WIDTH   # 30 m²


def density_to_counts(density, flow_ratio):
    """
    Convert density [ped/m²] and flow_ratio to (n_major, n_minor).
    Total N = density × measurement_area, clipped to [4, 60].
    flow_ratio = n_minor / N
    """
    N_total  = int(np.clip(round(density * MEASURE_AREA), 4, 60))
    n_minor  = int(round(flow_ratio * N_total))
    n_major  = N_total - n_minor
    # ensure at least 2 in each active group
    if n_minor == 0 and flow_ratio > 0:
        n_minor = 2; n_major = max(2, N_total - 2)
    if n_major == 0:
        n_major = 2; n_minor = max(2, N_total - 2)
    return n_major, n_minor


# def lhs_sample(n_samples: int, seed: int = 0) -> np.ndarray:
#     """
#     Generate n_samples × 6 LHS design matrix, scaled to parameter bounds.
#     Uses scipy LatinHypercube with strength=2 for better space-filling.
#     Returns array shape (n_samples, 6).
#     """
#     sampler = qmc.LatinHypercube(d=len(PARAM_NAMES), strength=1, seed=seed)
#     unit    = sampler.random(n_samples)          # (N, 6) in [0,1]

#     # scale each column to its physical range
#     lowers = np.array([PARAM_BOUNDS[k][0] for k in PARAM_NAMES])
#     uppers = np.array([PARAM_BOUNDS[k][1] for k in PARAM_NAMES])
#     scaled = qmc.scale(unit, lowers, uppers)
#     return scaled



def qmc_sobol_sample(n_samples: int, seed: int = 42) -> np.ndarray:
    """
    Generate n_samples × 6 QMC design matrix using a Sobol sequence.
    Scaled to physical parameter bounds.
    """
    # Check if n_samples is a power of 2 (bitwise operation)
    is_power_of_two = (n_samples != 0) and ((n_samples & (n_samples - 1)) == 0)
    if not is_power_of_two:
        print(f"  [WARN] QMC Sobol sequences are optimal only for powers of 2.")
        print(f"         Consider using 256 or 512 instead of {n_samples} for perfect balance.")

    # Initialize Sobol sampler. scramble=True adds random shifts while preserving uniformity
    sampler = qmc.Sobol(d=len(PARAM_NAMES), scramble=True, seed=seed)
    
    # Generate raw unit samples in [0,1)
    unit = sampler.random(n_samples)

    # Scale each column to its physical range
    lowers = np.array([PARAM_BOUNDS[k][0] for k in PARAM_NAMES])
    uppers = np.array([PARAM_BOUNDS[k][1] for k in PARAM_NAMES])
    scaled = qmc.scale(unit, lowers, uppers)
    
    return scaled






# def run_lhs_dataset(
#     n_samples   : int  = 300,
#     n_repeats   : int  = 3,      # average over n_repeats runs per LHS point
#     lhs_seed    : int  = 42,
#     base_sim_seed: int = 0,
#     save_path   : str  = "cafm_lhs_dataset.npz",
#     verbose     : bool = True,
# ) -> dict:
#     """
#     Generate full LHS dataset.

#     For each LHS point:
#       - Run n_repeats simulations with different seeds
#       - Average outputs to reduce stochastic noise
#       - Store (X_row, y_mean, y_std) in dataset

#     Saves .npz with:
#       X           : (n_samples, 6)  input parameter matrix
#       Y           : (n_samples, 4)  mean output matrix
#       Y_std       : (n_samples, 4)  std over repeats (aleatoric noise estimate)
#       param_names : list of input names
#       output_names: list of output names
#       param_bounds: (2, 6) array [lowers; uppers]
#     """
#     X_raw = lhs_sample(n_samples, seed=lhs_seed)  # (N, 6) raw param values

#     Y      = np.zeros((n_samples, len(OUTPUT_NAMES)))
#     Y_std  = np.zeros((n_samples, len(OUTPUT_NAMES)))


###   QMC version with Sobol sampling instead of LHS

def run_qmc_dataset(
    n_samples   : int  = 256,    # CHANGED: 256 is 2^8, optimal for Sobol
    n_repeats   : int  = 3,      
    qmc_seed    : int  = 42,     # Renamed variable
    base_sim_seed: int = 0,
    save_path   : str  = "cafm_qmc_dataset.npz", # Updated filename
    verbose     : bool = True,
) -> dict:
    """
    Generate full QMC dataset using Sobol sequences.
    """
    # CHANGED: Call the new Sobol function
    X_raw = qmc_sobol_sample(n_samples, seed=qmc_seed)  

    Y      = np.zeros((n_samples, len(OUTPUT_NAMES)))
    Y_std  = np.zeros((n_samples, len(OUTPUT_NAMES)))


# till here is mostly the same, except for the sampling method and some variable names. The rest of the function logic remains intact, as it handles the simulation runs and data aggregation in the same way regardless of how the input samples were generated.


    if verbose:
        print(f"\nCAFM QMC (Sobol) Dataset Generation") # Updated text
        print(f"  Samples    : {n_samples}")
        print(f"  Repeats    : {n_repeats} per sample")
        print(f"  Total runs : {n_samples * n_repeats}")
        print(f"  Parameters : {PARAM_NAMES}")
        print(f"  Outputs    : {OUTPUT_NAMES}")
        print(f"  Save path  : {save_path}")
        print()

    t_start = time.time()
    failed  = 0

    for i, x_row in enumerate(X_raw):
        v0_mean, tau, A, R_safety, density, flow_ratio = x_row
        n_major, n_minor = density_to_counts(density, flow_ratio)

        run_outputs = []
        for rep in range(n_repeats):
            p = SimParams(
                n_major   = n_major,
                n_minor   = n_minor,
                v0_mean   = float(v0_mean),
                tau       = float(tau),
                A         = float(A),
                R_safety  = float(R_safety),
                R_danger  = float(R_safety * 0.5),  # always half of R_safety
                seed      = base_sim_seed + i * n_repeats + rep,
            )
            try:
                result = run_simulation(p)
                run_outputs.append([result[k] for k in OUTPUT_NAMES])
            except Exception as e:
                failed += 1
                if verbose:
                    print(f"  [WARN] sample {i} rep {rep} failed: {e}")
                run_outputs.append([np.nan] * len(OUTPUT_NAMES))

        arr        = np.array(run_outputs)
        Y[i]       = np.nanmean(arr, axis=0)
        Y_std[i]   = np.nanstd(arr,  axis=0)

        # progress bar
        if verbose and (i % 20 == 0 or i == n_samples - 1):
            elapsed  = time.time() - t_start
            rate     = (i + 1) / elapsed if elapsed > 0 else 1
            eta      = (n_samples - i - 1) / rate
            pct      = (i + 1) / n_samples * 100
            bar      = "█" * int(pct / 5) + "░" * (20 - int(pct / 5))
            print(f"  [{bar}] {i+1:>4}/{n_samples}  "
                  f"{pct:5.1f}%  elapsed={elapsed:6.1f}s  ETA={eta:6.1f}s", end="\r")

    if verbose:
        print()
        elapsed = time.time() - t_start
        print(f"\nDone in {elapsed:.1f}s  |  failed runs: {failed}")
        print(f"\nOutput statistics (means):")
        for j, name in enumerate(OUTPUT_NAMES):
            vals = Y[:, j]
            print(f"  {name:<25} min={np.nanmin(vals):.3f}  "
                  f"mean={np.nanmean(vals):.3f}  max={np.nanmax(vals):.3f}")

    # build bounds array for saving
    lowers = np.array([PARAM_BOUNDS[k][0] for k in PARAM_NAMES])
    uppers = np.array([PARAM_BOUNDS[k][1] for k in PARAM_NAMES])

    np.savez(
        save_path,
        X            = X_raw,
        Y            = Y,
        Y_std        = Y_std,
        param_names  = np.array(PARAM_NAMES),
        output_names = np.array(OUTPUT_NAMES),
        param_bounds = np.vstack([lowers, uppers]),
    )
    if verbose:
        print(f"\nSaved → {save_path}")

    return {"X": X_raw, "Y": Y, "Y_std": Y_std}


# ─────────────────────────────────────────────
#  Quick smoke test (10 samples)
# ─────────────────────────────────────────────

# if __name__ == "__main__":
#     print("Smoke test: 10 samples × 2 repeats")
#     data = run_lhs_dataset(
#         n_samples    = 10,
#         n_repeats    = 2,
#         save_path    = "cafm_lhs_smoke.npz",
#         verbose      = True,
#     )

if __name__ == "__main__":
    print("Smoke test: 16 samples × 2 repeats (QMC optimal)")
    data = run_qmc_dataset(
        n_samples    = 16,     # CHANGED: 16 instead of 10
        n_repeats    = 2,
        save_path    = "cafm_qmc_smoke.npz",
        verbose      = True,
    )

    
    print("\nX shape:", data["X"].shape)
    print("Y shape:", data["Y"].shape)
    print("\nFirst 5 rows of X:")
    header = "  " + "  ".join(f"{n:>10}" for n in PARAM_NAMES)
    print(header)
    for row in data["X"][:5]:
        print("  " + "  ".join(f"{v:>10.4f}" for v in row))
    print("\nFirst 5 rows of Y:")
    header2 = "  " + "  ".join(f"{n:>22}" for n in OUTPUT_NAMES)
    print(header2)
    for row in data["Y"][:5]:
        print("  " + "  ".join(f"{v:>22.4f}" for v in row))