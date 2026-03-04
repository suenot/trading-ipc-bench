# trading-ipc-bench

Benchmarks for inter-process and network communication technologies used in algorithmic trading systems.

Measures round-trip latency (RTT) and throughput for:

| # | Transport | Description |
|---|---|---|
| 1 | **TCP socket** | TCP loopback baseline |
| 2 | **Unix Domain Socket (UDS)** | Raw UDS, no framework |
| 3 | **Named Pipe (FIFO)** | `mkfifo` round-trip |
| 4 | **ZeroMQ IPC** | ZMQ REQ/REP over IPC transport |
| 5 | **ZeroMQ TCP** | ZMQ REQ/REP over TCP |
| 6 | **WebSocket** | `ws://` loopback |
| 7 | **Redis Pub/Sub** | Publish → Subscribe round-trip |
| 8 | **Shared Memory** | `mmap` + semaphore signaling |

## What we measure

- **RTT latency** — round-trip: send message → receive response. Reports min, p50, p95, p99, p99.9, max.
- **Throughput** — messages per second under sustained load.
- **Message sizes** — 64 bytes (typical trading signal), 256 bytes (order message), 1024 bytes (market data snapshot).

## Quick start

```bash
# Install dependencies
pip install -r requirements.txt

# Run all benchmarks (sequential, results saved to results/)
python run_all.py

# Run a single benchmark
python benches/bench_tcp.py
python benches/bench_uds.py
python benches/bench_pipe.py
python benches/bench_zmq_ipc.py
python benches/bench_zmq_tcp.py
python benches/bench_websocket.py
python benches/bench_redis_pubsub.py  # requires Redis on 127.0.0.1:6379
python benches/bench_shm.py

# Generate summary report
python report.py
```

## Example output

```
════════════════════════════════════════════════════════════════════════════════
  Trading IPC Benchmark  |  msg size: 64 bytes  |  n=100,000
════════════════════════════════════════════════════════════════════════════════
Transport                  p50 (μs)   p95 (μs)   p99 (μs)   p99.9 (μs)        msg/s
────────────────────────────────────────────────────────────────────────────────
Shared Memory                   0.8        1.5        3.2         12.0    1,250,000
Unix Domain Socket               5.2        8.1       15.3         45.0      192,000
Named Pipe (FIFO)                6.8       12.4       22.1         58.0      147,000
ZeroMQ IPC                       8.5       14.2       28.0         65.0      117,000
TCP Loopback                    12.1       18.5       35.2         82.0       82,000
ZeroMQ TCP                      14.3       22.0       42.1         95.0       69,000
WebSocket                       25.0       38.0       65.0        150.0       40,000
Redis Pub/Sub                   45.0       72.0      120.0        280.0       22,000
────────────────────────────────────────────────────────────────────────────────
```

> ⚠️ Real numbers depend on hardware, OS, kernel version, and tuning. Run on your own machine!

## Methodology

1. **Warmup:** 1,000 iterations discarded before measurement
2. **Measurement:** 100,000 round-trips (10,000 for Redis)
3. **Timing:** `time.perf_counter_ns()` — nanosecond resolution
4. **Architecture:** server thread/process + client in the same run; each transport in a separate subprocess for clean state

## Project structure

```
trading-ipc-bench/
├── README.md
├── requirements.txt
├── run_all.py          # run all benchmarks sequentially
├── report.py           # generate summary table from results/
├── src/
│   └── common.py       # shared utilities: timing, stats, message generation
├── benches/
│   ├── bench_tcp.py
│   ├── bench_uds.py
│   ├── bench_pipe.py
│   ├── bench_zmq_ipc.py
│   ├── bench_zmq_tcp.py
│   ├── bench_websocket.py
│   ├── bench_redis_pubsub.py
│   └── bench_shm.py
└── results/            # JSON results (auto-generated)
```

## Dependencies

- Python 3.10+
- `pyzmq` — ZeroMQ bindings
- `websockets` — async WebSocket library
- `redis` — Redis client
- `numpy` — (optional, used by report)

## Context

Companion benchmark for the article [Data Communication in Algo Trading Systems](https://marketmaker.cc/en/blog/post/data-communication-algotrading).

## License

MIT
