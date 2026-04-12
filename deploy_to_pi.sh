#!/bin/bash
# ═══════════════════════════════════════════
# Deploy Pi DashCam code to Raspberry Pi
# Run this from the laptop
# ═══════════════════════════════════════════

PI_USER="abhiroop"
PI_HOST="10.42.0.116"
PI_PASS="24092006"
PI_DIR="/home/abhiroop/dashcam"
LOCAL_PI_DIR="$(dirname "$0")/pi_dashcam"

echo "╔══════════════════════════════════════╗"
echo "║  Deploying DashCam code to Pi        ║"
echo "╚══════════════════════════════════════╝"
echo ""

# Step 1: Create directory on Pi
echo "[1/5] Creating directory on Pi..."
sshpass -p "$PI_PASS" ssh -o StrictHostKeyChecking=no ${PI_USER}@${PI_HOST} "mkdir -p ${PI_DIR}"

# Step 2: Copy files to Pi
echo "[2/5] Copying files..."
sshpass -p "$PI_PASS" scp -o StrictHostKeyChecking=no \
    ${LOCAL_PI_DIR}/config_pi.py \
    ${LOCAL_PI_DIR}/camera_stream.py \
    ${LOCAL_PI_DIR}/sensor_reader.py \
    ${LOCAL_PI_DIR}/oled_display.py \
    ${LOCAL_PI_DIR}/command_listener.py \
    ${LOCAL_PI_DIR}/main_pi.py \
    ${LOCAL_PI_DIR}/requirements_pi.txt \
    ${PI_USER}@${PI_HOST}:${PI_DIR}/

# Step 3: Install requirements
echo "[3/5] Installing Python packages on Pi..."
sshpass -p "$PI_PASS" ssh ${PI_USER}@${PI_HOST} \
    "cd ${PI_DIR} && pip3 install -r requirements_pi.txt 2>/dev/null || pip3 install --break-system-packages -r requirements_pi.txt"

# Step 4: Setup systemd service
echo "[4/5] Setting up autostart service..."
sshpass -p "$PI_PASS" scp -o StrictHostKeyChecking=no \
    ${LOCAL_PI_DIR}/dashcam.service \
    ${PI_USER}@${PI_HOST}:/tmp/dashcam.service

sshpass -p "$PI_PASS" ssh ${PI_USER}@${PI_HOST} << 'REMOTE'
    echo "24092006" | sudo -S cp /tmp/dashcam.service /etc/systemd/system/dashcam.service
    echo "24092006" | sudo -S systemctl daemon-reload
    echo "24092006" | sudo -S systemctl enable dashcam.service
    echo "24092006" | sudo -S systemctl restart dashcam.service
REMOTE

# Step 5: Verify
echo "[5/5] Verifying..."
sshpass -p "$PI_PASS" ssh ${PI_USER}@${PI_HOST} \
    "systemctl is-active dashcam.service"

echo ""
echo "═══════════════════════════════════════"
echo "  Deployment complete!"
echo "  Pi service: systemctl status dashcam"
echo "  Pi logs: journalctl -u dashcam -f"
echo "═══════════════════════════════════════"
