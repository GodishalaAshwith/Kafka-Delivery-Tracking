const express = require('express');
const http = require('http');
const { Server } = require('socket.io');
const mongoose = require('mongoose');
const { Kafka } = require('kafkajs');
const cors = require('cors');

const app = express();
app.use(cors());

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

const consumer = kafka.consumer({ groupId: 'tracking-group' });

async function runKafka() {
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