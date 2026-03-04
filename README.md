# trading-ipc-bench

Бенчмарк различных технологий межпроцессной и сетевой коммуникации для алготрейдинговых систем.

Измеряем round-trip latency (RTT) и throughput для:

| # | Технология | Описание |
|---|---|---|
| 1 | **TCP socket** | Базовый TCP loopback (baseline) |
| 2 | **Unix Domain Socket (UDS)** | Raw UDS без фреймворков |
| 3 | **gRPC TCP** | gRPC bidirectional stream через TCP |
| 4 | **gRPC UDS** | gRPC bidirectional stream через Unix socket |
| 5 | **Redis Pub/Sub** | Publish → Subscribe round-trip |
| 6 | **WebSocket** | ws:// loopback |
| 7 | **ZeroMQ IPC** | ZMQ REQ/REP через IPC transport |
| 8 | **ZeroMQ TCP** | ZMQ REQ/REP через TCP |
| 9 | **Shared Memory** | mmap + eventfd signaling |
| 10 | **Named Pipe (FIFO)** | mkfifo round-trip |

## Что измеряем

- **RTT latency** — round-trip: отправка сообщения → получение ответа. Измеряем min, median (p50), p95, p99, p99.9, max.
- **Throughput** — сообщений в секунду при sustained load.
- **Размер сообщения** — фиксированный: 64 bytes (типичный trading signal), 256 bytes (order message), 1024 bytes (market data snapshot).

## Быстрый старт

```bash
# Установка зависимостей
pip install -r requirements.txt

# Запуск всех бенчмарков
python run_all.py

# Запуск конкретного бенчмарка
python benches/bench_tcp.py
python benches/bench_uds.py
python benches/bench_websocket.py
python benches/bench_redis_pubsub.py
python benches/bench_zmq_ipc.py
python benches/bench_zmq_tcp.py
python benches/bench_shm.py
python benches/bench_pipe.py

# Генерация отчёта
python report.py
```

## Результаты

После запуска `run_all.py` результаты сохраняются в `results/` в JSON-формате. `report.py` генерирует сводную таблицу и ASCII-гистограмму.

Пример вывода:
```
=== Trading IPC Benchmark Results ===
Message size: 64 bytes, Iterations: 100000

Transport          p50 (μs)  p95 (μs)  p99 (μs)  p99.9 (μs)  throughput (msg/s)
─────────────────────────────────────────────────────────────────────────────────
Shared Memory         0.8       1.5       3.2        12.0       1,250,000
Unix Domain Socket    5.2       8.1      15.3        45.0         192,000
Named Pipe            6.8      12.4      22.1        58.0         147,000
ZeroMQ IPC            8.5      14.2      28.0        65.0         117,000
TCP Loopback         12.1      18.5      35.2        82.0          82,000
ZeroMQ TCP           14.3      22.0      42.1        95.0          69,000
WebSocket            25.0      38.0      65.0       150.0          40,000
Redis Pub/Sub        45.0      72.0     120.0       280.0          22,000
```

> ⚠️ Реальные цифры зависят от hardware, OS, kernel version и настроек. Запускайте на своём железе!

## Методология

1. Warmup: 1000 итераций отбрасываются
2. Measurement: 100,000 round-trips
3. Timing: `time.perf_counter_ns()` (наносекундное разрешение)
4. Pinning: по возможности, server и client на разных CPU cores
5. Каждый тест запускается 3 раза, берётся медиана

## Структура проекта

```
trading-ipc-bench/
├── README.md
├── requirements.txt
├── run_all.py          # запуск всех бенчмарков
├── report.py           # генерация отчёта
├── src/
│   └── common.py       # общие утилиты (timing, stats, message gen)
├── benches/
│   ├── bench_tcp.py
│   ├── bench_uds.py
│   ├── bench_websocket.py
│   ├── bench_redis_pubsub.py
│   ├── bench_zmq_ipc.py
│   ├── bench_zmq_tcp.py
│   ├── bench_shm.py
│   └── bench_pipe.py
└── results/            # JSON-результаты (генерируются автоматически)
```

## Зависимости

- Python 3.10+
- pyzmq
- websockets
- redis
- numpy

## Контекст

Этот бенчмарк — companion к статье [Коммуникация данных в алготрейдинговых системах](./data-communication-algotrading.md).

## License

MIT
