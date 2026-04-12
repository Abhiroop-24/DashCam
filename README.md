# 🚗 Smart DashCam — AI-Powered Collision Monitoring System

A real-time dashcam system built with a **Raspberry Pi** and a **laptop (NVIDIA GPU)**, featuring live video streaming, AI object detection (YOLOv8), sensor fusion, and a web-based monitoring dashboard.

---

## 📸 System Overview

```
┌──────────────────────┐         UDP Video (H.264)          ┌──────────────────────────┐
│    Raspberry Pi      │ ──────────────────────────────────► │    Laptop (GPU)          │
│                      │         UDP Sensor Data             │                          │
│  • Pi Camera Module  │ ──────────────────────────────────► │  • YOLOv8 AI Detection   │
│  • MPU6050 (IMU)     │                                     │  • Flask Web Dashboard   │
│  • HC-SR04 (Sonar)   │ ◄────────────────────────────────── │  • Event Recording       │
│  • SSD1306 OLED      │         UDP Commands                │  • Collision Detection   │
│  • Status LED        │                                     │  • Ring Buffer (30s)     │
└──────────────────────┘                                     └──────────────────────────┘
```

### How It Works

1. **Pi streams live video** via `rpicam-vid → ffmpeg → UDP` to the laptop
2. **Pi reads sensors** (MPU6050 accelerometer/gyro/temperature + HC-SR04 ultrasonic) and sends data over UDP at 20 Hz
3. **Laptop runs YOLOv8** on the GPU to detect vehicles, pedestrians, and cyclists in real-time
4. **Collision detection** uses dual-validation: AI proximity (bounding box area) **AND** ultrasonic distance must both agree before triggering an alert
5. **Events are recorded** with a 5-second pre-event buffer + 5-second post-event capture, re-encoded to H.264 for browser playback
6. **Web dashboard** at `http://localhost:5000` shows everything live

---

## 🔧 Hardware Requirements

### Raspberry Pi Side
| Component | Connection | Purpose |
|-----------|-----------|---------|
| **Raspberry Pi 3B+/4** | — | Main controller |
| **Pi Camera Module** | CSI ribbon cable | Video capture |
| **MPU6050** | I2C Bus 1 (SDA→GPIO2, SCL→GPIO3) | Accelerometer, gyroscope, temperature |
| **HC-SR04** | TRIG→GPIO23, ECHO→GPIO24 | Ultrasonic distance |
| **SSD1306 OLED** | I2C Bus 3 (SCL→GPIO25, SDA→GPIO26) | Status display |
| **LED** | GPIO17 via resistor | Status indicator |

### Laptop Side
| Component | Requirement |
|-----------|------------|
| **GPU** | NVIDIA GPU with CUDA support (tested: RTX 2050) |
| **Python** | 3.10+ |
| **OS** | Linux (Ubuntu/Debian recommended) |
| **Network** | Direct connection to Pi (USB tethering / Ethernet) |

---

## 🔌 Wiring Diagram

```
MPU6050:       SDA → GPIO2 (Pin 3)     SCL → GPIO3 (Pin 5)     VCC → 3.3V    GND → GND
HC-SR04:      TRIG → GPIO23 (Pin 16)  ECHO → GPIO24 (Pin 18)   VCC → 5V      GND → GND
OLED SSD1306:  SDA → GPIO26 (Pin 37)   SCL → GPIO25 (Pin 22)   VCC → 3.3V    GND → GND
LED:                GPIO17 (Pin 11) → 220Ω Resistor → GND
```

---

## 📁 Project Structure

```
dashcam/
├── main.py                  # Laptop entry point — orchestrates everything
├── config.py                # Laptop configuration (ports, thresholds, paths)
├── stream_receiver.py       # Receives H.264 video stream from Pi via UDP
├── sensor_listener.py       # Receives MPU6050 + ultrasonic data via UDP
├── ai_detector.py           # YOLOv8 object detection with CUDA
├── event_recorder.py        # Saves video clips + snapshots on events
├── dashboard.py             # Flask + Socket.IO web dashboard server
├── pi_communicator.py       # Sends commands to Pi via UDP
├── start.sh                 # Quick-start script for laptop
├── deploy_to_pi.sh          # Deploys Pi code via SSH + SCP
├── requirements.txt         # Laptop Python dependencies
│
├── static/
│   ├── css/style.css        # Dashboard styles
│   └── js/dashboard.js      # Dashboard real-time JavaScript
├── templates/
│   └── index.html           # Dashboard HTML template
│
├── pi_dashcam/              # ← Code that runs ON the Raspberry Pi
│   ├── main_pi.py           # Pi entry point
│   ├── config_pi.py         # Pi configuration
│   ├── camera_stream.py     # rpicam-vid + ffmpeg streaming
│   ├── sensor_reader.py     # MPU6050 + HC-SR04 reader (I2C + GPIO)
│   ├── oled_display.py      # SSD1306 OLED driver (bit-banged I2C)
│   ├── command_listener.py  # Receives commands from laptop via UDP
│   ├── dashcam.service      # systemd service for autostart
│   └── requirements_pi.txt  # Pi Python dependencies
│
├── recordings/              # (gitignored) Saved event video clips
└── snapshots/               # (gitignored) Saved event snapshots
```

---

## 🚀 Setup & Installation

### 1. Clone the Repository

```bash
git clone https://github.com/<your-username>/smart-dashcam.git
cd smart-dashcam
```

### 2. Laptop Setup

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies (requires CUDA-compatible PyTorch)
pip install -r requirements.txt

# Download YOLOv8 model weights (auto-downloads on first run, or manually)
# The system uses yolov8s.pt by default (configured in config.py)
```

> **Note:** PyTorch with CUDA support must be installed separately. See [pytorch.org](https://pytorch.org/get-started/locally/) for the correct command for your CUDA version.

### 3. Network Configuration

Edit `config.py` (laptop) and `pi_dashcam/config_pi.py` (Pi) to match your network:

```python
# config.py (Laptop)
PI_IP = "10.42.0.116"       # Your Pi's IP
LAPTOP_IP = "10.42.0.1"     # Your laptop's IP

# config_pi.py (Pi)  
LAPTOP_IP = "10.42.0.1"     # Must match laptop's IP
PI_IP = "10.42.0.116"       # Must match Pi's IP
```

The default assumes a direct USB-tethered connection. Adjust IPs for your network setup.

### 4. Deploy to Raspberry Pi

```bash
# Edit deploy_to_pi.sh with your Pi's credentials, then:
bash deploy_to_pi.sh
```

This will:
- Copy all `pi_dashcam/` files to the Pi
- Install Python dependencies on the Pi
- Set up and start the `dashcam.service` systemd service

### 5. Start the System

```bash
# On the laptop (Pi should already be running via systemd)
bash start.sh
```

The dashboard will be available at **http://localhost:5000**

---

## 🖥️ Dashboard Features

| Feature | Description |
|---------|-------------|
| **Live Video Feed** | Real-time MJPEG stream with AI detection overlays |
| **G-Force Monitor** | Live accelerometer readings with collision threshold bar |
| **Proximity Sensor** | Ultrasonic distance with color-coded alerts |
| **Temperature** | MPU6050 on-chip temperature in °C and °F |
| **AI Detections** | Real-time list of detected objects with confidence scores |
| **Event Log** | Collision and proximity events with timestamps |
| **Recording Strip** | Thumbnail gallery of saved clips and snapshots |
| **Manual Controls** | Snapshot / Save Clip buttons |
| **Settings** | Adjustable alert distance threshold |

---

## ⚙️ Configuration Reference

### Laptop (`config.py`)

| Parameter | Default | Description |
|-----------|---------|-------------|
| `YOLO_MODEL` | `yolov8s.pt` | YOLO model file |
| `DETECTION_INTERVAL` | `3` | Process every Nth frame |
| `PROXIMITY_THRESHOLD` | `0.30` | Bbox area ratio to trigger "too close" |
| `CONFIDENCE_THRESHOLD` | `0.30` | Minimum detection confidence |
| `G_FORCE_THRESHOLD` | `1.5` | G-force to trigger collision event |
| `DISTANCE_ALERT_CM` | `25` | Ultrasonic distance alert threshold |
| `BUFFER_SECONDS` | `30` | Ring buffer duration for pre-event recording |

### Raspberry Pi (`pi_dashcam/config_pi.py`)

| Parameter | Default | Description |
|-----------|---------|-------------|
| `CAMERA_WIDTH` | `800` | Video resolution width |
| `CAMERA_HEIGHT` | `600` | Video resolution height |
| `CAMERA_FPS` | `30` | Camera framerate |
| `MPU_ADDRESS` | `0x68` | MPU6050 I2C address |
| `G_FORCE_THRESHOLD` | `1.5` | Pi-side collision detection threshold |
| `SENSOR_SEND_INTERVAL` | `0.05` | Sensor data rate (20 Hz) |

---

## 🛠️ Useful Commands

```bash
# Check Pi service status
ssh abhiroop@10.42.0.116 "systemctl status dashcam"

# View Pi logs in real-time
ssh abhiroop@10.42.0.116 "journalctl -u dashcam -f"

# Restart Pi service
ssh abhiroop@10.42.0.116 "sudo systemctl restart dashcam"

# Redeploy after code changes
bash deploy_to_pi.sh
```

---

## 📡 Network Ports

| Port | Protocol | Direction | Purpose |
|------|----------|-----------|---------|
| `8080` | UDP | Pi → Laptop | H.264 video stream |
| `8081` | UDP | Pi → Laptop | Sensor data (JSON) |
| `8082` | UDP | Laptop → Pi | Commands (JSON) |
| `5000` | TCP | Laptop | Web dashboard (Flask) |

---

## 🧠 AI Detection

The system uses **YOLOv8s** running on the laptop's GPU for real-time object detection:

- **Detected classes:** Person, Bicycle, Car, Motorcycle, Bus, Truck
- **Proximity alert:** Triggers when an object's bounding box occupies > 30% of the frame **AND** the ultrasonic sensor reads < 25cm
- **Inference:** ~15-25ms per frame on RTX 2050

---

## 📄 License

This project is for educational purposes.
