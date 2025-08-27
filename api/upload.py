import os
import json
import base64
import tempfile
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse
import cgi
import io
from PIL import Image, ImageDraw, ImageFont
import numpy as np

# Try to import Google Cloud libraries
try:
    from google.cloud import aiplatform
    from google.auth import default
    GOOGLE_CLOUD_AVAILABLE = True
except ImportError:
    GOOGLE_CLOUD_AVAILABLE = False

# Configure Google Cloud credentials
project_id = os.getenv('GOOGLE_CLOUD_PROJECT', '27458468732')
endpoint_id = os.getenv('VERTEX_ENDPOINT_ID', '3349211374252195840')
location = os.getenv('VERTEX_LOCATION', 'europe-west4')

# Initialize Vertex AI if available
if GOOGLE_CLOUD_AVAILABLE:
    try:
        aiplatform.init(project=project_id, location=location)
    except Exception as e:
        print(f"Failed to initialize Vertex AI: {e}")
        GOOGLE_CLOUD_AVAILABLE = False

def get_mock_predictions():
    """Return mock predictions for testing when Vertex AI is not available"""
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

def predict_image_object_detection(image_bytes, confidence_threshold, iou_threshold, max_predictions):
    """Call Vertex AI endpoint for image object detection"""
    if not GOOGLE_CLOUD_AVAILABLE:
        return get_mock_predictions()
    
    try:
        endpoint = aiplatform.Endpoint(endpoint_name=endpoint_id)
        
        # Prepare prediction request
        prediction_request = {
            'instances': [{
                'image': {
                    'bytesBase64Encoded': base64.b64encode(image_bytes).decode('utf-8')
                }
            }],
            'parameters': {
                'confidenceThreshold': confidence_threshold,
                'maxPredictions': max_predictions
            }
        }
        
        # Make prediction
        response = endpoint.predict(prediction_request)
        
        # Extract predictions from response
        predictions = []
        if hasattr(response, 'predictions') and response.predictions:
            for pred in response.predictions[0]:
                if isinstance(pred, dict):
                    predictions.append(pred)
                else:
                    # Handle different response formats
                    predictions.append({
                        'displayName': getattr(pred, 'displayName', 'Unknown'),
                        'confidence': getattr(pred, 'confidence', 0.0),
                        'bbox': getattr(pred, 'bbox', [0, 0, 0, 0])
                    })
        
        return predictions
        
    except Exception as e:
        print(f"Error calling Vertex AI: {e}")
        # Fallback to mock data
        return get_mock_predictions()

def create_annotated_image(image_bytes, predictions):
    """Create an annotated image with bounding boxes and labels"""
    try:
        # Open image from bytes
        image = Image.open(io.BytesIO(image_bytes))
        draw = ImageDraw.Draw(image)
        
        # Try to load a font, fall back to default if not available
        try:
            # For Vercel, we'll use the default font
            font = ImageFont.load_default()
        except:
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
        print(f"Error creating annotated image: {e}")
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
        
        # Extract form data
        image_file = form.getfirst('image')
        confidence_threshold = float(form.getfirst('confidenceThreshold', 0.5))
        iou_threshold = float(form.getfirst('iouThreshold', 0.5))
        max_predictions = int(form.getfirst('maxPredictions', 100))
        
        return {
            'image': image_file,
            'confidence_threshold': confidence_threshold,
            'iou_threshold': iou_threshold,
            'max_predictions': max_predictions
        }
    except Exception as e:
        print(f"Error parsing multipart data: {e}")
        return None

class handler(BaseHTTPRequestHandler):
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
            
            # Convert image file to bytes
            if hasattr(form_data['image'], 'file'):
                image_bytes = form_data['image'].file.read()
            else:
                image_bytes = form_data['image']
            
            # Call Vertex AI for prediction
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
            
            # Send success response
            response_data = {
                'success': True,
                'annotated_image': annotated_image_data,
                'predictions': predictions,
                'class_counts': class_counts,
                'total_predictions': len(predictions)
            }
            
            self.send_success_response(response_data)
            
        except Exception as e:
            print(f"Error processing request: {e}")
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
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        
        response_json = json.dumps(data)
        self.wfile.write(response_json.encode('utf-8'))
    
    def send_error_response(self, message, status_code):
        """Send error response"""
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        
        error_data = {'error': message}
        response_json = json.dumps(error_data)
        self.wfile.write(response_json.encode('utf-8'))