import os
import json
from datetime import datetime

# Ensure HADOOP_HOME is set first, and add to PATH so Java finds hadoop.dll
os.environ["HADOOP_HOME"] = "C:\\hadoop"
os.environ["hadoop.home.dir"] = "C:\\hadoop"
os.environ["PATH"] = "C:\\hadoop\\bin;" + os.environ.get("PATH", "")

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, from_json, udf, to_json, struct, window, count, atan2, sin, cos, sqrt
from pyspark.sql.types import StructType, StructField, StringType, DoubleType, BooleanType
import h3
import joblib
import math

# Append hadoop bin to PATH so JVM can load hadoop.dll
os.environ["PATH"] = os.environ["HADOOP_HOME"] + "\\bin;" + os.environ["PATH"]

# ==============================================================================
# PySpark Stream Processor for Real-Time Delivery Analytics
# ==============================================================================

# Kafka Configuration
KAFKA_BROKER = "localhost:9092"
INPUT_TOPIC = "rider-location"
OUTPUT_TOPIC_DENSITY = "traffic-density"
OUTPUT_TOPIC_ALERTS = "rider-alerts"
OUTPUT_TOPIC_PREDICTIONS = "rider-predictions"

MODEL_DIR = os.path.join(os.path.dirname(__file__), "models")
ETA_MODEL_PATH = os.path.join(MODEL_DIR, "eta_model.joblib")
ANOMALY_MODEL_PATH = os.path.join(MODEL_DIR, "anomaly_model.joblib")
MODEL_META_PATH = os.path.join(MODEL_DIR, "model_meta.json")


def _load_model_meta():
    if not os.path.exists(MODEL_META_PATH):
        return {"anomaly_threshold": 0.15}
    try:
        with open(MODEL_META_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"anomaly_threshold": 0.15}


ETA_MODEL = joblib.load(ETA_MODEL_PATH) if os.path.exists(ETA_MODEL_PATH) else None
ANOMALY_MODEL = joblib.load(ANOMALY_MODEL_PATH) if os.path.exists(ANOMALY_MODEL_PATH) else None
MODEL_META = _load_model_meta()
ANOMALY_THRESHOLD = float(MODEL_META.get("anomaly_threshold", 0.15))

# Initialize Spark Session with Kafka package
spark = SparkSession.builder \
    .appName("DeliveryTrackingAnalytics") \
    .config("spark.jars.packages", "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0") \
    .master("local[*]") \
    .getOrCreate()

# Ensure Spark logging is minimal to see output cleanly
spark.sparkContext.setLogLevel("WARN")

# Define the schema of the incoming JSON payload from `rider-location`
# Example: {"rider_id": "rider_1", "name": "Rider 1", "location": {"lat": 17.385, "lng": 78.486}, "timestamp": 12345678.90}
location_schema = StructType([
    StructField("lat", DoubleType(), True),
    StructField("lng", DoubleType(), True)
])

schema = StructType([
    StructField("rider_id", StringType(), True),
    StructField("name", StringType(), True),
    StructField("location", location_schema, True),
    StructField("timestamp", DoubleType(), True)
])

# UDF to map coordinates to Uber H3 Hexagon ID (Resolution 9)
@udf(returnType=StringType())
def get_h3_index(lat, lng):
    if lat is None or lng is None:
        return None
    try:
        # Resolution 9 is roughly the size of a city block
        return h3.latlng_to_cell(lat, lng, 9)
    except Exception:
        return None


def _feature_vector(lat, lng, ts):
    dt = datetime.fromtimestamp(float(ts))
    return [[float(lat), float(lng), float(dt.hour), float(dt.weekday())]]


@udf(returnType=DoubleType())
def predict_eta_minutes(lat, lng, ts):
    if ETA_MODEL is None or lat is None or lng is None or ts is None:
        return None
    try:
        return float(ETA_MODEL.predict(_feature_vector(lat, lng, ts))[0])
    except Exception:
        return None


@udf(returnType=DoubleType())
def anomaly_score(lat, lng, ts):
    if ANOMALY_MODEL is None or lat is None or lng is None or ts is None:
        return None
    try:
        # Higher score means more anomalous.
        return float(-ANOMALY_MODEL.decision_function(_feature_vector(lat, lng, ts))[0])
    except Exception:
        return None


@udf(returnType=BooleanType())
def is_anomaly(score):
    if score is None:
        return False
    return float(score) >= ANOMALY_THRESHOLD

# Simple geofence checking a bounding box (e.g., a "high-traffic restricted zone" in Hyderabad)
# HITEC City basic bounding box
RESTRICTED_ZONE = {
    "min_lat": 17.435, "max_lat": 17.450,
    "min_lng": 78.370, "max_lng": 78.385
}

@udf(returnType=BooleanType())
def is_in_restricted_zone(lat, lng):
    if lat is None or lng is None:
        return False
    return (RESTRICTED_ZONE["min_lat"] <= lat <= RESTRICTED_ZONE["max_lat"]) and \
           (RESTRICTED_ZONE["min_lng"] <= lng <= RESTRICTED_ZONE["max_lng"])

def process_stream():
    print("🚀 Starting Streaming Pipeline from Kafka...")

    # Read stream from Kafka
    raw_df = spark.readStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", KAFKA_BROKER) \
        .option("subscribe", INPUT_TOPIC) \
        .option("startingOffsets", "latest") \
        .load()

    # Parse JSON value and add H3 index
    parsed_df = raw_df \
        .selectExpr("CAST(value AS STRING)") \
        .select(from_json("value", schema).alias("data")) \
        .select("data.*")

    enriched_df = parsed_df \
        .withColumn("h3_index", get_h3_index(col("location.lat"), col("location.lng"))) \
        .withColumn("event_time", (col("timestamp").cast("timestamp")))

    # --- Phase 1: Windowed Aggregations (Traffic Density) ---
    # Count unique riders per H3 hexagon every 10 seconds, sliding by 5 seconds
    density_df = enriched_df \
        .withWatermark("event_time", "1 minute") \
        .groupBy(
            window(col("event_time"), "10 seconds", "5 seconds"),
            col("h3_index")
        ) \
        .agg(count("rider_id").alias("rider_density")) \
        .filter(col("h3_index").isNotNull())

    kafka_density_query = density_df \
        .select(
            to_json(
                struct(
                    col("window.start").cast("string").alias("window_start"),
                    col("window.end").cast("string").alias("window_end"),
                    col("h3_index"),
                    col("rider_density")
                )
            ).alias("value")
        ) \
        .writeStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", KAFKA_BROKER) \
        .option("topic", OUTPUT_TOPIC_DENSITY) \
        .option("checkpointLocation", "D:/college/Projects/Kafka/.spark-checkpoints/density") \
        .start()

    # --- Phase 3 & 2: Machine Learning & Geofencing Inferences ---
    predictions_df = enriched_df \
        .withColumn("predicted_eta_minutes", predict_eta_minutes(col("location.lat"), col("location.lng"), col("timestamp"))) \
        .withColumn("anomaly_score", anomaly_score(col("location.lat"), col("location.lng"), col("timestamp"))) \
        .withColumn("is_anomaly", is_anomaly(col("anomaly_score"))) \
        .withColumn("in_restricted_zone", is_in_restricted_zone(col("location.lat"), col("location.lng")))

    # --- Phase 2: Geofencing Alerts Pipeline ---
    # Filter only those inside the zone or flagged as anomaly
    alerts_df = predictions_df.filter((col("in_restricted_zone") == True) | (col("is_anomaly") == True))

    kafka_alerts_query = alerts_df \
        .select(
            to_json(
                struct(
                    col("rider_id"),
                    col("name"),
                    col("h3_index"),
                    col("in_restricted_zone"),
                    col("is_anomaly")
                )
            ).alias("value")
        ) \
        .writeStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", KAFKA_BROKER) \
        .option("topic", OUTPUT_TOPIC_ALERTS) \
        .option("checkpointLocation", "D:/college/Projects/Kafka/.spark-checkpoints/alerts") \
        .start()

    # --- Verification Sink (Terminal) ---
    
    console_query = predictions_df.writeStream \
        .outputMode("append") \
        .format("console") \
        .option("truncate", "false") \
        .option("checkpointLocation", "D:/college/Projects/Kafka/.spark-checkpoints/console") \
        .start()

    kafka_predictions_query = predictions_df \
        .select(
            to_json(
                struct(
                    col("rider_id"),
                    col("name"),
                    col("location"),
                    col("timestamp"),
                    col("event_time"),
                    col("h3_index"),
                    col("predicted_eta_minutes"),
                    col("anomaly_score"),
                    col("is_anomaly"),
                    col("in_restricted_zone")
                )
            ).alias("value")
        ) \
        .writeStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", KAFKA_BROKER) \
        .option("topic", OUTPUT_TOPIC_PREDICTIONS) \
        .option("checkpointLocation", "D:/college/Projects/Kafka/.spark-checkpoints/predictions") \
        .start()

    console_query.awaitTermination()
    kafka_predictions_query.awaitTermination()
    kafka_density_query.awaitTermination()
    kafka_alerts_query.awaitTermination()

if __name__ == "__main__":
    process_stream()
