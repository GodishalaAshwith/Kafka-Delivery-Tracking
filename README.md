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
