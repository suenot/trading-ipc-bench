"""Benchmark: TCP loopback (baseline).

Server and client run in the same process using threads.
TCP_NODELAY is set to disable Nagle's algorithm for fair comparison.
"""
import socket
import threading
import time
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from src.common import (
    make_message, recv_exact, compute_stats,
    save_results, print_stats,
    WARMUP_ITERATIONS, BENCH_ITERATIONS, MESSAGE_SIZES,
)

HOST = "127.0.0.1"
PORT = 17801


def _server(ready: threading.Event, stop: threading.Event, msg_size: int) -> None:
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((HOST, PORT))
    srv.listen(1)
    srv.settimeout(1.0)
    ready.set()
    try:
        conn, _ = srv.accept()
        conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        while not stop.is_set():
            try:
                data = recv_exact(conn.recv, msg_size)
                conn.sendall(data)
            except (socket.timeout, ConnectionError):
                break
    finally:
        srv.close()


def run(msg_size: int = 64) -> dict:
    msg = make_message(msg_size)
    ready, stop = threading.Event(), threading.Event()

    t = threading.Thread(target=_server, args=(ready, stop, msg_size), daemon=True)
    t.start()
    ready.wait(timeout=5)

    cli = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    cli.connect((HOST, PORT))
    cli.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

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
    print_stats("TCP Loopback", msg_size, stats)
    save_results("tcp", msg_size, stats)
    return stats


if __name__ == "__main__":
    for size in MESSAGE_SIZES:
        run(size)
