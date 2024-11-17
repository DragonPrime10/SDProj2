import csv
import json
import time
from threading import Thread
import pigpio
import board
import busio
from adafruit_bno08x import BNO_REPORT_ACCELEROMETER, BNO_REPORT_GYROSCOPE, BNO_REPORT_MAGNETOMETER
from adafruit_bno08x.i2c import BNO08X_I2C
import serial

# Initialize pigpio for software UART
pi = pigpio.pi()
TX_PIN = 23
BAUD_RATE = 9600

# Path to save the CSV file on the SD card
csv_file_path = "/media/sdcard/sensor_data.csv"

# Initialize CSV file with headers if it doesn't exist
def initialize_csv():
    with open(csv_file_path, mode="w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow([
            "IMU_Gyro_X", "IMU_Gyro_Y", "IMU_Gyro_Z",
            "IMU_Accel_X", "IMU_Accel_Y", "IMU_Accel_Z",
            "IMU_Magnetic_X", "IMU_Magnetic_Y", "IMU_Magnetic_Z",
            "GPS_Time", "GPS_Latitude", "GPS_Longitude",
            "GPS_Altitude", "GPS_Satellites"
        ])

# Save data to CSV
def save_to_csv(data):
    with open(csv_file_path, mode="a", newline="") as file:
        writer = csv.writer(file)
        writer.writerow([
            data.get("IMU_Gyro_X", "N/A"),
            data.get("IMU_Gyro_Y", "N/A"),
            data.get("IMU_Gyro_Z", "N/A"),
            data.get("IMU_Accel_X", "N/A"),
            data.get("IMU_Accel_Y", "N/A"),
            data.get("IMU_Accel_Z", "N/A"),
            data.get("IMU_Magnetic_X", "N/A"),
            data.get("IMU_Magnetic_Y", "N/A"),
            data.get("IMU_Magnetic_Z", "N/A"),
            data.get("GPS_Time", "N/A"),
            data.get("GPS_Latitude", "N/A"),
            data.get("GPS_Longitude", "N/A"),
            data.get("GPS_Altitude", "N/A"),
            data.get("GPS_Satellites", "N/A")
        ])

def send_data(data):
    pi.wave_clear()
    pi.wave_add_serial(TX_PIN, BAUD_RATE, data + "\n")
    wave_id = pi.wave_create()
    if wave_id >= 0:
        pi.wave_send_once(wave_id)
        while pi.wave_tx_busy():
            time.sleep(0.01)
        pi.wave_delete(wave_id)

# Initialize IMU
i2c = busio.I2C(board.SCL, board.SDA)
bno = BNO08X_I2C(i2c)
bno.enable_feature(BNO_REPORT_ACCELEROMETER)
bno.enable_feature(BNO_REPORT_GYROSCOPE)
bno.enable_feature(BNO_REPORT_MAGNETOMETER)

# Initialize GPS
gps_serial = serial.Serial("/dev/ttyS0", baudrate=9600, timeout=1)

def read_imu_data():
    gyro_x, gyro_y, gyro_z = bno.gyro
    accel_x, accel_y, accel_z = bno.acceleration
    mag_x, mag_y, mag_z = bno.magnetic
    return {
        "IMU_Gyro_X": gyro_x,
        "IMU_Gyro_Y": gyro_y,
        "IMU_Gyro_Z": gyro_z,
        "IMU_Accel_X": accel_x,
        "IMU_Accel_Y": accel_y,
        "IMU_Accel_Z": accel_z,
        "IMU_Magnetic_X": mag_x,
        "IMU_Magnetic_Y": mag_y,
        "IMU_Magnetic_Z": mag_z
    }

def parse_gpgga(sentence):
    fields = sentence.split(',')
    if fields[0] != "$GPGGA":
        return None
    return {
        "GPS_Time": fields[1],
        "GPS_Latitude": fields[2],
        "GPS_Longitude": fields[4],
        "GPS_Altitude": fields[9],
        "GPS_Satellites": fields[7]
    }

def read_gps_data():
    while True:
        if gps_serial.in_waiting > 0:
            line = gps_serial.readline().decode('utf-8', errors='ignore').strip()
            if line.startswith("$GPGGA"):
                return parse_gpgga(line)
        time.sleep(2)

# Modify the sender function to save JSON data to CSV
def sender():
    initialize_csv()  # Set up the CSV file initially
    while True:
        imu_data = read_imu_data()
        gps_data = read_gps_data() or {}
        combined_data = {**imu_data, **gps_data}
        
        # Convert to JSON and send (for UART functionality)
        json_data = json.dumps(combined_data)
        send_data(json_data)
        
        # Save to CSV on the SD card
        save_to_csv(combined_data)
        
        time.sleep(1)

if __name__ == "__main__":
    sender_thread = Thread(target=sender)
    sender_thread.start()
