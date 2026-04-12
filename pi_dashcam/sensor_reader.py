"""
Sensor Reader — Reads MPU6050 (accelerometer/gyroscope) and HC-SR04 (ultrasonic)
and sends data to laptop via UDP.

Wiring:
  MPU6050: SDA→GPIO2(Pin3), SCL→GPIO3(Pin5), VCC→3.3V, GND→GND  [I2C bus 1]
  HC-SR04: TRIG→GPIO23(Pin16), ECHO→GPIO24(Pin18), VCC→5V, GND→GND
"""
import smbus2
import RPi.GPIO as GPIO
import socket
import json
import time
import math
import threading
from datetime import datetime
from config_pi import (
    MPU_I2C_BUS, MPU_ADDRESS,
    GYRO_OFFSET_X, GYRO_OFFSET_Y, GYRO_OFFSET_Z,
    TRIG_PIN, ECHO_PIN,
    LAPTOP_IP, SENSOR_PORT,
    G_FORCE_THRESHOLD, SENSOR_SEND_INTERVAL
)


class SensorReader:
    def __init__(self):
        self.running = False
        self._thread = None
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # MPU6050 setup on I2C bus 1
        self.bus = smbus2.SMBus(MPU_I2C_BUS)
        self._init_mpu6050()

        # HC-SR04 setup
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(TRIG_PIN, GPIO.OUT)
        GPIO.setup(ECHO_PIN, GPIO.IN)
        GPIO.output(TRIG_PIN, False)
        time.sleep(0.1)

        # Latest readings
        self.accel = {"x": 0.0, "y": 0.0, "z": 0.0}
        self.gyro = {"x": 0.0, "y": 0.0, "z": 0.0}
        self.temperature = 0.0
        self.distance = 999.0
        self.collision = False

    def _init_mpu6050(self):
        try:
            # Wake up MPU6050 (write 0 to power management register)
            self.bus.write_byte_data(MPU_ADDRESS, 0x6B, 0x00)
            time.sleep(0.1)
            # Set accelerometer range to ±2g
            self.bus.write_byte_data(MPU_ADDRESS, 0x1C, 0x00)
            # Set gyroscope range to ±250 deg/s
            self.bus.write_byte_data(MPU_ADDRESS, 0x1B, 0x00)
            # Set DLPF (digital low pass filter) for smoother readings
            self.bus.write_byte_data(MPU_ADDRESS, 0x1A, 0x03)
            time.sleep(0.1)

            # Verify we can read the WHO_AM_I register
            who = self.bus.read_byte_data(MPU_ADDRESS, 0x75)
            print(f"[Sensor] MPU6050 initialized (WHO_AM_I: 0x{who:02x})")
        except Exception as e:
            print(f"[Sensor] MPU6050 init FAILED: {e}")

    def _read_word_2c(self, reg):
        high = self.bus.read_byte_data(MPU_ADDRESS, reg)
        low = self.bus.read_byte_data(MPU_ADDRESS, reg + 1)
        val = (high << 8) + low
        if val >= 0x8000:
            val = -(65536 - val)
        return val

    def _read_mpu6050(self):
        try:
            # Accelerometer (±2g, sensitivity = 16384 LSB/g)
            ax = self._read_word_2c(0x3B) / 16384.0
            ay = self._read_word_2c(0x3D) / 16384.0
            az = self._read_word_2c(0x3F) / 16384.0

            # Temperature (registers 0x41-0x42)
            raw_temp = self._read_word_2c(0x41)
            self.temperature = round(raw_temp / 340.0 + 36.53, 1)

            # Gyroscope (±250 deg/s, sensitivity = 131 LSB/deg/s)
            gx = self._read_word_2c(0x43) / 131.0 - GYRO_OFFSET_X
            gy = self._read_word_2c(0x45) / 131.0 - GYRO_OFFSET_Y
            gz = self._read_word_2c(0x47) / 131.0 - GYRO_OFFSET_Z

            self.accel = {"x": round(ax, 4), "y": round(ay, 4), "z": round(az, 4)}
            self.gyro = {"x": round(gx, 2), "y": round(gy, 2), "z": round(gz, 2)}

            # Check for collision (resultant g-force)
            g_force = math.sqrt(ax**2 + ay**2 + az**2)
            self.collision = g_force > G_FORCE_THRESHOLD

        except Exception as e:
            print(f"[Sensor] MPU6050 read error: {e}")

    def _read_ultrasonic(self):
        """Read HC-SR04 with retry. Holds last valid reading on failure."""
        for attempt in range(3):
            result = self._single_ultrasonic_read()
            if result is not None:
                self.distance = result
                self._ultrasonic_fails = 0
                return
            time.sleep(0.01)  # Small gap before retry

        # All 3 attempts failed — hold last valid reading for a while
        if not hasattr(self, '_ultrasonic_fails'):
            self._ultrasonic_fails = 0
        self._ultrasonic_fails += 1

        # Only set to 999 after 10 consecutive failures (about 1 second)
        if self._ultrasonic_fails > 10:
            self.distance = 999.0

    def _single_ultrasonic_read(self):
        """Single ultrasonic measurement. Returns distance in cm or None on timeout."""
        try:
            # Ensure trigger is low
            GPIO.output(TRIG_PIN, False)
            time.sleep(0.002)

            # Send 10us trigger pulse
            GPIO.output(TRIG_PIN, True)
            time.sleep(0.00001)
            GPIO.output(TRIG_PIN, False)

            # Wait for echo HIGH (with timeout)
            timeout = time.time() + 0.03
            pulse_start = time.time()
            while GPIO.input(ECHO_PIN) == 0:
                pulse_start = time.time()
                if pulse_start > timeout:
                    return None

            # Wait for echo LOW (with timeout)
            pulse_end = time.time()
            timeout = pulse_end + 0.03
            while GPIO.input(ECHO_PIN) == 1:
                pulse_end = time.time()
                if pulse_end > timeout:
                    return None

            # Calculate distance
            duration = pulse_end - pulse_start
            distance = round(duration * 17150.0, 1)

            if 2.0 <= distance <= 400.0:
                return distance
            return None

        except Exception:
            return None

    def start(self):
        self.running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        print(f"[Sensor] Sending data to {LAPTOP_IP}:{SENSOR_PORT}")

    def stop(self):
        self.running = False
        if self._thread:
            self._thread.join(timeout=3)
        try:
            self._sock.close()
        except:
            pass
        try:
            self.bus.close()
        except:
            pass
        print("[Sensor] Stopped")

    def _loop(self):
        while self.running:
            self._read_mpu6050()
            self._read_ultrasonic()

            packet = {
                "timestamp": datetime.now().isoformat(),
                "accel": self.accel,
                "gyro": self.gyro,
                "temperature": self.temperature,
                "distance": self.distance,
                "collision": self.collision
            }

            try:
                msg = json.dumps(packet).encode('utf-8')
                self._sock.sendto(msg, (LAPTOP_IP, SENSOR_PORT))
            except Exception as e:
                print(f"[Sensor] UDP send error: {e}")

            time.sleep(SENSOR_SEND_INTERVAL)

    def get_data(self):
        return {
            "accel": self.accel,
            "gyro": self.gyro,
            "temperature": self.temperature,
            "distance": self.distance,
            "collision": self.collision
        }


if __name__ == "__main__":
    sensor = SensorReader()
    sensor.start()
    try:
        while True:
            data = sensor.get_data()
            g = math.sqrt(data['accel']['x']**2 + data['accel']['y']**2 + data['accel']['z']**2)
            print(f"\rG: {g:.2f} | Dist: {data['distance']:.1f}cm | Col: {data['collision']}", end="", flush=True)
            time.sleep(0.2)
    except KeyboardInterrupt:
        sensor.stop()
        GPIO.cleanup()
