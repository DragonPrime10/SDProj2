import json
import time
import board
import busio
import os
import csv
import digitalio
from adafruit_bno08x import BNO_REPORT_ACCELEROMETER, BNO_REPORT_GYROSCOPE, BNO_REPORT_MAGNETOMETER
from adafruit_bno08x.i2c import BNO08X_I2C
import serial
import adafruit_rfm9x

# Initialize the hardware UART interface
serial_port = "/dev/ttyAMA2"
baud_rate = 9600

# Initialize the RFM9x radio module
RADIO_FREQ_MHZ = 915.0
CS = digitalio.DigitalInOut(board.CE1)
RESET = digitalio.DigitalInOut(board.D16)
spi = busio.SPI(board.SCK, MOSI=board.MOSI, MISO=board.MISO)
rfm9x = adafruit_rfm9x.RFM9x(spi, CS, RESET, RADIO_FREQ_MHZ)
rfm9x.tx_power = 23

try:
    ser = serial.Serial(serial_port, baud_rate, timeout=1)
except serial.SerialException as e:
    print(f"Failed to open UART interface {serial_port}: {e}")
    ser = None

# Initialize IMU
i2c = busio.I2C(board.SCL, board.SDA)
bno = BNO08X_I2C(i2c)
bno.enable_feature(BNO_REPORT_ACCELEROMETER)
bno.enable_feature(BNO_REPORT_GYROSCOPE)
bno.enable_feature(BNO_REPORT_MAGNETOMETER)

# Initialize GPS
gps_serial = serial.Serial("/dev/serial1", baudrate=9600, timeout=1)

radio_log_path = "/home/pi/Desktop/SDProj2/radio_log.txt"

# Send data via radio
def radio_send(data):
    chunk_size = 4
    for i in range(0, len(data), chunk_size):
        chunk = data[i:i + chunk_size]
        rfm9x.send(chunk.encode('utf-8'))
        time.sleep(0.1)  # Small delay to ensure proper transmission
        packet = rfm9x.receive()
        testnumber = 0
        if packet is not None:
            with open(radio_log_path, "a") as log_file:
                packet_text = str(packet, "utf-8")
                log_file.write(packet_text + "\n")
                print(f"Received: {packet_text}")
                time.sleep(0.05)
        else:
            with open(radio_log_path, "a") as log_file:
                log_file.write(str(testnumber))
                testnumber += 1
                time.sleep(0.05)

# Read IMU data from BNO08x sensor
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

# Parse GPS data from GPGGA sentence
def parse_gpgga(sentence):
    fields = sentence.split(',')
    if fields[0] != "$GPGGA":
        return None
    return {
        "GPS_Time": fields[1] if fields[1] else 0,
        "GPS_Latitude": fields[2] if fields[2] else 0,
        "GPS_Longitude": fields[4] if fields[4] else 0,
        "GPS_Altitude": fields[9] if fields[9] else 0,
        "GPS_Satellites": fields[7] if fields[7] else 0
    }

# Read GPS data from serial port
def read_gps_data():
    while True:
        if gps_serial.in_waiting > 0:
            line = gps_serial.readline().decode('utf-8', errors='ignore').strip()
            if line.startswith("$GPGGA"):
                return parse_gpgga(line)
        time.sleep(2)
        
# Path to save the CSV file on the SD card
csv_file_path = "/media/pi/4A21-0000/sensor_data.csv"
media_path = "/media/pi/4A21-0000"
        
# Initialize CSV file with headers if it doesn't exist
def initialize_csv():
    if os.path.exists(media_path):
        if not os.path.exists(csv_file_path):
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
    if os.path.exists(media_path):
        if not os.path.exists(csv_file_path):
            initialize_csv()
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

# Sender function to read, combine, and send data
def sender():
    if ser is None:
        print("UART interface not available. Exiting...")
        return

    initialize_csv()  # Set up the CSV file initially

    while True:
        # Get data from IMU and GPS
        imu_data = read_imu_data()
        gps_data = read_gps_data() or {}

        # Combine data into a single dictionary
        combined_data = {**imu_data, **gps_data}

        # Convert data to JSON format
        json_data = json.dumps(combined_data)

        # Send data via UART
        try:
            ser.write((json_data + "\n").encode("utf-8"))
            print(f"Sent: {json_data}")
        except serial.SerialException as e:
            print(f"Error sending data over UART: {e}")

        # Save data to CSV
        save_to_csv(combined_data)
        
        # Send data via radio
        radio_send(json_data)

        # Delay between data transmissions
        time.sleep(1)

if __name__ == "__main__":
    sender()
