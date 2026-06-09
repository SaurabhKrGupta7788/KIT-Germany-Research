import numpy as np
import pandas as pd
import time
import os
import sys

# Import your CAFM simulator (Make sure the name matches your v5 simulator file)
from cafm_sim_v3 import SimParams, run_simulation, CORRIDOR_WIDTH

# ==========================================
# CONFIGURATION
# ==========================================
CSV_PATH = "active_learning_targets.csv"
OLD_NPZ_PATH = r"D:\KIT\cafm_lhs_1000.npz"           # Your current dataset
NEW_NPZ_PATH = r"D:\KIT\cafm_lhs_3000_active.npz"    # The new super-dataset
N_REPEATS = 3
BASE_SIM_SEED = 8888  # New seed so we don't repeat the LHS noise

PARAM_NAMES = ["v0_mean", "tau", "A", "R_safety", "density", "flow_ratio"]
OUTPUT_NAMES = ["mean_crossing_time", "flow_rate", "order_param_mean", "mean_speed"]
MEASURE_AREA = 10.0 * CORRIDOR_WIDTH

def density_to_counts(density, flow_ratio):
    N_total  = int(np.clip(round(density * MEASURE_AREA), 4, 60))
    n_minor  = int(round(flow_ratio * N_total))
    n_major  = N_total - n_minor
    if n_minor == 0 and flow_ratio > 0:
        n_minor = 2; n_major = max(2, N_total - 2)
    if n_major == 0:
        n_major = 2; n_minor = max(2, N_total - 2)
    return n_major, n_minor

def generate_and_merge_active_data():
    print("="*70)
    print("🔄 ACTIVE LEARNING: SIMULATING CHAOTIC ZONES & MERGING 🔄")
    print("="*70)

    # 1. Load the CSV containing the blind spots
    try:
        df = pd.read_csv(CSV_PATH)
        X_new_raw = df[PARAM_NAMES].values
        n_new_samples = len(X_new_raw)
        print(f"Loaded {n_new_samples} targeted points from {CSV_PATH}")
    except FileNotFoundError:
        print(f"Error: {CSV_PATH} not found. Run the Radar first!")
        return

    # Arrays to hold the new simulation outputs
    Y_new = np.zeros((n_new_samples, len(OUTPUT_NAMES)))
    Y_std_new = np.zeros((n_new_samples, len(OUTPUT_NAMES)))

    print(f"\nRunning CAFM Simulator ({N_REPEATS} repeats per point)...")
    t_start = time.time()
    failed = 0

    # 2. Run the CAFM Simulator on the new points
    for i, x_row in enumerate(X_new_raw):
        v0_mean, tau, A, R_safety, density, flow_ratio = x_row
        n_major, n_minor = density_to_counts(density, flow_ratio)

        run_outputs = []
        for rep in range(N_REPEATS):
            p = SimParams(
                n_major   = n_major,
                n_minor   = n_minor,
                v0_mean   = float(v0_mean),
                tau       = float(tau),
                A         = float(A),
                R_safety  = float(R_safety),
                R_danger  = float(R_safety * 0.5),
                seed      = BASE_SIM_SEED + i * N_REPEATS + rep,
            )
            try:
                result = run_simulation(p)
                run_outputs.append([result[k] for k in OUTPUT_NAMES])
            except Exception as e:
                failed += 1
                run_outputs.append([np.nan] * len(OUTPUT_NAMES))

        # Calculate Mean and Std Dev for this chaotic point
        arr = np.array(run_outputs)
        Y_new[i] = np.nanmean(arr, axis=0)
        Y_std_new[i] = np.nanstd(arr, axis=0)

        # Progress tracker
        if i % 10 == 0 or i == n_new_samples - 1:
            elapsed = time.time() - t_start
            rate = (i + 1) / elapsed if elapsed > 0 else 1
            eta = (n_new_samples - i - 1) / rate
            print(f"  Progress: {i+1}/{n_new_samples} | Elapsed: {elapsed:.1f}s | ETA: {eta:.1f}s", end="\r")

    print(f"\n\nSimulation complete! Failed runs: {failed}")

    # 3. Load the Original LHS Dataset
    print("\nLoading original dataset and merging...")
    old_data = np.load(OLD_NPZ_PATH)
    
    X_old = old_data['X']
    Y_old = old_data['Y']
    Y_std_old = old_data['Y_std']
    
    # 4. Merge (Stack) the datasets together
    X_combined = np.vstack((X_old, X_new_raw))
    Y_combined = np.vstack((Y_old, Y_new))
    Y_std_combined = np.vstack((Y_std_old, Y_std_new))

    print(f"Original Dataset Size : {len(X_old)} points")
    print(f"New Targeted Points   : {len(X_new_raw)} points")
    print(f"Super-Dataset Size    : {len(X_combined)} points")

    # 5. Save the new Super-Dataset
    np.savez(
        NEW_NPZ_PATH,
        X = X_combined,
        Y = Y_combined,
        Y_std = Y_std_combined,
        param_names = old_data['param_names'],
        output_names = old_data['output_names'],
        param_bounds = old_data['param_bounds'],
    )
    
    print("\n" + "="*70)
    print(f"✅ SUCCESS! New augmented dataset saved to: {NEW_NPZ_PATH}")
    print("Update DATA_PATH in your master GP script to point to this new file!")
    print("="*70)

if __name__ == "__main__":
    generate_and_merge_active_data()