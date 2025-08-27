import os
import json
from http.server import BaseHTTPRequestHandler

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Handle GET request to check environment variables at runtime"""
        try:
            env_vars = {
                "GOOGLE_CLOUD_PROJECT": os.getenv('GOOGLE_CLOUD_PROJECT'),
                "VERTEX_ENDPOINT_ID": os.getenv('VERTEX_ENDPOINT_ID'),
                "VERTEX_LOCATION": os.getenv('VERTEX_LOCATION'),
                "GOOGLE_CREDENTIALS": "SET" if os.getenv('GOOGLE_CREDENTIALS') else "NOT SET",
                "VERTEX_AI_ENABLED": all([
                    os.getenv('GOOGLE_CLOUD_PROJECT'),
                    os.getenv('VERTEX_ENDPOINT_ID'),
                    os.getenv('VERTEX_LOCATION'),
                    os.getenv('GOOGLE_CREDENTIALS')
                ])
            }
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type')
            self.end_headers()
            
            response_json = json.dumps(env_vars, indent=2)
            self.wfile.write(response_json.encode('utf-8'))
            
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            error_data = {'error': str(e)}
            response_json = json.dumps(error_data)
            self.wfile.write(response_json.encode('utf-8'))
    
    def do_OPTIONS(self):
        """Handle CORS preflight request"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()