require('dotenv').config();
const express = require('express');
const http = require('http');
const { Server } = require('socket.io');
const mongoose = require('mongoose');
const { Kafka } = require('kafkajs');
const cors = require('cors');
const fs = require('fs');
const path = require('path');

const app = express();

// Since phones on 4G/5G hit the ngrok URL, we need to allow them explicitly
// Note: Ngrok's weird "Skip Browser Warning" header must be allowed!
app.use(cors({
    origin: '*',
    methods: ['GET', 'POST'],
    allowedHeaders: ['Content-Type', 'ngrok-skip-browser-warning']
}));

app.use(express.json()); // Parse JSON requests from mobile trackers

const server = http.createServer(app);

// Update Socket.io to allow Cross-Origin requests from Vercel (or any other domain)
const io = new Server(server, { 
    cors: { 
        origin: "*",
        methods: ["GET", "POST"],
        allowedHeaders: ["ngrok-skip-browser-warning"]
    } 
});

// Mongoose schema definition
const RiderLocationSchema = new mongoose.Schema({
  rider_id: String,
  lat: Number,
  lng: Number,
  timestamp: Number
});

const RiderLocation = mongoose.model('RiderLocation', RiderLocationSchema);

// Keep the latest location in memory for when a user reloads the page
const latestLocations = {};
const endedShiftAt = {};
const END_SHIFT_COOLDOWN_MS = 10000;

// Connect to MongoDB
mongoose.connect(process.env.MONGO_URI || 'mongodb://localhost:27017/tracking-app', {
  useNewUrlParser: true,
  useUnifiedTopology: true
}).then(() => {
  console.log('MongoDB connected');
})
  .catch(console.error);

// Kafka Consumer setup
const kafkaConfig = {
  clientId: 'tracking-app',
  brokers: (process.env.KAFKA_BROKERS || 'localhost:9092').split(',')
};

if (process.env.KAFKA_USERNAME && process.env.KAFKA_PASSWORD) {
  kafkaConfig.ssl = true;
  kafkaConfig.sasl = {
    mechanism: 'plain', // Confluent Cloud usually requires plain
    username: process.env.KAFKA_USERNAME,
    password: process.env.KAFKA_PASSWORD
  };
}

const kafka = new Kafka(kafkaConfig);

const producer = kafka.producer();
const consumer = kafka.consumer({ groupId: 'tracking-group' });

// Global Admin Configuration State
const CONFIG_FILE = path.join(__dirname, 'adminConfig.json');
let adminConfig = {
    simulationEnabled: true,
    realRidersEnabled: true,
    simulatedRiders: {
        "rider_1": { name: "John (Charminar)", active: true },
        "rider_2": { name: "Alice (HITEC City)", active: true },
        "rider_3": { name: "Bob (Nampally)", active: true }
    }
};

// Load from file if exists to persist settings
if (fs.existsSync(CONFIG_FILE)) {
    try {
        const fileContent = fs.readFileSync(CONFIG_FILE, 'utf8');
        if (fileContent.trim()) {
            const parsedConfig = JSON.parse(fileContent);
            // Verify everything defaults to ON if missing fields
            adminConfig = {
                simulationEnabled: parsedConfig.simulationEnabled ?? true,
                realRidersEnabled: parsedConfig.realRidersEnabled ?? true,
                simulatedRiders: {
                    "rider_1": parsedConfig.simulatedRiders?.rider_1 ?? { name: "John (Charminar)", active: true },
                    "rider_2": parsedConfig.simulatedRiders?.rider_2 ?? { name: "Alice (HITEC City)", active: true },
                    "rider_3": parsedConfig.simulatedRiders?.rider_3 ?? { name: "Bob (Nampally)", active: true }
                }
            };
        }
    } catch (e) {
        console.error("Error reading adminConfig.json, falling back to defaults:", e);
    }
}

// Admin Endpoints
app.get('/api/admin/config', (req, res) => {
    res.json(adminConfig);
});

app.post('/api/admin/config', (req, res) => {
    adminConfig = { ...adminConfig, ...req.body };
    try {
        fs.writeFileSync(CONFIG_FILE, JSON.stringify(adminConfig, null, 2));
    } catch (e) {
        console.error("Failed to save config:", e);
    }
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
    const normalizedRiderId = typeof rider_id === 'string' ? rider_id.trim() : '';
    
    if (!normalizedRiderId || !lat || !lng) {
        return res.status(400).json({ error: "Missing parameters" });
    }

    const endedAt = endedShiftAt[normalizedRiderId];
    if (endedAt && (Date.now() - endedAt) < END_SHIFT_COOLDOWN_MS) {
      return res.status(409).json({ error: "Shift ended for this rider. Start a new shift before tracking." });
    }

    const payload = {
      rider_id: normalizedRiderId,
      name: req.body.name || normalizedRiderId, // Default to rider_id if name missing   
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

app.post('/api/end-shift', (req, res) => {
  const normalizedRiderId = typeof req.body?.rider_id === 'string' ? req.body.rider_id.trim() : '';
  if (normalizedRiderId) {
    endedShiftAt[normalizedRiderId] = Date.now();
    if (latestLocations[normalizedRiderId]) {
      delete latestLocations[normalizedRiderId];
        }
        // Always emit the disconnect so map always clears it on frontend
    io.emit('rider-disconnected', { rider_id: normalizedRiderId });
    }
    res.json({ success: true, message: "Shift ended." });
});

// Run Kafka Consumer
async function runKafka() {

  await producer.connect();
  console.log("Kafka Producer connected (Ready for real trackers)");

  await consumer.connect();
  console.log("Kafka Consumer connected");
  
  await consumer.subscribe({ topic: 'rider-predictions', fromBeginning: false });
  await consumer.subscribe({ topic: 'traffic-density', fromBeginning: false });
  await consumer.subscribe({ topic: 'rider-alerts', fromBeginning: false });

  await consumer.run({
    eachMessage: async ({ topic, partition, message }) => {
      try {
        const data = JSON.parse(message.value.toString());

        if (topic === 'traffic-density') {
          io.emit("traffic-density-update", data);
          return;
        }

        if (topic === 'rider-alerts') {
          io.emit("rider-alert", data);
          return;
        }

        data.rider_id = typeof data.rider_id === 'string' ? data.rider_id.trim() : data.rider_id;

        const endedAt = endedShiftAt[data.rider_id];
        if (endedAt && (Date.now() - endedAt) < END_SHIFT_COOLDOWN_MS) {
          return;
        }

        console.log("Received:", data);

        // Track state locally for reloads
        latestLocations[data.rider_id] = data;

        // 1. Send via WebSocket
        io.emit("rider-location-update", data);

        // 2. Store in DB (Non-blocking so tracking still works if DB fails)
        try {
          await RiderLocation.create({
            rider_id: data.rider_id,
            lat: data.location.lat,
            lng: data.location.lng,
            timestamp: data.timestamp
          });
        } catch (dbErr) {
          console.error("DB Insert Error:", dbErr.message);
        }
      } catch (err) {
        console.error("Error processing message:", err);
      }
    }
  });
}

runKafka().catch(console.error);

io.on('connection', (socket) => {
  console.log('Client connected:', socket.id);
  // Send the admin config
  socket.emit('config-updated', adminConfig);
  
  // Send whatever locations are actively in memory from incoming tracking
  Object.values(latestLocations).forEach(riderData => {
    socket.emit("rider-location-update", riderData);
  });
});

const PORT = process.env.PORT || 3001;
server.listen(PORT, () => {
    console.log(`Tracking server running on port ${PORT}`);
});
