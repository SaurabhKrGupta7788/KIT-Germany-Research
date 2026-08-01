from lhs_generator import run_qmc_dataset
# from lhs_generator import run_lhs_dataset, run_qmc_dataset

# run_lhs_dataset(n_samples=1000, n_repeats=1, save_path="cafm_lhs_1repetation_1000.npz")

print("Smoke test: 256 samples × 3 repeats (QMC optimal)")
run_qmc_dataset(
        n_samples    = 256,     # CHANGED: 16 instead of 10
        n_repeats    = 3,
        save_path    = "cafm_qmc_256.npz",
        verbose      = True,
    )

