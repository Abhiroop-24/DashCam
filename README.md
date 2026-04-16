# 🚗 Smart DashCam — AI-Powered Collision Monitoring System

A real-time dashcam system built with a **Raspberry Pi** and a **laptop (NVIDIA GPU)**, featuring live video streaming, AI object detection (YOLOv8), sensor fusion, SOS emergency alerts, and a web-based monitoring dashboard.

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
│  • Status LED        │                                     │  • SOS Emergency System  │
└──────────────────────┘                                     └──────────────────────────┘
```

### How It Works

1. **Pi streams live video** via `rpicam-vid → ffmpeg → UDP` to the laptop
2. **Pi reads sensors** (MPU6050 accelerometer/gyro/temperature + HC-SR04 ultrasonic) and sends data over UDP at 20 Hz
3. **Laptop runs YOLOv8s** on the GPU to detect vehicles, pedestrians, and cyclists in real-time
4. **Collision detection** uses dual-validation: AI proximity (bounding box area) **AND** ultrasonic distance must both agree before triggering an alert
5. **SOS Emergency** auto-triggers after 2 consecutive G-force spikes — contacts emergency services with crash evidence
6. **Events are recorded** with a 5-second pre-event buffer + 5-second post-event capture, re-encoded to H.264 for browser playback
7. **Web dashboard** at `http://localhost:5000` shows everything live

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
| **OS** | Linux (Ubuntu 22.04+ / Debian 12+ recommended) |
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
DashCam/
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
├── recordings/              # Saved event video clips (auto-created)
└── snapshots/               # Saved event snapshots (auto-created)
```

---

## 🚀 Setup & Installation (Fresh Linux Laptop)

### Step 1: Install System Dependencies

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip ffmpeg sshpass git
```

| Package | Why it's needed |
|---------|----------------|
| `python3`, `python3-venv`, `python3-pip` | Python runtime and package manager |
| `ffmpeg` | Video stream decoding + H.264 re-encoding for saved clips |
| `sshpass` | Auto-SSH into Pi during deployment (used by `deploy_to_pi.sh`) |
| `git` | Clone the repository |

### Step 2: Install NVIDIA Drivers + CUDA

```bash
# Check if CUDA is already working
nvidia-smi
```

If NVIDIA drivers are **not installed**:
```bash
# Ubuntu:
sudo apt install -y nvidia-driver-535    # or latest version for your GPU
sudo reboot

# Verify after reboot:
nvidia-smi
```

### Step 3: Clone the Repository

```bash
git clone https://github.com/Abhiroop-24/DashCam.git
cd DashCam
```

### Step 4: Create Virtual Environment & Install Python Dependencies

```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install PyTorch with CUDA support
# Check your CUDA version: nvidia-smi (top right shows CUDA version)

# For CUDA 12.x:
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121

# For CUDA 11.8:
# pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118

# Install all other dependencies
pip install -r requirements.txt
```

### Step 5: Download YOLOv8 Model

The system uses **YOLOv8s** for object detection. Download the model weights:

```bash
# Download YOLOv8s weights (22MB) — auto-downloads via ultralytics
source venv/bin/activate
python -c "from ultralytics import YOLO; YOLO('yolov8s.pt')"
```

> This downloads `yolov8s.pt` to the project directory. The file is ~22MB and is gitignored (not uploaded to GitHub).

### Step 6: Verify Everything Works

```bash
source venv/bin/activate

# Check CUDA
python -c "import torch; print(f'CUDA: {torch.cuda.is_available()}, GPU: {torch.cuda.get_device_name(0)}')"
# Expected: CUDA: True, GPU: <your GPU name>

# Check YOLO
python -c "from ultralytics import YOLO; m = YOLO('yolov8s.pt'); print('YOLOv8s loaded OK')"
# Expected: YOLOv8s loaded OK

# Check Flask
python -c "import flask, flask_socketio; print('Flask OK')"
# Expected: Flask OK
```

### Step 7: Configure Network IPs

Find your Pi's IP:
```bash
# If Pi is connected via USB tethering:
arp -a | grep 10.42

# Or scan the network:
nmap -sn 10.42.0.0/24
```

Edit the config files to match your network:

```bash
nano config.py
```
```python
PI_IP = "10.42.0.116"       # ← Your Pi's IP address
LAPTOP_IP = "10.42.0.1"     # ← Your laptop's IP address
```

```bash
nano pi_dashcam/config_pi.py
```
```python
LAPTOP_IP = "10.42.0.1"     # ← Must match your laptop's IP
PI_IP = "10.42.0.116"       # ← Must match your Pi's IP
```

### Step 8: Configure & Run Deploy Script

```bash
nano deploy_to_pi.sh
```
```bash
PI_USER="your_pi_username"          # default: pi or your username
PI_HOST="10.42.0.116"               # your Pi's IP
PI_PASS="your_pi_password"          # your Pi's SSH password
PI_DIR="/home/your_pi_username/dashcam"
```

Then deploy:
```bash
# Test Pi connectivity first
ping -c 1 10.42.0.116

# Deploy code + install dependencies + start service
bash deploy_to_pi.sh
```

### Step 9: Start the System

```bash
bash start.sh
```

Open **http://localhost:5000** in your browser. 🎉

---

### Quick Copy-Paste Setup (All Commands)

```bash
# System packages
sudo apt update && sudo apt install -y python3 python3-venv python3-pip ffmpeg sshpass git

# Clone
git clone https://github.com/Abhiroop-24/DashCam.git && cd DashCam

# Python environment
python3 -m venv venv && source venv/bin/activate

# PyTorch (CUDA 12.x — change if you have CUDA 11.8)
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121

# Dependencies
pip install -r requirements.txt

# Download YOLO model
python -c "from ultralytics import YOLO; YOLO('yolov8s.pt')"

# ⚠️ Edit these files with YOUR Pi's IP and credentials:
#   nano config.py
#   nano pi_dashcam/config_pi.py
#   nano deploy_to_pi.sh

# Deploy to Pi and start
bash deploy_to_pi.sh
bash start.sh
```

---

## 🖥️ Dashboard Features

| Feature | Description |
|---------|-------------|
| **Live Video Feed** | Real-time MJPEG stream with AI detection overlays |
| **G-Force Monitor** | Live accelerometer readings with collision threshold bar |
| **Proximity Sensor** | Ultrasonic distance with color-coded alerts |
| **Temperature** | MPU6050 on-chip temperature in °C and °F |
| **AI Detections** | Real-time list of detected objects with confidence scores |
| **SOS Emergency** | Auto-triggers on multiple impacts, manual button, 10s countdown |
| **Event Log** | Collision and proximity events with timestamps |
| **Recording Strip** | Thumbnail gallery of saved clips and snapshots |
| **Manual Controls** | Snapshot / Save Clip / SOS buttons |
| **Settings** | Adjustable alert distance threshold |

---

## 🚨 SOS Emergency System

### Auto-Trigger
After **2 G-force spikes** within 10 seconds, SOS activates automatically.

### Manual Trigger
Red **SOS** button in the dashboard header — requires confirmation.

### What Happens
1. Full-screen emergency overlay with **10-second countdown**
2. Ambulance (108) and Police (100) dispatch simulation
3. Crash evidence is saved: **video clip + snapshot + sensor data + GPS location**
4. Pi OLED shows `!! SOS ACTIVE !!` and LED flashes
5. **Cancel button** available during countdown if you're okay
6. After countdown → dispatch confirmation with ETA info

---

## ⚙️ Configuration Reference

### Laptop (`config.py`)

| Parameter | Default | Description |
|-----------|---------|-------------|
| `YOLO_MODEL` | `yolov8s.pt` | YOLO model file (auto-downloads) |
| `DETECTION_INTERVAL` | `3` | Process every Nth frame |
| `PROXIMITY_THRESHOLD` | `0.30` | Bbox area ratio to trigger "too close" |
| `CONFIDENCE_THRESHOLD` | `0.30` | Minimum detection confidence |
| `G_FORCE_THRESHOLD` | `1.5` | G-force to trigger collision event |
| `DISTANCE_ALERT_CM` | `25` | Ultrasonic distance alert threshold |
| `BUFFER_SECONDS` | `30` | Ring buffer duration for pre-event recording |
| `SOS_SPIKE_COUNT` | `2` | G-force spikes to auto-trigger SOS |
| `SOS_SPIKE_WINDOW` | `10` | Seconds window for consecutive spikes |

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
# Start the dashboard
bash start.sh

# Deploy code changes to Pi
bash deploy_to_pi.sh

# Check Pi service status
ssh abhiroop@10.42.0.116 "systemctl status dashcam"

# View Pi logs in real-time
ssh abhiroop@10.42.0.116 "journalctl -u dashcam -f"

# Restart Pi service
ssh abhiroop@10.42.0.116 "sudo systemctl restart dashcam"

# Kill busy ports and restart
sudo fuser -k 5000/tcp 8080/udp 8081/udp 8082/udp 2>/dev/null; bash start.sh
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

The system uses **YOLOv8s** (`yolov8s.pt`, 22MB) running on the laptop's GPU for real-time object detection.

| Setting | Value |
|---------|-------|
| **Model** | YOLOv8s (small) |
| **Detected classes** | Person, Bicycle, Car, Motorcycle, Bus, Truck |
| **Inference speed** | ~15-25ms per frame on RTX 2050 |
| **Proximity alert** | Triggers when bbox > 30% of frame **AND** ultrasonic < 25cm |
| **Events** | Proximity → snapshot only; Collision → snapshot + video |

> The model weights (`yolov8s.pt`) are **not included in the repo** (gitignored). They download automatically from Ultralytics on first run via Step 5.

---

## ❗ Troubleshooting

### Port Already in Use

```bash
# Kill all DashCam ports at once
sudo fuser -k 5000/tcp 8080/udp 8081/udp 8082/udp

# Then restart
bash start.sh
```

### Pi Stream Not Connecting

```bash
# Check if Pi is reachable
ping -c 1 10.42.0.116

# Check if dashcam service is running on Pi
ssh abhiroop@10.42.0.116 "systemctl status dashcam"

# Restart the service
ssh abhiroop@10.42.0.116 "sudo systemctl restart dashcam"

# Check Pi logs for errors
ssh abhiroop@10.42.0.116 "journalctl -u dashcam -n 50"
```

### `yolov8s.pt` Not Found

```bash
source venv/bin/activate
python -c "from ultralytics import YOLO; YOLO('yolov8s.pt')"
```

### H.264 Decode Errors (`non-existing PPS 0 referenced`)

These messages during startup are **normal** — they appear while ffmpeg waits for the first keyframe. They stop once the stream syncs (2-3 seconds).

### Dashboard Shows `--` for Sensor Values

- Make sure the Pi is connected and the dashcam service is running
- Check that `PI_IP` in `config.py` matches the Pi's actual IP
- Verify UDP port 8081 is not blocked: `sudo ufw allow 8081/udp`

### Segmentation Fault on Exit

Occasional segfaults on `Ctrl+C` shutdown are caused by OpenCV's internal cleanup and are harmless — the system has already saved all data before exiting.

---

## 📄 License

This project is for educational purposes.
