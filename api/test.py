import os
import json
import base64
import time
from http.server import BaseHTTPRequestHandler

# Try to import cryptography for JWT signing
try:
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa, padding
    CRYPTOGRAPHY_AVAILABLE = True
except ImportError as e:
    CRYPTOGRAPHY_AVAILABLE = False

def test_google_cloud_authentication():
    """Test Google Cloud authentication step by step"""
    test_results = {
        "step": "start",
        "success": False,
        "details": {},
        "errors": []
    }
    
    try:
        # Step 1: Check environment variables
        test_results["step"] = "environment_check"
        test_results["details"]["environment"] = {
            "GOOGLE_CLOUD_PROJECT": os.getenv('GOOGLE_CLOUD_PROJECT', 'NOT SET'),
            "VERTEX_ENDPOINT_ID": os.getenv('VERTEX_ENDPOINT_ID', 'NOT SET'),
            "VERTEX_LOCATION": os.getenv('VERTEX_LOCATION', 'NOT SET'),
            "GOOGLE_CREDENTIALS": 'SET' if os.getenv('GOOGLE_CREDENTIALS') else 'NOT SET'
        }
        
        # Check if all required variables are set
        required_vars = ['GOOGLE_CLOUD_PROJECT', 'VERTEX_ENDPOINT_ID', 'VERTEX_LOCATION', 'GOOGLE_CREDENTIALS']
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        
        if missing_vars:
            test_results["errors"].append(f"Missing environment variables: {missing_vars}")
            return test_results
        
        test_results["details"]["environment"]["status"] = "✅ All environment variables set"
        
        # Step 2: Check cryptography library
        test_results["step"] = "cryptography_check"
        test_results["details"]["cryptography"] = {
            "available": CRYPTOGRAPHY_AVAILABLE
        }
        
        if not CRYPTOGRAPHY_AVAILABLE:
            test_results["errors"].append("Cryptography library not available")
            return test_results
        
        test_results["details"]["cryptography"]["status"] = "✅ Cryptography library available"
        
        # Step 3: Parse credentials JSON
        test_results["step"] = "credentials_parse"
        try:
            credentials_json = os.getenv('GOOGLE_CREDENTIALS')
            credentials = json.loads(credentials_json)
            
            required_cred_fields = ['type', 'project_id', 'private_key_id', 'private_key', 'client_email']
            missing_cred_fields = [field for field in required_cred_fields if field not in credentials]
            
            if missing_cred_fields:
                test_results["errors"].append(f"Missing credential fields: {missing_cred_fields}")
                return test_results
            
            test_results["details"]["credentials"] = {
                "type": credentials.get('type'),
                "project_id": credentials.get('project_id'),
                "client_email": credentials.get('client_email'),
                "private_key_length": len(credentials.get('private_key', '')),
                "status": "✅ Credentials parsed successfully"
            }
            
        except json.JSONDecodeError as e:
            test_results["errors"].append(f"Invalid JSON in credentials: {e}")
            return test_results
        except Exception as e:
            test_results["errors"].append(f"Error parsing credentials: {e}")
            return test_results
        
        # Step 4: Test JWT token creation
        test_results["step"] = "jwt_creation"
        try:
            private_key_pem = credentials['private_key']
            client_email = credentials['client_email']
            
            # Load the private key
            private_key = serialization.load_pem_private_key(
                private_key_pem.encode(),
                password=None
            )
            
            # Create JWT header and payload
            header = {"alg": "RS256", "typ": "JWT"}
            now = int(time.time())
            payload = {
                "iss": client_email,
                "scope": "https://www.googleapis.com/auth/cloud-platform",
                "aud": "https://oauth2.googleapis.com/token",
                "exp": now + 3600,
                "iat": now
            }
            
            # Encode header and payload
            header_b64 = base64.urlsafe_b64encode(json.dumps(header).encode()).rstrip(b'=').decode()
            payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).rstrip(b'=').decode()
            
            # Create the data to sign
            data_to_sign = f"{header_b64}.{payload_b64}"
            
            # Sign the data
            signature = private_key.sign(
                data_to_sign.encode(),
                padding.PKCS1v15(),
                hashes.SHA256()
            )
            
            # Encode the signature
            signature_b64 = base64.urlsafe_b64encode(signature).rstrip(b'=').decode()
            
            # Create the complete JWT
            jwt_token = f"{header_b64}.{payload_b64}.{signature_b64}"
            
            test_results["details"]["jwt"] = {
                "token_length": len(jwt_token),
                "header": header,
                "payload": payload,
                "status": "✅ JWT token created successfully"
            }
            
        except Exception as e:
            test_results["errors"].append(f"Error creating JWT token: {e}")
            return test_results
        
        # Step 5: Test access token exchange
        test_results["step"] = "access_token_exchange"
        try:
            import requests
            
            token_url = "https://oauth2.googleapis.com/token"
            token_data = {
                "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                "assertion": jwt_token
            }
            
            response = requests.post(
                token_url,
                data=token_data,
                timeout=30
            )
            
            test_results["details"]["token_exchange"] = {
                "url": token_url,
                "status_code": response.status_code,
                "response_headers": dict(response.headers)
            }
            
            if response.status_code == 200:
                result = response.json()
                access_token = result.get('access_token')
                if access_token:
                    test_results["details"]["token_exchange"]["access_token_length"] = len(access_token)
                    test_results["details"]["token_exchange"]["status"] = "✅ Access token obtained successfully"
                else:
                    test_results["errors"].append("No access token in response")
                    test_results["details"]["token_exchange"]["response_body"] = result
                    return test_results
            else:
                test_results["errors"].append(f"Token exchange failed: {response.status_code}")
                test_results["details"]["token_exchange"]["response_body"] = response.text
                return test_results
                
        except Exception as e:
            test_results["errors"].append(f"Error exchanging token: {e}")
            return test_results
        
        # Step 6: Test Vertex AI endpoint connectivity
        test_results["step"] = "endpoint_test"
        try:
            project_id = os.getenv('GOOGLE_CLOUD_PROJECT')
            endpoint_id = os.getenv('VERTEX_ENDPOINT_ID')
            location = os.getenv('VERTEX_LOCATION')
            
            endpoint_url = f"https://{location}-aiplatform.googleapis.com/v1/projects/{project_id}/locations/{location}/endpoints/{endpoint_id}"
            
            # Test endpoint accessibility (without making a prediction)
            headers = {"Authorization": f"Bearer {access_token}"}
            response = requests.get(endpoint_url, headers=headers, timeout=30)
            
            test_results["details"]["endpoint"] = {
                "url": endpoint_url,
                "status_code": response.status_code,
                "accessible": response.status_code in [200, 403, 401]  # 403/401 means endpoint exists but no access
            }
            
            if response.status_code == 200:
                test_results["details"]["endpoint"]["status"] = "✅ Endpoint accessible"
            elif response.status_code in [403, 401]:
                test_results["details"]["endpoint"]["status"] = "⚠️ Endpoint exists but access denied (check permissions)"
            else:
                test_results["details"]["endpoint"]["status"] = f"❌ Endpoint not accessible: {response.status_code}"
                test_results["details"]["endpoint"]["response"] = response.text
            
        except Exception as e:
            test_results["errors"].append(f"Error testing endpoint: {e}")
            return test_results
        
        # All tests passed
        test_results["step"] = "complete"
        test_results["success"] = True
        test_results["details"]["summary"] = "✅ All Google Cloud authentication tests passed!"
        
    except Exception as e:
        test_results["errors"].append(f"Unexpected error: {e}")
    
    return test_results

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Handle GET request to test Google Cloud authentication"""
        try:
            test_results = test_google_cloud_authentication()
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type')
            self.end_headers()
            
            response_json = json.dumps(test_results, indent=2)
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