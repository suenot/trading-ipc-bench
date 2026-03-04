"""Benchmark: WebSocket (ws:// loopback).

The server echoes every message back. Client sends binary frames.
Uses the `websockets` async library.
Requires: pip install websockets
"""
import asyncio
import threading
import time
import sys
from pathlib import Path

try:
    import websockets
except ImportError:
    print("websockets not installed. Run: pip install websockets")
    sys.exit(1)

sys.path.insert(0, str(Path(__file__).parent.parent))
from src.common import (
    make_message, compute_stats,
    save_results, print_stats,
    WARMUP_ITERATIONS, BENCH_ITERATIONS, MESSAGE_SIZES,
)

HOST = "127.0.0.1"
PORT = 17803


def _run_server_thread(ready: threading.Event, stop: threading.Event) -> None:
    async def handler(ws):
        async for msg in ws:
            await ws.send(msg)

    async def serve():
        async with websockets.serve(handler, HOST, PORT):
            ready.set()
            while not stop.is_set():
                await asyncio.sleep(0.05)

    asyncio.run(serve())


async def _bench(msg: bytes, n_warmup: int, n_bench: int) -> list:
    uri = f"ws://{HOST}:{PORT}"
    async with websockets.connect(uri, max_size=None) as ws:
        for _ in range(n_warmup):
            await ws.send(msg)
            await ws.recv()

        latencies = []
        for _ in range(n_bench):
            t0 = time.perf_counter_ns()
            await ws.send(msg)
            await ws.recv()
            latencies.append(time.perf_counter_ns() - t0)
        return latencies


def run(msg_size: int = 64) -> dict:
    msg = make_message(msg_size)
    ready, stop = threading.Event(), threading.Event()

    t = threading.Thread(target=_run_server_thread, args=(ready, stop), daemon=True)
    t.start()
    ready.wait(timeout=5)

    latencies = asyncio.run(_bench(msg, WARMUP_ITERATIONS, BENCH_ITERATIONS))
    stop.set()

    stats = compute_stats(latencies)
    print_stats("WebSocket", msg_size, stats)
    save_results("websocket", msg_size, stats)
    return stats


if __name__ == "__main__":
    for size in MESSAGE_SIZES:
        run(size)
