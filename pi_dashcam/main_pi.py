"""
Smart DashCam — Raspberry Pi Main Entry Point

Orchestrates all Pi-side components:
- Camera streaming (rpicam-vid → ffmpeg → UDP to laptop)
- Sensor reading (MPU6050 + HC-SR04) → UDP to laptop
- OLED display status updates
- Command listener from laptop
- LED indicator on GPIO17

Pin Reference:
  MPU6050:  SDA→GPIO2(Pin3), SCL→GPIO3(Pin5), VCC→3.3V, GND→GND
  HC-SR04:  TRIG→GPIO23(Pin16), ECHO→GPIO24(Pin18), VCC→5V, GND→GND
  OLED:     SCL→GPIO25(Pin22), SDA→GPIO26(Pin37), VCC→3.3V, GND→GND
  LED:      GPIO17(Pin11) via resistor to GND
"""
import signal
import sys
import time
import math
import threading
import subprocess

import RPi.GPIO as GPIO

from config_pi import LED_PIN, PI_IP
from camera_stream import CameraStream
from sensor_reader import SensorReader
from oled_display import OLEDDisplay
from command_listener import CommandListener


class LEDController:
    """Controls the status LED on GPIO17."""

    def __init__(self, pin=LED_PIN):
        self.pin = pin
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(self.pin, GPIO.OUT)
        GPIO.output(self.pin, False)

    def on(self):
        GPIO.output(self.pin, True)

    def off(self):
        GPIO.output(self.pin, False)

    def flash(self, times=3, interval=0.2):
        def _do_flash():
            for _ in range(times):
                self.on()
                time.sleep(interval)
                self.off()
                time.sleep(interval)
        threading.Thread(target=_do_flash, daemon=True).start()

    def cleanup(self):
        self.off()


def get_ip():
    """Get the Pi's IP address."""
    try:
        result = subprocess.check_output(
            "hostname -I", shell=True, timeout=5
        ).decode().strip().split()
        return result[0] if result else PI_IP
    except Exception:
        return PI_IP


def main():
    print("=" * 44)
    print("  Smart DashCam — Raspberry Pi")
    print("=" * 44)
    print()

    ip = get_ip()
    print(f"[MAIN] Pi IP: {ip}")

    # Initialize components
    led = LEDController()
    oled = OLEDDisplay()
    camera = CameraStream()
    sensor = SensorReader()
    commands = CommandListener(oled_display=oled, led_controller=led)

    # Graceful shutdown handler
    shutting_down = False

    def shutdown(signum=None, frame=None):
        nonlocal shutting_down
        if shutting_down:
            return
        shutting_down = True

        print("\n[MAIN] Shutting down Pi...")
        oled.update(line1="Shutting down...", line2="", line3="", line4="")
        time.sleep(0.5)

        camera.stop()
        sensor.stop()
        commands.stop()
        oled.stop()
        led.cleanup()

        try:
            GPIO.cleanup()
        except:
            pass

        print("[MAIN] Pi stopped. Goodbye!")
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    # Start everything
    oled.start()
    oled.update(
        line1="DashCam Starting",
        line2=f"IP: {ip}",
        line3="Initializing...",
        line4=""
    )

    # Start camera
    camera.start()
    time.sleep(2)

    # Start sensors
    sensor.start()

    # Start command listener
    commands.start()

    # Startup LED flash
    led.flash(times=3)

    oled.update(
        line1="DashCam Active",
        line2=f"IP: {ip}",
        line3="Stream: Running",
        line4="Sensors: OK"
    )

    print("\n[MAIN] All Pi systems running!")
    print("[MAIN] Press Ctrl+C to stop\n")

    # Main status loop
    try:
        while True:
            data = sensor.get_data()
            cam_ok = camera.is_alive()

            g = math.sqrt(
                data['accel']['x']**2 +
                data['accel']['y']**2 +
                data['accel']['z']**2
            )

            dist_str = f"{data['distance']:.0f}" if data['distance'] < 999 else "--"
            temp_str = f"{data['temperature']:.1f}" if data.get('temperature') else "--"

            oled.update(
                line1=f"G:{g:.2f} D:{dist_str}cm",
                line2=f"Cam:{'OK' if cam_ok else 'DN'} T:{temp_str}C",
                line3=f"IP: {ip}",
                line4=time.strftime("%H:%M:%S")
            )

            # Flash LED on collision detection
            if data['collision']:
                led.flash(times=5, interval=0.1)

            # Print status to console
            print(f"\r[STATUS] G:{g:.2f}g | Dist:{dist_str}cm | Temp:{temp_str}°C | Cam:{'OK' if cam_ok else 'DOWN'}", end="", flush=True)

            time.sleep(1)

    except KeyboardInterrupt:
        shutdown()


if __name__ == "__main__":
    main()
