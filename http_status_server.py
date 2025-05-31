import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import json

# Define the HTTP request handler
class RequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/status':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            status = {
                'mqtt_connected': self.server.flag_connected.is_set()
            }
            self.wfile.write(json.dumps(status).encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()

# Function to start the HTTP server
def start_http_server(flag_connected):
    server_address = ('', 8080)  # Listen on port 8080
    httpd = HTTPServer(server_address, RequestHandler)
    httpd.flag_connected = flag_connected
    print('Starting HTTP server on port 8080...')
    httpd.serve_forever()

# Function to run the HTTP server in a separate thread
def run_http_server_in_thread(flag_connected):
    http_server_thread = threading.Thread(target=start_http_server, args=(flag_connected,))
    http_server_thread.daemon = True
    http_server_thread.start()
