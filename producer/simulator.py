from kafka import KafkaProducer
import json, time, random, os
import requests
import polyline
from dotenv import load_dotenv

load_dotenv() # Load variables from .env

# --- CLOUD CONFIGURATION ---
KAFKA_BROKERS = os.getenv("KAFKA_BROKERS", "localhost:9092")
KAFKA_USERNAME = os.getenv("KAFKA_USERNAME")
KAFKA_PASSWORD = os.getenv("KAFKA_PASSWORD")
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:3001")

producer_config = {
    'bootstrap_servers': KAFKA_BROKERS,
    'value_serializer': lambda v: json.dumps(v).encode('utf-8')
}

# Add Secure SASL configuration if running in Confluent Cloud
if KAFKA_USERNAME and KAFKA_PASSWORD:
    producer_config['security_protocol'] = 'SASL_SSL'
    producer_config['sasl_mechanism'] = 'PLAIN'
    producer_config['sasl_plain_username'] = KAFKA_USERNAME
    producer_config['sasl_plain_password'] = KAFKA_PASSWORD

producer = KafkaProducer(**producer_config)

# Fetch a real route from OSRM (Open Source Routing Machine)
def get_route(start, end):
    # OSRM expects coordinates in lng,lat format
    url = f"http://router.project-osrm.org/route/v1/driving/{start[1]},{start[0]};{end[1]},{end[0]}?overview=full"
    response = requests.get(url).json()
    if response["code"] != "Ok":
        return []
    
    # polyline decodes to list of (lat, lng) tuples
    route_geometry = response["routes"][0]["geometry"]
    coordinates = polyline.decode(route_geometry)
    return [{"lat": coord[0], "lng": coord[1]} for coord in coordinates]

# Define 3 delivery routes in Hyderabad
print("Calculating real routes using OSRM...")
routes = {
    "rider_1": get_route((17.3850, 78.4867), (17.4399, 78.4983)), # Charminar to Secunderabad
    "rider_2": get_route((17.4435, 78.3772), (17.4486, 78.3908)), # HITEC City to Madhapur
    "rider_3": get_route((17.3984, 78.4728), (17.4056, 78.4849))  # Nampally to Abids
}

# Keep track of where each rider is on their specific route
progress = { "rider_1": 0, "rider_2": 0, "rider_3": 0 }
riders = ["rider_1", "rider_2", "rider_3"]

print("Starting realistic rider simulator...")
while True:
    try:
        # Fetch the live admin configuration on every loop
        admin_config = requests.get(f"{BACKEND_URL}/api/admin/config").json()
    except Exception as e:
        print(f"Waiting for backend at {BACKEND_URL}... ({e})")
        time.sleep(2)
        continue

    if not admin_config.get("simulationEnabled", False):
        print("Simulation is globally disabled by Admin.")
        time.sleep(2)
        continue

    sim_riders = admin_config.get("simulatedRiders", {})

    for rider in riders:
        # Only simulate riders that are explicitly active in the admin config
        rider_config = sim_riders.get(rider, {})
        if not rider_config.get("active", False):
            continue

        route = routes[rider]
        current_idx = progress[rider]
        
        # If rider reached destination, reset back to start for simulation purposes
        if current_idx >= len(route):
            progress[rider] = 0
            current_idx = 0
            
        current_location = route[current_idx]
        
        data = {
            "rider_id": rider,
            "name": rider_config.get("name", rider),
            "location": current_location,
            "timestamp": time.time()
        }
        producer.send("rider-location", value=data)
        print(f"Sent ({data['name']}):", data)
        
        # Move rider forward by 1 step every interval
        progress[rider] += 1
    
    time.sleep(2)