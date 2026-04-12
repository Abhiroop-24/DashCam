"""
UDP H264 Video Stream Receiver with 30-second Ring Buffer.
Receives MPEGTS/H264 stream from Raspberry Pi and decodes frames using OpenCV + ffmpeg.
"""
import cv2
import numpy as np
import threading
import time
import collections
import subprocess
import sys
from config import (
    VIDEO_PORT, FRAME_WIDTH, FRAME_HEIGHT, FPS,
    BUFFER_SIZE, BUFFER_SECONDS
)


class StreamReceiver:
    def __init__(self):
        self.frame_buffer = collections.deque(maxlen=BUFFER_SIZE)
        self.current_frame = None
        self.frame_lock = threading.Lock()
        self.running = False
        self.connected = False
        self.frame_count = 0
        self.fps_actual = 0.0
        self._cap = None
        self._thread = None

    def start(self):
        self.running = True
        self._thread = threading.Thread(target=self._receive_loop, daemon=True)
        self._thread.start()
        print(f"[StreamReceiver] Listening for video on UDP port {VIDEO_PORT}")

    def stop(self):
        self.running = False
        if self._cap:
            self._cap.release()
        if self._thread:
            self._thread.join(timeout=3)
        print("[StreamReceiver] Stopped")

    def _receive_loop(self):
        uri = f"udp://@:{VIDEO_PORT}"

        while self.running:
            try:
                self._cap = cv2.VideoCapture(uri, cv2.CAP_FFMPEG)
                self._cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

                if not self._cap.isOpened():
                    print("[StreamReceiver] Waiting for stream...")
                    time.sleep(2)
                    continue

                self.connected = True
                print("[StreamReceiver] Stream connected!")

                fps_timer = time.time()
                fps_count = 0

                while self.running:
                    ret, frame = self._cap.read()
                    if not ret:
                        print("[StreamReceiver] Stream lost, reconnecting...")
                        self.connected = False
                        break

                    timestamp = time.time()

                    with self.frame_lock:
                        self.current_frame = frame.copy()
                        self.frame_buffer.append((timestamp, frame.copy()))
                        self.frame_count += 1

                    fps_count += 1
                    elapsed = time.time() - fps_timer
                    if elapsed >= 1.0:
                        self.fps_actual = fps_count / elapsed
                        fps_count = 0
                        fps_timer = time.time()

            except Exception as e:
                print(f"[StreamReceiver] Error: {e}")
                self.connected = False
                time.sleep(2)

            finally:
                if self._cap:
                    self._cap.release()

    def get_frame(self):
        with self.frame_lock:
            if self.current_frame is not None:
                return self.current_frame.copy()
            return None

    def get_buffer_snapshot(self, seconds=None):
        """Get a copy of the ring buffer (or last N seconds)."""
        with self.frame_lock:
            frames = list(self.frame_buffer)

        if seconds and frames:
            cutoff = time.time() - seconds
            frames = [(ts, f) for ts, f in frames if ts >= cutoff]

        return frames

    def get_status(self):
        return {
            "connected": self.connected,
            "frame_count": self.frame_count,
            "fps": round(self.fps_actual, 1),
            "buffer_frames": len(self.frame_buffer),
            "buffer_seconds": len(self.frame_buffer) / FPS if self.frame_buffer else 0
        }


if __name__ == "__main__":
    receiver = StreamReceiver()
    receiver.start()

    try:
        while True:
            frame = receiver.get_frame()
            if frame is not None:
                cv2.imshow("DashCam Stream", frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
            else:
                time.sleep(0.1)
    except KeyboardInterrupt:
        pass
    finally:
        receiver.stop()
        cv2.destroyAllWindows()
