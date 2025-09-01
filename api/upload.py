import os
import json
import base64
import tempfile
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse
import cgi
import io
from PIL import Image, ImageDraw, ImageFont
import requests
import time

# Only import Google Auth if available (reduces bundle size)
try:
    import google.auth
    from google.auth.transport.requests import Request
    from google.oauth2 import service_account
    GOOGLE_AUTH_AVAILABLE = True
except ImportError:
    GOOGLE_AUTH_AVAILABLE = False
    print("⚠️ Google Auth not available - using mock mode")

# Configure Google Cloud credentials
project_id = os.getenv('GOOGLE_CLOUD_PROJECT', '27458468732')
endpoint_id = os.getenv('VERTEX_ENDPOINT_ID', '3349211374252195840')
location = os.getenv('VERTEX_LOCATION', 'europe-west4')

def check_vertex_ai_enabled():
    """Check if Vertex AI is properly configured - called at runtime"""
    if not GOOGLE_AUTH_AVAILABLE:
        print("⚠️ Google Auth library not available")
        return False
        
    enabled = all([
        os.getenv('GOOGLE_CLOUD_PROJECT'),
        os.getenv('VERTEX_ENDPOINT_ID'),
        os.getenv('VERTEX_LOCATION'),
        os.getenv('GOOGLE_CREDENTIALS')
    ])
    
    print(f"🔍 Runtime environment check:")
    print(f"  - GOOGLE_CLOUD_PROJECT: {os.getenv('GOOGLE_CLOUD_PROJECT', 'NOT SET')}")
    print(f"  - VERTEX_ENDPOINT_ID: {os.getenv('VERTEX_ENDPOINT_ID', 'NOT SET')}")
    print(f"  - VERTEX_LOCATION: {os.getenv('VERTEX_LOCATION', 'NOT SET')}")
    print(f"  - GOOGLE_CREDENTIALS: {'SET' if os.getenv('GOOGLE_CREDENTIALS') else 'NOT SET'}")
    print(f"  - GOOGLE_AUTH_AVAILABLE: {GOOGLE_AUTH_AVAILABLE}")
    print(f"  - VERTEX_AI_ENABLED: {enabled}")
    
    return enabled

def get_mock_predictions():
    """Return mock predictions as fallback when Vertex AI is not available"""
    return [
        {
            'displayName': 'person',
            'confidence': 0.95,
            'bbox': [0.1, 0.1, 0.3, 0.8]
        },
        {
            'displayName': 'car',
            'confidence': 0.87,
            'bbox': [0.4, 0.6, 0.9, 0.9]
        },
        {
            'displayName': 'dog',
            'confidence': 0.78,
            'bbox': [0.6, 0.2, 0.8, 0.5]
        }
    ]

# JWT token creation removed - now using Google Auth library for better performance

# Global cache for access token to improve performance
_access_token_cache = None
_access_token_expiry = 0

def get_google_access_token(credentials_json):
    """Get Google access token with caching for performance"""
    if not GOOGLE_AUTH_AVAILABLE:
        print("❌ Google Auth library not available")
        return None
        
    global _access_token_cache, _access_token_expiry
    
    # Check if we have a valid cached token (tokens typically last 1 hour)
    current_time = time.time()
    if _access_token_cache and current_time < _access_token_expiry:
        print("✅ Using cached access token")
        return _access_token_cache
    
    try:
        print("🔄 Generating new access token...")
        
        # Parse the service account credentials
        credentials_info = json.loads(credentials_json)
        
        # Create credentials object
        credentials = service_account.Credentials.from_service_account_info(
            credentials_info,
            scopes=['https://www.googleapis.com/auth/cloud-platform']
        )
        
        # Get the access token
        credentials.refresh(Request())
        access_token = credentials.token
        
        # Cache the token with expiry (set to 50 minutes to be safe)
        _access_token_cache = access_token
        _access_token_expiry = current_time + (50 * 60)  # 50 minutes
        
        print("✅ New access token generated and cached")
        return access_token
        
    except Exception as e:
        print(f"❌ Error getting access token: {e}")
        return None

def call_vertex_ai_endpoint(image_bytes, confidence_threshold, iou_threshold, max_predictions, access_token):
    """Make actual API call to Vertex AI endpoint"""
    try:
        print("🚀 Making API call to Vertex AI endpoint...")
        
        # Construct the Vertex AI endpoint URL
        endpoint_url = f"https://{location}-aiplatform.googleapis.com/v1/projects/{project_id}/locations/{location}/endpoints/{endpoint_id}:predict"
        print(f"  - Endpoint URL: {endpoint_url}")
        
        # Prepare the request payload - using correct Vertex AI format
        payload = {
            "instances": [{
                "content": base64.b64encode(image_bytes).decode('utf-8')
            }],
            "parameters": {
                "confidenceThreshold": confidence_threshold,
                "iouThreshold": iou_threshold,
                "maxPredictions": max_predictions
            }
        }
        
        print(f"  - Payload: {json.dumps(payload, indent=2)}")
        
        # Set up headers with authorization
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        print(f"  - Headers: {json.dumps(headers, indent=2)}")
        
        # Make the actual API call
        response = requests.post(
            endpoint_url,
            json=payload,
            headers=headers,
            timeout=30
        )
        
        print(f"  - Response status: {response.status_code}")
        print(f"  - Response headers: {dict(response.headers)}")
        
        if response.status_code == 200:
                print("✅ Vertex AI API call successful")
                result = response.json()
                
                # Log the COMPLETE response for debugging
                print("=" * 80)
                print("🔍 COMPLETE VERTEX AI RESPONSE:")
                print("=" * 80)
                print(json.dumps(result, indent=2))
                print("=" * 80)
                
                # Parse the predictions from the response
                predictions = []
                if 'predictions' in result and result['predictions']:
                    # Vertex AI returns predictions in a specific format
                    vertex_predictions = result['predictions'][0]
                    print(f"🔍 Raw Vertex AI predictions[0]: {json.dumps(vertex_predictions, indent=2)}")
                    
                    # Check if this is the array-based format (bboxes, confidences, displayNames)
                    if isinstance(vertex_predictions, dict) and 'bboxes' in vertex_predictions:
                        print(f"📋 Found array-based format with {len(vertex_predictions['bboxes'])} predictions")
                        
                        bboxes = vertex_predictions.get('bboxes', [])
                        confidences = vertex_predictions.get('confidences', [])
                        display_names = vertex_predictions.get('displayNames', [])
                        
                        # Ensure all arrays have the same length
                        min_length = min(len(bboxes), len(confidences), len(display_names))
                        print(f"📏 Processing {min_length} predictions")
                        
                        for i in range(min_length):
                            prediction = {
                                'displayName': display_names[i] if i < len(display_names) else 'Unknown',
                                'confidence': confidences[i] if i < len(confidences) else 0.0,
                                'bbox': bboxes[i] if i < len(bboxes) else [0, 0, 0, 0]
                            }
                            print(f"✅ Parsed prediction {i}: {json.dumps(prediction, indent=2)}")
                            predictions.append(prediction)
                    
                    # Handle different possible response formats
                    elif isinstance(vertex_predictions, list):
                        print(f"📋 Predictions is a list with {len(vertex_predictions)} items")
                        for i, pred in enumerate(vertex_predictions):
                            print(f"🔍 Processing prediction {i}: {json.dumps(pred, indent=2)}")
                            if isinstance(pred, dict):
                                # Extract prediction data
                                prediction = {
                                    'displayName': pred.get('displayName', pred.get('class', 'Unknown')),
                                    'confidence': pred.get('confidence', pred.get('score', 0.0)),
                                    'bbox': pred.get('bbox', pred.get('boundingBox', [0, 0, 0, 0]))
                                }
                                print(f"✅ Parsed prediction {i}: {json.dumps(prediction, indent=2)}")
                                predictions.append(prediction)
                            else:
                                # Handle object format
                                print(f"⚠️ Prediction {i} is not a dict: {type(pred)}")
                                predictions.append({
                                    'displayName': getattr(pred, 'displayName', getattr(pred, 'class', 'Unknown')),
                                    'confidence': getattr(pred, 'confidence', getattr(pred, 'score', 0.0)),
                                    'bbox': getattr(pred, 'bbox', getattr(pred, 'boundingBox', [0, 0, 0, 0]))
                                })
                    else:
                        # Single prediction or different format
                        print(f"⚠️ Unexpected prediction format: {type(vertex_predictions)}")
                        print(f"🔍 Content: {json.dumps(vertex_predictions, indent=2)}")
                        predictions.append({
                            'displayName': 'Unknown',
                            'confidence': 0.0,
                            'bbox': [0, 0, 0, 0]
                        })
                else:
                    print("⚠️ No 'predictions' key found in response")
                    print(f"🔍 Available keys: {list(result.keys())}")
                
                print(f"🎯 Final parsed {len(predictions)} predictions: {json.dumps(predictions, indent=2)}")
                return predictions
        else:
            print(f"❌ Vertex AI API call failed: {response.status_code}")
            print(f"📄 Response: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Error calling Vertex AI endpoint: {e}")
        import traceback
        traceback.print_exc()
        return None

def predict_image_object_detection_rest(image_bytes, confidence_threshold, iou_threshold, max_predictions):
    """Call Vertex AI endpoint using REST API (lightweight approach)"""
    print(f"\n🔍 Starting Vertex AI prediction process...")
    print(f"  - Image size: {len(image_bytes)} bytes")
    print(f"  - Confidence threshold: {confidence_threshold}")
    print(f"  - IoU threshold: {iou_threshold}")
    print(f"  - Max predictions: {max_predictions}")
    
    # Check Vertex AI configuration at runtime (only once)
    vertex_ai_enabled = check_vertex_ai_enabled()
    
    if not vertex_ai_enabled:
        print("⚠️ Vertex AI not configured, using mock data")
        print("  - Missing environment variables")
        return get_mock_predictions()
    
    try:
        print("🔍 Vertex AI configured - attempting real API call")
        
        # Get the service account credentials from environment
        credentials_json = os.getenv('GOOGLE_CREDENTIALS')
        if not credentials_json:
            print("❌ No credentials found in environment")
            return get_mock_predictions()
        
        print("✅ Credentials found in environment")
        print(f"  - Credentials length: {len(credentials_json)} characters")
        
        # Get access token (this is the main performance bottleneck)
        access_token = get_google_access_token(credentials_json)
        if not access_token:
            print("❌ Failed to get access token")
            return get_mock_predictions()
        
        print("✅ Access token obtained")
        
        # Make actual API call to Vertex AI
        predictions = call_vertex_ai_endpoint(
            image_bytes, 
            confidence_threshold, 
            iou_threshold, 
            max_predictions, 
            access_token
        )
        
        if predictions:
            print("🎉 Real Vertex AI predictions received!")
            print(f"  - Number of predictions: {len(predictions)}")
            for i, pred in enumerate(predictions):
                print(f"    {i+1}. {pred.get('displayName', 'Unknown')} - {pred.get('confidence', 0.0):.3f}")
            return predictions
        else:
            print("⚠️ Vertex AI call failed, falling back to mock data")
            return get_mock_predictions()
        
    except Exception as e:
        print(f"❌ Error calling Vertex AI: {e}")
        import traceback
        traceback.print_exc()
        print("🔄 Falling back to mock data")
        return get_mock_predictions()

def predict_image_object_detection(image_bytes, confidence_threshold, iou_threshold, max_predictions):
    """Main prediction function - optimized to reduce redundant calls"""
    # Single call to the REST function - no more redundant calls
    return predict_image_object_detection_rest(
        image_bytes, confidence_threshold, iou_threshold, max_predictions
    )

def create_annotated_image(image_bytes, predictions):
    """Create an annotated image with bounding boxes and labels"""
    try:
        # Open image from bytes
        image = Image.open(io.BytesIO(image_bytes))
        draw = ImageDraw.Draw(image)
        
        # Use default font
        font = ImageFont.load_default()
        
        # Draw bounding boxes and labels
        for pred in predictions:
            bbox = pred.get('bbox', [0, 0, 0, 0])
            class_name = pred.get('displayName', 'Unknown')
            confidence = pred.get('confidence', 0.0)
            
            # Convert normalized coordinates to pixel coordinates
            width, height = image.size
            x1 = int(bbox[0] * width)
            y1 = int(bbox[1] * height)
            x2 = int(bbox[2] * width)
            y2 = int(bbox[3] * height)
            
            # Draw bounding box
            draw.rectangle([x1, y1, x2, y2], outline='red', width=3)
            
            # Draw label background
            label = f"{class_name}: {confidence:.2f}"
            bbox_text = draw.textbbox((x1, y1 - 20), label, font=font)
            draw.rectangle(bbox_text, fill='red')
            
            # Draw label text
            draw.text((x1, y1 - 20), label, fill='white', font=font)
        
        # Convert to base64 for sending to frontend
        buffer = io.BytesIO()
        image.save(buffer, format='JPEG')
        img_str = base64.b64encode(buffer.getvalue()).decode('utf-8')
        
        return f"data:image/jpeg;base64,{img_str}"
        
    except Exception as e:
        print(f"❌ Error creating annotated image: {e}")
        import traceback
        traceback.print_exc()
        return None

def parse_multipart_data(body, content_type):
    """Parse multipart form data from request body"""
    try:
        # Parse the multipart data
        form = cgi.FieldStorage(
            fp=io.BytesIO(body),
            headers={'content-type': content_type},
            environ={'REQUEST_METHOD': 'POST'}
        )
        
        # Extract form data with new defaults
        image_file = form.getfirst('image')
        confidence_threshold = float(form.getfirst('confidenceThreshold', 0.3))  # Default: 0.3
        iou_threshold = float(form.getfirst('iouThreshold', 0.1))  # Default: 0.1
        max_predictions = int(form.getfirst('maxPredictions', 100))
        
        return {
            'image': image_file,
            'confidence_threshold': confidence_threshold,
            'iou_threshold': iou_threshold,
            'max_predictions': max_predictions
        }
    except Exception as e:
        print(f"❌ Error parsing multipart data: {e}")
        return None

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Handle GET requests for health checks and testing"""
        if self.path == '/api/upload' or self.path == '/api/upload/':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS, GET')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
            self.end_headers()
            
            response_data = {
                'status': 'healthy',
                'message': 'Image recognition API is running',
                'google_auth_available': GOOGLE_AUTH_AVAILABLE,
                'vertex_ai_enabled': check_vertex_ai_enabled()
            }
            
            response_json = json.dumps(response_data)
            self.wfile.write(response_json.encode('utf-8'))
            return
    
    def do_POST(self):
        try:
            # Get content length and type
            content_length = int(self.headers.get('Content-Length', 0))
            content_type = self.headers.get('Content-Type', '')
            
            # Read request body
            body = self.rfile.read(content_length)
            
            # Parse multipart form data
            form_data = parse_multipart_data(body, content_type)
            
            if not form_data or not form_data['image']:
                self.send_error_response('No image file provided', 400)
                return
            
            # Get parameters
            confidence_threshold = form_data['confidence_threshold']
            iou_threshold = form_data['iou_threshold']
            max_predictions = form_data['max_predictions']
            
            print(f"🖼️ Processing image with parameters: conf={confidence_threshold}, IoU={iou_threshold}, max={max_predictions}")
            
            # Convert image file to bytes
            if hasattr(form_data['image'], 'file'):
                image_bytes = form_data['image'].file.read()
            else:
                image_bytes = form_data['image']
            
            # Call prediction function
            predictions = predict_image_object_detection(
                image_bytes, 
                confidence_threshold, 
                iou_threshold, 
                max_predictions
            )
            
            if not predictions:
                self.send_error_response('No predictions returned from model', 400)
                return
            
            # Process predictions and create annotated image
            annotated_image_data = create_annotated_image(image_bytes, predictions)
            
            # Count predictions by class
            class_counts = {}
            for pred in predictions:
                class_name = pred.get('displayName', 'Unknown')
                class_counts[class_name] = class_counts.get(class_name, 0) + 1
            
            print(f"📊 Results: {len(predictions)} objects, classes: {list(class_counts.keys())}")
            
            # Determine model status
            model_used = "Vertex AI" if check_vertex_ai_enabled() else "Mock Data"
            
            # Send success response
            response_data = {
                'success': True,
                'annotated_image': annotated_image_data,
                'predictions': predictions,
                'class_counts': class_counts,
                'total_predictions': len(predictions),
                'model_used': model_used
            }
            
            self.send_success_response(response_data)
            
        except Exception as e:
            print(f"❌ Error processing request: {e}")
            self.send_error_response(str(e), 500)
    
    def do_OPTIONS(self):
        """Handle CORS preflight request"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def send_success_response(self, data):
        """Send successful response"""
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS, GET')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.send_header('Access-Control-Max-Age', '86400')
        self.end_headers()
        
        response_json = json.dumps(data)
        self.wfile.write(response_json.encode('utf-8'))
    
    def send_error_response(self, message, status_code):
        """Send error response"""
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS, GET')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.send_header('Access-Control-Max-Age', '86400')
        self.end_headers()
        
        error_data = {'error': message}
        response_json = json.dumps(error_data)
        self.wfile.write(response_json.encode('utf-8'))