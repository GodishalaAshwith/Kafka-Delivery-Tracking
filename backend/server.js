const express = require('express');
const http = require('http');
const { Server } = require('socket.io');
const mongoose = require('mongoose');
const { Kafka } = require('kafkajs');
const cors = require('cors');

const app = express();
app.use(cors());
app.use(express.json()); // Parse JSON requests from mobile trackers

const server = http.createServer(app);
const io = new Server(server, { cors: { origin: "*" } });

// Mongoose schema definition
const RiderLocationSchema = new mongoose.Schema({
  rider_id: String,
  lat: Number,
  lng: Number,
  timestamp: Number
});

const RiderLocation = mongoose.model('RiderLocation', RiderLocationSchema);

// Connect to MongoDB
mongoose.connect('mongodb://localhost:27017/tracking-app', {
  useNewUrlParser: true,
  useUnifiedTopology: true
}).then(() => console.log('MongoDB connected'))
  .catch(console.error);

// Kafka Consumer setup
const kafka = new Kafka({
  clientId: 'tracking-app',
  brokers: ['localhost:9092']
});

const producer = kafka.producer();
const consumer = kafka.consumer({ groupId: 'tracking-group' });

// Global Admin Configuration State (In-Memory for Demo)
let adminConfig = {
    simulationEnabled: true,
    realRidersEnabled: true,
    simulatedRiders: {
        "rider_1": { name: "John (Charminar)", active: true },
        "rider_2": { name: "Alice (HITEC City)", active: true },
        "rider_3": { name: "Bob (Nampally)", active: true }
    }
};

// Admin Endpoints
app.get('/api/admin/config', (req, res) => {
    res.json(adminConfig);
});

app.post('/api/admin/config', (req, res) => {
    adminConfig = { ...adminConfig, ...req.body };
    io.emit('config-updated', adminConfig); // Tell frontend to hard refresh if needed
    res.json({ success: true, adminConfig });
});

// REST Endpoint to receive live coordinates from Real Mobile Devices
app.post('/api/track', async (req, res) => {
  try {
    if (!adminConfig.realRidersEnabled) {
        return res.status(403).json({ error: "Real rider tracking is currently disabled by Admin." });
    }

    const { rider_id, lat, lng, name } = req.body;
    
    if (!rider_id || !lat || !lng) {
        return res.status(400).json({ error: "Missing parameters" });
    }

    const payload = {
      rider_id: rider_id,
      name: req.body.name || rider_id, // Default to rider_id if name missing
      location: { lat: parseFloat(lat), lng: parseFloat(lng) },
      timestamp: Date.now() / 1000
    };

    // Forward the real GPS device location to Kafka
    await producer.send({
      topic: 'rider-location',
      messages: [{ value: JSON.stringify(payload) }],
    });

    res.status(200).json({ success: true, message: "Location published to Kafka" });
  } catch (err) {
    console.error("Error publishing from real tracker:", err);
    res.status(500).json({ error: err.message });
  }
});

async function runKafka() {
  await producer.connect();
  console.log("Kafka Producer connected (Ready for real trackers)");

  await consumer.connect();
  console.log("Kafka Consumer connected");
  
  await consumer.subscribe({ topic: 'rider-location', fromBeginning: false });

  await consumer.run({
    eachMessage: async ({ message }) => {
      try {
        const data = JSON.parse(message.value.toString());
        console.log("Received:", data);

        // 1. Store in DB
        await RiderLocation.create({
          rider_id: data.rider_id,
          lat: data.location.lat,
          lng: data.location.lng,
          timestamp: data.timestamp
        });

        // 2. Send via WebSocket
        io.emit("rider-location-update", data);
      } catch (err) {
        console.error("Error processing message:", err);
      }
    }
  });
}

runKafka().catch(console.error);

io.on('connection', (socket) => {
  console.log('Client connected:', socket.id);
});

const PORT = process.env.PORT || 3001;
server.listen(PORT, () => {
    console.log(`Tracking server running on port ${PORT}`);
});