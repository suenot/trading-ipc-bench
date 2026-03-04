"""Benchmark: Redis Pub/Sub round-trip.

Two channels: "bench:req" (client → server) and "bench:resp" (server → client).
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

# Redis is ~5× slower than TCP — use fewer iterations for a reasonable runtime
REDIS_ITERATIONS = 10_000
REQ_CH = "bench:req"
RESP_CH = "bench:resp"


def _check_redis() -> bool:
    try:
        r = redis.Redis(socket_connect_timeout=2)
        r.ping()
        return True
    except Exception as e:
        print(f"Redis not available ({e}). Skipping.")
        return False


def _server(ready: threading.Event, stop: threading.Event) -> None:
    r_pub = redis.Redis()
    r_sub = redis.Redis()
    sub = r_sub.pubsub()
    sub.subscribe(REQ_CH)
    ready.set()
    for msg in sub.listen():
        if stop.is_set():
            break
        if msg["type"] == "message":
            r_pub.publish(RESP_CH, msg["data"])


def run(msg_size: int = 64) -> dict:
    if not _check_redis():
        return {}

    msg = make_message(msg_size)
    ready, stop = threading.Event(), threading.Event()

    t = threading.Thread(target=_server, args=(ready, stop), daemon=True)
    t.start()
    ready.wait(timeout=5)
    time.sleep(0.1)  # let server's subscription propagate

    r_pub = redis.Redis()
    r_sub = redis.Redis()
    sub = r_sub.pubsub()
    sub.subscribe(RESP_CH)
    sub.get_message(timeout=1.0)  # consume subscription-confirmation message
    time.sleep(0.1)

    def send_recv(data: bytes) -> None:
        r_pub.publish(REQ_CH, data)
        while True:
            m = sub.get_message(ignore_subscribe_messages=True, timeout=5.0)
            if m and m["type"] == "message":
                return

    for _ in range(min(WARMUP_ITERATIONS, 500)):
        send_recv(msg)

    latencies = []
    for _ in range(REDIS_ITERATIONS):
        t0 = time.perf_counter_ns()
        send_recv(msg)
        latencies.append(time.perf_counter_ns() - t0)

    stop.set()
    sub.close()

    stats = compute_stats(latencies)
    print_stats("Redis Pub/Sub", msg_size, stats)
    save_results("redis_pubsub", msg_size, stats, iterations=REDIS_ITERATIONS)
    return stats


if __name__ == "__main__":
    for size in MESSAGE_SIZES:
        run(size)
