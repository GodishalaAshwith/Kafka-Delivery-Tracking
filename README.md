# 🚀 Real-Time Delivery Rider Tracking System

An end-to-end, event-driven architecture simulating a real-world delivery tracking system (like Swiggy, Zomato, or UberEats). Built with **Node.js, Apache Kafka, Python, WebSockets, MongoDB, and Leaflet.js**.

## 🧠 System Architecture

```text
[ Rider Simulator (Python) ] 
   │
   ├─ Fetch Real-world Route (OSRM API)
   ├─ Step through coordinates
   ↓
[ Kafka Producer ] 
   │
   ├─ Topic: rider-location
   ↓
[ Apache Kafka Broker (KRaft) ]
   │
   ↓
[ Kafka Consumer (Node.js) ]
   │
   ├─ Save data to MongoDB (Mongoose)
   ├─ Broadcast updates via WebSockets
   ↓
[ Frontend Dashboard (HTML/JS + Leaflet) ]
   │
   └─ Listen to WebSockets & Animates 🛵 Markers live on Map
```

---

## 📦 Core Features Implemented

- **Highly Scalable Event Streaming (Apache Kafka)**: Ingests thousands of GPS coordinates asynchronously across `rider-location`, `rider-predictions`, `traffic-density`, and `rider-alerts` topics.
- **PySpark Structured Streaming**: Replaces slow database queries by processing telemetry natively in the streaming layer over a 10-second sliding window.
- **Machine Learning at the Edge**: Scikit-Learn models (`RandomForestRegressor` and `IsolationForest`) are embedded directly into PySpark UDFs to calculate real-time AI ETAs and detect "Ghost Rider" GPS fraud instantly.
- **Spatial Heatmaps (Uber H3 Indexing)**: Replaces scattered UI dots with dynamic, color-coded hexagonal aggregations (Green/Orange/Red) representing clustered traffic density.
- **Dynamic Geofencing**: Real-time bounded polygon checks alerting when riders enter restricted zones (e.g., HITEC City).
- **Real-Time WebSockets**: Frontend subscribes via Socket.io to receive live updates with sub-second latency from the Node.js consumer.
- **Custom UI Integration**: Maps powered by Leaflet and OpenStreetMap native tiles, customized with SVG drop-shadow rider tokens that pulse red on fraud detection.

---

## 📁 Project Structure

```text
delivery-tracking/
│
├── backend/
│   ├── package.json         # Express, KafkaJS, Mongoose, Socket.io
│   └── server.js            # Consumer + WebSocket Server + MongoDB schemas
│
├── producer/
│   ├── requirements.txt     
│   ├── simulator.py         # Advanced OSRM route coordinate simulator
│   └── benchmark.py         # Kafka throughput load-stress generator (10k+ riders)
│
├── spark/
│   ├── train_models.py      # Scikit-Learn Offline Training (RandomForest/IsolationForest)
│   ├── stream_processor.py  # PySpark Streaming Engine (H3, ML Inference, Windowing)
│   └── models/              # Pre-trained .joblib intelligence files
│
└── frontend/
    ├── index.html           # Leaflet.js Interactive frontend mapping & AI Status
    └── mobile-tracker.html  # HTML5 Geolocation API interface for real 5G tracking 
```

---

## ⚙️ Prerequisites (Windows Setup)
Make sure you have installed:
1. **Java Development Kit (JDK 11+)** - Required by Kafka.
2. **Apache Kafka** - Downloaded and configured locally in `C:\kafka`.
3. **Node.js (v16+)** - For the backend.
4. **Python (3.x)** - For the simulator.
5. **MongoDB** - Running locally on port `27017` or configured via Atlas.

---

## 🏃‍♂️ Step-by-Step Running Guide

### 1. Start Apache Kafka (KRaft mode)
*Open a Git Bash terminal.* Format storage (first time only) and start the server:
```bash
cd /c/kafka
# Format storage (replace <uuid> if first time run: ./bin/windows/kafka-storage.bat random-uuid)
# ./bin/windows/kafka-storage.bat format -t <uuid> -c ./config/server.properties
./bin/windows/kafka-server-start.bat ./config/server.properties
```

### 1.5 Create Kafka Topics (First time only)
*Open a new Git Bash terminal while Kafka is running.* Create the required topic(s):
```bash
cd /c/kafka

# Core topic used by producer and backend
./bin/windows/kafka-topics.bat --create --topic rider-location --bootstrap-server localhost:9092 --partitions 1 --replication-factor 1

# Optional research topics for upcoming analytics features
./bin/windows/kafka-topics.bat --create --topic traffic-density --bootstrap-server localhost:9092 --partitions 1 --replication-factor 1
./bin/windows/kafka-topics.bat --create --topic rider-alerts --bootstrap-server localhost:9092 --partitions 1 --replication-factor 1
./bin/windows/kafka-topics.bat --create --topic rider-predictions --bootstrap-server localhost:9092 --partitions 1 --replication-factor 1

# Verify topics
./bin/windows/kafka-topics.bat --list --bootstrap-server localhost:9092
```

If a topic already exists, Kafka will report it. You can safely continue.

### 2. Prepare the AI Models
*Open a Git Bash terminal.* Train the Machine Learning models using the historical data synthesizer.
```bash
cd delivery-tracking/spark
source .venv/Scripts/activate
python -m ensurepip --default-pip
python -m pip install -r requirements.txt
python train_models.py
```
*(You will see `.joblib` files generated inside the `spark/models/` folder).*

### 3. Start PySpark Streaming Processor
*In the same Spark terminal,* start the stream processing engine that applies the ML models and Spatial H3 logic natively over Kafka.
```bash
python stream_processor.py
```

### 4. Start the Backend Consumer Server
*Open a new Git Bash terminal.* This hooks into MongoDB and listens to the Kafka ML prediction/density/alert topics.
```bash
cd delivery-tracking/backend
npm install
node server.js
```

### 5. Start the Rider Simulator
*Open a third Git Bash terminal.* This processes OSRM routes and begins producing data into Kafka every 2 seconds.
```bash
cd delivery-tracking/producer
python -m pip install -r requirements.txt
python simulator.py
```
*(Alternatively, run `python benchmark.py` to stress-test your system with 10,000 riders).*

### 6. View the Live AI Dashboard
Navigate to the `delivery-tracking/frontend/` folder in your Windows File Explorer and **double-click `index.html`** to open it in your browser. 

You will immediately see 🛵 scooters tracking live along the streets, predicting ETAs, glowing red on anomalies, and projecting traffic hit-maps cleanly via HTML5 WebSocket events!

---


## 🌍 Exposing to the Internet (Ngrok + Vercel Deployment)

To track a real mobile phone on 4G/5G and view the live dashboard from anywhere, we use a hybrid deployment architecture:
- **Frontend**: Hosted on [Vercel](https://vercel.com) (Static HTML/JS).
- **Backend / Kafka**: Hosted locally on your machine, tunneled securely to the internet via **Ngrok**.

### 1. Tunnel your Local Backend
1. Download and authenticate [Ngrok](https://download.ngrok.com/) on your backend machine.
2. In a terminal, expose your Node.js Backend port (default `3001`):
   ```bash
   ngrok http 3001
   ```
3. Copy the output `Forwarding URL` (e.g., `https://vannesa-unflaked-zoraida.ngrok-free.dev`).

### 2. Configure the Frontend
1. Open `frontend/config.js`.
2. Update the `DEPLOYED_URL` variable to your new Ngrok URL:
   ```javascript
   const DEPLOYED_URL = "https://<your-ngrok-id>.ngrok-free.dev";
   const BACKEND_URL = DEPLOYED_URL;
   ```
3. **Commit and push** your changes to GitHub.

### 3. Deploy Frontend to Vercel
1. Go to [Vercel](https://vercel.com) and import your GitHub repository.
2. Set the "Framework Preset" to **Other** and the "Root Directory" to `frontend`.
3. Click **Deploy**. Your frontend is now available globally!

*(Note: Ngrok's free tier shows an interstitial browser warning screen when visiting a URL. The frontend architecture automatically injects the HTTP Header `"ngrok-skip-browser-warning": "69420"` into all Socket.io & Fetch requests to silently bypass this block without needing a paid Ngrok account).*

### 4. Track Your Real Phone!
1. Start your `server.js` and your Ngrok tunnel on your laptop.
2. Open your Vercel deployment URL on your smartphone (e.g., `https://kafka-delivery-tracking.vercel.app/mobile-tracker.html`).
3. Enter your assigned `Rider ID` and press **Start Tracking Me**.
4. Open the map dashboard (`index.html` on Vercel) on your laptop or another device, and watch your real-world movements stream directly into your local Kafka broker!
