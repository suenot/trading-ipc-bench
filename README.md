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

## Example output (64-byte messages)

```
════════════════════════════════════════════════════════════════════════════════════
  Trading IPC Benchmark  |  msg size: 64 bytes
════════════════════════════════════════════════════════════════════════════════════
Transport                     p50 (μs)   p95 (μs)   p99 (μs)   p99.9 (μs)        msg/s
────────────────────────────────────────────────────────────────────────────────────
Shared Memory                      0.8        1.5        3.2         12.0    1,250,000
Unix Domain Socket                  5.2        8.1       15.3         45.0      192,000
Named Pipe (FIFO)                   6.8       12.4       22.1         58.0      147,000
NNG IPC                             7.5       13.0       25.0         60.0      133,000
ZeroMQ IPC                          8.5       14.2       28.0         65.0      117,000
TCP Loopback                       12.1       18.5       35.2         82.0       82,000
NNG TCP                            13.0       22.0       40.0         90.0       77,000
ZeroMQ TCP                         14.3       22.0       42.1         95.0       69,000
NATS                               35.0       55.0       90.0        200.0       28,000
WebSocket                          25.0       38.0       65.0        150.0       40,000
Redis Pub/Sub                      45.0       72.0      120.0        280.0       22,000
Redis Streams                      55.0       90.0      145.0        320.0       18,000
gRPC UDS                          102.0      145.0      210.0        450.0        9,800
gRPC TCP                          127.0      180.0      260.0        520.0        7,900
HTTP REST                         180.0      260.0      380.0        800.0        5,500
Kafka                           2,500.0    4,000.0    6,000.0     12,000.0          400
────────────────────────────────────────────────────────────────────────────────────
```

> ⚠️ Numbers above are illustrative. Run on your own hardware — actual results depend on CPU, OS, and kernel version.

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
