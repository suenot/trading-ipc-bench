# trading-ipc-bench

Benchmarks for inter-process and network communication technologies used in algorithmic trading systems.

Measures **round-trip latency** (p50 / p95 / p99 / p99.9) and **throughput** for every transport discussed in the article [Data Communication in Algo Trading Systems](https://marketmaker.cc/en/blog/post/data-communication-algotrading).

## Transports

| # | Transport | Article section | Notes |
|---|---|---|---|
| 1 | **Shared Memory** | §2.3 | `mmap` + semaphore signaling |
| 2 | **Named Pipe (FIFO)** | §2 | `mkfifo` two-pipe round-trip |
| 3 | **Unix Domain Socket** | §2.2 | Raw UDS, no framework |
| 4 | **NNG IPC** | §3.5 | nanomsg-next-generation over IPC |
| 5 | **NNG TCP** | §3.5 | nanomsg-next-generation over TCP |
| 6 | **ZeroMQ IPC** | §3.5 | ZMQ REQ/REP over `ipc://` |
| 7 | **TCP socket** | §2 | TCP loopback baseline |
| 8 | **ZeroMQ TCP** | §3.5 | ZMQ REQ/REP over TCP |
| 9 | **gRPC UDS** | §2.2 | gRPC unary over Unix socket |
| 10 | **gRPC TCP** | §2.1 | gRPC unary over TCP |
| 11 | **WebSocket** | §1.2 | `ws://` loopback |
| 12 | **HTTP REST** | §1.1 | aiohttp POST, keep-alive |
| 13 | **Redis Pub/Sub** | §3.3 | Publish → Subscribe RTT *(needs Redis)* |
| 14 | **Redis Streams** | §3.3 | XADD → XREAD RTT *(needs Redis)* |
| 15 | **NATS** | §3.4 | request/reply *(needs nats-server)* |
| 16 | **Kafka** | §3.2 | produce → consume RTT *(needs Kafka)* |

## Quick start

```bash
git clone https://github.com/suenot/trading-ipc-bench
cd trading-ipc-bench

# Install core dependencies
pip install -r requirements.txt

# Run all core benchmarks (no external server needed)
python run_all.py

# Also run Redis / NATS / Kafka (start servers first — see below)
python run_all.py --optional

# Run a single benchmark
python benches/bench_shm.py
python benches/bench_grpc_tcp.py
python benches/bench_http_rest.py

# Print summary table from saved results
python report.py
```

## Optional benchmarks setup

| Benchmark | How to start the server |
|---|---|
| `bench_redis_pubsub.py` / `bench_redis_streams.py` | `brew install redis && redis-server` |
| `bench_nats.py` | `brew install nats-server && nats-server` |
| `bench_kafka.py` | `docker run -d -p 9092:9092 apache/kafka:3.7.0` |

## Results

<!-- BENCH_RESULTS_START -->
_No results yet — run `python run_all.py` first._
<!-- BENCH_RESULTS_END -->

> Results above are recorded on `ubuntu-latest` (GitHub Actions). Actual latency depends on CPU, OS, and kernel version — run locally to get your own numbers.

## Methodology

1. **Warmup:** 1,000 iterations discarded before measurement
2. **Measurement:** 100,000 round-trips (10,000 for Redis/NATS, 1,000 for Kafka)
3. **Timing:** `time.perf_counter_ns()` — nanosecond resolution
4. **Isolation:** each transport runs in its own subprocess for clean state
5. **Message sizes:** 64 B / 256 B / 1024 B (trading signal / order / market snapshot)

## Project structure

```
trading-ipc-bench/
├── README.md
├── requirements.txt
├── run_all.py                  # run all benchmarks, print summary
├── report.py                   # pretty-print saved results
├── src/
│   └── common.py               # shared: timing, stats, message generation
├── benches/
│   ├── _grpc_common.py         # shared gRPC setup (proto compilation, server)
│   ├── proto/
│   │   └── echo.proto          # protobuf definition (stubs auto-generated)
│   ├── bench_shm.py            # Shared Memory
│   ├── bench_pipe.py           # Named Pipe (FIFO)
│   ├── bench_uds.py            # Unix Domain Socket
│   ├── bench_tcp.py            # TCP socket
│   ├── bench_nng.py            # NNG IPC + TCP
│   ├── bench_zmq_ipc.py        # ZeroMQ IPC
│   ├── bench_zmq_tcp.py        # ZeroMQ TCP
│   ├── bench_grpc_uds.py       # gRPC over UDS
│   ├── bench_grpc_tcp.py       # gRPC over TCP
│   ├── bench_websocket.py      # WebSocket
│   ├── bench_http_rest.py      # HTTP REST (aiohttp)
│   ├── bench_redis_pubsub.py   # Redis Pub/Sub
│   ├── bench_redis_streams.py  # Redis Streams
│   ├── bench_nats.py           # NATS
│   └── bench_kafka.py          # Kafka
└── results/                    # JSON results (auto-generated)
```

## Dependencies

```
# Core (pip install -r requirements.txt)
pyzmq, websockets, redis, aiohttp, grpcio, grpcio-tools, pynng

# Optional
nats-py        # pip install nats-py
kafka-python   # pip install kafka-python
```

## Context

Companion benchmark for the article [Data Communication in Algo Trading Systems](https://marketmaker.cc/en/blog/post/data-communication-algotrading).

## License

MIT
