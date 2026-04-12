"""
OLED Display Controller — SSD1306 128x64 on software I2C bus 3.

Wiring:
  SCL → GPIO25 (Pin 22)
  SDA → GPIO26 (Pin 21)  -- NOTE: Physical Pin 21 is GPIO9 on standard header,
                            but user has GPIO26 on Pin 37. Using I2C bus 3 overlay.
  VCC → 3.3V
  GND → GND
  Address: 0x3C
"""
import threading
import time

LUMA_AVAILABLE = False
try:
    from luma.core.interface.serial import i2c
    from luma.oled.device import ssd1306
    from luma.core.render import canvas
    LUMA_AVAILABLE = True
except ImportError:
    pass

# Fallback: direct SSD1306 via smbus2
SMBUS_AVAILABLE = False
if not LUMA_AVAILABLE:
    try:
        import smbus2
        SMBUS_AVAILABLE = True
    except ImportError:
        pass

from config_pi import OLED_I2C_BUS, OLED_WIDTH, OLED_HEIGHT


SSD1306_ADDR = 0x3C

# SSD1306 init sequence for 128x64
SSD1306_INIT = [
    0xAE,        # display off
    0xD5, 0x80,  # clock div
    0xA8, 0x3F,  # multiplex 63
    0xD3, 0x00,  # display offset 0
    0x40,        # start line 0
    0x8D, 0x14,  # charge pump enable
    0x20, 0x00,  # horizontal addressing
    0xA1,        # segment remap
    0xC8,        # com scan dec
    0xDA, 0x12,  # com pins
    0x81, 0xCF,  # contrast
    0xD9, 0xF1,  # precharge
    0xDB, 0x40,  # vcomh deselect
    0xA4,        # display from RAM
    0xA6,        # normal display
    0xAF,        # display on
]


class DirectSSD1306:
    """Direct SSD1306 driver using smbus2 — fallback when luma is not installed."""

    def __init__(self, bus_num, addr=SSD1306_ADDR):
        self.bus = smbus2.SMBus(bus_num)
        self.addr = addr
        self.width = 128
        self.height = 64
        self.pages = self.height // 8
        self.buffer = [0x00] * (self.width * self.pages)
        self._init_display()

    def _cmd(self, c):
        self.bus.write_byte_data(self.addr, 0x00, c)

    def _init_display(self):
        for cmd in SSD1306_INIT:
            self._cmd(cmd)
            time.sleep(0.001)

    def clear(self):
        self.buffer = [0x00] * (self.width * self.pages)

    def set_pixel(self, x, y, on=True):
        if 0 <= x < self.width and 0 <= y < self.height:
            page = y // 8
            bit = y % 8
            idx = page * self.width + x
            if on:
                self.buffer[idx] |= (1 << bit)
            else:
                self.buffer[idx] &= ~(1 << bit)

    def draw_char(self, x, y, ch):
        """Draw a simple 5x7 character at (x, y). Uses built-in tiny font."""
        FONT = _get_font()
        code = ord(ch)
        if code < 32 or code > 127:
            code = 32
        idx = code - 32
        for col in range(5):
            bits = FONT[idx * 5 + col] if idx * 5 + col < len(FONT) else 0
            for row in range(7):
                if bits & (1 << row):
                    self.set_pixel(x + col, y + row, True)

    def draw_text(self, x, y, text):
        for i, ch in enumerate(text):
            self.draw_char(x + i * 6, y, ch)

    def show(self):
        # Set column and page address
        self._cmd(0x21)  # column addr
        self._cmd(0)
        self._cmd(self.width - 1)
        self._cmd(0x22)  # page addr
        self._cmd(0)
        self._cmd(self.pages - 1)

        # Send buffer in 32-byte chunks
        for i in range(0, len(self.buffer), 32):
            chunk = self.buffer[i:i+32]
            self.bus.write_i2c_block_data(self.addr, 0x40, chunk)

    def off(self):
        self._cmd(0xAE)

    def close(self):
        self.off()
        self.bus.close()


def _get_font():
    """Minimal 5x7 ASCII font (chars 32-127)."""
    return [
        0x00,0x00,0x00,0x00,0x00, # space
        0x00,0x00,0x5F,0x00,0x00, # !
        0x00,0x07,0x00,0x07,0x00, # "
        0x14,0x7F,0x14,0x7F,0x14, # #
        0x24,0x2A,0x7F,0x2A,0x12, # $
        0x23,0x13,0x08,0x64,0x62, # %
        0x36,0x49,0x55,0x22,0x50, # &
        0x00,0x05,0x03,0x00,0x00, # '
        0x00,0x1C,0x22,0x41,0x00, # (
        0x00,0x41,0x22,0x1C,0x00, # )
        0x08,0x2A,0x1C,0x2A,0x08, # *
        0x08,0x08,0x3E,0x08,0x08, # +
        0x00,0x50,0x30,0x00,0x00, # ,
        0x08,0x08,0x08,0x08,0x08, # -
        0x00,0x60,0x60,0x00,0x00, # .
        0x20,0x10,0x08,0x04,0x02, # /
        0x3E,0x51,0x49,0x45,0x3E, # 0
        0x00,0x42,0x7F,0x40,0x00, # 1
        0x42,0x61,0x51,0x49,0x46, # 2
        0x21,0x41,0x45,0x4B,0x31, # 3
        0x18,0x14,0x12,0x7F,0x10, # 4
        0x27,0x45,0x45,0x45,0x39, # 5
        0x3C,0x4A,0x49,0x49,0x30, # 6
        0x01,0x71,0x09,0x05,0x03, # 7
        0x36,0x49,0x49,0x49,0x36, # 8
        0x06,0x49,0x49,0x29,0x1E, # 9
        0x00,0x36,0x36,0x00,0x00, # :
        0x00,0x56,0x36,0x00,0x00, # ;
        0x00,0x08,0x14,0x22,0x41, # <
        0x14,0x14,0x14,0x14,0x14, # =
        0x41,0x22,0x14,0x08,0x00, # >
        0x02,0x01,0x51,0x09,0x06, # ?
        0x32,0x49,0x79,0x41,0x3E, # @
        0x7E,0x11,0x11,0x11,0x7E, # A
        0x7F,0x49,0x49,0x49,0x36, # B
        0x3E,0x41,0x41,0x41,0x22, # C
        0x7F,0x41,0x41,0x22,0x1C, # D
        0x7F,0x49,0x49,0x49,0x41, # E
        0x7F,0x09,0x09,0x01,0x01, # F
        0x3E,0x41,0x41,0x51,0x32, # G
        0x7F,0x08,0x08,0x08,0x7F, # H
        0x00,0x41,0x7F,0x41,0x00, # I
        0x20,0x40,0x41,0x3F,0x01, # J
        0x7F,0x08,0x14,0x22,0x41, # K
        0x7F,0x40,0x40,0x40,0x40, # L
        0x7F,0x02,0x04,0x02,0x7F, # M
        0x7F,0x04,0x08,0x10,0x7F, # N
        0x3E,0x41,0x41,0x41,0x3E, # O
        0x7F,0x09,0x09,0x09,0x06, # P
        0x3E,0x41,0x51,0x21,0x5E, # Q
        0x7F,0x09,0x19,0x29,0x46, # R
        0x46,0x49,0x49,0x49,0x31, # S
        0x01,0x01,0x7F,0x01,0x01, # T
        0x3F,0x40,0x40,0x40,0x3F, # U
        0x1F,0x20,0x40,0x20,0x1F, # V
        0x7F,0x20,0x18,0x20,0x7F, # W
        0x63,0x14,0x08,0x14,0x63, # X
        0x03,0x04,0x78,0x04,0x03, # Y
        0x61,0x51,0x49,0x45,0x43, # Z
        0x00,0x00,0x7F,0x41,0x41, # [
        0x02,0x04,0x08,0x10,0x20, # backslash
        0x41,0x41,0x7F,0x00,0x00, # ]
        0x04,0x02,0x01,0x02,0x04, # ^
        0x40,0x40,0x40,0x40,0x40, # _
        0x00,0x01,0x02,0x04,0x00, # `
        0x20,0x54,0x54,0x54,0x78, # a
        0x7F,0x48,0x44,0x44,0x38, # b
        0x38,0x44,0x44,0x44,0x20, # c
        0x38,0x44,0x44,0x48,0x7F, # d
        0x38,0x54,0x54,0x54,0x18, # e
        0x08,0x7E,0x09,0x01,0x02, # f
        0x08,0x14,0x54,0x54,0x3C, # g
        0x7F,0x08,0x04,0x04,0x78, # h
        0x00,0x44,0x7D,0x40,0x00, # i
        0x20,0x40,0x44,0x3D,0x00, # j
        0x00,0x7F,0x10,0x28,0x44, # k
        0x00,0x41,0x7F,0x40,0x00, # l
        0x7C,0x04,0x18,0x04,0x78, # m
        0x7C,0x08,0x04,0x04,0x78, # n
        0x38,0x44,0x44,0x44,0x38, # o
        0x7C,0x14,0x14,0x14,0x08, # p
        0x08,0x14,0x14,0x18,0x7C, # q
        0x7C,0x08,0x04,0x04,0x08, # r
        0x48,0x54,0x54,0x54,0x20, # s
        0x04,0x3F,0x44,0x40,0x20, # t
        0x3C,0x40,0x40,0x20,0x7C, # u
        0x1C,0x20,0x40,0x20,0x1C, # v
        0x3C,0x40,0x30,0x40,0x3C, # w
        0x44,0x28,0x10,0x28,0x44, # x
        0x0C,0x50,0x50,0x50,0x3C, # y
        0x44,0x64,0x54,0x4C,0x44, # z
        0x00,0x08,0x36,0x41,0x00, # {
        0x00,0x00,0x7F,0x00,0x00, # |
        0x00,0x41,0x36,0x08,0x00, # }
        0x08,0x08,0x2A,0x1C,0x08, # ~
        0x08,0x1C,0x2A,0x08,0x08, # DEL
    ]


class OLEDDisplay:
    def __init__(self):
        self.device = None
        self.direct = None
        self.lines = ["DashCam Starting...", "", "", ""]
        self._lock = threading.Lock()
        self._thread = None
        self.running = False
        self.use_luma = False

        if LUMA_AVAILABLE:
            try:
                serial = i2c(port=OLED_I2C_BUS, address=SSD1306_ADDR)
                self.device = ssd1306(serial, width=OLED_WIDTH, height=OLED_HEIGHT)
                self.device.contrast(200)
                self.use_luma = True
                print("[OLED] Initialized with luma.oled on bus 3")
            except Exception as e:
                print(f"[OLED] luma init failed: {e}, trying direct driver")

        if not self.use_luma and SMBUS_AVAILABLE:
            try:
                self.direct = DirectSSD1306(OLED_I2C_BUS, SSD1306_ADDR)
                print("[OLED] Initialized with direct SSD1306 driver on bus 3")
            except Exception as e:
                print(f"[OLED] Direct init also failed: {e}")
                self.direct = None

        if not self.use_luma and self.direct is None:
            print("[OLED] WARNING: No display driver available. OLED disabled.")

    def start(self):
        if not self.use_luma and self.direct is None:
            return
        self.running = True
        self._thread = threading.Thread(target=self._refresh_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self.running = False
        if self._thread:
            self._thread.join(timeout=2)
        if self.use_luma and self.device:
            try:
                self.device.hide()
            except:
                pass
        if self.direct:
            try:
                self.direct.close()
            except:
                pass
        print("[OLED] Stopped")

    def update(self, line1=None, line2=None, line3=None, line4=None):
        with self._lock:
            if line1 is not None:
                self.lines[0] = str(line1)[:21]
            if line2 is not None:
                self.lines[1] = str(line2)[:21]
            if line3 is not None:
                self.lines[2] = str(line3)[:21]
            if line4 is not None:
                self.lines[3] = str(line4)[:21]

    def show_alert(self, message, duration=3):
        old_lines = list(self.lines)
        self.update(line1="!! ALERT !!", line2=str(message)[:21], line3="", line4="")
        time.sleep(duration)
        with self._lock:
            self.lines = old_lines

    def _refresh_loop(self):
        while self.running:
            try:
                with self._lock:
                    lines = list(self.lines)

                if self.use_luma:
                    self._draw_luma(lines)
                elif self.direct:
                    self._draw_direct(lines)

            except Exception as e:
                print(f"[OLED] Refresh error: {e}")

            time.sleep(0.5)

    def _draw_luma(self, lines):
        with canvas(self.device) as draw:
            y = 2
            for line in lines:
                draw.text((2, y), line, fill="white")
                y += 15

    def _draw_direct(self, lines):
        self.direct.clear()
        y = 2
        for line in lines:
            self.direct.draw_text(2, y, line)
            y += 15
        self.direct.show()


if __name__ == "__main__":
    oled = OLEDDisplay()
    oled.start()
    oled.update("DashCam AI", "Status: Ready", "Stream: Active", "IP: 10.42.0.116")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        oled.stop()
