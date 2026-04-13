import os

# Ensure HADOOP_HOME is set first, and add to PATH so Java finds hadoop.dll
os.environ["HADOOP_HOME"] = "C:\\hadoop"
os.environ["hadoop.home.dir"] = "C:\\hadoop"
os.environ["PATH"] = "C:\\hadoop\\bin;" + os.environ.get("PATH", "")

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, from_json, udf, window, avg, count
from pyspark.sql.types import StructType, StructField, StringType, DoubleType, TimestampType
import h3

# Append hadoop bin to PATH so JVM can load hadoop.dll
os.environ["PATH"] = os.environ["HADOOP_HOME"] + "\\bin;" + os.environ["PATH"]

# ==============================================================================
# PySpark Stream Processor for Real-Time Delivery Analytics
# Conference Research Implementation - Phase 1 Foundation
# ==============================================================================

# Kafka Configuration
KAFKA_BROKER = "localhost:9092"
INPUT_TOPIC = "rider-location"
OUTPUT_TOPIC_DENSITY = "traffic-density"

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

    # --- Phase 1: Spatial Tagging Verification Sink (Terminal) ---
    # To start with, we'll write the raw enriched stream to the console to verify
    # the H3 indexes are successfully calculating.
    
    query = enriched_df.writeStream \
        .outputMode("append") \
        .format("console") \
        .option("truncate", "false") \
        .start()

    query.awaitTermination()

if __name__ == "__main__":
    process_stream()
