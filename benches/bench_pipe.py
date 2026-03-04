"""Benchmark: Named Pipe (FIFO).

Two FIFOs are used: req (client→server) and resp (server→client).
Both client and server open their ends in the correct order to avoid deadlock.
"""
import os
import threading
import time
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from src.common import (
    make_message, compute_stats,
    save_results, print_stats,
    WARMUP_ITERATIONS, BENCH_ITERATIONS, MESSAGE_SIZES,
)

REQ_PIPE = "/tmp/trading_bench_req.fifo"
RESP_PIPE = "/tmp/trading_bench_resp.fifo"


def _recv_pipe(fd: int, n: int) -> bytes:
    buf = bytearray()
    while len(buf) < n:
        chunk = os.read(fd, n - len(buf))
        if not chunk:
            raise ConnectionError("Pipe closed")
        buf += chunk
    return bytes(buf)


def _server(ready: threading.Event, stop: threading.Event, msg_size: int) -> None:
    # Open req for reading — blocks until client opens for writing
    req_fd = os.open(REQ_PIPE, os.O_RDONLY)
    # Open resp for writing — blocks until client opens for reading
    resp_fd = os.open(RESP_PIPE, os.O_WRONLY)
    ready.set()
    try:
        while not stop.is_set():
            try:
                data = _recv_pipe(req_fd, msg_size)
                os.write(resp_fd, data)
            except (ConnectionError, OSError):
                break
    finally:
        os.close(req_fd)
        os.close(resp_fd)


def run(msg_size: int = 64) -> dict:
    msg = make_message(msg_size)

    # (Re)create FIFOs
    for path in (REQ_PIPE, RESP_PIPE):
        if os.path.exists(path):
            os.unlink(path)
        os.mkfifo(path)

    ready, stop = threading.Event(), threading.Event()
    t = threading.Thread(target=_server, args=(ready, stop, msg_size), daemon=True)
    t.start()

    # Open req for writing — unblocks server's O_RDONLY open
    req_fd = os.open(REQ_PIPE, os.O_WRONLY)
    # Open resp for reading — unblocks server's O_WRONLY open
    resp_fd = os.open(RESP_PIPE, os.O_RDONLY)
    ready.wait(timeout=5)

    for _ in range(WARMUP_ITERATIONS):
        os.write(req_fd, msg)
        _recv_pipe(resp_fd, msg_size)

    latencies = []
    for _ in range(BENCH_ITERATIONS):
        t0 = time.perf_counter_ns()
        os.write(req_fd, msg)
        _recv_pipe(resp_fd, msg_size)
        latencies.append(time.perf_counter_ns() - t0)

    os.close(req_fd)
    os.close(resp_fd)
    stop.set()

    for path in (REQ_PIPE, RESP_PIPE):
        if os.path.exists(path):
            os.unlink(path)

    stats = compute_stats(latencies)
    print_stats("Named Pipe (FIFO)", msg_size, stats)
    save_results("pipe", msg_size, stats)
    return stats


if __name__ == "__main__":
    for size in MESSAGE_SIZES:
        run(size)
