import http.server
import socketserver
import socket
import json
from threading import Thread, Lock

# --- Configuration ---
LISTEN_IP = "0.0.0.0"
UDP_PORT = 12345
HTTP_PORT = 8000
BUFFER_SIZE = 4096

# --- Shared Data and Threading Lock ---
# This lock is critical. It prevents the UDP and HTTP threads from
# interfering with each other when accessing the `latest_detections` list.
thread_lock = Lock()
latest_detections = []

# --- 1. The UDP Listener (Runs in a separate thread) ---
def udp_listener():
    """
    This is your original UDP receiving logic, adapted to run as a thread.
    It continuously listens for UDP packets and updates the global `latest_detections`.
    """
    global latest_detections
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((LISTEN_IP, UDP_PORT))
    print(f"Starting UDP listener on port {UDP_PORT}")

    while True:
        try:
            data_bytes, _ = sock.recvfrom(BUFFER_SIZE)
            detections = json.loads(data_bytes.decode('utf-8'))
            
            # Use the lock to ensure this update is "atomic" or thread-safe
            with thread_lock:
                latest_detections = detections
                
        except Exception as e:
            print(f"UDP Listener error: {e}")

# --- 2. The Custom HTTP Request Handler ---
class MyHttpRequestHandler(http.server.SimpleHTTPRequestHandler):
    """
    A custom handler that serves files but also provides our JSON API endpoint.
    """
    def do_GET(self):
        # If the browser is requesting our API endpoint...
        if self.path == '/api/detections':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            # Use the lock to safely read the shared data
            with thread_lock:
                data_to_send = latest_detections
            
            response_bytes = json.dumps(data_to_send).encode('utf-8')
            self.wfile.write(response_bytes)
        else:
            # For any other path (like '/' for index.html or '/main.js'),
            # let the default file server handle it.
            return http.server.SimpleHTTPRequestHandler.do_GET(self)

# --- 3. The Main Execution Block ---
if __name__ == '__main__':
    # Start the UDP listener in a background thread.
    # daemon=True ensures the thread will exit when the main program does.
    udp_thread = Thread(target=udp_listener, daemon=True)
    udp_thread.start()
    
    # Create the multi-threaded HTTP server.
    Handler = MyHttpRequestHandler
    httpd = socketserver.ThreadingTCPServer(("", HTTP_PORT), Handler)
    
    print(f"HTTP server running. Open your browser to:")
    print(f"http://127.0.0.1:{HTTP_PORT}  (if on this machine)")
    print(f"http://<your_pc_ip>:{HTTP_PORT} (from another device on the LAN)")
    
    # Start the HTTP server. It will block here and run forever.
    httpd.serve_forever()