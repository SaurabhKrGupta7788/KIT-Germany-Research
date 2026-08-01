import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import RBF, ConstantKernel as C

def create_gp_gif(output_filename="gp_fitting.gif", frames=60, fps=2):
    print(f"Generating GP fitting animation: {output_filename}")
    
    # Ground truth function
    def f(x):
        return x * np.sin(x)
    
    X_plot = np.linspace(0, 10, 200)[:, np.newaxis]
    y_plot = f(X_plot)
    
    # Randomly select points for training
    rng = np.random.RandomState(42)
    X_full = rng.uniform(0, 10, size=(frames, 1))
    noise_std = 0.5
    y_full = f(X_full).ravel() + rng.normal(0, noise_std, size=frames)
    
    kernel = C(1.0, (1e-3, 1e3)) * RBF(10, (1e-2, 1e2))
    
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.set_xlim(0, 10)
    ax.set_ylim(-10, 10)
    ax.set_xlabel("Input Parameter")
    ax.set_ylabel("Target Metric (e.g., Crossing Time)")
    ax.set_title("Gaussian Process Fitting (Active Data Collection)")
    
    true_line, = ax.plot(X_plot, y_plot, 'k:', label='True Function')
    points, = ax.plot([], [], 'r.', markersize=10, label='Observations')
    mean_line, = ax.plot([], [], 'b-', label='GP Mean')
    fill = None
    
    ax.legend(loc='upper left')
    
    def update(frame):
        nonlocal fill
        if fill is not None:
            fill.remove()
            
        # Current data up to frame + 1
        n_points = frame + 1
        X_train = X_full[:n_points]
        y_train = y_full[:n_points]
        
        # Fit GP with noise level assumption
        gp = GaussianProcessRegressor(kernel=kernel, alpha=noise_std**2, n_restarts_optimizer=2)
        if n_points > 1:
            gp.fit(X_train, y_train)
        else:
            # Cannot properly fit with 1 point and hyperparameter tuning, use default kernel
            gp.fit(X_train, y_train)
            
        y_mean, y_std = gp.predict(X_plot, return_std=True)
        
        points.set_data(X_train, y_train)
        mean_line.set_data(X_plot, y_mean)
        
        # 95% confidence interval
        fill = ax.fill_between(X_plot.ravel(), y_mean - 1.96 * y_std, y_mean + 1.96 * y_std, 
                               alpha=0.3, color='blue')
        
        ax.set_title(f"Gaussian Process Fitting: {n_points} Observations")
        return mean_line, points

    anim = FuncAnimation(fig, update, frames=frames, interval=1000/fps, blit=False)
    anim.save(output_filename, writer='pillow', fps=fps, dpi=72)
    print(f"Saved {output_filename} successfully.")

if __name__ == '__main__':
    create_gp_gif()
