"""Benchmark: ZeroMQ REQ/REP over IPC transport.

ZMQ IPC uses a Unix socket under the hood but adds ZMQ framing.
Requires: pip install pyzmq
"""
import threading
import time
import sys
from pathlib import Path

try:
    import zmq
except ImportError:
    print("pyzmq not installed. Run: pip install pyzmq")
    sys.exit(1)

sys.path.insert(0, str(Path(__file__).parent.parent))
from src.common import (
    make_message, compute_stats,
    save_results, print_stats,
    WARMUP_ITERATIONS, BENCH_ITERATIONS, MESSAGE_SIZES,
)

IPC_ADDR = "ipc:///tmp/trading_bench_zmq_ipc.ipc"


def _server(ready: threading.Event, stop: threading.Event) -> None:
    ctx = zmq.Context()
    sock = ctx.socket(zmq.REP)
    sock.bind(IPC_ADDR)
    sock.setsockopt(zmq.RCVTIMEO, 200)
    ready.set()
    while not stop.is_set():
        try:
            msg = sock.recv()
            sock.send(msg)
        except zmq.Again:
            pass
    sock.close()
    ctx.term()


def run(msg_size: int = 64) -> dict:
    msg = make_message(msg_size)
    ready, stop = threading.Event(), threading.Event()

    t = threading.Thread(target=_server, args=(ready, stop), daemon=True)
    t.start()
    ready.wait(timeout=5)

    ctx = zmq.Context()
    sock = ctx.socket(zmq.REQ)
    sock.connect(IPC_ADDR)

    for _ in range(WARMUP_ITERATIONS):
        sock.send(msg)
        sock.recv()

    latencies = []
    for _ in range(BENCH_ITERATIONS):
        t0 = time.perf_counter_ns()
        sock.send(msg)
        sock.recv()
        latencies.append(time.perf_counter_ns() - t0)

    sock.close()
    ctx.term()
    stop.set()

    stats = compute_stats(latencies)
    print_stats("ZeroMQ IPC", msg_size, stats)
    save_results("zmq_ipc", msg_size, stats)
    return stats


if __name__ == "__main__":
    for size in MESSAGE_SIZES:
        run(size)
