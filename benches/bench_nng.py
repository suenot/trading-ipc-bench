"""Benchmark: NNG (nanomsg-next-generation) REQ/REP.

Represents section 3.5 of the article — nanomsg/NNG.
NNG is the successor to nanomsg and ZeroMQ alternative, with cleaner API
and better latency on small messages. Uses REQ0/REP0 pattern (request/reply).

Benchmarks both IPC and TCP transports.
Requires: pip install pynng
"""
import threading
import time
import sys
from pathlib import Path

try:
    import pynng
except ImportError:
    print("pynng not installed. Run: pip install pynng")
    sys.exit(1)

sys.path.insert(0, str(Path(__file__).parent.parent))
from src.common import (
    make_message, compute_stats,
    save_results, print_stats,
    WARMUP_ITERATIONS, BENCH_ITERATIONS, MESSAGE_SIZES,
)

IPC_ADDR = "ipc:///tmp/trading_bench_nng.ipc"
TCP_ADDR = "tcp://127.0.0.1:17812"


def _server(addr: str, ready: threading.Event, stop: threading.Event) -> None:
    with pynng.Rep0() as sock:
        sock.listen(addr)
        sock.recv_timeout = 200
        ready.set()
        while not stop.is_set():
            try:
                msg = sock.recv()
                sock.send(msg)
            except pynng.Timeout:
                pass


def _run(addr: str, name: str, msg_size: int) -> dict:
    msg = make_message(msg_size)
    ready, stop = threading.Event(), threading.Event()

    t = threading.Thread(target=_server, args=(addr, ready, stop), daemon=True)
    t.start()
    ready.wait(timeout=5)

    with pynng.Req0() as sock:
        sock.dial(addr)

        for _ in range(WARMUP_ITERATIONS):
            sock.send(msg)
            sock.recv()

        latencies = []
        for _ in range(BENCH_ITERATIONS):
            t0 = time.perf_counter_ns()
            sock.send(msg)
            sock.recv()
            latencies.append(time.perf_counter_ns() - t0)

    stop.set()

    stats = compute_stats(latencies)
    print_stats(name, msg_size, stats)
    save_results(name.lower().replace(" ", "_"), msg_size, stats)
    return stats


def run(msg_size: int = 64) -> dict:
    ipc = _run(IPC_ADDR, "NNG IPC", msg_size)
    tcp = _run(TCP_ADDR, "NNG TCP", msg_size)
    return {"ipc": ipc, "tcp": tcp}


if __name__ == "__main__":
    for size in MESSAGE_SIZES:
        run(size)
