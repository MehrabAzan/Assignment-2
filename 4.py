import time

try:
    import numpy as np
except ImportError:
    raise SystemExit("numpy is required: pip install numpy")

from numba import njit

@njit(cache=True)
def apply_random_updates(matrixM, sizeN, countM, seed):
    """
    Apply countM random triples [i, j, x] to the n-by-n matrix M.
    Input: matrixM, sizeN, countM, seed.
    Output: last LCG state (matrixM updated in place).
    Locals: state, k, i, j, x.
    """
    state = seed
    for k in range(countM):
        state = (state * 1103515245 + 12345) & 0x7FFFFFFF
        i = state % sizeN
        state = (state * 1103515245 + 12345) & 0x7FFFFFFF
        j = state % sizeN
        state = (state * 1103515245 + 12345) & 0x7FFFFFFF
        x = (state % 1000) * 0.001 + 0.001
        matrixM[i, j] = matrixM[i, j] + x
    return state

def allocate_matrix(sizeN):
    """
    Allocate an n-by-n float32 matrix of zeros.
    Input: sizeN.
    Output: matrix or None on MemoryError.
    Locals: matrixM.
    """
    try:
        matrixM = np.zeros((sizeN, sizeN), dtype=np.float32)
    except MemoryError:
        return None
    return matrixM

def time_one_run(matrixM, sizeN, countM, seed):
    """
    Time one apply_random_updates call. Setup is not timed.
    Input: matrixM, sizeN, countM, seed.
    Output: elapsed seconds.
    Locals: startTime, elapsed.
    """
    startTime = time.perf_counter()
    apply_random_updates(matrixM, sizeN, countM, seed)
    elapsed = time.perf_counter() - startTime
    return elapsed

def warm_up_kernel():
    """
    Compile the Numba kernel on a tiny instance.
    Input: none. Output: none.
    Locals: tinyM.
    """
    tinyM = np.zeros((8, 8), dtype=np.float32)
    apply_random_updates(tinyM, 8, 1000, 1)

def run_instance(sizeN, countM, seed, repeatCount):
    """
    Allocate, time repeatCount runs, return the minimum elapsed time.
    Input: sizeN, countM, seed, repeatCount.
    Output: (minSeconds, allSeconds) or None if allocation failed.
    Locals: matrixM, allSeconds, r, elapsed, gibEstimate.
    """
    gibEstimate = (sizeN * sizeN * 4) / (1024 ** 3)
    print(
        f"n = {sizeN}  m = {countM}  "
        f"(~{gibEstimate:.4f} GiB for M)  repeats = {repeatCount}"
    )
    matrixM = allocate_matrix(sizeN)
    if matrixM is None:
        print("  skipped: not enough memory\n")
        return None
    allSeconds = []
    for r in range(repeatCount):
        matrixM.fill(0.0)
        elapsed = time_one_run(matrixM, sizeN, countM, seed + r)
        allSeconds.append(elapsed)
        print(f"  run {r + 1}: {elapsed:.6f} s")
    minSeconds = min(allSeconds)
    print(f"  min: {minSeconds:.6f} s\n")
    return minSeconds, allSeconds

def print_summary_table(results):
    """
    Print the timing table for all (n, m) instances.
    Input: results list of (sizeN, countM, minSeconds).
    Output: none.
    Locals: sizeN, countM, minSeconds, perUpdateNs.
    """
    print("=" * 72)
    print(
        f"{'n':>8}  {'m':>14}  {'min time (s)':>14}  "
        f"{'ns per update':>14}"
    )
    print("=" * 72)
    for sizeN, countM, minSeconds in results:
        perUpdateNs = (minSeconds / countM) * 1e9 if countM else 0.0
        print(
            f"{sizeN:>8}  {countM:>14}  {minSeconds:>14.6f}  "
            f"{perUpdateNs:>14.3f}"
        )
    print("=" * 72)

def main():
    """
    Time the p.126 random matrix update algorithm for the assignment grid.
    Input: none.
    Output: per-instance timings and a summary table.
    Locals: sizeList, mList, repeatCount, results, sizeN, countM, timed.
    """
    sizeList = [16, 64, 256, 1024, 4096, 16384]
    mList = [1677721600, 13421772800]
    repeatCount = 1
    print(
        "Leiss p.126 algorithm: while more input, "
        "read [i,j,x], M[i,j] += x\n"
        "float32 matrix, random triples via LCG, init not timed\n"
    )
    warm_up_kernel()
    results = []
    for countM in mList:
        for sizeN in sizeList:
            timed = run_instance(sizeN, countM, 42, repeatCount)
            if timed is not None:
                results.append((sizeN, countM, timed[0]))
    if results:
        print_summary_table(results)

if __name__ == "__main__":
    main()
