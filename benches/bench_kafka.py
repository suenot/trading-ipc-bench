"""Benchmark: Kafka produce/consume round-trip.

Represents section 3.2 of the article — Apache Kafka.
Kafka is NOT designed for low-latency IPC (typical latency 2–15 ms),
but is the industry standard for high-throughput event streaming pipelines.
This benchmark quantifies that latency cost.

Pattern: client produces to "bench.req" → server consumes + produces to "bench.resp"
         → client consumes from "bench.resp".

Requires a running Kafka broker on 127.0.0.1:9092.
  docker run -d -p 9092:9092 apache/kafka:3.7.0
Requires: pip install kafka-python
"""
import threading
import time
import sys
import uuid
from pathlib import Path

try:
    from kafka import KafkaProducer, KafkaConsumer
    from kafka.errors import NoBrokersAvailable
except ImportError:
    print("kafka-python not installed. Run: pip install kafka-python")
    sys.exit(1)

sys.path.insert(0, str(Path(__file__).parent.parent))
from src.common import (
    make_message, compute_stats,
    save_results, print_stats,
    WARMUP_ITERATIONS, BENCH_ITERATIONS, MESSAGE_SIZES,
)

BROKER = "127.0.0.1:9092"
REQ_TOPIC = "bench-req"
RESP_TOPIC = "bench-resp"

# Kafka round-trip is 2–15 ms — 1000 iterations is sufficient for statistics
KAFKA_ITERATIONS = min(BENCH_ITERATIONS, 1_000)
KAFKA_WARMUP = min(WARMUP_ITERATIONS, 50)


def _check_kafka() -> bool:
    try:
        p = KafkaProducer(bootstrap_servers=BROKER, request_timeout_ms=3000)
        p.close()
        return True
    except NoBrokersAvailable:
        print(f"  Kafka broker not available at {BROKER}.")
        print("  Start it with: docker run -d -p 9092:9092 apache/kafka:3.7.0")
        return False
    except Exception as e:
        print(f"  Kafka not available: {e}")
        return False


def _server(ready: threading.Event, stop: threading.Event) -> None:
    consumer = KafkaConsumer(
        REQ_TOPIC,
        bootstrap_servers=BROKER,
        group_id=f"bench-server-{uuid.uuid4().hex[:8]}",
        auto_offset_reset="latest",
        enable_auto_commit=True,
        consumer_timeout_ms=200,
    )
    producer = KafkaProducer(bootstrap_servers=BROKER)
    ready.set()
    while not stop.is_set():
        for msg in consumer:
            producer.send(RESP_TOPIC, msg.value)
            producer.flush()
            if stop.is_set():
                break
    consumer.close()
    producer.close()


def run(msg_size: int = 64) -> dict:
    if not _check_kafka():
        return {}

    msg = make_message(msg_size)
    ready, stop = threading.Event(), threading.Event()

    t = threading.Thread(target=_server, args=(ready, stop), daemon=True)
    t.start()
    ready.wait(timeout=10)
    time.sleep(1.0)  # let consumer join the group

    producer = KafkaProducer(bootstrap_servers=BROKER)
    consumer = KafkaConsumer(
        RESP_TOPIC,
        bootstrap_servers=BROKER,
        group_id=f"bench-client-{uuid.uuid4().hex[:8]}",
        auto_offset_reset="latest",
        enable_auto_commit=True,
        consumer_timeout_ms=10_000,
    )
    time.sleep(0.5)  # let consumer join

    def send_recv(data: bytes) -> None:
        producer.send(REQ_TOPIC, data)
        producer.flush()
        for _ in consumer:
            return  # got one message

    for _ in range(KAFKA_WARMUP):
        send_recv(msg)

    latencies = []
    for _ in range(KAFKA_ITERATIONS):
        t0 = time.perf_counter_ns()
        send_recv(msg)
        latencies.append(time.perf_counter_ns() - t0)

    stop.set()
    consumer.close()
    producer.close()

    stats = compute_stats(latencies)
    print_stats("Kafka", msg_size, stats)
    save_results("kafka", msg_size, stats, iterations=KAFKA_ITERATIONS)
    return stats


if __name__ == "__main__":
    for size in MESSAGE_SIZES:
        run(size)
