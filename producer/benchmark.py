import time
import json
import random
import uuid
from kafka import KafkaProducer
from threading import Thread

# Benchmarking properties
KAFKA_BROKER = "localhost:9092"
TOPIC = "rider-location"
RIDER_COUNTS = [10, 100, 1000, 10000] # For load simulation
DURATION_PER_TEST = 30 # seconds

producer = KafkaProducer(
    bootstrap_servers=[KAFKA_BROKER],
    value_serializer=lambda x: json.dumps(x).encode("utf-8")
)

def simulate_riders(num_riders, duration):
    print(f"--- Starting benchmark with {num_riders} concurrent riders ---")
    start_time = time.time()
    messages_sent = 0

    while time.time() - start_time < duration:
        for _ in range(num_riders):
            rider_id = f"bench_rider_{random.randint(1, num_riders)}"
            payload = {
                "rider_id": rider_id,
                "lat": 17.385 + random.uniform(-0.05, 0.05),
                "lng": 78.486 + random.uniform(-0.05, 0.05),
                "timestamp": time.time()
            }
            producer.send(TOPIC, value=payload)
            messages_sent += 1
            
        time.sleep(1) # Emit 1 ping per second per rider roughly

    end_time = time.time()
    elapsed = end_time - start_time
    throughput = messages_sent / elapsed
    print(f"Results for {num_riders} riders: Sent {messages_sent} events in {elapsed:.2f}s.")
    print(f"Throughput: {throughput:.2f} messages/sec\n")

if __name__ == "__main__":
    print("Starting Delivery Tracking Benchmarking Suite...\n")
    for payload in RIDER_COUNTS:
        simulate_riders(payload, DURATION_PER_TEST)
    print("Benchmarking Complete. Logs ready for graph generation (Phase 4).")
