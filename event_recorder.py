"""
Event Recorder - Saves video clips and snapshots on trigger events.
Uses SQLite for event logging. Videos re-encoded to H.264 for browser playback.
"""
import cv2
import os
import time
import glob
import sqlite3
import subprocess
import threading
from datetime import datetime
from config import (
    RECORDING_DIR, SNAPSHOT_DIR, DB_PATH,
    FRAME_WIDTH, FRAME_HEIGHT, FPS,
    PRE_EVENT_SECONDS, POST_EVENT_SECONDS
)


class EventRecorder:
    def __init__(self, stream_receiver):
        self.stream = stream_receiver
        self.recording = False
        self._record_thread = None
        self._db_lock = threading.Lock()
        self._init_db()

    def _init_db(self):
        with self._db_lock:
            conn = sqlite3.connect(DB_PATH)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    description TEXT,
                    video_path TEXT,
                    snapshot_path TEXT,
                    sensor_data TEXT,
                    created_at REAL
                )
            """)
            conn.commit()
            conn.close()

    def save_event(self, event_type, description="", sensor_data=None, snapshot_frame=None, snapshot_only=False):
        """Save an event: snapshot only, or snapshot + ring buffer video."""
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        video_path = None
        snap_path = None

        # Save snapshot
        if snapshot_frame is not None:
            snap_name = f"{event_type}_{ts}.jpg"
            snap_path = os.path.join(SNAPSHOT_DIR, snap_name)
            cv2.imwrite(snap_path, snapshot_frame, [cv2.IMWRITE_JPEG_QUALITY, 90])
            print(f"[EventRecorder] Snapshot saved: {snap_name}")

        # Save video from ring buffer (async) — skip for snapshot-only events
        if not snapshot_only:
            video_name = f"{event_type}_{ts}.mp4"
            video_path = os.path.join(RECORDING_DIR, video_name)

            buffer_frames = self.stream.get_buffer_snapshot(seconds=PRE_EVENT_SECONDS)

            if buffer_frames:
                t = threading.Thread(
                    target=self._write_video_with_continuation,
                    args=(video_path, buffer_frames, POST_EVENT_SECONDS),
                    daemon=True
                )
                t.start()
            else:
                video_path = None

        # Log to database
        self._log_event(event_type, description, video_path, snap_path, sensor_data)

        return {"video": video_path, "snapshot": snap_path}

    def _write_video_with_continuation(self, path, pre_frames, post_seconds):
        """Write pre-event buffer + continue recording post-event frames.
        Then re-encode to H.264 so browsers can play the video."""
        self.recording = True

        # Write raw video with mp4v first
        tmp_path = path + ".tmp.avi"
        fourcc = cv2.VideoWriter_fourcc(*'XVID')
        writer = cv2.VideoWriter(tmp_path, fourcc, FPS, (FRAME_WIDTH, FRAME_HEIGHT))

        # Write pre-event frames
        for ts, frame in pre_frames:
            if frame.shape[1] != FRAME_WIDTH or frame.shape[0] != FRAME_HEIGHT:
                frame = cv2.resize(frame, (FRAME_WIDTH, FRAME_HEIGHT))
            writer.write(frame)

        # Continue recording post-event
        end_time = time.time() + post_seconds
        while time.time() < end_time:
            frame = self.stream.get_frame()
            if frame is not None:
                if frame.shape[1] != FRAME_WIDTH or frame.shape[0] != FRAME_HEIGHT:
                    frame = cv2.resize(frame, (FRAME_WIDTH, FRAME_HEIGHT))
                writer.write(frame)
            time.sleep(1.0 / FPS)

        writer.release()
        self.recording = False

        # Re-encode to H.264 mp4 for browser playback
        try:
            subprocess.run(
                [
                    "ffmpeg", "-y", "-i", tmp_path,
                    "-c:v", "libx264", "-preset", "fast",
                    "-crf", "23", "-pix_fmt", "yuv420p",
                    "-movflags", "+faststart",
                    path
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=30
            )
            os.remove(tmp_path)
            print(f"[EventRecorder] Video saved: {os.path.basename(path)}")
        except Exception as e:
            # Fallback: rename raw file
            if os.path.exists(tmp_path):
                os.rename(tmp_path, path)
            print(f"[EventRecorder] Video saved (raw): {os.path.basename(path)} ({e})")

    def _log_event(self, event_type, description, video_path, snap_path, sensor_data):
        import json
        with self._db_lock:
            conn = sqlite3.connect(DB_PATH)
            conn.execute(
                "INSERT INTO events (timestamp, event_type, description, video_path, snapshot_path, sensor_data, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    datetime.now().isoformat(),
                    event_type,
                    description,
                    video_path,
                    snap_path,
                    json.dumps(sensor_data) if sensor_data else None,
                    time.time()
                )
            )
            conn.commit()
            conn.close()

    def get_events(self, limit=50):
        with self._db_lock:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM events ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
            conn.close()
            return [dict(row) for row in rows]

    def get_event_count(self):
        with self._db_lock:
            conn = sqlite3.connect(DB_PATH)
            count = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
            conn.close()
            return count

    def clear_all(self):
        """Delete all recordings, snapshots, and database entries."""
        with self._db_lock:
            # Clear database
            conn = sqlite3.connect(DB_PATH)
            conn.execute("DELETE FROM events")
            conn.commit()
            conn.close()

        # Delete snapshot files
        for f in glob.glob(os.path.join(SNAPSHOT_DIR, "*")):
            try:
                os.remove(f)
            except Exception:
                pass

        # Delete recording files
        for f in glob.glob(os.path.join(RECORDING_DIR, "*")):
            try:
                os.remove(f)
            except Exception:
                pass

        print("[EventRecorder] All recordings and snapshots cleared.")
