"""Benchmark: Shared Memory (mmap) + semaphore signaling.

Uses multiprocessing.shared_memory for zero-copy data transfer between processes.
Signaling is done via multiprocessing.Event (OS semaphore).

This measures the absolute minimum IPC overhead: one syscall to write + one
semaphore post/wait cycle, no kernel copy of the payload.
"""
import time
import sys
from multiprocessing import Process, Event, shared_memory
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from src.common import (
    make_message, compute_stats,
    save_results, print_stats,
    WARMUP_ITERATIONS, BENCH_ITERATIONS, MESSAGE_SIZES,
)


def _server(
    shm_name: str,
    msg_size: int,
    srv_ready: object,
    cli_evt: object,
    srv_evt: object,
    stop_evt: object,
) -> None:
    shm = shared_memory.SharedMemory(name=shm_name)
    srv_ready.set()
    while not stop_evt.is_set():
        # Wait for client to write
        cli_evt.wait()
        cli_evt.clear()
        if stop_evt.is_set():
            break
        # Echo: copy request to response area (second half of shm)
        shm.buf[msg_size : msg_size * 2] = shm.buf[:msg_size]
        srv_evt.set()
    shm.close()


def run(msg_size: int = 64) -> dict:
    msg = make_message(msg_size)

    # Allocate shared memory: first half = request, second half = response
    shm = shared_memory.SharedMemory(create=True, size=msg_size * 2)
    shm.buf[:msg_size] = msg

    srv_ready = Event()
    cli_evt = Event()
    srv_evt = Event()
    stop_evt = Event()

    proc = Process(
        target=_server,
        args=(shm.name, msg_size, srv_ready, cli_evt, srv_evt, stop_evt),
        daemon=True,
    )
    proc.start()
    srv_ready.wait(timeout=5)

    def roundtrip() -> None:
        shm.buf[:msg_size] = msg
        cli_evt.set()
        srv_evt.wait()
        srv_evt.clear()

    for _ in range(WARMUP_ITERATIONS):
        roundtrip()

    latencies = []
    for _ in range(BENCH_ITERATIONS):
        t0 = time.perf_counter_ns()
        roundtrip()
        latencies.append(time.perf_counter_ns() - t0)

    stop_evt.set()
    cli_evt.set()  # unblock server if waiting
    proc.join(timeout=3)
    proc.terminate()

    shm.close()
    shm.unlink()

    stats = compute_stats(latencies)
    print_stats("Shared Memory", msg_size, stats)
    save_results("shm", msg_size, stats)
    return stats


if __name__ == "__main__":
    for size in MESSAGE_SIZES:
        run(size)
