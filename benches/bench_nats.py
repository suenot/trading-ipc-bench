"""Benchmark: NATS request/reply round-trip.

Represents section 3.4 of the article — NATS messaging.
NATS is an ultra-lightweight Go messaging system with sub-ms latency.
Uses the native request/reply pattern (built-in, no two-channel setup needed).

Requires a running NATS server: https://docs.nats.io/running-a-nats-service/introduction/installation
  brew install nats-server && nats-server &
Requires: pip install nats-py
"""
import asyncio
import time
import sys
from pathlib import Path

try:
    import nats
except ImportError:
    print("nats-py not installed. Run: pip install nats-py")
    sys.exit(1)

sys.path.insert(0, str(Path(__file__).parent.parent))
from src.common import (
    make_message, compute_stats,
    save_results, print_stats,
    WARMUP_ITERATIONS, MESSAGE_SIZES,
)

NATS_URL = "nats://127.0.0.1:4222"
SUBJECT = "bench.echo"
NATS_ITERATIONS = 10_000  # NATS is fast but async overhead adds up


async def _check_nats() -> bool:
    try:
        nc = await nats.connect(NATS_URL, connect_timeout=2)
        await nc.close()
        return True
    except Exception as e:
        print(f"  NATS server not available at {NATS_URL} ({e}).")
        print("  Start it with: nats-server &")
        return False


async def _bench(msg: bytes, n_warmup: int, n_bench: int) -> list:
    nc = await nats.connect(NATS_URL)

    # Server: subscribe and reply
    async def handler(msg_in):
        await msg_in.respond(msg_in.data)

    sub = await nc.subscribe(SUBJECT, cb=handler)

    for _ in range(n_warmup):
        await nc.request(SUBJECT, msg, timeout=5)

    latencies = []
    for _ in range(n_bench):
        t0 = time.perf_counter_ns()
        await nc.request(SUBJECT, msg, timeout=5)
        latencies.append(time.perf_counter_ns() - t0)

    await sub.unsubscribe()
    await nc.close()
    return latencies


def run(msg_size: int = 64) -> dict:
    if not asyncio.run(_check_nats()):
        return {}

    msg = make_message(msg_size)
    latencies = asyncio.run(_bench(msg, min(WARMUP_ITERATIONS, 500), NATS_ITERATIONS))

    stats = compute_stats(latencies)
    print_stats("NATS", msg_size, stats)
    save_results("nats", msg_size, stats, iterations=NATS_ITERATIONS)
    return stats


if __name__ == "__main__":
    for size in MESSAGE_SIZES:
        run(size)
