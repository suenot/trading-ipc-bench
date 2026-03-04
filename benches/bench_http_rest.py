"""Benchmark: HTTP REST round-trip (loopback).

Represents section 1.1 of the article — REST API.
An aiohttp server echoes POST requests. This measures the full HTTP overhead:
TCP connection reuse (keep-alive), HTTP/1.1 framing, headers, request parsing.

This is intentionally the slowest transport in the benchmark — it shows
the cost of the HTTP abstraction layer over raw TCP.

Requires: pip install aiohttp
"""
import asyncio
import threading
import time
import sys
from pathlib import Path

try:
    from aiohttp import web, ClientSession, TCPConnector
except ImportError:
    print("aiohttp not installed. Run: pip install aiohttp")
    sys.exit(1)

sys.path.insert(0, str(Path(__file__).parent.parent))
from src.common import (
    make_message, compute_stats,
    save_results, print_stats,
    WARMUP_ITERATIONS, BENCH_ITERATIONS, MESSAGE_SIZES,
)

HOST = "127.0.0.1"
PORT = 17815
URL = f"http://{HOST}:{PORT}/echo"

# HTTP is much slower than raw sockets — cap iterations for reasonable runtime
HTTP_ITERATIONS = min(BENCH_ITERATIONS, 20_000)


async def _echo_handler(request: web.Request) -> web.Response:
    body = await request.read()
    return web.Response(body=body, content_type="application/octet-stream")


def _run_server_thread(ready: threading.Event, stop: threading.Event) -> None:
    async def serve():
        app = web.Application()
        app.router.add_post("/echo", _echo_handler)
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, HOST, PORT)
        await site.start()
        ready.set()
        while not stop.is_set():
            await asyncio.sleep(0.05)
        await runner.cleanup()

    asyncio.run(serve())


async def _bench(msg: bytes, n_warmup: int, n_bench: int) -> list:
    # Use a single persistent TCP connection (keep-alive) for fair comparison
    connector = TCPConnector(limit=1, force_close=False)
    async with ClientSession(connector=connector) as session:
        for _ in range(n_warmup):
            async with session.post(URL, data=msg) as resp:
                await resp.read()

        latencies = []
        for _ in range(n_bench):
            t0 = time.perf_counter_ns()
            async with session.post(URL, data=msg) as resp:
                await resp.read()
            latencies.append(time.perf_counter_ns() - t0)
        return latencies


def run(msg_size: int = 64) -> dict:
    msg = make_message(msg_size)
    ready, stop = threading.Event(), threading.Event()

    t = threading.Thread(target=_run_server_thread, args=(ready, stop), daemon=True)
    t.start()
    ready.wait(timeout=5)

    latencies = asyncio.run(_bench(msg, min(WARMUP_ITERATIONS, 200), HTTP_ITERATIONS))
    stop.set()

    stats = compute_stats(latencies)
    print_stats("HTTP REST", msg_size, stats)
    save_results("http_rest", msg_size, stats, iterations=HTTP_ITERATIONS)
    return stats


if __name__ == "__main__":
    for size in MESSAGE_SIZES:
        run(size)
