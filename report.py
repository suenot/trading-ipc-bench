"""Generate a human-readable report from saved benchmark results.

Usage:
    python report.py              # report for all message sizes
    python report.py --size 64    # report for one message size
"""
import json
import argparse
from pathlib import Path

RESULTS_DIR = Path(__file__).parent / "results"


def load_results(msg_size: int) -> list[dict]:
    rows = []
    for f in sorted(RESULTS_DIR.glob(f"*_{msg_size}b.json")):
        rows.append(json.loads(f.read_text()))
    rows.sort(key=lambda r: r.get("p50_us", float("inf")))
    return rows


def print_table(rows: list[dict], msg_size: int) -> None:
    if not rows:
        print(f"  No results for {msg_size}B messages. Run benchmarks first.")
        return

    w = 80
    print(f"\n{'═' * w}")
    print(f"  Trading IPC Benchmark  |  msg size: {msg_size} bytes  |  n={rows[0].get('iterations', '?'):,}")
    print(f"{'═' * w}")
    print(f"{'Transport':<26} {'p50 (μs)':>9} {'p95 (μs)':>9} {'p99 (μs)':>9} {'p99.9 (μs)':>11} {'msg/s':>12}")
    print(f"{'─' * w}")
    for r in rows:
        print(
            f"{r['transport']:<26}"
            f" {r['p50_us']:>9.1f}"
            f" {r['p95_us']:>9.1f}"
            f" {r['p99_us']:>9.1f}"
            f" {r['p999_us']:>11.1f}"
            f" {r['throughput_msg_s']:>12,.0f}"
        )
    print(f"{'─' * w}")

    max_p50 = max(r["p50_us"] for r in rows)
    print(f"\n  p50 latency  (lower = faster)")
    print(f"  {'─' * 52}")
    for r in rows:
        bar = "█" * max(1, int(48 * r["p50_us"] / max_p50))
        print(f"  {r['transport']:<24} {bar}  {r['p50_us']:.1f} μs")
    print()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--size", type=int, default=None, help="Message size in bytes (64 | 256 | 1024)")
    args = parser.parse_args()

    sizes = [args.size] if args.size else [64, 256, 1024]
    for size in sizes:
        rows = load_results(size)
        print_table(rows, size)


if __name__ == "__main__":
    main()
