"""Batch generator for CAFM GP surrogate data."""

import argparse

import numpy as np
from scipy.stats import qmc

from utils.config import SimConfig
from run_single import run_simulation

PARAM_NAMES = ['v0_mean', 'tau', 'A', 'R_safety', 'density', 'flow_ratio']
OUTPUT_NAMES = ['mean_crossing_time', 'flow_rate', 'order_param_mean', 'mean_speed']
MEASURE_AREA = 30.0

BOUNDS = {
    'v0_mean':   (0.80, 1.60),
    'tau':       (0.30, 0.80),
    'A':         (10.0, 40.0),
    'R_safety':  (0.80, 1.60),
    'density':   (0.10, 1.0),
    'flow_ratio':(0.00, 0.50),
}

def density_to_counts(density, flow_ratio):
    N = int(np.clip(round(density * MEASURE_AREA), 4, 60))
    n_minor = int(round(flow_ratio * N))
    n_major = N - n_minor
    if n_minor == 0 and flow_ratio > 0:
        n_minor, n_major = 2, max(2, N-2)
    if n_major == 0:
        n_major, n_minor = 2, max(2, N-2)
    return n_major, n_minor

def generate_qmc_samples(n_samples=256, seed=42):
    """Generate 6D input samples for the full parameter space."""
    is_power_of_two = (n_samples > 0) and ((n_samples & (n_samples - 1)) == 0)

    if is_power_of_two:
        sampler = qmc.Sobol(d=len(PARAM_NAMES), scramble=True, seed=seed)
    else:
        sampler = qmc.LatinHypercube(d=len(PARAM_NAMES), strength=1, seed=seed)

    unit = sampler.random(n_samples)
    lowers = np.array([BOUNDS[k][0] for k in PARAM_NAMES])
    uppers = np.array([BOUNDS[k][1] for k in PARAM_NAMES])
    return qmc.scale(unit, lowers, uppers)

def single_run(params_dict, base_seed):
    """Run one simulation and return output vector."""
    n_major, n_minor = density_to_counts(params_dict['density'], params_dict['flow_ratio'])
    cfg = SimConfig(
        n_major=n_major, n_minor=n_minor,
        v0_mean=params_dict['v0_mean'],
        tau=params_dict['tau'],
        A=params_dict['A'],
        R_safety=params_dict['R_safety'],
        R_danger=params_dict['R_safety'] * 0.5,
        seed=base_seed,
        avoidance_enabled=True
    )
    res = run_simulation(cfg)
    return [res[name] for name in OUTPUT_NAMES]

def create_dataset(n_samples=256, n_repeats=10, seed=42, save_path='cafm_qmc_dataset.npz'):
    X_raw = generate_qmc_samples(n_samples, seed=seed)
    Y = np.zeros((n_samples, len(OUTPUT_NAMES)))
    Y_std = np.zeros_like(Y)

    is_power_of_two = (n_samples > 0) and ((n_samples & (n_samples - 1)) == 0)
    sampler_name = 'Sobol QMC' if is_power_of_two else 'Latin Hypercube'
    print(f"Generating {n_samples} samples with {n_repeats} repeats each using {sampler_name}...")

    for i in range(n_samples):
        x_row = dict(zip(PARAM_NAMES, X_raw[i]))
        runs_out = []
        for rep in range(n_repeats):
            runs_out.append(single_run(x_row, seed + i * n_repeats + rep))

        arr = np.array(runs_out, dtype=float)
        Y[i] = np.nanmean(arr, axis=0)
        Y_std[i] = np.nanstd(arr, axis=0)

        if i % 20 == 0 or i == n_samples - 1:
            print(f"  {i+1}/{n_samples} complete")

    lowers = np.array([BOUNDS[k][0] for k in PARAM_NAMES])
    uppers = np.array([BOUNDS[k][1] for k in PARAM_NAMES])
    np.savez(save_path,
             X=X_raw, Y=Y, Y_std=Y_std,
             param_names=np.array(PARAM_NAMES),
             output_names=np.array(OUTPUT_NAMES),
             param_bounds=np.vstack([lowers, uppers]))
    print(f"Dataset saved to {save_path}")
    return X_raw, Y, Y_std


def parse_args():
    parser = argparse.ArgumentParser(description='Generate CAFM dataset with output repeat variance.')
    parser.add_argument('--n-samples', type=int, default=256, help='Number of complete input samples to generate')
    parser.add_argument('--n-repeats', type=int, default=10, help='Repetitions per sample to estimate output variance')
    parser.add_argument('--seed', type=int, default=42, help='Random seed for sample generation')
    parser.add_argument('--save-path', type=str, default='cafm_qmc_new_dataset_256x10.npz', help='Output dataset file path')
    return parser.parse_args()


if __name__ == '__main__':
    args = parse_args()
    create_dataset(
        n_samples=args.n_samples,
        n_repeats=args.n_repeats,
        seed=args.seed,
        save_path=args.save_path,
    )












































# #######################################################################################################

# #  freeze code

# #######################################################################################################


# """
# Sweep dataset generator using 1‑D Latin Hypercube Sampling for density.

# Density is varied via LHS while all other parameters are frozen at a random point.
# At each density step, N_REPEATS simulations are run to estimate per‑point noise (Y_std).

# Saves:
#     X           : (N_SWEEP, 6)   input matrix
#     Y           : (N_SWEEP, 4)   mean outputs over repeats
#     Y_std       : (N_SWEEP, 4)   std over repeats (per‑point noise)
#     param_names, output_names, param_bounds (metadata)
# """

# import numpy as np
# from scipy.stats import qmc
# from utils.config import SimConfig
# from run_single import run_simulation

# # ─── Configuration ──────────────────────────────────────────────
# SWEEP_PARAM   = "density"          # which input to sweep
# N_SWEEP       = 100                # number of unique density values
# N_REPEATS     = 10                  # repetitions per density value
# BASE_SEED     = 42                 # base random seed (incremented per row/rep)
# SAVE_PATH     = "cafm_sweep_lhs_100x10.npz"

# # Parameter names and bounds (must match SimConfig)
# PARAM_NAMES = ["v0_mean", "tau", "A", "R_safety", "density", "flow_ratio"]
# PARAM_BOUNDS = {
#     "v0_mean"   : (0.80, 1.60),
#     "tau"       : (0.30, 0.80),
#     "A"         : (10.0, 40.0),
#     "R_safety"  : (0.80, 1.60),
#     "density"   : (0.10, 1.0),
#     "flow_ratio": (0.00, 0.50),
# }
# OUTPUT_NAMES = ["mean_crossing_time", "flow_rate", "order_param_mean", "mean_speed"]
# MEASURE_AREA = 30.0   # 10m × 3m corridor

# # Freeze mode: "random" or "mean"
# FREEZE_MODE  = "random"


# # ─── Helper: density → pedestrian counts ──────────────────────
# def density_to_counts(density, flow_ratio):
#     N_total = int(np.clip(round(density * MEASURE_AREA), 4, 60))
#     n_minor = int(round(flow_ratio * N_total))
#     n_major = N_total - n_minor
#     if n_minor == 0 and flow_ratio > 0:
#         n_minor = 2
#         n_major = max(2, N_total - 2)
#     if n_major == 0:
#         n_major = 2
#         n_minor = max(2, N_total - 2)
#     return n_major, n_minor


# # ─── Create sweep design using 1‑D Latin Hypercube Sampling ───
# def generate_sweep(freeze_mode="random"):
#     """
#     Returns (X_sweep, freeze_point). X_sweep shape = (N_SWEEP, 6).
#     Density values are generated via LHS (d=1) and then scaled to [lo, hi].
#     All other parameters are set to the freeze point.
#     """
#     rng = np.random.default_rng(42)

#     # ---- 1. Freeze point ----
#     if freeze_mode == "random":
#         freeze_point = np.array([
#             rng.uniform(*PARAM_BOUNDS[p]) for p in PARAM_NAMES
#         ])
#     elif freeze_mode == "mean":
#         freeze_point = np.array([
#             (PARAM_BOUNDS[p][0] + PARAM_BOUNDS[p][1]) / 2
#             for p in PARAM_NAMES
#         ])
#     else:
#         raise ValueError("freeze_mode must be 'random' or 'mean'")

#     # ---- 2. LHS for the sweep parameter (1 dimension) ----
#     sweep_idx = PARAM_NAMES.index(SWEEP_PARAM)
#     lo, hi = PARAM_BOUNDS[SWEEP_PARAM]
    
#     # 1‑D Latin Hypercube
#     sampler = qmc.LatinHypercube(d=1, strength=1, seed=BASE_SEED)
#     unit = sampler.random(N_SWEEP)          # shape (N_SWEEP, 1), values in [0,1)
#     sweep_vals = qmc.scale(unit, lo, hi).flatten()  # scale to [lo, hi]

#     # ---- 3. Build sweep matrix ----
#     X_sweep = np.tile(freeze_point, (N_SWEEP, 1))
#     X_sweep[:, sweep_idx] = sweep_vals

#     print("Freeze point (random):")
#     for i, name in enumerate(PARAM_NAMES):
#         marker = " ← sweep" if i == sweep_idx else ""
#         print(f"  {name:12s}: {freeze_point[i]:.4f}{marker}")
#     print(f"Sweep over {SWEEP_PARAM} with {N_SWEEP} LHS points in [{lo:.2f}, {hi:.2f}]\n")

#     return X_sweep, freeze_point


# # ─── Run the sweep ─────────────────────────────────────────────
# def run_sweep(X_sweep):
#     """For each row in X_sweep, run N_REPEATS simulations and collect mean/std."""
#     n = len(X_sweep)
#     Y = np.zeros((n, len(OUTPUT_NAMES)))
#     Y_std = np.zeros_like(Y)
#     failed = 0

#     for i in range(n):
#         row = dict(zip(PARAM_NAMES, X_sweep[i]))
#         n_major, n_minor = density_to_counts(row["density"], row["flow_ratio"])

#         runs_out = []
#         for rep in range(N_REPEATS):
#             seed = BASE_SEED + i * N_REPEATS + rep
#             cfg = SimConfig(
#                 n_major=n_major,
#                 n_minor=n_minor,
#                 v0_mean=row["v0_mean"],
#                 tau=row["tau"],
#                 A=row["A"],
#                 R_safety=row["R_safety"],
#                 R_danger=row["R_safety"] * 0.5,
#                 seed=seed,
#                 avoidance_enabled=True,
#             )
#             try:
#                 res = run_simulation(cfg)
#                 runs_out.append([res[name] for name in OUTPUT_NAMES])
#             except Exception as e:
#                 failed += 1
#                 print(f"  [WARN] sample {i} rep {rep} failed: {e}")
#                 runs_out.append([np.nan] * len(OUTPUT_NAMES))

#         arr = np.array(runs_out)
#         Y[i] = np.nanmean(arr, axis=0)
#         Y_std[i] = np.nanstd(arr, axis=0)

#         if i % 5 == 0 or i == n - 1:
#             print(f"  {i+1:>4}/{n} done  (failed so far: {failed})", flush=True)

#     print(f"\nTotal failed runs: {failed}")
#     return Y, Y_std


# # ─── Save dataset ──────────────────────────────────────────────
# def save_dataset(X, Y, Y_std, path):
#     lowers = np.array([PARAM_BOUNDS[k][0] for k in PARAM_NAMES])
#     uppers = np.array([PARAM_BOUNDS[k][1] for k in PARAM_NAMES])

#     np.savez(
#         path,
#         X=X,
#         Y=Y,
#         Y_std=Y_std,
#         param_names=np.array(PARAM_NAMES),
#         output_names=np.array(OUTPUT_NAMES),
#         param_bounds=np.vstack([lowers, uppers]),
#     )
#     print(f"Dataset saved to {path}")


# # ─── Main ──────────────────────────────────────────────────────
# if __name__ == "__main__":
#     print("=" * 60)
#     print("Generating sweep dataset with 1‑D Latin Hypercube Sampling")
#     print(f"  Sweep parameter : {SWEEP_PARAM}")
#     print(f"  LHS points      : {N_SWEEP}")
#     print(f"  Repeats per pt  : {N_REPEATS}")
#     print(f"  Total runs      : {N_SWEEP * N_REPEATS}")
#     print("=" * 60)

#     X_sweep, freeze_pt = generate_sweep(freeze_mode=FREEZE_MODE)
#     Y, Y_std = run_sweep(X_sweep)

#     # Quick stats
#     print("\nOutput statistics (means across sweep):")
#     for j, name in enumerate(OUTPUT_NAMES):
#         col = Y[:, j]
#         print(f"  {name:<25} min={np.nanmin(col):.4f}  "
#               f"mean={np.nanmean(col):.4f}  max={np.nanmax(col):.4f}")

#     save_dataset(X_sweep, Y, Y_std, SAVE_PATH)