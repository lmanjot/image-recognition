import os
import json
from http.server import BaseHTTPRequestHandler

def check_google_cloud_status():
    """Check the status of Google Cloud configuration"""
    status = {
        "environment_variables": {},
        "cryptography_available": False,
        "vertex_ai_enabled": False,
        "overall_status": "unknown"
    }
    
    # Check environment variables
    status["environment_variables"] = {
        "GOOGLE_CLOUD_PROJECT": os.getenv('GOOGLE_CLOUD_PROJECT', 'NOT SET'),
        "VERTEX_ENDPOINT_ID": os.getenv('VERTEX_ENDPOINT_ID', 'NOT SET'),
        "VERTEX_LOCATION": os.getenv('VERTEX_LOCATION', 'NOT SET'),
        "GOOGLE_CREDENTIALS": 'SET' if os.getenv('GOOGLE_CREDENTIALS') else 'NOT SET'
    }
    
    # Check cryptography library
    try:
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import rsa, padding
        status["cryptography_available"] = True
    except ImportError:
        status["cryptography_available"] = False
    
    # Check if Vertex AI is enabled
    status["vertex_ai_enabled"] = all([
        os.getenv('GOOGLE_CLOUD_PROJECT'),
        os.getenv('VERTEX_ENDPOINT_ID'),
        os.getenv('VERTEX_LOCATION'),
        os.getenv('GOOGLE_CREDENTIALS')
    ])
    
    # Determine overall status
    if status["vertex_ai_enabled"] and status["cryptography_available"]:
        status["overall_status"] = "ready"
    elif status["vertex_ai_enabled"] and not status["cryptography_available"]:
        status["overall_status"] = "missing_cryptography"
    elif not status["vertex_ai_enabled"]:
        status["overall_status"] = "missing_config"
    else:
        status["overall_status"] = "unknown"
    
    return status

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Handle GET request to check status"""
        try:
            status = check_google_cloud_status()
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type')
            self.end_headers()
            
            response_json = json.dumps(status, indent=2)
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