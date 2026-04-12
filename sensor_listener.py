"""
Sensor Data Listener - Receives MPU6050 + Ultrasonic data from Pi via UDP.
"""
import socket
import json
import threading
import time
import math
from config import SENSOR_PORT, G_FORCE_THRESHOLD, DISTANCE_ALERT_CM


class SensorListener:
    def __init__(self, on_collision=None, on_proximity_alert=None):
        self.running = False
        self._thread = None
        self._sock = None

        # Latest sensor data
        self.latest_data = {
            "timestamp": None,
            "accel": {"x": 0.0, "y": 0.0, "z": 0.0},
            "gyro": {"x": 0.0, "y": 0.0, "z": 0.0},
            "temperature": 0.0,
            "distance": 999.0,
            "collision": False,
            "g_force": 0.0
        }
        self.data_lock = threading.Lock()
        self.connected = False
        self.last_packet_time = 0

        # Callbacks
        self.on_collision = on_collision
        self.on_proximity_alert = on_proximity_alert

        # Collision tracking
        self._collision_start = None
        self._collision_triggered = False

    def start(self):
        self.running = True
        self._thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._thread.start()
        print(f"[SensorListener] Listening on UDP port {SENSOR_PORT}")

    def stop(self):
        self.running = False
        if self._sock:
            self._sock.close()
        if self._thread:
            self._thread.join(timeout=3)
        print("[SensorListener] Stopped")

    def _listen_loop(self):
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.bind(("0.0.0.0", SENSOR_PORT))
        self._sock.settimeout(1.0)

        while self.running:
            try:
                data, addr = self._sock.recvfrom(4096)
                packet = json.loads(data.decode('utf-8'))
                self._process_packet(packet)
            except socket.timeout:
                if time.time() - self.last_packet_time > 5:
                    self.connected = False
                continue
            except json.JSONDecodeError:
                continue
            except Exception as e:
                if self.running:
                    print(f"[SensorListener] Error: {e}")
                    time.sleep(0.5)

    def _process_packet(self, packet):
        accel = packet.get("accel", {})
        ax = accel.get("x", 0)
        ay = accel.get("y", 0)
        az = accel.get("z", 0)

        g_force = math.sqrt(ax**2 + ay**2 + az**2)
        distance = packet.get("distance", 999.0)

        with self.data_lock:
            self.latest_data = {
                "timestamp": packet.get("timestamp"),
                "accel": accel,
                "gyro": packet.get("gyro", {}),
                "temperature": packet.get("temperature", 0.0),
                "distance": distance,
                "collision": packet.get("collision", False),
                "g_force": round(g_force, 3)
            }
            self.last_packet_time = time.time()
            self.connected = True

        # Check collision from Pi or computed G-force
        if packet.get("collision", False) or g_force > G_FORCE_THRESHOLD:
            if not self._collision_triggered:
                self._collision_triggered = True
                print(f"[SensorListener] COLLISION DETECTED! G-force: {g_force:.2f}g")
                if self.on_collision:
                    self.on_collision(self.latest_data)

                # Reset after 5 seconds
                threading.Timer(5.0, self._reset_collision).start()

        # Check proximity alert
        if distance < DISTANCE_ALERT_CM:
            if self.on_proximity_alert:
                self.on_proximity_alert(distance)

    def _reset_collision(self):
        self._collision_triggered = False

    def get_data(self):
        with self.data_lock:
            return dict(self.latest_data)

    def get_status(self):
        return {
            "connected": self.connected,
            "last_packet": self.last_packet_time,
            "g_force": self.latest_data.get("g_force", 0),
            "distance": self.latest_data.get("distance", 999)
        }


if __name__ == "__main__":
    def on_collision(data):
        print(f"COLLISION! Data: {data}")

    def on_proximity(dist):
        print(f"PROXIMITY ALERT: {dist:.1f}cm")

    listener = SensorListener(on_collision=on_collision, on_proximity_alert=on_proximity)
    listener.start()

    try:
        while True:
            data = listener.get_data()
            print(f"\rG: {data['g_force']:.2f}g | Dist: {data['distance']:.1f}cm", end="")
            time.sleep(0.2)
    except KeyboardInterrupt:
        listener.stop()
