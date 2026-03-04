"""Common utilities for trading-ipc-bench."""
import os
import json
import time
from pathlib import Path
from typing import List, Dict, Any

RESULTS_DIR = Path(__file__).parent.parent / "results"

WARMUP_ITERATIONS = int(os.environ.get("IPC_BENCH_WARMUP", 1_000))
BENCH_ITERATIONS = int(os.environ.get("IPC_BENCH_ITERATIONS", 100_000))
MESSAGE_SIZES = [int(s) for s in os.environ.get("IPC_BENCH_SIZES", "64,256,1024").split(",")]


def make_message(size: int) -> bytes:
    """Generate a random payload of exactly `size` bytes."""
    return os.urandom(size)


def recv_exact(recv_fn, n: int) -> bytes:
    """Receive exactly n bytes using the provided recv callable."""
    buf = bytearray()
    while len(buf) < n:
        chunk = recv_fn(n - len(buf))
        if not chunk:
            raise ConnectionError("Connection closed")
        buf += chunk
    return bytes(buf)


def compute_stats(latencies_ns: List[int]) -> Dict[str, float]:
    """Compute latency statistics from a list of nanosecond RTT values."""
    s = sorted(latencies_ns)
    n = len(s)

    def pct(p: float) -> int:
        return s[min(int(n * p / 100), n - 1)]

    mean_ns = sum(latencies_ns) / n
    return {
        "min_us":            s[0] / 1_000,
        "p50_us":            pct(50) / 1_000,
        "p95_us":            pct(95) / 1_000,
        "p99_us":            pct(99) / 1_000,
        "p999_us":           pct(99.9) / 1_000,
        "max_us":            s[-1] / 1_000,
        "mean_us":           mean_ns / 1_000,
        "throughput_msg_s":  1_000_000_000 / mean_ns,
    }


def save_results(name: str, msg_size: int, stats: Dict[str, Any], iterations: int = BENCH_ITERATIONS) -> None:
    """Persist benchmark results to results/<name>_<size>b.json."""
    RESULTS_DIR.mkdir(exist_ok=True)
    path = RESULTS_DIR / f"{name}_{msg_size}b.json"
    data = {
        "transport":      name,
        "msg_size_bytes": msg_size,
        "iterations":     iterations,
        **stats,
    }
    path.write_text(json.dumps(data, indent=2))
    print(f"  Saved → {path}")


def print_stats(name: str, msg_size: int, stats: Dict[str, float]) -> None:
    print(f"\n{'─' * 60}")
    print(f"  {name}  (msg={msg_size}B)")
    print(f"{'─' * 60}")
    print(f"  min:       {stats['min_us']:>9.2f} μs")
    print(f"  p50:       {stats['p50_us']:>9.2f} μs")
    print(f"  p95:       {stats['p95_us']:>9.2f} μs")
    print(f"  p99:       {stats['p99_us']:>9.2f} μs")
    print(f"  p99.9:     {stats['p999_us']:>9.2f} μs")
    print(f"  max:       {stats['max_us']:>9.2f} μs")
    print(f"  throughput: {stats['throughput_msg_s']:>12,.0f} msg/s")
