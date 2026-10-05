"""Only a built-in bounded sum; this is not an arbitrary-code sandbox."""
import json
import math
import os
import resource
import signal
import sys
import time


def main():
    request = json.loads(sys.stdin.read(8192))
    spec = request["task"]
    memory = request["memory_mib"] * 1024 * 1024
    cpu_seconds = max(1, math.ceil(request["limits"]["cpu_ms"] / 1000))
    resource.setrlimit(resource.RLIMIT_AS, (memory, memory))
    resource.setrlimit(resource.RLIMIT_CPU, (cpu_seconds, cpu_seconds + 1))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    resource.setrlimit(resource.RLIMIT_FSIZE, (4096, 4096))
    resource.setrlimit(resource.RLIMIT_NOFILE, (16, 16))
    # Independent timers survive loss of the parent supervisor. No forking or
    # network operations exist in this fixed workload.
    signal.setitimer(signal.ITIMER_REAL, request["wall_ms"] / 1000 + 0.25)
    signal.setitimer(signal.ITIMER_PROF, request["limits"]["cpu_ms"] / 1000)
    if hasattr(os, "sched_getaffinity"):
        os.sched_setaffinity(0, {min(os.sched_getaffinity(0))})
    start = time.monotonic_ns()
    cpu_start = time.process_time_ns()
    time.sleep(spec["delay_ms"] / 1000)
    total = 0
    for value in range(1, spec["n"] + 1):
        total += value
    wall_ms = max(1, math.ceil((time.monotonic_ns() - start) / 1_000_000))
    cpu_ms = max(1, math.ceil((time.process_time_ns() - cpu_start) / 1_000_000))
    # Linux ru_maxrss is KiB. The runner explicitly requires Linux.
    peak_mib = math.ceil(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024)
    print(json.dumps({"output": {"sum": total}, "cpu_ms": cpu_ms,
                      "wall_ms": wall_ms, "peak_rss_mib": peak_mib}))


if __name__ == "__main__":
    main()
