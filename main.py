"""
Smart DashCam & Collision Monitoring System — Main Entry Point
"""
import signal
import sys
import time
import threading

import config
from stream_receiver import StreamReceiver
from sensor_listener import SensorListener
from ai_detector import AIDetector
from event_recorder import EventRecorder
from pi_communicator import PiCommunicator
from dashboard import init_dashboard, run_dashboard, socketio


def main():
    print("=" * 56)
    print("  Smart DashCam & Collision Monitoring System")
    print("  AI-Powered | RTX 2050 | YOLOv8n")
    print("=" * 56)
    print()

    stream = StreamReceiver()
    recorder = EventRecorder(stream)
    pi_comm = PiCommunicator()

    # Cooldown to prevent spam — one event per 15 seconds max
    last_proximity_event = 0
    last_collision_event = 0
    PROXIMITY_COOLDOWN = 15
    COLLISION_COOLDOWN = 10

    # Collision callback — saves 5s buffer + snapshot
    def on_collision(sensor_data):
        nonlocal last_collision_event
        now = time.time()
        if now - last_collision_event < COLLISION_COOLDOWN:
            return
        last_collision_event = now

        print("\n[MAIN] *** COLLISION EVENT ***")
        frame = stream.get_frame()
        recorder.save_event(
            "collision",
            f"G-force: {sensor_data.get('g_force', 0):.2f}g",
            sensor_data=sensor_data,
            snapshot_frame=frame
        )
        pi_comm.send_alert("COLLISION DETECTED")
        try:
            socketio.emit('collision_alert', {})
        except Exception:
            pass

    # AI proximity — ONLY triggers when AI sees person close AND ultrasonic < threshold
    def on_ai_proximity(detection, frame):
        nonlocal last_proximity_event
        now = time.time()
        if now - last_proximity_event < PROXIMITY_COOLDOWN:
            return

        # Check ultrasonic distance too
        sensor_data = sensor.get_data()
        ultrasonic_dist = sensor_data.get("distance", 999)
        threshold = config.DISTANCE_ALERT_CM

        if ultrasonic_dist > threshold:
            return  # Ultrasonic doesn't agree, skip

        last_proximity_event = now
        print(f"\n[MAIN] *** PROXIMITY: {detection['class_name']} at {detection['area_ratio']:.0%} + ultrasonic {ultrasonic_dist:.0f}cm ***")
        recorder.save_event(
            "proximity",
            f"{detection['class_name']} close ({detection['area_ratio']:.0%}) + ultrasonic {ultrasonic_dist:.0f}cm",
            sensor_data=sensor_data,
            snapshot_frame=frame
        )

    # Sensor listener — collision only, NO proximity spam
    sensor = SensorListener(
        on_collision=on_collision,
        on_proximity_alert=None  # Disabled — handled by AI+ultrasonic combo
    )

    detector = AIDetector(on_proximity_detection=on_ai_proximity)

    init_dashboard(stream, sensor, detector, recorder, pi_comm)

    stream.start()
    sensor.start()
    detector.start()

    frame_counter = 0

    def ai_loop():
        nonlocal frame_counter
        while True:
            frame = stream.get_frame()
            if frame is not None:
                frame_counter += 1
                if frame_counter % config.DETECTION_INTERVAL == 0:
                    detector.submit_frame(frame)
            time.sleep(0.01)

    ai_thread = threading.Thread(target=ai_loop, daemon=True)
    ai_thread.start()

    def shutdown(signum=None, frame=None):
        print("\n\n[MAIN] Shutting down...")
        stream.stop()
        sensor.stop()
        detector.stop()
        pi_comm.close()
        print("[MAIN] Goodbye!")
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    pi_comm.update_oled(
        line1="DashCam Active",
        line2="AI: YOLOv8n",
        line3="Stream: OK",
        line4=""
    )

    print("\n[MAIN] All systems started!")
    print(f"[MAIN] Dashboard: http://localhost:5000")
    print("[MAIN] Press Ctrl+C to stop\n")

    run_dashboard()


if __name__ == "__main__":
    main()
