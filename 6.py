import ctypes
import gc
import mmap
import os
import random
import statistics
import sys
import tempfile
import time
from ctypes import wintypes

class SystemInfo(ctypes.Structure):
    _fields_ = [
        ("wProcessorArchitecture", wintypes.WORD),
        ("wReserved", wintypes.WORD),
        ("dwPageSize", wintypes.DWORD),
        ("lpMinimumApplicationAddress", ctypes.c_void_p),
        ("lpMaximumApplicationAddress", ctypes.c_void_p),
        ("dwActiveProcessorMask", ctypes.POINTER(ctypes.c_ulong)),
        ("dwNumberOfProcessors", wintypes.DWORD),
        ("dwProcessorType", wintypes.DWORD),
        ("dwAllocationGranularity", wintypes.DWORD),
        ("wProcessorLevel", wintypes.WORD),
        ("wProcessorRevision", wintypes.WORD),
    ]

class MemoryStatusEx(ctypes.Structure):
    _fields_ = [
        ("dwLength", wintypes.DWORD),
        ("dwMemoryLoad", wintypes.DWORD),
        ("ullTotalPhys", ctypes.c_uint64),
        ("ullAvailPhys", ctypes.c_uint64),
        ("ullTotalPageFile", ctypes.c_uint64),
        ("ullAvailPageFile", ctypes.c_uint64),
        ("ullTotalVirtual", ctypes.c_uint64),
        ("ullAvailVirtual", ctypes.c_uint64),
        ("ullAvailExtendedVirtual", ctypes.c_uint64),
    ]

def get_page_size():
    """
    Return the OS memory page size in bytes via GetSystemInfo.
    Input: none.
    Output: page size (bytes).
    Locals: info.
    """
    info = SystemInfo()
    ctypes.windll.kernel32.GetSystemInfo(ctypes.byref(info))
    if info.dwPageSize == 0:
        return 4096
    return int(info.dwPageSize)

def get_memory_status():
    """
    Query physical and pagefile memory with GlobalMemoryStatusEx.
    Input: none.
    Output: dict with totalPhys, availPhys, totalPage, availPage, loadPct.
    Locals: status.
    """
    status = MemoryStatusEx()
    status.dwLength = ctypes.sizeof(MemoryStatusEx)
    ok = ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status))
    if not ok:
        return {
            "totalPhys": 0,
            "availPhys": 0,
            "totalPage": 0,
            "availPage": 0,
            "loadPct": 0,
        }
    return {
        "totalPhys": int(status.ullTotalPhys),
        "availPhys": int(status.ullAvailPhys),
        "totalPage": int(status.ullTotalPageFile),
        "availPage": int(status.ullAvailPageFile),
        "loadPct": int(status.dwMemoryLoad),
    }

def format_mib(numBytes):
    """
    Format a byte count as mebibytes with two decimals.
    Input: numBytes.
    Output: string such as '12.34'.
    Locals: none.
    """
    return f"{numBytes / (1024 * 1024):.2f}"

def allocate_buffer(numBytes, pageSize):
    """
    Allocate a bytearray and touch every page so RAM is committed.
    Input: numBytes, pageSize.
    Output: buffer or None on MemoryError.
    Locals: buf, offset.
    """
    try:
        buf = bytearray(numBytes)
    except MemoryError:
        return None
    offset = 0
    while offset < numBytes:
        buf[offset] = 1
        offset += pageSize
    if numBytes > 0:
        buf[numBytes - 1] = 1
    return buf

def buffer_address(buf):
    """
    Return the raw data pointer for a bytearray buffer.
    Input: buf.
    Output: integer address.
    Locals: view.
    """
    view = (ctypes.c_char * len(buf)).from_buffer(buf)
    return ctypes.addressof(view)

def unlock_buffer_pages(buf, chunkBytes):
    """
    VirtualUnlock buf in chunks after the ratio experiment.
    Input: buf, chunkBytes.
    Output: none.
    Locals: addr, total, offset, n.
    """
    if buf is None or len(buf) == 0:
        return
    addr = buffer_address(buf)
    total = len(buf)
    offset = 0
    while offset < total:
        n = min(chunkBytes, total - offset)
        ctypes.windll.kernel32.VirtualUnlock(
            ctypes.c_void_p(addr + offset), ctypes.c_size_t(n)
        )
        offset += n

def measure_random_page_access(buf, pageSize, numOps, seed):
    """
    Time numOps random page-strided reads and writes on buf.
    Input: buf, pageSize, numOps, seed.
    Output: elapsed seconds.
    Locals: numPages, rng, t0, i, pageIndex, offset, value, t1.
    """
    numPages = max(1, len(buf) // pageSize)
    rng = random.Random(seed)
    t0 = time.perf_counter()
    for i in range(numOps):
        pageIndex = rng.randrange(numPages)
        offset = pageIndex * pageSize
        value = buf[offset]
        buf[offset] = (value + 1) & 0xFF
    t1 = time.perf_counter()
    return t1 - t0

def choose_ops_for_size(numBytes, baseOps):
    """
    Scale operation count so large thrashing sizes still finish.
    Input: numBytes, baseOps.
    Output: positive op count.
    Locals: scaled.
    """
    scaled = baseOps
    if numBytes >= 2 * 1024 * 1024 * 1024:
        scaled = max(80000, baseOps // 50)
    elif numBytes >= 512 * 1024 * 1024:
        scaled = max(150000, baseOps // 15)
    elif numBytes >= 128 * 1024 * 1024:
        scaled = max(400000, baseOps // 4)
    return scaled

def probe_hierarchy(pageSize, sizeList, baseOps):
    """
    Grow buffers through the hierarchy and time random page access.
    Input: pageSize, sizeList in bytes, baseOps.
    Output: list of result dicts.
    Locals: results, sizeBytes, buf, numOps, elapsed, nsPerOp, mem.
    """
    results = []
    for sizeBytes in sizeList:
        gc.collect()
        buf = allocate_buffer(sizeBytes, pageSize)
        if buf is None:
            results.append(
                {
                    "bytes": sizeBytes,
                    "ok": False,
                    "nsPerOp": None,
                    "ops": 0,
                    "seconds": None,
                }
            )
            print(f"hierarchy {format_mib(sizeBytes):>10} MiB  SKIP (alloc failed)")
            sys.stdout.flush()
            continue
        numOps = choose_ops_for_size(sizeBytes, baseOps)
        elapsed = measure_random_page_access(buf, pageSize, numOps, 17)
        nsPerOp = (elapsed / numOps) * 1e9
        mem = get_memory_status()
        results.append(
            {
                "bytes": sizeBytes,
                "ok": True,
                "nsPerOp": nsPerOp,
                "ops": numOps,
                "seconds": elapsed,
            }
        )
        print(
            f"hierarchy {format_mib(sizeBytes):>10} MiB  "
            f"ops={numOps:>9}  {elapsed:.4f} s  "
            f"{nsPerOp:10.1f} ns/op  "
            f"avail={format_mib(mem['availPhys'])} MiB"
        )
        sys.stdout.flush()
        del buf
        gc.collect()
    return results

def estimate_cache_cliff(hierarchyRows):
    """
    Find the first size where ns/op jumps by at least 1.4x over the prior.
    Input: hierarchyRows from probe_hierarchy.
    Output: (cliffBytes, priorNs, cliffNs) or (None, None, None).
    Locals: prior, row, ratio.
    """
    prior = None
    for row in hierarchyRows:
        if not row["ok"]:
            continue
        if prior is not None and prior["nsPerOp"] > 0:
            ratio = row["nsPerOp"] / prior["nsPerOp"]
            if ratio >= 1.4 and prior["bytes"] >= 1 * 1024 * 1024:
                return row["bytes"], prior["nsPerOp"], row["nsPerOp"]
        prior = row
    return None, None, None

def estimate_ram_access_ns(hierarchyRows):
    """
    Median ns/op among hierarchy rows between 8 MiB and 256 MiB.
    Input: hierarchyRows.
    Output: median ns or None.
    Locals: samples, row.
    """
    samples = []
    for row in hierarchyRows:
        if not row["ok"]:
            continue
        if 8 * 1024 * 1024 <= row["bytes"] <= 256 * 1024 * 1024:
            samples.append(row["nsPerOp"])
    if not samples:
        return None
    return statistics.median(samples)

def raise_working_set_ceiling(maxBytes):
    """
    Raise the process working-set maximum so VirtualLock can pin ballast.
    Input: maxBytes desired ceiling.
    Output: True on success.
    Locals: handle, ok.
    """
    handle = ctypes.c_void_p(-1)
    ok = ctypes.windll.kernel32.SetProcessWorkingSetSize(
        handle, ctypes.c_size_t(max(65536, maxBytes // 8)), ctypes.c_size_t(maxBytes)
    )
    return bool(ok)

def lock_buffer_pages(buf, chunkBytes):
    """
    VirtualLock buf in chunks, growing the working-set ceiling as needed.
    Input: buf, chunkBytes.
    Output: number of bytes locked.
    Locals: addr, total, locked, offset, n, ok, ceiling.
    """
    if buf is None or len(buf) == 0:
        return 0
    addr = buffer_address(buf)
    total = len(buf)
    locked = 0
    offset = 0
    ceiling = 128 * 1024 * 1024
    raise_working_set_ceiling(ceiling)
    while offset < total:
        n = min(chunkBytes, total - offset)
        ok = ctypes.windll.kernel32.VirtualLock(
            ctypes.c_void_p(addr + offset), ctypes.c_size_t(n)
        )
        if not ok:
            ceiling = min(total + 256 * 1024 * 1024, ceiling + 256 * 1024 * 1024)
            raise_working_set_ceiling(ceiling)
            ok = ctypes.windll.kernel32.VirtualLock(
                ctypes.c_void_p(addr + offset), ctypes.c_size_t(n)
            )
        if ok:
            locked += n
            offset += n
        else:
            offset += n
    return locked

def build_ballast(pageSize, activeM, headroomBytes):
    """
    Fill most free RAM and VirtualLock it so only about M remains usable.
    Input: pageSize, activeM, headroomBytes.
    Output: ballast buffer or None.
    Locals: mem, leaveFree, ballastBytes, ballast, locked, chunk.
    """
    mem = get_memory_status()
    leaveFree = activeM + headroomBytes
    if mem["availPhys"] <= leaveFree:
        return None
    ballastBytes = mem["availPhys"] - leaveFree
    ballastBytes = (ballastBytes // pageSize) * pageSize
    if ballastBytes < 64 * 1024 * 1024:
        return None
    print(
        f"building ballast {format_mib(ballastBytes)} MiB  "
        f"(leave ~{format_mib(leaveFree)} MiB free around M)"
    )
    sys.stdout.flush()
    ballast = allocate_buffer(ballastBytes, pageSize)
    if ballast is None:
        return None
    chunk = 2 * 1024 * 1024
    locked = lock_buffer_pages(ballast, chunk)
    mem = get_memory_status()
    print(
        f"ballast ready  locked={format_mib(locked)} MiB  "
        f"availPhys={format_mib(mem['availPhys'])} MiB  "
        f"load={mem['loadPct']}%"
    )
    sys.stdout.flush()
    return ballast

def measure_mmap_random_access(numBytes, pageSize, numOps, seed):
    """
    Time random page touches on a file-backed mmap of size numBytes.
    Input: numBytes, pageSize, numOps, seed.
    Output: (elapsedSeconds, okFlag).
    Locals: path, fileObj, mapObj, numPages, rng, t0, i, pageIndex, offset, t1.
    """
    path = None
    try:
        fd, path = tempfile.mkstemp(prefix="vmm_c_", suffix=".dat")
        os.close(fd)
        with open(path, "wb") as fileObj:
            block = b"\x01" * (1024 * 1024)
            written = 0
            while written + len(block) <= numBytes:
                fileObj.write(block)
                written += len(block)
            if written < numBytes:
                fileObj.write(b"\x01" * (numBytes - written))
        with open(path, "r+b") as fileObj:
            mapObj = mmap.mmap(fileObj.fileno(), numBytes)
            numPages = max(1, numBytes // pageSize)
            rng = random.Random(seed)
            t0 = time.perf_counter()
            for i in range(numOps):
                pageIndex = rng.randrange(numPages)
                offset = pageIndex * pageSize
                value = mapObj[offset]
                mapObj[offset] = (value + 1) & 0xFF
            t1 = time.perf_counter()
            mapObj.close()
        return t1 - t0, True
    except (OSError, ValueError, MemoryError):
        return None, False
    finally:
        if path is not None and os.path.exists(path):
            try:
                os.remove(path)
            except OSError:
                pass

def run_mmap_ratio_subset(activeM, pageSize, ratioList, baseOps, maxCBytes):
    """
    File-backed mmap timings for selected C/M ratios (disk-level VMM path).
    Input: activeM, pageSize, ratioList, baseOps, maxCBytes.
    Output: list of result dicts.
    Locals: results, ratio, sizeC, numOps, elapsed, ok, nsPerOp.
    """
    results = []
    for ratio in ratioList:
        sizeC = max(pageSize, int(ratio * activeM))
        sizeC = (sizeC // pageSize) * pageSize
        if sizeC > maxCBytes:
            results.append(
                {
                    "ratio": ratio,
                    "bytes": sizeC,
                    "ok": False,
                    "skipped": True,
                    "nsPerOp": None,
                    "ops": 0,
                    "seconds": None,
                }
            )
            print(f"mmap ratio {ratio:>6.2f}  SKIP (cap)")
            continue
        numOps = choose_ops_for_size(sizeC, baseOps)
        if ratio >= 5.0:
            numOps = min(numOps, 50000)
        elapsed, ok = measure_mmap_random_access(sizeC, pageSize, numOps, 123)
        if not ok:
            results.append(
                {
                    "ratio": ratio,
                    "bytes": sizeC,
                    "ok": False,
                    "skipped": True,
                    "nsPerOp": None,
                    "ops": 0,
                    "seconds": None,
                }
            )
            print(f"mmap ratio {ratio:>6.2f}  SKIP (mmap failed)")
            continue
        nsPerOp = (elapsed / numOps) * 1e9
        results.append(
            {
                "ratio": ratio,
                "bytes": sizeC,
                "ok": True,
                "skipped": False,
                "nsPerOp": nsPerOp,
                "ops": numOps,
                "seconds": elapsed,
            }
        )
        print(
            f"mmap ratio {ratio:>6.2f}  C={format_mib(sizeC):>10} MiB  "
            f"ops={numOps:>9}  {elapsed:.4f} s  {nsPerOp:12.1f} ns/op"
        )
        sys.stdout.flush()
    return results

def run_ratio_experiment(activeM, pageSize, ratioList, baseOps, maxCBytes):
    """
    Time random page work for each data size C = ratio * activeM.
    Input: activeM, pageSize, ratioList, baseOps, maxCBytes safety cap.
    Output: list of result dicts.
    Locals: results, ratio, sizeC, mem, buf, numOps, elapsed, nsPerOp.
    """
    results = []
    for ratio in ratioList:
        sizeC = max(pageSize, int(ratio * activeM))
        sizeC = (sizeC // pageSize) * pageSize
        if sizeC > maxCBytes:
            print(
                f"ratio {ratio:>6.2f}  C={format_mib(sizeC)} MiB  "
                f"SKIP (above safety cap {format_mib(maxCBytes)} MiB)"
            )
            sys.stdout.flush()
            results.append(
                {
                    "ratio": ratio,
                    "bytes": sizeC,
                    "ok": False,
                    "skipped": True,
                    "nsPerOp": None,
                    "ops": 0,
                    "seconds": None,
                }
            )
            continue
        gc.collect()
        buf = allocate_buffer(sizeC, pageSize)
        if buf is None:
            print(f"ratio {ratio:>6.2f}  C={format_mib(sizeC)} MiB  SKIP (alloc)")
            sys.stdout.flush()
            results.append(
                {
                    "ratio": ratio,
                    "bytes": sizeC,
                    "ok": False,
                    "skipped": True,
                    "nsPerOp": None,
                    "ops": 0,
                    "seconds": None,
                }
            )
            continue
        numOps = choose_ops_for_size(sizeC, baseOps)
        elapsed = measure_random_page_access(buf, pageSize, numOps, 99)
        nsPerOp = (elapsed / numOps) * 1e9
        mem = get_memory_status()
        results.append(
            {
                "ratio": ratio,
                "bytes": sizeC,
                "ok": True,
                "skipped": False,
                "nsPerOp": nsPerOp,
                "ops": numOps,
                "seconds": elapsed,
            }
        )
        print(
            f"ratio {ratio:>6.2f}  C={format_mib(sizeC):>10} MiB  "
            f"ops={numOps:>9}  {elapsed:.4f} s  "
            f"{nsPerOp:12.1f} ns/op  "
            f"avail={format_mib(mem['availPhys'])} MiB"
        )
        sys.stdout.flush()
        del buf
        gc.collect()
    return results

def print_ratio_table(title, ratioRows):
    """
    Print one C/M timing table.
    Input: title, ratioRows.
    Output: none.
    Locals: row.
    """
    print()
    print(title)
    print(
        f"{'C/M':>8}  {'C MiB':>12}  {'ops':>10}  "
        f"{'seconds':>10}  {'ns/op':>14}"
    )
    for row in ratioRows:
        if row["skipped"] or not row["ok"]:
            print(
                f"{row['ratio']:>8.2f}  {format_mib(row['bytes']):>12}  "
                f"{'SKIP':>10}"
            )
            continue
        print(
            f"{row['ratio']:>8.2f}  {format_mib(row['bytes']):>12}  "
            f"{row['ops']:>10}  {row['seconds']:>10.4f}  "
            f"{row['nsPerOp']:>14.1f}"
        )

def print_summary(pageSize, mem, activeM, hierarchyRows, ratioRows, mmapRows, cliff):
    """
    Print the research summary tables for VMM components and C/M timings.
    Input: pageSize, mem, activeM, hierarchyRows, ratioRows, mmapRows, cliff.
    Output: none.
    Locals: row, ramNs, cliffBytes, priorNs, cliffNs.
    """
    ramNs = estimate_ram_access_ns(hierarchyRows)
    cliffBytes, priorNs, cliffNs = cliff
    print()
    print("=" * 72)
    print("VMM component summary")
    print("=" * 72)
    print(f"page size:              {pageSize} bytes")
    print(f"total physical:         {format_mib(mem['totalPhys'])} MiB")
    print(f"available physical:     {format_mib(mem['availPhys'])} MiB")
    print(f"memory load:            {mem['loadPct']} %")
    print(f"active set M (forced):  {format_mib(activeM)} MiB")
    if ramNs is not None:
        print(f"approx RAM access:      {ramNs:.1f} ns per page touch")
    if cliffBytes is not None:
        print(
            f"first timing cliff:     {format_mib(cliffBytes)} MiB "
            f"({priorNs:.1f} -> {cliffNs:.1f} ns/op)"
        )
    print()
    print("hierarchy probe (random page touch)")
    print(f"{'size MiB':>12}  {'ops':>10}  {'seconds':>10}  {'ns/op':>12}")
    for row in hierarchyRows:
        if not row["ok"]:
            print(f"{format_mib(row['bytes']):>12}  {'SKIP':>10}")
            continue
        print(
            f"{format_mib(row['bytes']):>12}  {row['ops']:>10}  "
            f"{row['seconds']:>10.4f}  {row['nsPerOp']:>12.1f}"
        )
    print_ratio_table(
        "synthetic C relative to M (RAM buffer under locked ballast)", ratioRows
    )
    print_ratio_table(
        "file-backed mmap C relative to M (page cache / disk path)", mmapRows
    )
    print("=" * 72)

def hierarchy_size_list():
    """
    Return the buffer sizes used in the hierarchy probe phase.
    Input: none.
    Output: list of sizes in bytes.
    Locals: none.
    """
    return [
        4 * 1024,
        16 * 1024,
        64 * 1024,
        256 * 1024,
        1 * 1024 * 1024,
        4 * 1024 * 1024,
        16 * 1024 * 1024,
        64 * 1024 * 1024,
        256 * 1024 * 1024,
        512 * 1024 * 1024,
    ]

def ratio_value_list():
    """
    Return the C/M ratios timed against the forced active set M.
    Input: none.
    Output: list of float ratios.
    Locals: none.
    """
    return [
        0.5,
        0.6,
        0.7,
        0.8,
        0.9,
        0.95,
        0.99,
        1.0,
        1.01,
        1.1,
        1.5,
        2.0,
        5.0,
        10.0,
        100.0,
    ]

def choose_max_c_bytes(activeM):
    """
    Cap C so ratio trials stay within pagefile and a 100 M multiple.
    Input: activeM.
    Output: max C in bytes.
    Locals: none.
    """
    return min(
        int(get_memory_status()["availPage"] * 0.40),
        int(100.0 * activeM),
        4 * 1024 * 1024 * 1024,
    )

def run_hierarchy_phase(pageSize, baseOps):
    """
    Run Phase 1 hierarchy probe and estimate the first timing cliff.
    Input: pageSize, baseOps.
    Output: (hierarchyRows, cliff).
    Locals: hierarchyRows, cliff.
    """
    print("Phase 1: hierarchy probe (no ballast)")
    hierarchyRows = probe_hierarchy(pageSize, hierarchy_size_list(), baseOps)
    cliff = estimate_cache_cliff(hierarchyRows)
    print()
    return hierarchyRows, cliff

def run_ballast_ratio_phase(pageSize, activeM, headroom, baseOps, maxCBytes):
    """
    Lock ballast near M and time anonymous C/M ratio accesses.
    Input: pageSize, activeM, headroom, baseOps, maxCBytes.
    Output: (ballast, ratioRows).
    Locals: ballast, ratioRows.
    """
    print(f"safety cap for C: {format_mib(maxCBytes)} MiB")
    print(
        f"Phase 2: treat active set M = {format_mib(activeM)} MiB  "
        f"by VirtualLocking a ballast so free RAM sits near M"
    )
    ballast = build_ballast(pageSize, activeM, headroom)
    if ballast is None:
        print("warning: ballast not built, ratios may stay in core")
    ratioRows = run_ratio_experiment(
        activeM, pageSize, ratio_value_list(), baseOps, maxCBytes
    )
    return ballast, ratioRows

def run_mmap_phase(activeM, pageSize, baseOps, maxCBytes):
    """
    Run Phase 3 file-backed mmap timings for selected C/M ratios.
    Input: activeM, pageSize, baseOps, maxCBytes.
    Output: mmapRows.
    Locals: mmapRatios.
    """
    print()
    print("Phase 3: file-backed mmap ratios (page cache / disk faults)")
    mmapRatios = [0.5, 1.0, 1.5, 2.0, 5.0, 10.0, 100.0]
    return run_mmap_ratio_subset(
        activeM, pageSize, mmapRatios, baseOps, maxCBytes
    )

def release_ballast(ballast):
    """
    Unlock and drop the ballast buffer if one was built.
    Input: ballast or None.
    Output: none.
    Locals: none.
    """
    if ballast is None:
        return
    unlock_buffer_pages(ballast, 2 * 1024 * 1024)
    del ballast
    gc.collect()

def main():
    """
    Measure VMM page size and access times, then time C/M thrashing ratios.
    Input: none.
    Output: printed tables (and returned result dict).
    Locals: pageSize, mem, baseOps, hierarchyRows, cliff, activeM, headroom,
            maxCBytes, ballast, ratioRows, mmapRows, memEnd.
    """
    pageSize = get_page_size()
    mem = get_memory_status()
    print("Virtual memory management influence experiment")
    print(f"page size: {pageSize} bytes")
    print(
        f"physical RAM total={format_mib(mem['totalPhys'])} MiB  "
        f"avail={format_mib(mem['availPhys'])} MiB  "
        f"load={mem['loadPct']}%"
    )
    print()
    baseOps = 4_000_000
    hierarchyRows, cliff = run_hierarchy_phase(pageSize, baseOps)
    activeM = 32 * 1024 * 1024
    headroom = 32 * 1024 * 1024
    maxCBytes = choose_max_c_bytes(activeM)
    ballast, ratioRows = run_ballast_ratio_phase(
        pageSize, activeM, headroom, baseOps, maxCBytes
    )
    mmapRows = run_mmap_phase(activeM, pageSize, baseOps, maxCBytes)
    release_ballast(ballast)
    memEnd = get_memory_status()
    print_summary(
        pageSize, memEnd, activeM, hierarchyRows, ratioRows, mmapRows, cliff
    )
    return {
        "pageSize": pageSize,
        "mem": memEnd,
        "activeM": activeM,
        "hierarchyRows": hierarchyRows,
        "ratioRows": ratioRows,
        "mmapRows": mmapRows,
        "cliff": cliff,
    }

if __name__ == "__main__":
    main()