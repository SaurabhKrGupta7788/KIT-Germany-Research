import numpy as np
import matplotlib.pyplot as plt
from gaussian_process import CAFM_Surrogate

def plot_uq_surface(surrogate, target_idx, param_x_idx, param_y_idx, resolution=50):
    target_name = surrogate.output_names[target_idx]
    p_name_x = surrogate.param_names[param_x_idx]
    p_name_y = surrogate.param_names[param_y_idx]
    
    print(f"\nGenerating UQ Surface for {target_name}")
    print(f"Sweeping {p_name_x} vs {p_name_y}...")

    # 1. Define baseline values for all 6 parameters (Mean values from bounds)
    # ["v0_mean", "tau", "A", "R_safety", "density", "flow_ratio"]
    baseline = np.array([1.21, 0.5, 20.0, 1.22, 0.5, 0.25])
    
    # 2. Create the 2D grid for the two parameters we want to sweep
    # We will pull the actual bounds from the scaler
    bounds_x = [np.min(surrogate.X_raw[:, param_x_idx]), np.max(surrogate.X_raw[:, param_x_idx])]
    bounds_y = [np.min(surrogate.X_raw[:, param_y_idx]), np.max(surrogate.X_raw[:, param_y_idx])]
    
    x_vals = np.linspace(bounds_x[0], bounds_x[1], resolution)
    y_vals = np.linspace(bounds_y[0], bounds_y[1], resolution)
    X_grid, Y_grid = np.meshgrid(x_vals, y_vals)
    
    # 3. Build the 2500x6 input matrix
    X_pred = np.tile(baseline, (resolution * resolution, 1))
    X_pred[:, param_x_idx] = X_grid.ravel()
    X_pred[:, param_y_idx] = Y_grid.ravel()
    
    # 4. Predict using the trained GP
    gp = surrogate.models[target_name]
    scaler_X = surrogate.scalers_X[target_name]
    scaler_y = surrogate.scalers_y[target_name]
    
    X_pred_scaled = scaler_X.transform(X_pred)
    mu_scaled, sigma_scaled = gp.predict(X_pred_scaled, return_std=True)
    
    # Inverse transform to get physical units
    mu = scaler_y.inverse_transform(mu_scaled.reshape(-1, 1)).ravel()
    sigma = sigma_scaled * scaler_y.scale_[0]
    
    # Reshape back to 2D grids
    Mu_grid = mu.reshape(resolution, resolution)
    Sigma_grid = sigma.reshape(resolution, resolution)
    
    # 5. Plotting
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
    
    # Plot Mean Prediction
    c1 = ax1.contourf(X_grid, Y_grid, Mu_grid, levels=30, cmap='viridis')
    fig.colorbar(c1, ax=ax1, label=f'Predicted {target_name}')
    ax1.set_title(rf'Surrogate Mean ($\mu$)')
    ax1.set_xlabel(p_name_x)
    ax1.set_ylabel(p_name_y)
    
    # Plot Uncertainty
    c2 = ax2.contourf(X_grid, Y_grid, Sigma_grid, levels=30, cmap='inferno')
    fig.colorbar(c2, ax=ax2, label=rf'Uncertainty ($\sigma$)')
    ax2.set_title(rf'Surrogate Uncertainty ($\sigma$)')
    ax2.set_xlabel(p_name_x)
    ax2.set_ylabel(p_name_y)
    
    plt.suptitle(f"UQ Analysis: {target_name} | {p_name_x} vs {p_name_y}")
    plt.tight_layout()
    plt.savefig(f"uq_surface_{p_name_x}_vs_{p_name_y}.png", dpi=300)
    print(f"Saved UQ Plot!")



from SALib.sample import saltelli
from SALib.analyze import sobol

def plot_1d_slice(surrogate, target_idx, sweep_idx, resolution=100):
    """Generates a 1D sensitivity plot with a 95% confidence interval band."""
    target_name = surrogate.output_names[target_idx]
    p_name = surrogate.param_names[sweep_idx]
    
    print(f"\nGenerating 1D Slice Plot for {target_name} sweeping {p_name}...")

    # 1. Physical baselines: ["v0_mean", "tau", "A", "R_safety", "density", "flow_ratio"]
    baseline = np.array([1.21, 0.5, 20.0, 1.22, 0.5, 0.25])
    
    # 2. Sweep the selected parameter
    x_min = np.min(surrogate.X_raw[:, sweep_idx])
    x_max = np.max(surrogate.X_raw[:, sweep_idx])
    x_vals = np.linspace(x_min, x_max, resolution)
    
    X_pred = np.tile(baseline, (resolution, 1))
    X_pred[:, sweep_idx] = x_vals
    
    # 3. Predict with GP
    gp = surrogate.models[target_name]
    scaler_X = surrogate.scalers_X[target_name]
    scaler_y = surrogate.scalers_y[target_name]
    
    X_pred_scaled = scaler_X.transform(X_pred)
    mu_scaled, sigma_scaled = gp.predict(X_pred_scaled, return_std=True)
    
    mu = scaler_y.inverse_transform(mu_scaled.reshape(-1, 1)).ravel()
    sigma = sigma_scaled * scaler_y.scale_[0]
    
    # 4. Plotting
    plt.figure(figsize=(10, 6))
    plt.plot(x_vals, mu, 'b-', lw=2, label=f'Mean Predicted {target_name}')
    
    # Shaded 95% Confidence Interval
    plt.fill_between(x_vals, mu - 2*sigma, mu + 2*sigma, color='royalblue', alpha=0.3, label=r'$\pm 2\sigma$ Confidence')
    
    plt.title(f"1D Sensitivity & Uncertainty: {target_name} vs {p_name}")
    plt.xlabel(p_name)
    plt.ylabel(target_name)
    plt.grid(True, linestyle=':', alpha=0.7)
    plt.legend()
    
    plt.tight_layout()
    filename = f"uq_1d_slice_{target_name}_vs_{p_name}.png"
    plt.savefig(filename, dpi=300)
    print(f"Saved 1D Slice Plot: {filename}")

def calculate_sobol_indices(surrogate, target_idx, n_samples=2048):
    """Calculates Global Sensitivity using the GP as a rapid emulator."""
    target_name = surrogate.output_names[target_idx]
    print(f"\nRunning Global Sensitivity Analysis (Sobol) for {target_name}...")
    
    # 1. Define the SALib problem dictionary dynamically from the data bounds
    bounds = [[np.min(surrogate.X_raw[:, i]), np.max(surrogate.X_raw[:, i])] for i in range(6)]
    
    problem = {
        'num_vars': 6,
        'names': list(surrogate.param_names),
        'bounds': bounds
    }
    
    # 2. Generate Saltelli samples (this creates a massive parameter matrix)
    X_saltelli = saltelli.sample(problem, n_samples)
    print(f"Generated {X_saltelli.shape[0]} parameter combinations for evaluation.")
    
    # 3. Predict using the ultra-fast GP Surrogate (Instead of the slow simulation)
    gp = surrogate.models[target_name]
    scaler_X = surrogate.scalers_X[target_name]
    scaler_y = surrogate.scalers_y[target_name]
    
    X_scaled = scaler_X.transform(X_saltelli)
    y_pred_scaled = gp.predict(X_scaled)
    y_pred = scaler_y.inverse_transform(y_pred_scaled.reshape(-1, 1)).ravel()
    
    # 4. Analyze the variance
    Si = sobol.analyze(problem, y_pred, print_to_console=False)
    
    print("\n--- Sobol Global Sensitivity Indices ---")
    print(f"{'Parameter':<12} | {'S1 (Direct Impact)':<20} | {'ST (Total Impact)':<20}")
    print("-" * 58)
    
    for i, name in enumerate(problem['names']):
        s1 = Si['S1'][i]
        st = Si['ST'][i]
        print(f"{name:<12} | {s1:>6.2%}                | {st:>6.2%}")
        
    return Si


if __name__ == "__main__":
    import warnings
    # Suppress the deprecation and convergence warnings for clean output
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    warnings.filterwarnings("ignore", module="sklearn.gaussian_process.kernels")

    surrogate = CAFM_Surrogate()
    surrogate.load_data("cafm_lhs_300.npz")
    
    # Loop through all 4 output targets in the dataset
    for target_idx in range(4):
        target_name = surrogate.output_names[target_idx]
        print(f"\n{'#'*60}")
        print(f"MASTER PIPELINE: Processing Target -> {target_name}")
        print(f"{'#'*60}")
        
        # 1. Train the GP for this specific output
        surrogate.train_target(target_idx)
        
        # 2. Run Global Sensitivity Analysis (Sobol)
        calculate_sobol_indices(surrogate, target_idx)
        
        # 3. Generate 1D Slice Plots for EVERY input parameter (0 through 5)
        print(f"\nGenerating 1D UQ Slices for all parameters...")
        for param_idx in range(6):
            plot_1d_slice(surrogate, target_idx=target_idx, sweep_idx=param_idx, resolution=100)
            
        # 4. Generate the primary 2D Heatmap (Density vs Flow Ratio)
        plot_uq_surface(surrogate, target_idx=target_idx, param_x_idx=4, param_y_idx=5)
        
    print("\n" + "="*60)
    print("ALL TARGETS PROCESSED SUCCESSFULLY. Check your directory for the plots!")
    print("="*60)