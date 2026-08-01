"""Helper to run many simulations in parallel."""

import multiprocessing as mp

def run_in_parallel(func, args_list, n_workers=4):
    with mp.Pool(processes=n_workers) as pool:
        results = pool.starmap(func, args_list)
    return results