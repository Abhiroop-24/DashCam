"""
Command Listener — Receives UDP commands from the laptop.
Handles OLED updates, alerts, and control commands.
"""
import socket
import json
import threading
from config_pi import COMMAND_PORT


class CommandListener:
    def __init__(self, oled_display=None, led_controller=None):
        self.oled = oled_display
        self.led = led_controller
        self.running = False
        self._thread = None
        self._sock = None
        self._handlers = {}

    def register_handler(self, command, handler):
        self._handlers[command] = handler

    def start(self):
        self.running = True
        self._thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._thread.start()
        print(f"[CommandListener] Listening on UDP port {COMMAND_PORT}")

    def stop(self):
        self.running = False
        if self._sock:
            self._sock.close()
        if self._thread:
            self._thread.join(timeout=3)
        print("[CommandListener] Stopped")

    def _listen_loop(self):
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.bind(("0.0.0.0", COMMAND_PORT))
        self._sock.settimeout(1.0)

        while self.running:
            try:
                data, addr = self._sock.recvfrom(4096)
                payload = json.loads(data.decode('utf-8'))
                self._process_command(payload)
            except socket.timeout:
                continue
            except json.JSONDecodeError:
                continue
            except Exception as e:
                if self.running:
                    print(f"[CommandListener] Error: {e}")

    def _process_command(self, payload):
        command = payload.get("command", "")
        data = payload.get("data", {})

        print(f"[CommandListener] Received: {command}")

        if command == "OLED_UPDATE" and self.oled:
            self.oled.update(
                line1=data.get("line1"),
                line2=data.get("line2"),
                line3=data.get("line3"),
                line4=data.get("line4")
            )

        elif command == "ALERT" and self.oled:
            msg = data.get("message", "Alert!")
            self.oled.show_alert(msg)
            if self.led:
                self.led.flash(times=5)

        elif command in self._handlers:
            self._handlers[command](data)

        else:
            print(f"[CommandListener] Unknown command: {command}")
