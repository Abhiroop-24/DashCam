"""
Configuration constants for the Smart DashCam system.
"""
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Network
PI_IP = "10.42.0.116"
LAPTOP_IP = "10.42.0.1"
VIDEO_PORT = 8080
SENSOR_PORT = 8081
COMMAND_PORT = 8082

# Video
FRAME_WIDTH = 800
FRAME_HEIGHT = 600
FPS = 30

# Ring Buffer
BUFFER_SECONDS = 30
BUFFER_SIZE = BUFFER_SECONDS * FPS  # 900 frames

# AI Detection
YOLO_MODEL = "yolov8s.pt"
DETECTION_INTERVAL = 3  # Process every Nth frame
DETECTION_CLASSES = [0, 1, 2, 3, 5, 7]  # person, bicycle, car, motorcycle, bus, truck
PROXIMITY_THRESHOLD = 0.30  # Bounding box area > 30% of frame = too close
CONFIDENCE_THRESHOLD = 0.30

# Collision Detection
G_FORCE_THRESHOLD = 1.5
COLLISION_DURATION_MS = 50

# Proximity Alert (both AI + ultrasonic must agree)
DISTANCE_ALERT_CM = 25

# Recording
RECORDING_DIR = os.path.join(BASE_DIR, "recordings")
SNAPSHOT_DIR = os.path.join(BASE_DIR, "snapshots")
DB_PATH = os.path.join(BASE_DIR, "events.db")

# Pre-collision + post-collision recording
PRE_EVENT_SECONDS = 5
POST_EVENT_SECONDS = 5

# Dashboard
DASHBOARD_HOST = "0.0.0.0"
DASHBOARD_PORT = 5000

# SOS Emergency System
SOS_SPIKE_COUNT = 2          # Number of G-force spikes to auto-trigger SOS
SOS_SPIKE_WINDOW = 10        # Seconds window for consecutive spikes
SOS_COOLDOWN = 60            # Seconds before SOS can re-trigger

# Ensure directories exist
os.makedirs(RECORDING_DIR, exist_ok=True)
os.makedirs(SNAPSHOT_DIR, exist_ok=True)
