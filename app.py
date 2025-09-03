import os
import json
import base64
from io import BytesIO
from flask import Flask, render_template, request, jsonify, send_file
from PIL import Image, ImageDraw, ImageFont
import numpy as np
from google.cloud import aiplatform
from google.auth import default
import tempfile

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Configure Google Cloud credentials
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = os.getenv('GOOGLE_APPLICATION_CREDENTIALS', '')
project_id = os.getenv('GOOGLE_CLOUD_PROJECT', '27458468732')
endpoint_id = os.getenv('VERTEX_ENDPOINT_ID', '3349211374252195840')
location = os.getenv('VERTEX_LOCATION', 'europe-west4')

# Initialize Vertex AI
aiplatform.init(project=project_id, location=location)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_image():
    try:
        if 'image' not in request.files:
            return jsonify({'error': 'No image file provided'}), 400
        
        file = request.files['image']
        if file.filename == '':
            return jsonify({'error': 'No image file selected'}), 400
        
        # Get parameters
        confidence_threshold = float(request.form.get('confidenceThreshold', 0.5))
        iou_threshold = float(request.form.get('iouThreshold', 0.5))
        max_predictions = int(request.form.get('maxPredictions', 100))
        
        # Save uploaded image temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as tmp_file:
            file.save(tmp_file.name)
            tmp_path = tmp_file.name
        
        # Call Vertex AI for prediction
        predictions = predict_image_object_detection(
            tmp_path, 
            confidence_threshold, 
            iou_threshold, 
            max_predictions
        )
        
        # Clean up temporary file
        os.unlink(tmp_path)
        
        if not predictions:
            return jsonify({'error': 'No predictions returned from model'}), 400
        
        # Process predictions and create annotated image
        annotated_image_data = create_annotated_image(file, predictions)
        
        # Count predictions by class
        class_counts = {}
        for pred in predictions:
            class_name = pred.get('displayName', 'Unknown')
            class_counts[class_name] = class_counts.get(class_name, 0) + 1
        
        return jsonify({
            'success': True,
            'annotated_image': annotated_image_data,
            'predictions': predictions,
            'class_counts': class_counts,
            'total_predictions': len(predictions)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def predict_image_object_detection(image_path, confidence_threshold, iou_threshold, max_predictions):
    """Call Vertex AI endpoint for image object detection"""
    try:
        endpoint = aiplatform.Endpoint(endpoint_name=endpoint_id)
        
        # Read and encode image
        with open(image_path, 'rb') as f:
            image_bytes = f.read()
        
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
        # Fallback to mock data for testing
        return get_mock_predictions()

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

def create_annotated_image(file, predictions):
    """Create an annotated image with bounding boxes and labels"""
    try:
        # Open image
        image = Image.open(file.stream)
        draw = ImageDraw.Draw(image)
        
        # Try to load a font, fall back to default if not available
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 16)
        except:
            font = ImageFont.load_default()
        
        # Define consistent colors based on class names
        def get_class_color(class_name):
            class_name_lower = class_name.lower()
            if 'weak' in class_name_lower:
                return 'red'
            elif 'medium' in class_name_lower:
                return 'yellow'
            elif 'thick' in class_name_lower:
                return 'green'
            elif class_name_lower == '1':
                return 'blue'
            elif class_name_lower == '2':
                return 'white'
            else:
                return 'red'  # default color
        
        # Draw bounding boxes and labels
        for pred in predictions:
            bbox = pred.get('bbox', [0, 0, 0, 0])
            class_name = pred.get('displayName', 'Unknown')
            confidence = pred.get('confidence', 0.0)
            
            # Get consistent color for this class
            color = get_class_color(class_name)
            
            # Convert normalized coordinates to pixel coordinates
            width, height = image.size
            x1 = int(bbox[0] * width)
            y1 = int(bbox[1] * height)
            x2 = int(bbox[2] * width)
            y2 = int(bbox[3] * height)
            
            # Draw bounding box
            draw.rectangle([x1, y1, x2, y2], outline=color, width=3)
            
            # Draw label background
            label = f"{class_name}: {confidence:.2f}"
            bbox_text = draw.textbbox((x1, y1 - 20), label, font=font)
            draw.rectangle(bbox_text, fill=color)
            
            # Draw label text - use black text for yellow background, white for others
            text_color = 'black' if color == 'yellow' else 'white'
            draw.text((x1, y1 - 20), label, fill=text_color, font=font)
        
        # Convert to base64 for sending to frontend
        buffer = BytesIO()
        image.save(buffer, format='JPEG')
        img_str = base64.b64encode(buffer.getvalue()).decode('utf-8')
        
        return f"data:image/jpeg;base64,{img_str}"
        
    except Exception as e:
        print(f"Error creating annotated image: {e}")
        return None

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)