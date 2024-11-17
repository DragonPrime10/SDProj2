import json
import tkinter as tk
from tkinter import messagebox
import serial
import time
from threading import Thread
import glob
import sys

class DataReceiver:
    def __init__(self, root):
        self.root = root
        self.root.title("IMU & GPS Data Display")
        self.root.geometry("300x400")  # Set a fixed window size
        self.root.resizable(False, False)  # Disable window resizing

        # Initialize GUI components
        self.main_menu_frame = tk.Frame(root)
        self.data_frame = tk.Frame(root)
        
        # Main Menu Components
        self.main_menu_label = tk.Label(self.main_menu_frame, text="Main Menu")
        self.view_data_button = tk.Button(self.main_menu_frame, text="View Data", command=self.show_data_view, state=tk.DISABLED)
        self.exit_button = tk.Button(self.main_menu_frame, text="Exit", command=self.exit_program)
        
        # Data View Components
        self.back_button = tk.Button(self.data_frame, text="Back to Main Menu", command=self.show_main_menu)
        self.data_labels = {}

        # Arrange Main Menu Components
        self.main_menu_label.pack(pady=10)
        self.view_data_button.pack(pady=5)
        self.exit_button.pack(pady=5)

        # Arrange Data View Components
        self.back_button.pack(pady=5)
        fields = {
            "IMU_Gyro_X": "Gyro X (rad/s): ",
            "IMU_Gyro_Y": "Gyro Y (rad/s): ",
            "IMU_Gyro_Z": "Gyro Z (rad/s): ",
            "IMU_Accel_X": "Accel X (m/s²): ",
            "IMU_Accel_Y": "Accel Y (m/s²): ",
            "IMU_Accel_Z": "Accel Z (m/s²): ",
            "IMU_Magnetic_X": "Mag X (µT): ",
            "IMU_Magnetic_Y": "Mag Y (µT): ",
            "IMU_Magnetic_Z": "Mag Z (µT): ",
            "GPS_Time": "Time (UTC): ",
            "GPS_Latitude": "Latitude: ",
            "GPS_Longitude": "Longitude: ",
            "GPS_Altitude": "Altitude (m): ",
            "GPS_Satellites": "Satellites: "
        }
        for field, label_text in fields.items():
            label = tk.Label(self.data_frame, text=label_text + "N/A")
            label.pack()
            self.data_labels[field] = label

        # Show Main Menu initially
        self.show_main_menu()
        
        # Start monitoring for USB connection status
        self.ser = None
        self.check_usb_connection()

    def auto_detect_usb(self):
        # Automatically detect and connect to the first available USB device
        usb_devices = glob.glob('/dev/ttyUSB*')
        if usb_devices:
            try:
                return serial.Serial(usb_devices[0], 9600, timeout=1)
            except serial.SerialException:
                return None
        return None

    def check_usb_connection(self):
        # Check for USB connection periodically
        if not self.ser:
            self.ser = self.auto_detect_usb()
            if self.ser:
                self.view_data_button.config(state=tk.NORMAL)  # Enable the "View Data" button if USB is connected
                self.update_thread = Thread(target=self.update_data)
                self.update_thread.daemon = True
                self.update_thread.start()
        else:
            # Check if the serial connection is still open
            if not self.ser.is_open:
                self.view_data_button.config(state=tk.DISABLED)
                self.ser = None

        # Schedule the next check
        self.root.after(1000, self.check_usb_connection)

    def show_main_menu(self):
        # Switch to main menu
        self.data_frame.pack_forget()
        self.main_menu_frame.pack()

    def show_data_view(self):
        # Switch to data view
        self.main_menu_frame.pack_forget()
        self.data_frame.pack()

    def exit_program(self):
        # Exit the program gracefully
        if self.ser:
            self.ser.close()
        self.root.quit()
        sys.exit()

    def format_gps_data(self, data):
        # Format GPS data if available
        if "GPS_Time" in data:
            time_str = data["GPS_Time"]
            data["GPS_Time"] = f"{time_str[:2]}:{time_str[2:4]}:{time_str[4:6]}"
        
        if "GPS_Latitude" in data and "GPS_Longitude" in data:
            data["GPS_Latitude"] = self.format_lat_lon(data["GPS_Latitude"], "latitude")
            data["GPS_Longitude"] = self.format_lat_lon(data["GPS_Longitude"], "longitude")

    def format_lat_lon(self, value, coord_type):
        # Format latitude/longitude in degrees and add N/S or E/W
        degrees = int(value[:2])
        minutes = float(value[2:])
        decimal_degrees = degrees + (minutes / 60)
        if coord_type == "latitude":
            return f"{decimal_degrees:.6f}° {'N' if decimal_degrees >= 0 else 'S'}"
        elif coord_type == "longitude":
            return f"{decimal_degrees:.6f}° {'E' if decimal_degrees >= 0 else 'W'}"
        return "N/A"

    def update_data(self):
        while True:
            if self.ser and self.ser.in_waiting > 0:
                raw_data = self.ser.readline().decode('utf-8').strip()
                try:
                    data = json.loads(raw_data)
                    self.format_gps_data(data)
                    
                    # Update each label with formatted data
                    for field, label in self.data_labels.items():
                        value = data.get(field, "N/A")
                        label.config(text=f"{self.data_labels[field].cget('text').split(':')[0]}: {value}")
                
                except json.JSONDecodeError:
                    print("Received malformed JSON:", raw_data)
            time.sleep(0.5)

if __name__ == "__main__":
    root = tk.Tk()
    app = DataReceiver(root)
    root.mainloop()
