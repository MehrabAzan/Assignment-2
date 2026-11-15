import array
import gc
import random
import statistics
import sys
import time
import tracemalloc

def matrix_size(val):
    """
    Return the flattened matrix length M for key val.
    Input: val.
    Output: M in {2^20, 2^19+2^18, 2^3+2^2}.
    Locals: rem.
    """
    rem = val % 3
    if rem == 0:
        return 1 << 20
    if rem == 1:
        return (1 << 19) + (1 << 18)
    return (1 << 3) + (1 << 2)

def build_matrix(val):
    """
    Allocate a flattened float matrix of length M(val) and touch entries.
    Input: val.
    Output: array.array('f') of length M.
    Locals: sizeM, data, step, i.
    """
    sizeM = matrix_size(val)
    data = array.array("f", [0.0]) * sizeM
    step = max(1, sizeM // 64)
    for i in range(0, sizeM, step):
        data[i] = float(val + i)
    data[sizeM - 1] = float(val)
    return data

class AvlNode:
    def __init__(self, val):
        self.val = val
        self.matrix = build_matrix(val)
        self.left = None
        self.right = None
        self.height = 1

def height_of(node):
    """
    Return AVL height of node or 0 if node is None.
    Input: node.
    Output: height.
    Locals: none.
    """
    if node is None:
        return 0
    return node.height

def balance_of(node):
    """
    Return left height minus right height.
    Input: node.
    Output: balance factor.
    Locals: none.
    """
    if node is None:
        return 0
    return height_of(node.left) - height_of(node.right)

def refresh_height(node):
    """
    Recompute height from children.
    Input: node.
    Output: none.
    Locals: none.
    """
    node.height = 1 + max(height_of(node.left), height_of(node.right))

def rotate_right(y):
    """
    Right rotation about y.
    Input: y.
    Output: new subtree root.
    Locals: x, t2.
    """
    x = y.left
    t2 = x.right
    x.right = y
    y.left = t2
    refresh_height(y)
    refresh_height(x)
    return x

def rotate_left(x):
    """
    Left rotation about x.
    Input: x.
    Output: new subtree root.
    Locals: y, t2.
    """
    y = x.right
    t2 = y.left
    y.left = x
    x.right = t2
    refresh_height(x)
    refresh_height(y)
    return y

def rebalance(node):
    """
    Restore AVL balance at node after a local update.
    Input: node.
    Output: balanced subtree root.
    Locals: balance.
    """
    refresh_height(node)
    balance = balance_of(node)
    if balance > 1:
        if balance_of(node.left) < 0:
            node.left = rotate_left(node.left)
        return rotate_right(node)
    if balance < -1:
        if balance_of(node.right) > 0:
            node.right = rotate_right(node.right)
        return rotate_left(node)
    return node

def insert_node(root, val):
    """
    Insert val with its fat matrix into the AVL tree.
    Input: root, val.
    Output: (newRoot, insertedFlag).
    Locals: inserted.
    """
    if root is None:
        return AvlNode(val), True
    if val < root.val:
        root.left, inserted = insert_node(root.left, val)
    elif val > root.val:
        root.right, inserted = insert_node(root.right, val)
    else:
        return root, False
    return rebalance(root), inserted

def min_node(node):
    """
    Return the leftmost node in the subtree.
    Input: node.
    Output: minimum node.
    Locals: current.
    """
    current = node
    while current.left is not None:
        current = current.left
    return current

def delete_node(root, val):
    """
    Delete val from the AVL tree and drop its matrix.
    Input: root, val.
    Output: (newRoot, deletedFlag).
    Locals: deleted, succ.
    """
    if root is None:
        return None, False
    if val < root.val:
        root.left, deleted = delete_node(root.left, val)
    elif val > root.val:
        root.right, deleted = delete_node(root.right, val)
    else:
        deleted = True
        if root.left is None:
            return root.right, True
        if root.right is None:
            return root.left, True
        succ = min_node(root.right)
        root.val = succ.val
        root.matrix = succ.matrix
        root.right, _ = delete_node(root.right, succ.val)
    if not deleted:
        return root, False
    return rebalance(root), True

def choose_action(treeSize, maxSize):
    """
    Choose insert or delete while keeping treeSize in [0, maxSize].
    Input: treeSize, maxSize.
    Output: 'insert' or 'delete'.
    Locals: none.
    """
    if treeSize <= 0:
        return "insert"
    if treeSize >= maxSize:
        return "delete"
    if random.random() < 0.5:
        return "insert"
    return "delete"

def record_gc_snapshot(label, samples):
    """
    Append a GC and allocator snapshot to samples.
    Input: label, samples.
    Output: none.
    Locals: counts, stats, gen0, gen1, gen2, current, peak.
    """
    counts = gc.get_count()
    stats = gc.get_stats()
    gen0 = stats[0]["collections"] if len(stats) > 0 else 0
    gen1 = stats[1]["collections"] if len(stats) > 1 else 0
    gen2 = stats[2]["collections"] if len(stats) > 2 else 0
    current, peak = tracemalloc.get_traced_memory()
    samples.append(
        {
            "label": label,
            "count0": counts[0],
            "count1": counts[1],
            "count2": counts[2],
            "coll0": gen0,
            "coll1": gen1,
            "coll2": gen2,
            "currentMb": current / (1024 * 1024),
            "peakMb": peak / (1024 * 1024),
        }
    )

def summarize_times(times):
    """
    Compute timing summary statistics in microseconds.
    Input: times in seconds.
    Output: dict of count, mean, median, p95, p99, max.
    Locals: micros, sortedTimes, n, p95, p99.
    """
    if not times:
        return {
            "count": 0,
            "mean": 0.0,
            "median": 0.0,
            "p95": 0.0,
            "p99": 0.0,
            "max": 0.0,
        }
    micros = [t * 1e6 for t in times]
    sortedTimes = sorted(micros)
    n = len(sortedTimes)
    p95 = sortedTimes[min(n - 1, int(0.95 * (n - 1)))]
    p99 = sortedTimes[min(n - 1, int(0.99 * (n - 1)))]
    return {
        "count": n,
        "mean": statistics.fmean(micros),
        "median": statistics.median(micros),
        "p95": p95,
        "p99": p99,
        "max": sortedTimes[-1],
    }

def window_means(times, windowSize):
    """
    Mean microseconds for successive windows of times.
    Input: times in seconds, windowSize.
    Output: list of (startIndex, meanUs).
    Locals: out, i, chunk, meanUs.
    """
    out = []
    for i in range(0, len(times), windowSize):
        chunk = times[i : i + windowSize]
        if not chunk:
            continue
        meanUs = statistics.fmean(chunk) * 1e6
        out.append((i, meanUs))
    return out

def run_experiment(opCount, maxNodes, valueMax, seed):
    """
    Run opCount insert or delete ops on a fat-node AVL tree.
    Input: opCount, maxNodes, valueMax, seed.
    Output: result dict with timings and GC snapshots.
    Locals: root, present, insertTimes, deleteTimes, allOpTimes, gcSamples,
            gc_callback, collectionsSeen, opIndex, action, val,
            t0, t1, inserted, deleted, maxObserved, startWall, endWall,
            elapsed, forcedBefore, forcedAfter.
    """
    random.seed(seed)
    gc.enable()
    forcedBefore = gc.collect()
    tracemalloc.start()
    collectionsSeen = []

    def gc_callback(phase, info):
        if phase == "start":
            collectionsSeen.append(
                {
                    "generation": info.get("generation", -1),
                    "opIndex": len(allOpTimes),
                }
            )

    gc.callbacks.append(gc_callback)
    root = None
    present = set()
    insertTimes = []
    deleteTimes = []
    allOpTimes = []
    gcSamples = []
    maxObserved = 0
    record_gc_snapshot("start", gcSamples)
    startWall = time.perf_counter()
    for opIndex in range(opCount):
        action = choose_action(len(present), maxNodes)
        if action == "insert":
            if len(present) >= valueMax + 1:
                action = "delete"
            else:
                val = random.randint(0, valueMax)
                while val in present:
                    val = random.randint(0, valueMax)
                t0 = time.perf_counter()
                root, inserted = insert_node(root, val)
                t1 = time.perf_counter()
                if inserted:
                    present.add(val)
                    elapsed = t1 - t0
                    insertTimes.append(elapsed)
                    allOpTimes.append(elapsed)
        if action == "delete":
            if not present:
                continue
            val = random.choice(tuple(present))
            t0 = time.perf_counter()
            root, deleted = delete_node(root, val)
            t1 = time.perf_counter()
            if deleted:
                present.discard(val)
                elapsed = t1 - t0
                deleteTimes.append(elapsed)
                allOpTimes.append(elapsed)
        if len(present) > maxObserved:
            maxObserved = len(present)
        if (opIndex + 1) % (opCount // 10) == 0:
            record_gc_snapshot(f"after_{opIndex + 1}", gcSamples)
            print(
                f"progress {opIndex + 1}/{opCount}  "
                f"|tree|={len(present)}  "
                f"inserts={len(insertTimes)}  deletes={len(deleteTimes)}  "
                f"gc_callbacks={len(collectionsSeen)}"
            )
            sys.stdout.flush()
    endWall = time.perf_counter()
    record_gc_snapshot("end", gcSamples)
    forcedAfter = gc.collect()
    if gc_callback in gc.callbacks:
        gc.callbacks.remove(gc_callback)
    peakMb = tracemalloc.get_traced_memory()[1] / (1024 * 1024)
    tracemalloc.stop()
    return {
        "wallSeconds": endWall - startWall,
        "maxObserved": maxObserved,
        "finalSize": len(present),
        "insertSummary": summarize_times(insertTimes),
        "deleteSummary": summarize_times(deleteTimes),
        "allSummary": summarize_times(allOpTimes),
        "insertWindows": window_means(insertTimes, 10000),
        "allWindows": window_means(allOpTimes, 20000),
        "gcSamples": gcSamples,
        "collectionsSeen": collectionsSeen,
        "peakMb": peakMb,
        "insertCount": len(insertTimes),
        "deleteCount": len(deleteTimes),
        "forcedBefore": forcedBefore,
        "forcedAfter": forcedAfter,
    }

def print_summary(result):
    """
    Print timing and GC results for the experiment.
    Input: result.
    Output: none.
    Locals: ins, dele, allOps, sample, event, startIndex, meanUs.
    """
    ins = result["insertSummary"]
    dele = result["deleteSummary"]
    allOps = result["allSummary"]
    print()
    print("=" * 72)
    print("Garbage collection AVL experiment")
    print("=" * 72)
    print(f"wall clock (s):           {result['wallSeconds']:.3f}")
    print(f"successful inserts:       {result['insertCount']}")
    print(f"successful deletes:       {result['deleteCount']}")
    print(f"max |tree|:               {result['maxObserved']}")
    print(f"final |tree|:             {result['finalSize']}")
    print(f"tracemalloc peak (MiB):   {result['peakMb']:.2f}")
    print()
    print(
        f"{'op':<10} {'n':>8} {'mean us':>12} {'median us':>12} "
        f"{'p95 us':>12} {'p99 us':>12} {'max us':>12}"
    )
    for name, summary in (
        ("insert", ins),
        ("delete", dele),
        ("all", allOps),
    ):
        print(
            f"{name:<10} {summary['count']:>8} {summary['mean']:>12.3f} "
            f"{summary['median']:>12.3f} {summary['p95']:>12.3f} "
            f"{summary['p99']:>12.3f} {summary['max']:>12.3f}"
        )
    print()
    print("GC snapshots (collections are cumulative since process start)")
    for sample in result["gcSamples"]:
        print(
            f"  {sample['label']:<16} "
            f"coll=({sample['coll0']},{sample['coll1']},{sample['coll2']})  "
            f"count=({sample['count0']},{sample['count1']},{sample['count2']})  "
            f"cur={sample['currentMb']:.1f} MiB  peak={sample['peakMb']:.1f} MiB"
        )
    print(f"gc.callbacks events: {len(result['collectionsSeen'])}")
    if result["collectionsSeen"]:
        for event in result["collectionsSeen"][:20]:
            print(
                f"  gen={event['generation']} near op index {event['opIndex']}"
            )
        if len(result["collectionsSeen"]) > 20:
            print(f"  ... {len(result['collectionsSeen']) - 20} more")
    print(
        f"forced gc.collect() reclaimed before={result['forcedBefore']} "
        f"after={result['forcedAfter']} objects"
    )
    print()
    print("mean us per 20000 successful ops (mixed insert/delete)")
    for startIndex, meanUs in result["allWindows"]:
        print(f"  ops {startIndex:>6}..{startIndex + 19999:>6}: {meanUs:10.3f} us")
    print("mean us per 10000 inserts")
    for startIndex, meanUs in result["insertWindows"]:
        print(f"  inserts {startIndex:>6}..{startIndex + 9999:>6}: {meanUs:10.3f} us")
    print("=" * 72)

def main():
    """
    Drive the fat-node AVL GC fragmentation experiment.
    Input: none.
    Output: printed timing and GC report.
    Locals: opCount, maxNodes, valueMax, seed, result.
    """
    opCount = 200000
    maxNodes = 50
    valueMax = 299
    seed = 3320
    print(
        "AVL insert/delete with per-node matrix of size M(val).\n"
        "M = 2^20 if val%3==0, 2^19+2^18 if val%3==1, 2^3+2^2 if val%3==2.\n"
        f"ops={opCount}, values in 0..{valueMax}, |tree| <= {maxNodes}, "
        f"seed={seed}\n"
    )
    result = run_experiment(opCount, maxNodes, valueMax, seed)
    print_summary(result)
    return result

if __name__ == "__main__":
    main()