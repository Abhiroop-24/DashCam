"""
Camera Stream — Streams H264 video over UDP to laptop using rpicam-vid + ffmpeg.
"""
import subprocess
import os
import time
import threading
from config_pi import LAPTOP_IP, VIDEO_PORT, CAMERA_WIDTH, CAMERA_HEIGHT, CAMERA_FPS


class CameraStream:
    def __init__(self):
        self.process = None
        self.running = False
        self._thread = None

    def start(self):
        self.running = True
        self._thread = threading.Thread(target=self._stream_loop, daemon=True)
        self._thread.start()
        print(f"[Camera] Streaming to udp://{LAPTOP_IP}:{VIDEO_PORT}")

    def stop(self):
        self.running = False
        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.process.kill()
        os.system("killall rpicam-vid ffmpeg 2>/dev/null")
        print("[Camera] Stopped")

    def _stream_loop(self):
        while self.running:
            try:
                cmd = (
                    f"rpicam-vid -t 0 "
                    f"--width {CAMERA_WIDTH} --height {CAMERA_HEIGHT} "
                    f"--framerate {CAMERA_FPS} "
                    f"--inline --intra {CAMERA_FPS} "
                    f"--profile baseline --codec h264 --flush "
                    f"-o - | "
                    f"ffmpeg -y -f h264 -i - "
                    f"-c:v copy -f mpegts -flush_packets 1 "
                    f"\"udp://{LAPTOP_IP}:{VIDEO_PORT}?pkt_size=1316\""
                )

                self.process = subprocess.Popen(
                    cmd, shell=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )

                print("[Camera] Stream started")

                while self.running:
                    if self.process.poll() is not None:
                        print("[Camera] Process died, restarting...")
                        break
                    time.sleep(1)

            except Exception as e:
                print(f"[Camera] Error: {e}")
                time.sleep(3)

    def is_alive(self):
        return self.process is not None and self.process.poll() is None


if __name__ == "__main__":
    cam = CameraStream()
    cam.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        cam.stop()
