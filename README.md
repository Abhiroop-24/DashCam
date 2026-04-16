# 🚗 Smart DashCam — AI-Powered Collision Monitoring System

A real-time dashcam system built with a **Raspberry Pi** and a **laptop (NVIDIA GPU)**, featuring live video streaming, AI object detection (YOLOv8), sensor fusion, and a web-based monitoring dashboard.

---

## 📸 System Overview

```
┌──────────────────────┐         UDP Video (H.264)           ┌──────────────────────────┐
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

## 🚀 Setup & Installation (Fresh Linux Laptop)

### Prerequisites

- **Linux** (Ubuntu 22.04+ / Debian 12+ recommended)
- **NVIDIA GPU** with CUDA support
- **Python 3.10+**
- **Raspberry Pi** connected via USB tethering or Ethernet

### Step 1: Install System Dependencies

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip ffmpeg sshpass git
```

- `ffmpeg` — needed for video stream decoding and H.264 re-encoding
- `sshpass` — needed for `deploy_to_pi.sh` to SSH into the Pi without password prompts

### Step 2: Install NVIDIA Drivers + CUDA (if not already installed)

```bash
# Check if CUDA is already working
nvidia-smi

# If not installed, install NVIDIA drivers:
sudo apt install -y nvidia-driver-535    # or your GPU's compatible version
sudo reboot
```

### Step 3: Clone the Repository

```bash
git clone https://github.com/Abhiroop-24/DashCam.git
cd DashCam
```

### Step 4: Create Virtual Environment & Install Dependencies

```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install PyTorch with CUDA first (check your CUDA version with: nvcc --version)
# For CUDA 12.x:
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121

# For CUDA 11.8:
# pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118

# Install remaining dependencies
pip install -r requirements.txt
```

> **Verify CUDA is working:**
> ```bash
> python -c "import torch; print(f'CUDA: {torch.cuda.is_available()}, GPU: {torch.cuda.get_device_name(0)}')"
> ```
> You should see `CUDA: True, GPU: <your GPU name>`

### Step 5: Configure Network IPs

Find your laptop's IP and Pi's IP on the shared network:

```bash
# Find your laptop's IP (look for the Pi-facing interface)
ip addr show
```

Then edit the config files:

```bash
nano config.py
```
```python
# Change these to match YOUR network
PI_IP = "10.42.0.116"       # ← Your Pi's IP address
LAPTOP_IP = "10.42.0.1"     # ← Your laptop's IP address
```

```bash
nano pi_dashcam/config_pi.py
```
```python
# Must match the values above
LAPTOP_IP = "10.42.0.1"
PI_IP = "10.42.0.116"
```

### Step 6: Configure Deploy Script

Edit `deploy_to_pi.sh` with your Pi's SSH credentials:

```bash
nano deploy_to_pi.sh
```
```bash
PI_USER="your_pi_username"          # default: pi
PI_HOST="10.42.0.116"               # your Pi's IP
PI_PASS="your_pi_password"          # your Pi's password
PI_DIR="/home/your_pi_username/dashcam"
```

### Step 7: Deploy Code to Raspberry Pi

Make sure your Pi is connected and reachable:

```bash
# Test connectivity
ping -c 1 10.42.0.116

# Deploy
bash deploy_to_pi.sh
```

This copies code to the Pi, installs Python packages, and starts the `dashcam` service.

### Step 8: Start the Dashboard

```bash
bash start.sh
```

Open **http://localhost:5000** in your browser. Done! 🎉

### Quick Reference — All Commands

```bash
# One-time setup (copy-paste all at once)
sudo apt install -y python3 python3-venv python3-pip ffmpeg sshpass git
git clone https://github.com/Abhiroop-24/DashCam.git
cd DashCam
python3 -m venv venv
source venv/bin/activate
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
pip install -r requirements.txt

# Edit config.py and pi_dashcam/config_pi.py with your IPs
# Edit deploy_to_pi.sh with your Pi's SSH credentials

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

## ❗ Troubleshooting

### Port Already in Use (Address already in use)

If you see `OSError: [Errno 98] Address already in use` when starting the dashboard, a previous process is still holding the port.

```bash
# Find what's using port 5000 (dashboard)
sudo lsof -i :5000

# Kill it by PID
sudo kill -9 <PID>

# Or kill all processes on ports 5000, 8080, 8081, 8082 at once
sudo fuser -k 5000/tcp 8080/udp 8081/udp 8082/udp
```

**Quick one-liner to kill everything and restart:**
```bash
sudo fuser -k 5000/tcp 8080/udp 8081/udp 8082/udp 2>/dev/null; bash start.sh
```

### Pi Stream Not Connecting

```bash
# Check if Pi service is running
ssh abhiroop@10.42.0.116 "systemctl status dashcam"

# Restart the Pi service
ssh abhiroop@10.42.0.116 "sudo systemctl restart dashcam"

# Check Pi logs for errors
ssh abhiroop@10.42.0.116 "journalctl -u dashcam -n 50"
```

### H.264 Decode Errors (`non-existing PPS 0 referenced`)

These messages during startup are **normal** — they appear while ffmpeg waits for the first keyframe from the Pi's H.264 stream. They stop once the stream syncs (usually within 2-3 seconds).

### Dashboard Shows `--` for Sensor Values

- Make sure the Pi is connected and the dashcam service is running
- Check that `PI_IP` in `config.py` matches the Pi's actual IP
- Verify UDP port 8081 is not blocked: `sudo ufw allow 8081/udp`

### Segmentation Fault on Exit

Occasional segfaults on `Ctrl+C` shutdown are caused by OpenCV's internal cleanup and are harmless — the system has already saved all data before exiting.

---

## 📄 License

This project is for educational purposes.
