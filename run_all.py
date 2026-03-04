"""Run all benchmarks sequentially and print a summary table.

Each benchmark is executed in a subprocess to ensure clean state
(no shared ports, no lingering threads).
"""
import subprocess
import sys
import json
import time
from pathlib import Path

BENCHES = [
    "benches/bench_shm.py",
    "benches/bench_pipe.py",
    "benches/bench_uds.py",
    "benches/bench_zmq_ipc.py",
    "benches/bench_tcp.py",
    "benches/bench_zmq_tcp.py",
    "benches/bench_websocket.py",
    "benches/bench_redis_pubsub.py",
]

ROOT = Path(__file__).parent


def run_bench(script: str) -> bool:
    name = Path(script).stem
    print(f"\n{'═' * 60}")
    print(f"  Running: {script}")
    print(f"{'═' * 60}")
    result = subprocess.run(
        [sys.executable, str(ROOT / script)],
        cwd=str(ROOT),
    )
    return result.returncode == 0


def print_summary(msg_size: int = 64) -> None:
    results_dir = ROOT / "results"
    rows = []
    for f in sorted(results_dir.glob(f"*_{msg_size}b.json")):
        data = json.loads(f.read_text())
        rows.append(data)

    if not rows:
        print("No results found. Run benchmarks first.")
        return

    rows.sort(key=lambda r: r.get("p50_us", float("inf")))

    header = f"{'Transport':<26} {'p50':>8} {'p95':>8} {'p99':>8} {'p99.9':>10} {'throughput':>16}"
    units  = f"{'':26} {'(μs)':>8} {'(μs)':>8} {'(μs)':>8} {'(μs)':>10} {'(msg/s)':>16}"
    sep    = "─" * len(header)

    print(f"\n{'═' * len(header)}")
    print(f"  Trading IPC Benchmark — msg size: {msg_size} bytes")
    print(f"{'═' * len(header)}")
    print(header)
    print(units)
    print(sep)
    for r in rows:
        print(
            f"{r['transport']:<26}"
            f" {r['p50_us']:>8.1f}"
            f" {r['p95_us']:>8.1f}"
            f" {r['p99_us']:>8.1f}"
            f" {r['p999_us']:>10.1f}"
            f" {r['throughput_msg_s']:>16,.0f}"
        )
    print(sep)

    # ASCII bar chart (p50, log-ish scale capped at 60 cols)
    max_p50 = max(r["p50_us"] for r in rows)
    print("\n  p50 latency (μs)  [shorter bar = faster]")
    print(f"  {'─'*50}")
    for r in rows:
        bar_len = max(1, int(50 * r["p50_us"] / max_p50))
        bar = "█" * bar_len
        print(f"  {r['transport']:<24} {bar}  {r['p50_us']:.1f} μs")


if __name__ == "__main__":
    failed = []
    t_start = time.time()

    for bench in BENCHES:
        ok = run_bench(bench)
        if not ok:
            failed.append(bench)

    elapsed = time.time() - t_start
    print(f"\n\n{'═' * 60}")
    print(f"  All benchmarks finished in {elapsed:.1f}s")
    if failed:
        print(f"  Failed: {', '.join(failed)}")
    print(f"{'═' * 60}")

    print_summary(msg_size=64)
