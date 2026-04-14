import json
import math
import os
from datetime import datetime

import joblib
import numpy as np
from sklearn.ensemble import IsolationForest, RandomForestRegressor

try:
    from pymongo import MongoClient
except Exception:
    MongoClient = None

MODEL_DIR = os.path.join(os.path.dirname(__file__), "models")
ETA_MODEL_PATH = os.path.join(MODEL_DIR, "eta_model.joblib")
ANOMALY_MODEL_PATH = os.path.join(MODEL_DIR, "anomaly_model.joblib")
MODEL_META_PATH = os.path.join(MODEL_DIR, "model_meta.json")


def haversine_km(lat1, lon1, lat2, lon2):
    r = 6371.0
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (
        math.sin(d_lat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(d_lon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return r * c


def build_features(lat, lng, ts):
    dt = datetime.fromtimestamp(ts)
    hour = dt.hour
    weekday = dt.weekday()
    return [lat, lng, hour, weekday]


def load_from_mongo(max_records=20000):
    if MongoClient is None:
        return []

    mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017/tracking-app")
    try:
        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=3000)
        db = client.get_default_database() if client.get_default_database() else client["tracking-app"]
        col = db["riderlocations"]
        docs = list(
            col.find(
                {"lat": {"$ne": None}, "lng": {"$ne": None}, "timestamp": {"$ne": None}},
                {"_id": 0, "lat": 1, "lng": 1, "timestamp": 1},
            ).limit(max_records)
        )
        return docs
    except Exception:
        return []


def generate_synthetic(n=5000):
    np.random.seed(42)
    base_lat, base_lng = 17.40, 78.47

    data = []
    now = int(datetime.now().timestamp())
    for i in range(n):
        lat = base_lat + np.random.normal(0, 0.03)
        lng = base_lng + np.random.normal(0, 0.03)
        ts = now - np.random.randint(0, 86400 * 14)
        data.append({"lat": float(lat), "lng": float(lng), "timestamp": float(ts)})
    return data


def prepare_training_data(records):
    x = []
    y_eta = []

    # Dummy destination (city-center proxy) used for ETA supervision.
    dest_lat, dest_lng = 17.3850, 78.4867

    for rec in records:
        lat = float(rec["lat"])
        lng = float(rec["lng"])
        ts = float(rec["timestamp"])
        feats = build_features(lat, lng, ts)

        # Synthesize ETA label from geographic distance + peak-hour multiplier.
        km = haversine_km(lat, lng, dest_lat, dest_lng)
        hour = feats[2]
        traffic_factor = 1.35 if (8 <= hour <= 11 or 17 <= hour <= 21) else 1.0
        avg_kmph = 24.0 / traffic_factor
        eta_minutes = (km / avg_kmph) * 60.0

        x.append(feats)
        y_eta.append(float(max(1.0, eta_minutes)))

    return np.array(x, dtype=float), np.array(y_eta, dtype=float)


def main():
    os.makedirs(MODEL_DIR, exist_ok=True)

    mongo_records = load_from_mongo()
    if mongo_records:
        records = mongo_records
        source = "mongo"
    else:
        records = generate_synthetic()
        source = "synthetic"

    x, y_eta = prepare_training_data(records)

    eta_model = RandomForestRegressor(n_estimators=120, random_state=42)
    eta_model.fit(x, y_eta)

    anomaly_model = IsolationForest(contamination=0.03, random_state=42)
    anomaly_model.fit(x)

    scores = -anomaly_model.decision_function(x)
    threshold = float(np.quantile(scores, 0.97))

    joblib.dump(eta_model, ETA_MODEL_PATH)
    joblib.dump(anomaly_model, ANOMALY_MODEL_PATH)

    with open(MODEL_META_PATH, "w", encoding="utf-8") as f:
        json.dump(
            {
                "source": source,
                "records": int(len(records)),
                "features": ["lat", "lng", "hour", "weekday"],
                "anomaly_threshold": threshold,
            },
            f,
            indent=2,
        )

    print(f"Trained ETA model and anomaly model using {len(records)} rows from '{source}'.")
    print(f"Saved: {ETA_MODEL_PATH}")
    print(f"Saved: {ANOMALY_MODEL_PATH}")
    print(f"Saved: {MODEL_META_PATH}")


if __name__ == "__main__":
    main()
