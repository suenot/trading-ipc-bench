"""Benchmark: Unix Domain Socket (raw UDS).

No HTTP or framing overhead — raw bytes over a local UNIX socket.
Typically 2-3× lower latency than TCP loopback on the same machine.
"""
import socket
import threading
import time
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from src.common import (
    make_message, recv_exact, compute_stats,
    save_results, print_stats,
    WARMUP_ITERATIONS, BENCH_ITERATIONS, MESSAGE_SIZES,
)

SOCK_PATH = "/tmp/trading_bench_uds.sock"


def _server(ready: threading.Event, stop: threading.Event, msg_size: int) -> None:
    if os.path.exists(SOCK_PATH):
        os.unlink(SOCK_PATH)
    srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    srv.bind(SOCK_PATH)
    srv.listen(1)
    srv.settimeout(1.0)
    ready.set()
    try:
        conn, _ = srv.accept()
        while not stop.is_set():
            try:
                data = recv_exact(conn.recv, msg_size)
                conn.sendall(data)
            except (socket.timeout, ConnectionError):
                break
    finally:
        srv.close()
        if os.path.exists(SOCK_PATH):
            os.unlink(SOCK_PATH)


def run(msg_size: int = 64) -> dict:
    msg = make_message(msg_size)
    ready, stop = threading.Event(), threading.Event()

    t = threading.Thread(target=_server, args=(ready, stop, msg_size), daemon=True)
    t.start()
    ready.wait(timeout=5)

    cli = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    cli.connect(SOCK_PATH)

    for _ in range(WARMUP_ITERATIONS):
        cli.sendall(msg)
        recv_exact(cli.recv, msg_size)

    latencies = []
    for _ in range(BENCH_ITERATIONS):
        t0 = time.perf_counter_ns()
        cli.sendall(msg)
        recv_exact(cli.recv, msg_size)
        latencies.append(time.perf_counter_ns() - t0)

    cli.close()
    stop.set()

    stats = compute_stats(latencies)
    print_stats("Unix Domain Socket", msg_size, stats)
    save_results("uds", msg_size, stats)
    return stats


if __name__ == "__main__":
    for size in MESSAGE_SIZES:
        run(size)
