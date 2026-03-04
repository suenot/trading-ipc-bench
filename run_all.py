"""Run all benchmarks sequentially and print a summary table.

Each benchmark is executed in a subprocess to ensure clean state
(no shared ports, no lingering threads).

Benchmarks that require external servers (Redis, NATS, Kafka) are skipped
gracefully when the server is not running.
"""
import subprocess
import sys
import json
import time
from pathlib import Path

# ── Sorted by expected latency (fastest first) ───────────────────────────────
# Core — no external server needed
BENCHES_CORE = [
    "benches/bench_shm.py",
    "benches/bench_pipe.py",
    "benches/bench_uds.py",
    "benches/bench_nng.py",
    "benches/bench_zmq_ipc.py",
    "benches/bench_tcp.py",
    "benches/bench_zmq_tcp.py",
    "benches/bench_grpc_uds.py",
    "benches/bench_grpc_tcp.py",
    "benches/bench_websocket.py",
    "benches/bench_http_rest.py",
]

# Optional — skipped silently when the server is not running
BENCHES_OPTIONAL = [
    "benches/bench_redis_pubsub.py",
    "benches/bench_redis_streams.py",
    "benches/bench_nats.py",
    "benches/bench_kafka.py",
]

ROOT = Path(__file__).parent


def run_bench(script: str) -> bool:
    print(f"\n{'═' * 64}")
    print(f"  Running: {script}")
    print(f"{'═' * 64}")
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

    w = 84
    header = f"{'Transport':<28} {'p50 (μs)':>9} {'p95 (μs)':>9} {'p99 (μs)':>9} {'p99.9 (μs)':>11} {'msg/s':>12}"
    sep = "─" * w

    print(f"\n{'═' * w}")
    print(f"  Trading IPC Benchmark  |  msg size: {msg_size} bytes")
    print(f"{'═' * w}")
    print(header)
    print(sep)
    for r in rows:
        print(
            f"{r['transport']:<28}"
            f" {r['p50_us']:>9.1f}"
            f" {r['p95_us']:>9.1f}"
            f" {r['p99_us']:>9.1f}"
            f" {r['p999_us']:>11.1f}"
            f" {r['throughput_msg_s']:>12,.0f}"
        )
    print(sep)

    max_p50 = max(r["p50_us"] for r in rows)
    print(f"\n  p50 latency (shorter = faster)")
    print(f"  {'─' * 56}")
    for r in rows:
        bar = "█" * max(1, int(52 * r["p50_us"] / max_p50))
        print(f"  {r['transport']:<26} {bar}  {r['p50_us']:.1f} μs")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--optional", action="store_true",
                        help="Also run optional benchmarks (Redis, NATS, Kafka)")
    args = parser.parse_args()

    benches = BENCHES_CORE + (BENCHES_OPTIONAL if args.optional else [])

    failed = []
    t_start = time.time()
    for bench in benches:
        ok = run_bench(bench)
        if not ok:
            failed.append(bench)

    elapsed = time.time() - t_start
    print(f"\n\n{'═' * 64}")
    print(f"  Finished in {elapsed:.1f}s")
    if failed:
        print(f"  Non-zero exit: {', '.join(failed)}")
    print(f"{'═' * 64}")

    print_summary(msg_size=64)
