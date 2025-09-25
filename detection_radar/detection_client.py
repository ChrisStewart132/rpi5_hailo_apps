# SENDER SCRIPT (to run on Raspberry Pi 5)

import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst
import hailo
import socket  # Added for networking
import json    # Added for data serialization
import os      # Added for environment variable
from pathlib import Path # Added for path handling
import sys     # <--- ADDED: System module for path modification


# ----------------------------------------------------------------------
# START: Solution 1 - Path Modification
# This block allows the script to import modules from the project root 
# (two directories up)
# ----------------------------------------------------------------------

# 1. Get the path to the directory containing this script
current_script_dir = Path(__file__).resolve().parent

# 2. Go up two levels to reach the assumed project root
# If structure is root/github_folder/another_dir/this_script.py
# .parent.parent gives us 'root/'
project_root = current_script_dir.parent.parent

# 3. Add the project root to the system path
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root)) 
    print(f"Added {project_root} to sys.path for external imports.")

# ----------------------------------------------------------------------
# END: Solution 1 - Path Modification
# ----------------------------------------------------------------------

# Now, any script file named e.g., 'utility_script.py' in the project_root 
# can be imported like this:
# import utility_script 

# Note: The existing Hailo imports below are relative to the Hailo environment, 
# not your local project structure, so they remain unchanged.
from hailo_apps.hailo_app_python.core.gstreamer.gstreamer_app import app_callback_class
# Note: Using the simple app class
from hailo_apps.hailo_app_python.apps.detection_simple.detection_pipeline_simple import GStreamerDetectionApp

# --- Configuration for the UDP Sender ---
# !!! IMPORTANT: CHANGE THIS TO YOUR PC's IP ADDRESS !!!
PC_IP = "localhost"  # Using localhost since we assume the server runs on the same RPi5
PORT = 12345
# ----------------------------------------

class user_app_callback_class(app_callback_class):
    def __init__(self, server_ip, server_port):
        super().__init__()
        # These are from your original template
        self.total_people = 0
        self.total_frames = 0
        
        # --- New socket initialization ---
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.server_address = (server_ip, server_port)
        print(f"UDP Sender configured. Will send data to {self.server_address}")

    def close_socket(self):
        """A cleanup function to close the socket."""
        print("Closing UDP socket.")
        self.sock.close()


def app_callback(pad, info, user_data):
    user_data.increment()
    buffer = info.get_buffer()
    if buffer is None:
        return Gst.PadProbeReturn.OK
        
    roi = hailo.get_roi_from_buffer(buffer)
    detections = roi.get_objects_typed(hailo.HAILO_DETECTION)
    
    # --- Part 1: Original Logic for Console Output ---
    # This section remains the same to keep your console logging
    people_count = 0
    for det in detections:
        if det.get_label() == "person":
            people_count = people_count + 1
            
    user_data.total_people += people_count
    user_data.total_frames += 1
    running_average = user_data.total_people / user_data.total_frames if user_data.total_frames > 0 else 0.0
    
    # --- Part 2: New Logic for Network Sending ---
    # Create a list to hold all detection data for this frame
    frame_detections_data = []

    for detection in detections:
        # Package the data for sending over the network
        bbox = detection.get_bbox()
        detection_info = {
            "label": detection.get_label(),
            "confidence": round(detection.get_confidence(), 4),
            "bbox_normalized": {
                "ymin": round(bbox.ymin(), 4),
                "xmin": round(bbox.xmin(), 4),
                "ymax": round(bbox.ymax(), 4),
                "xmax": round(bbox.xmax(), 4)
            }
        }
        frame_detections_data.append(detection_info)

    # Only send a UDP packet if there were any detections in the frame
    if frame_detections_data:
        try:
            # Serialize the list to a JSON string and encode it to bytes
            payload_bytes = json.dumps(frame_detections_data).encode('utf-8')
            
            # Send the data
            user_data.sock.sendto(payload_bytes, user_data.server_address)
        except Exception as e:
            # It's good practice to catch potential network errors
            print(f"Error sending UDP packet: {e}")
            
    
    
    return Gst.PadProbeReturn.OK

if __name__ == "__main__":
    
    # Note: If your project structure logic for finding the .env file 
    # was already using the project root (like the line below was before), 
    # you can remove the path modification block above, as you were already 
    # calculating the project root here. However, calculating it explicitly 
    # at the top makes the import intent clearer.
    
    # It's good practice to set the Hailo environment file explicitly
    # project_root is calculated above and is two levels up
    env_file     = project_root / ".env"
    os.environ["HAILO_ENV_FILE"] = str(env_file)
    
    # Initialize the user_data class with the network info
    user_data = user_app_callback_class(PC_IP, PORT)
    
    try:
        app = GStreamerDetectionApp(app_callback, user_data)
        app.run()
    finally:
        # This ensures the socket is closed when the app is stopped (e.g., with Ctrl+C)
        user_data.close_socket()