"""
Configuration for Raspberry Pi DashCam components.
"""

# Network
LAPTOP_IP = "10.42.0.1"
PI_IP = "10.42.0.116"
VIDEO_PORT = 8080
SENSOR_PORT = 8081
COMMAND_PORT = 8082

# Camera
CAMERA_WIDTH = 800
CAMERA_HEIGHT = 600
CAMERA_FPS = 30

# MPU6050
MPU_I2C_BUS = 1
MPU_ADDRESS = 0x68
G_FORCE_THRESHOLD = 1.5

# Gyro calibration offsets (from your testing)
GYRO_OFFSET_X = 0.0
GYRO_OFFSET_Y = 0.0
GYRO_OFFSET_Z = 0.0

# HC-SR04 Ultrasonic
TRIG_PIN = 23
ECHO_PIN = 24

# OLED (SSD1306 on separate I2C bus)
OLED_SCL = 25
OLED_SDA = 26
OLED_I2C_BUS = 3
OLED_WIDTH = 128
OLED_HEIGHT = 64

# LED Indicator
LED_PIN = 17

# Sensor send rate
SENSOR_SEND_INTERVAL = 0.05  # 20 Hz
