from kafka import KafkaProducer
import json, time, random
import requests
import polyline

producer = KafkaProducer(
    bootstrap_servers='localhost:9092',
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

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
    for rider in riders:
        route = routes[rider]
        current_idx = progress[rider]
        
        # If rider reached destination, reset back to start for simulation purposes
        if current_idx >= len(route):
            progress[rider] = 0
            current_idx = 0
            
        current_location = route[current_idx]
        
        data = {
            "rider_id": rider,
            "location": current_location,
            "timestamp": time.time()
        }
        producer.send("rider-location", value=data)
        print("Sent:", data)
        
        # Move rider forward by 1 step every interval
        progress[rider] += 1
    
    time.sleep(2)