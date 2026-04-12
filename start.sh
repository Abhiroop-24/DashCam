#!/bin/bash
# ═══════════════════════════════════════════
# Quick Start Script — Laptop Side
# ═══════════════════════════════════════════

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="${SCRIPT_DIR}/venv"

echo "╔══════════════════════════════════════════╗"
echo "║  Smart DashCam AI — Starting Dashboard   ║"
echo "╚══════════════════════════════════════════╝"
echo ""

# Check venv
if [ ! -d "${VENV}" ]; then
    echo "[ERROR] Virtual environment not found. Run:"
    echo "  python3 -m venv ${VENV}"
    echo "  ${VENV}/bin/pip install -r requirements.txt"
    exit 1
fi

# Check CUDA
echo "[Check] CUDA..."
${VENV}/bin/python -c "import torch; print(f'  GPU: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"CPU only\"}')"

# Check Pi connectivity
echo "[Check] Pi connectivity..."
ping -c 1 -W 2 10.42.0.116 > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "  Pi: Connected (10.42.0.116)"
else
    echo "  Pi: NOT REACHABLE (sensor data will be empty)"
fi

echo ""
echo "[Starting] Dashboard on http://localhost:5000"
echo "Press Ctrl+C to stop"
echo ""

${VENV}/bin/python ${SCRIPT_DIR}/main.py
