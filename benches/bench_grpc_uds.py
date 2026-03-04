"""Benchmark: gRPC unary RPC over Unix Domain Socket.

Represents section 2.2 of the article — gRPC via UDS.
UDS bypasses the TCP stack (no handshake, no checksumming, no routing),
giving ~20% lower latency than gRPC TCP on small messages.

Requires: pip install grpcio grpcio-tools
"""
import time
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from src.common import (
    make_message, compute_stats,
    save_results, print_stats,
    WARMUP_ITERATIONS, BENCH_ITERATIONS, MESSAGE_SIZES,
)
from benches._grpc_common import load_grpc, start_server

SOCK_PATH = "/tmp/trading_bench_grpc.sock"
ADDRESS = f"unix://{SOCK_PATH}"


def run(msg_size: int = 64) -> dict:
    loaded = load_grpc()
    if loaded is None:
        return {}
    grpc, echo_pb2, echo_pb2_grpc = loaded

    server = start_server(grpc, echo_pb2, echo_pb2_grpc, ADDRESS)

    channel = grpc.insecure_channel(ADDRESS)
    stub = echo_pb2_grpc.EchoServiceStub(channel)

    msg = make_message(msg_size)
    req = echo_pb2.EchoRequest(data=msg)

    for _ in range(WARMUP_ITERATIONS):
        stub.Echo(req)

    latencies = []
    for _ in range(BENCH_ITERATIONS):
        t0 = time.perf_counter_ns()
        stub.Echo(req)
        latencies.append(time.perf_counter_ns() - t0)

    channel.close()
    server.stop(grace=0)

    stats = compute_stats(latencies)
    print_stats("gRPC UDS", msg_size, stats)
    save_results("grpc_uds", msg_size, stats)
    return stats


if __name__ == "__main__":
    for size in MESSAGE_SIZES:
        run(size)
