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

- **Highly Scalable Event Streaming**: Uses Apache Kafka to ingest thousands of GPS coordinates asynchronously.
- **Realistic Routing Engine**: Rather than teleporting randomly, Python uses the **OSRM (Open Source Routing Machine) API** to fetch exact real-world driving street coordinates and simulate realistic vehicle movement.
- **Real-Time WebSockets**: Frontend subscribes via Socket.io to receive live updates with sub-second latency from the Node.js consumer.
- **Persistent Storage**: All location history is logged into MongoDB to allow data analysis, playback, or auditing.
- **Custom UI Integration**: Maps powered by Leaflet and OpenStreetMap native tiles, heavily customized with SVG/Emoji hybrid drop-shadow rider tracking tokens.

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
│   ├── requirements.txt     # kafka-python, requests, polyline
│   └── simulator.py         # Advanced OSRM route coordinate simulator
│
└── frontend/
    └── index.html           # Leaflet.js Interactive frontend mapping
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

### 2. Start the Backend Consumer Server
*Open a new Git Bash terminal.* This hooks into MongoDB and listens to the Kafka topic.
```bash
cd delivery-tracking/backend
npm install
node server.js
```
*(You should see "MongoDB connected" and "Kafka Consumer connected" in the terminal).*

### 3. Start the Rider Simulator
*Open a third Git Bash terminal.* This processes OSRM routes and begins producing data into Kafka every 2 seconds.
```bash
cd delivery-tracking/producer
python -m pip install -r requirements.txt
# Additional map tools
python -m pip install requests polyline
python simulator.py
```

### 4. View the Live Dashboard
Navigate to the `delivery-tracking/frontend/` folder in your Windows File Explorer and **double-click `index.html`** to open it in your browser. 

You will immediately see 🛵 scooters tracking live along the streets of Hyderabad!

---


## ��� Exposing to the Internet (100% Free via Ngrok)
Instead of paying for managed Kafka Cloud providers to track your real phone remotely, you can use **Ngrok** to securely tunnel your local Node.js Server to the web!

1. Download [Ngrok](https://ngrok.com/) for Windows.
2. In a terminal, expose your Node.js Backend port:
   ```bash
   ngrok http 3001
   ```
3. Ngrok will output a Forwarding URL (e.g., `https://abc-123.ngrok-free.app`). 
4. Paste that exact URL as the `DEPLOYED_URL` in `frontend/config.js`.
5. Send the `frontend/mobile-tracker.html` file to your smartphone and start tracking. Your real-world movements will stream directly into your local Kafka broker!
