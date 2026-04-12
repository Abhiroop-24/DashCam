"""
AI Object Detector using YOLOv8n with CUDA acceleration.
Detects vehicles, pedestrians, and cyclists for proximity awareness.
"""
import cv2
import numpy as np
import threading
import time
from ultralytics import YOLO
from config import (
    YOLO_MODEL, DETECTION_INTERVAL, DETECTION_CLASSES,
    PROXIMITY_THRESHOLD, CONFIDENCE_THRESHOLD,
    FRAME_WIDTH, FRAME_HEIGHT
)


CLASS_NAMES = {
    0: "person", 1: "bicycle", 2: "car", 3: "motorcycle",
    5: "bus", 7: "truck"
}

COLORS = {
    0: (0, 255, 128),    # person - green
    1: (255, 200, 0),    # bicycle - cyan
    2: (0, 128, 255),    # car - orange
    3: (255, 0, 128),    # motorcycle - pink
    5: (128, 0, 255),    # bus - purple
    7: (0, 0, 255),      # truck - red
}


class AIDetector:
    def __init__(self, on_proximity_detection=None):
        self.model = None
        self.running = False
        self._thread = None

        self.detections = []
        self.detection_lock = threading.Lock()
        self.detection_count = 0
        self.inference_time_ms = 0
        self.gpu_enabled = False

        # Frame to process
        self._frame_queue = None
        self._frame_event = threading.Event()

        # Callback when object is dangerously close
        self.on_proximity_detection = on_proximity_detection

    def start(self):
        print("[AIDetector] Loading YOLOv8n model...")
        self.model = YOLO(YOLO_MODEL)

        # Force CUDA if available
        import torch
        if torch.cuda.is_available():
            self.model.to('cuda')
            self.gpu_enabled = True
            gpu_name = torch.cuda.get_device_name(0)
            print(f"[AIDetector] Using GPU: {gpu_name}")
        else:
            print("[AIDetector] WARNING: CUDA not available, using CPU")

        # Warm up the model
        dummy = np.zeros((FRAME_HEIGHT, FRAME_WIDTH, 3), dtype=np.uint8)
        self.model.predict(dummy, verbose=False)
        print("[AIDetector] Model ready")

        self.running = True
        self._thread = threading.Thread(target=self._detect_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self.running = False
        self._frame_event.set()
        if self._thread:
            self._thread.join(timeout=5)
        print("[AIDetector] Stopped")

    def submit_frame(self, frame):
        """Submit a frame for detection (non-blocking)."""
        self._frame_queue = frame
        self._frame_event.set()

    def _detect_loop(self):
        while self.running:
            self._frame_event.wait(timeout=1.0)
            self._frame_event.clear()

            if not self.running:
                break

            frame = self._frame_queue
            if frame is None:
                continue

            try:
                start = time.time()
                results = self.model.predict(
                    frame,
                    classes=DETECTION_CLASSES,
                    conf=CONFIDENCE_THRESHOLD,
                    verbose=False,
                    imgsz=640
                )
                self.inference_time_ms = (time.time() - start) * 1000

                new_detections = []
                frame_area = FRAME_WIDTH * FRAME_HEIGHT

                for result in results:
                    boxes = result.boxes
                    if boxes is None:
                        continue

                    for box in boxes:
                        cls_id = int(box.cls[0])
                        conf = float(box.conf[0])
                        x1, y1, x2, y2 = map(int, box.xyxy[0])

                        bbox_area = (x2 - x1) * (y2 - y1)
                        area_ratio = bbox_area / frame_area

                        det = {
                            "class_id": cls_id,
                            "class_name": CLASS_NAMES.get(cls_id, "unknown"),
                            "confidence": round(conf, 2),
                            "bbox": [x1, y1, x2, y2],
                            "area_ratio": round(area_ratio, 3),
                            "too_close": area_ratio > PROXIMITY_THRESHOLD
                        }
                        new_detections.append(det)

                        if det["too_close"] and self.on_proximity_detection:
                            self.on_proximity_detection(det, frame)

                with self.detection_lock:
                    self.detections = new_detections
                    self.detection_count += 1

            except Exception as e:
                print(f"[AIDetector] Inference error: {e}")

    def get_detections(self):
        with self.detection_lock:
            return list(self.detections)

    def draw_detections(self, frame):
        """Draw bounding boxes on frame and return annotated frame."""
        annotated = frame.copy()
        detections = self.get_detections()

        for det in detections:
            x1, y1, x2, y2 = det["bbox"]
            cls_id = det["class_id"]
            color = COLORS.get(cls_id, (255, 255, 255))

            thickness = 3 if det["too_close"] else 2
            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, thickness)

            label = f"{det['class_name']} {det['confidence']:.0%}"
            if det["too_close"]:
                label += " CLOSE!"
                # Draw warning background
                cv2.rectangle(annotated, (x1, y1 - 30), (x2, y1), (0, 0, 255), -1)
                cv2.putText(annotated, label, (x1 + 4, y1 - 8),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            else:
                label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)[0]
                cv2.rectangle(annotated, (x1, y1 - 22), (x1 + label_size[0] + 8, y1), color, -1)
                cv2.putText(annotated, label, (x1 + 4, y1 - 6),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)

        return annotated

    def get_status(self):
        return {
            "gpu_enabled": self.gpu_enabled,
            "inference_ms": round(self.inference_time_ms, 1),
            "detection_count": self.detection_count,
            "active_detections": len(self.detections)
        }
