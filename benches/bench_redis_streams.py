"""Benchmark: Redis Streams round-trip (XADD / XREAD).

Represents section 3.3 of the article — Redis Streams.
Unlike Pub/Sub (fire-and-forget), Streams are persistent and support
consumer groups. This benchmark measures the XADD → XREAD round-trip
latency using two streams: "bench:req" and "bench:resp".

Requires a running Redis instance on 127.0.0.1:6379.
Requires: pip install redis
"""
import threading
import time
import sys
from pathlib import Path

try:
    import redis
except ImportError:
    print("redis not installed. Run: pip install redis")
    sys.exit(1)

sys.path.insert(0, str(Path(__file__).parent.parent))
from src.common import (
    make_message, compute_stats,
    save_results, print_stats,
    WARMUP_ITERATIONS, MESSAGE_SIZES,
)

# Redis Streams are persistent but slower than Pub/Sub — use 10K iterations
STREAM_ITERATIONS = 10_000
REQ_STREAM = "bench:streams:req"
RESP_STREAM = "bench:streams:resp"


def _check_redis() -> bool:
    try:
        r = redis.Redis(socket_connect_timeout=2)
        r.ping()
        return True
    except Exception as e:
        print(f"  Redis not available ({e}). Skipping.")
        return False


def _server(ready: threading.Event, stop: threading.Event) -> None:
    r = redis.Redis()
    r.delete(REQ_STREAM, RESP_STREAM)
    last_id = "0"
    ready.set()
    while not stop.is_set():
        entries = r.xread({REQ_STREAM: last_id}, block=100, count=1)
        if not entries:
            continue
        for _, msgs in entries:
            for msg_id, fields in msgs:
                last_id = msg_id
                r.xadd(RESP_STREAM, {"data": fields[b"data"]})


def run(msg_size: int = 64) -> dict:
    if not _check_redis():
        return {}

    msg = make_message(msg_size)
    ready, stop = threading.Event(), threading.Event()

    t = threading.Thread(target=_server, args=(ready, stop), daemon=True)
    t.start()
    ready.wait(timeout=5)
    time.sleep(0.1)

    r = redis.Redis()
    r.delete(REQ_STREAM, RESP_STREAM)
    resp_last_id = "0"

    def send_recv(data: bytes) -> None:
        nonlocal resp_last_id
        r.xadd(REQ_STREAM, {"data": data})
        while True:
            entries = r.xread({RESP_STREAM: resp_last_id}, block=5000, count=1)
            if entries:
                for _, msgs in entries:
                    for msg_id, _ in msgs:
                        resp_last_id = msg_id
                return

    for _ in range(min(WARMUP_ITERATIONS, 200)):
        send_recv(msg)

    latencies = []
    for _ in range(STREAM_ITERATIONS):
        t0 = time.perf_counter_ns()
        send_recv(msg)
        latencies.append(time.perf_counter_ns() - t0)

    stop.set()
    r.delete(REQ_STREAM, RESP_STREAM)

    stats = compute_stats(latencies)
    print_stats("Redis Streams", msg_size, stats)
    save_results("redis_streams", msg_size, stats, iterations=STREAM_ITERATIONS)
    return stats


if __name__ == "__main__":
    for size in MESSAGE_SIZES:
        run(size)
