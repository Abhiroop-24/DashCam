"""
Flask + Socket.IO Dashboard for the Smart DashCam system.
Serves live video, real-time sensor data, and event gallery.
"""
import cv2
import os
import json
import time
import threading
from flask import Flask, render_template, Response, jsonify, send_from_directory, request
from flask_socketio import SocketIO
import config
from config import (
    DASHBOARD_HOST, DASHBOARD_PORT,
    RECORDING_DIR, SNAPSHOT_DIR
)


app = Flask(__name__)
app.config['SECRET_KEY'] = 'dashcam-secret-2024'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# References set by main.py
stream_receiver = None
sensor_listener = None
ai_detector = None
event_recorder = None
pi_comm = None


def init_dashboard(stream, sensor, detector, recorder, comm):
    global stream_receiver, sensor_listener, ai_detector, event_recorder, pi_comm
    stream_receiver = stream
    sensor_listener = sensor
    ai_detector = detector
    event_recorder = recorder
    pi_comm = comm


# ─── Routes ──────────────────────────────────────────────

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/video_feed')
def video_feed():
    """MJPEG stream endpoint for the dashboard."""
    return Response(
        _generate_frames(),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )


def _generate_frames():
    while True:
        if stream_receiver is None:
            time.sleep(0.1)
            continue

        frame = stream_receiver.get_frame()
        if frame is None:
            # Send a black frame placeholder
            import numpy as np
            frame = np.zeros((600, 800, 3), dtype=np.uint8)
            cv2.putText(frame, "Waiting for stream...", (200, 300),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.2, (100, 100, 100), 2)

        # Draw AI detections if available
        if ai_detector is not None:
            frame = ai_detector.draw_detections(frame)

        # Draw recording indicator
        if event_recorder and event_recorder.recording:
            cv2.circle(frame, (30, 30), 12, (0, 0, 255), -1)
            cv2.putText(frame, "REC", (50, 38),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

        # Encode to JPEG
        ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 75])
        if not ret:
            continue

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' +
               buffer.tobytes() + b'\r\n')

        time.sleep(0.033)  # ~30fps


@app.route('/api/status')
def api_status():
    status = {
        "stream": stream_receiver.get_status() if stream_receiver else {},
        "sensor": sensor_listener.get_status() if sensor_listener else {},
        "ai": ai_detector.get_status() if ai_detector else {},
        "events": event_recorder.get_event_count() if event_recorder else 0,
        "recording": event_recorder.recording if event_recorder else False
    }
    return jsonify(status)


@app.route('/api/sensor')
def api_sensor():
    if sensor_listener:
        return jsonify(sensor_listener.get_data())
    return jsonify({})


@app.route('/api/events')
def api_events():
    if event_recorder:
        events = event_recorder.get_events(limit=50)
        # Convert paths to web-accessible URLs
        for evt in events:
            if evt.get("snapshot_path") and os.path.exists(evt["snapshot_path"]):
                evt["snapshot_url"] = f"/snapshots/{os.path.basename(evt['snapshot_path'])}"
            if evt.get("video_path") and os.path.exists(evt["video_path"]):
                evt["video_url"] = f"/recordings/{os.path.basename(evt['video_path'])}"
        return jsonify(events)
    return jsonify([])


@app.route('/api/detections')
def api_detections():
    if ai_detector:
        return jsonify(ai_detector.get_detections())
    return jsonify([])


@app.route('/api/settings', methods=['GET', 'POST'])
def api_settings():
    if request.method == 'POST':
        data = request.get_json()
        if 'distance_threshold' in data:
            val = max(5, min(200, int(data['distance_threshold'])))
            config.DISTANCE_ALERT_CM = val
            print(f"[Dashboard] Ultrasonic threshold set to {val}cm")
        if 'proximity_threshold' in data:
            val = max(0.05, min(0.80, float(data['proximity_threshold'])))
            config.PROXIMITY_THRESHOLD = val
        return jsonify({'ok': True})
    return jsonify({
        'distance_threshold': config.DISTANCE_ALERT_CM,
        'proximity_threshold': config.PROXIMITY_THRESHOLD,
        'g_force_threshold': config.G_FORCE_THRESHOLD
    })


@app.route('/snapshots/<filename>')
def serve_snapshot(filename):
    return send_from_directory(SNAPSHOT_DIR, filename)


@app.route('/recordings/<filename>')
def serve_recording(filename):
    return send_from_directory(RECORDING_DIR, filename)


@app.route('/api/clear', methods=['POST'])
def api_clear():
    if event_recorder:
        event_recorder.clear_all()
        return jsonify({'ok': True, 'message': 'All cleared'})
    return jsonify({'ok': False})


# ─── Socket.IO Events ────────────────────────────────────

@socketio.on('connect')
def handle_connect():
    print("[Dashboard] Client connected")


@socketio.on('command')
def handle_command(data):
    """Handle commands from the dashboard UI."""
    cmd = data.get('command', '')

    if cmd == 'snapshot' and stream_receiver:
        frame = stream_receiver.get_frame()
        if frame is not None and event_recorder:
            event_recorder.save_event("manual_snapshot", "Manual snapshot from dashboard", snapshot_frame=frame)
            socketio.emit('notification', {'type': 'success', 'message': 'Snapshot saved!'})

    elif cmd == 'record_event' and event_recorder:
        frame = stream_receiver.get_frame() if stream_receiver else None
        sensor = sensor_listener.get_data() if sensor_listener else None
        event_recorder.save_event("manual_record", "Manual recording from dashboard",
                                  sensor_data=sensor, snapshot_frame=frame)
        socketio.emit('notification', {'type': 'success', 'message': 'Event recording started!'})

    elif cmd == 'pi_command' and pi_comm:
        pi_cmd = data.get('pi_command', '')
        pi_comm.send_command(pi_cmd)

    elif cmd == 'sos_manual':
        from main import trigger_sos
        frame = stream_receiver.get_frame() if stream_receiver else None
        sensor = sensor_listener.get_data() if sensor_listener else None
        trigger_sos(
            "Manual SOS activated from dashboard",
            sensor_data=sensor,
            frame=frame,
            recorder=event_recorder,
            pi_comm=pi_comm
        )

    elif cmd == 'sos_cancel':
        from main import cancel_sos
        cancel_sos(pi_comm=pi_comm)


def emit_realtime_data():
    """Background thread to push real-time data via Socket.IO."""
    while True:
        try:
            data = {}

            if sensor_listener:
                data['sensor'] = sensor_listener.get_data()

            if ai_detector:
                data['detections'] = ai_detector.get_detections()
                data['ai_status'] = ai_detector.get_status()

            if stream_receiver:
                data['stream'] = stream_receiver.get_status()

            if event_recorder:
                data['recording'] = event_recorder.recording
                data['event_count'] = event_recorder.get_event_count()

            data['settings'] = {
                'distance_threshold': config.DISTANCE_ALERT_CM
            }

            socketio.emit('realtime_data', data)

        except Exception as e:
            pass

        socketio.sleep(0.5)  # 2 updates per second


def run_dashboard():
    """Start the dashboard server."""
    # Start real-time data emitter
    socketio.start_background_task(emit_realtime_data)

    print(f"[Dashboard] Starting on http://{DASHBOARD_HOST}:{DASHBOARD_PORT}")
    socketio.run(app, host=DASHBOARD_HOST, port=DASHBOARD_PORT,
                 debug=False, use_reloader=False, allow_unsafe_werkzeug=True)
