import os
import json
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse
from database import get_database_manager

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Handle GET requests to retrieve user uploads"""
        try:
            # Parse URL and query parameters
            parsed_url = urlparse(self.path)
            query_params = parse_qs(parsed_url.query)
            
            # Extract user_id from query parameters
            user_id = query_params.get('user_id', [None])[0]
            
            if not user_id:
                self.send_error_response('user_id parameter is required', 400)
                return
            
            # Get pagination parameters
            limit = int(query_params.get('limit', [50])[0])
            offset = int(query_params.get('offset', [0])[0])
            
            # Limit the maximum number of results
            limit = min(limit, 100)
            
            print(f"🔍 Retrieving uploads for user: {user_id}, limit: {limit}, offset: {offset}")
            
            # Get database manager
            db_manager = get_database_manager()
            
            # Retrieve user uploads
            uploads = db_manager.get_user_uploads(user_id, limit, offset)
            
            # Prepare response
            response_data = {
                'success': True,
                'user_id': user_id,
                'uploads': uploads,
                'total_count': len(uploads),
                'limit': limit,
                'offset': offset
            }
            
            self.send_success_response(response_data)
            
        except Exception as e:
            print(f"❌ Error retrieving user uploads: {e}")
            self.send_error_response(str(e), 500)
    
    def do_OPTIONS(self):
        """Handle CORS preflight request"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def send_success_response(self, data):
        """Send successful response"""
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.send_header('Access-Control-Max-Age', '86400')
        self.end_headers()
        
        response_json = json.dumps(data, default=str)  # default=str handles datetime objects
        self.wfile.write(response_json.encode('utf-8'))
    
    def send_error_response(self, message, status_code):
        """Send error response"""
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.send_header('Access-Control-Max-Age', '86400')
        self.end_headers()
        
        error_data = {'error': message}
        response_json = json.dumps(error_data)
        self.wfile.write(response_json.encode('utf-8'))