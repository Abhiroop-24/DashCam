"""
Pi Communicator - Sends commands to the Raspberry Pi via UDP.
"""
import socket
import json
import threading
from config import PI_IP, COMMAND_PORT


class PiCommunicator:
    def __init__(self):
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def send_command(self, command, data=None):
        """Send a command to Pi."""
        payload = {
            "command": command,
            "data": data or {}
        }
        try:
            msg = json.dumps(payload).encode('utf-8')
            self._sock.sendto(msg, (PI_IP, COMMAND_PORT))
            print(f"[PiComm] Sent: {command}")
            return True
        except Exception as e:
            print(f"[PiComm] Send error: {e}")
            return False

    def record_start(self):
        return self.send_command("RECORD_START")

    def record_stop(self):
        return self.send_command("RECORD_STOP")

    def take_snapshot(self):
        return self.send_command("TAKE_SNAPSHOT")

    def update_oled(self, line1="", line2="", line3="", line4=""):
        return self.send_command("OLED_UPDATE", {
            "line1": line1,
            "line2": line2,
            "line3": line3,
            "line4": line4
        })

    def send_alert(self, message):
        return self.send_command("ALERT", {"message": message})

    def close(self):
        self._sock.close()
