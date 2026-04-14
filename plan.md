# Research Implementation Plan: Delivery Tracking System

## Phase 1: Stream Processing Foundation
- [x] Set up PySpark Structured Streaming to consume from Kafka (`rider-location` topic).
- [x] Implement Uber H3 Spatial Indexing mapping lat/lng coordinates to H3 Hexagons.
- [ ] Implement Windowed Aggregations (Average speed, rider density per hexagon) and publish to `traffic-density` Kafka topic.

## Phase 2: Geofencing & Complex Event Processing
- [ ] Implement dynamic geofencing (point-in-polygon checks for restricted/high-traffic zones).
- [ ] Implement stateful processing to detect basic anomalies (e.g., speed > 150km/h) and publish to `rider-alerts` topic.

## Phase 3: Machine Learning & Predictive Edge
- [x] Generate/Extract a training dataset from historical data.
- [x] Train offline ML models for ETA Prediction (Regression) and Fraud/Ghost Rider Detection (Isolation Forest).
- [x] Deploy ML models directly inside the PySpark streaming pipeline for real-time inference.
- [x] Emit inferences to a new `rider-predictions` Kafka topic.

## Phase 4: Frontend Upgrades & Benchmarking
- [ ] Update Node.js backend to consume new topics (`traffic-density`, `rider-alerts`, `rider-predictions`) and broadcast over WebSockets.
- [ ] Update Leaflet.js frontend to visualize H3 density heatmaps, live AI ETAs, and anomaly warning pulses.
- [ ] Conduct benchmarking (End-to-End Latency, Throughput) under varying simulated loads (10 to 10,000 riders) and graph the results for the paper.
