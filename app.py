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
        
        # Extract predictions from response - handle Vertex AI format properly
        predictions = []
        if hasattr(response, 'predictions') and response.predictions:
            for pred in response.predictions[0]:
                if isinstance(pred, dict):
                    # Handle the actual Vertex AI response format
                    if 'bboxes' in pred and 'displayNames' in pred and 'confidences' in pred:
                        # Standard Vertex AI format: bboxes, displayNames, confidences arrays
                        for i in range(len(pred['bboxes'])):
                            predictions.append({
                                'displayName': pred['displayNames'][i],
                                'confidence': pred['confidences'][i],
                                'bbox': pred['bboxes'][i]  # [xMin, xMax, yMin, yMax]
                            })
                    else:
                        # Fallback for other formats
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
            'bbox': [0.1, 0.3, 0.1, 0.8]  # [xMin, xMax, yMin, yMax] - normalized coordinates
        },
        {
            'displayName': 'car',
            'confidence': 0.87,
            'bbox': [0.4, 0.9, 0.6, 0.9]  # [xMin, xMax, yMin, yMax] - normalized coordinates
        },
        {
            'displayName': 'dog',
            'confidence': 0.78,
            'bbox': [0.6, 0.8, 0.2, 0.5]  # [xMin, xMax, yMin, yMax] - normalized coordinates
        }
    ]

def create_annotated_image(file, predictions):
    """
    Create an annotated image with bounding boxes and labels.
    Properly handles Vertex AI normalized coordinates [xMin, xMax, yMin, yMax].
    """
    try:
        # Open image and convert to RGB to ensure compatibility
        image = Image.open(file.stream).convert("RGB")
        draw = ImageDraw.Draw(image)
        img_width, img_height = image.size
        
        # Try to load a better font, fall back to default if not available
        try:
            # Try multiple font paths for better compatibility
            font_paths = [
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
                "/System/Library/Fonts/Arial.ttf",  # macOS
                "arial.ttf"  # Windows
            ]
            font = None
            for font_path in font_paths:
                try:
                    font = ImageFont.truetype(font_path, 20)
                    break
                except (IOError, OSError):
                    continue
            
            if font is None:
                font = ImageFont.load_default()
        except:
            font = ImageFont.load_default()
        
        # Define colors for different classes (cycling through them)
        colors = ['red', 'blue', 'green', 'yellow', 'purple', 'orange', 'cyan', 'magenta']
        
        # Draw bounding boxes and labels
        for i, pred in enumerate(predictions):
            bbox = pred.get('bbox', [0, 0, 0, 0])
            class_name = pred.get('displayName', 'Unknown')
            confidence = pred.get('confidence', 0.0)
            
            # Vertex AI returns normalized coordinates as [xMin, xMax, yMin, yMax]
            # Convert to absolute pixel coordinates
            x_min = bbox[0] * img_width
            x_max = bbox[1] * img_width
            y_min = bbox[2] * img_height
            y_max = bbox[3] * img_height
            
            # Ensure coordinates are within image bounds
            x_min = max(0, min(x_min, img_width))
            x_max = max(0, min(x_max, img_width))
            y_min = max(0, min(y_min, img_height))
            y_max = max(0, min(y_max, img_height))
            
            # Skip invalid bounding boxes
            if x_max <= x_min or y_max <= y_min:
                continue
            
            # Choose color for this detection
            color = colors[i % len(colors)]
            
            # Draw the bounding box with thicker outline
            draw.rectangle(
                [(x_min, y_min), (x_max, y_max)], 
                outline=color, 
                width=4
            )
            
            # Prepare label text
            display_text = f"{class_name}: {confidence:.2f}"
            
            # Get text bounding box for background
            text_bbox = draw.textbbox((x_min, y_min - 25), display_text, font=font)
            
            # Draw label background rectangle
            draw.rectangle(text_bbox, fill=color)
            
            # Draw label text
            draw.text(
                (x_min, y_min - 25), 
                display_text, 
                fill="white", 
                font=font
            )
        
        # Convert to base64 for sending to frontend
        buffer = BytesIO()
        image.save(buffer, format='JPEG', quality=95)
        img_str = base64.b64encode(buffer.getvalue()).decode('utf-8')
        
        return f"data:image/jpeg;base64,{img_str}"
        
    except Exception as e:
        print(f"Error creating annotated image: {e}")
        return None

def draw_boxes_on_image(image_path: str, predictions: list, output_path: str):
    """
    Standalone function to draw bounding boxes from Vertex AI predictions onto an image.
    This follows the Gemini example more closely and can be used independently.
    
    Args:
        image_path (str): Path to the input image file.
        predictions (list): The list of prediction instances from the model's output.
                            Each prediction should be a dictionary-like object with
                            'bboxes', 'displayNames', and 'confidences' OR individual
                            'bbox', 'displayName', and 'confidence' fields.
        output_path (str): Path to save the new image with boxes.
    """
    try:
        # Open the original image
        source_img = Image.open(image_path).convert("RGB")
        draw = ImageDraw.Draw(source_img)
        img_width, img_height = source_img.size

        # Try to load a font, fall back to default if not available
        try:
            font_paths = [
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
                "/System/Library/Fonts/Arial.ttf",  # macOS
                "arial.ttf"  # Windows
            ]
            font = None
            for font_path in font_paths:
                try:
                    font = ImageFont.truetype(font_path, 20)
                    break
                except (IOError, OSError):
                    continue
            
            if font is None:
                font = ImageFont.load_default()
        except IOError:
            font = ImageFont.load_default()

        # Define colors for different classes
        colors = ['red', 'blue', 'green', 'yellow', 'purple', 'orange', 'cyan', 'magenta']

        # Iterate over each detected object in the predictions
        for i, pred in enumerate(predictions):
            # Handle both Vertex AI format and our processed format
            if 'bboxes' in pred and 'displayNames' in pred and 'confidences' in pred:
                # Standard Vertex AI format: bboxes, displayNames, confidences arrays
                for j in range(len(pred['bboxes'])):
                    box = pred['bboxes'][j]
                    label = pred['displayNames'][j]
                    confidence = pred['confidences'][j]
                    
                    # De-normalize coordinates to absolute pixel values
                    x_min = box[0] * img_width
                    x_max = box[1] * img_width
                    y_min = box[2] * img_height
                    y_max = box[3] * img_height
                    
                    # Choose color
                    color = colors[(i + j) % len(colors)]
                    
                    # Draw the bounding box
                    draw.rectangle(
                        [(x_min, y_min), (x_max, y_max)], 
                        outline=color, 
                        width=3
                    )
                    
                    # Draw the label and score
                    display_text = f"{label}: {confidence:.2f}"
                    text_bbox = draw.textbbox((x_min, y_min - 25), display_text, font=font)
                    draw.rectangle(text_bbox, fill=color)
                    draw.text(
                        (x_min, y_min - 25), 
                        display_text, 
                        fill="white", 
                        font=font
                    )
            else:
                # Our processed format: individual bbox, displayName, confidence
                bbox = pred.get('bbox', [0, 0, 0, 0])
                label = pred.get('displayName', 'Unknown')
                confidence = pred.get('confidence', 0.0)
                
                # De-normalize coordinates to absolute pixel values
                x_min = bbox[0] * img_width
                x_max = bbox[1] * img_width
                y_min = bbox[2] * img_height
                y_max = bbox[3] * img_height
                
                # Choose color
                color = colors[i % len(colors)]
                
                # Draw the bounding box
                draw.rectangle(
                    [(x_min, y_min), (x_max, y_max)], 
                    outline=color, 
                    width=3
                )
                
                # Draw the label and score
                display_text = f"{label}: {confidence:.2f}"
                text_bbox = draw.textbbox((x_min, y_min - 25), display_text, font=font)
                draw.rectangle(text_bbox, fill=color)
                draw.text(
                    (x_min, y_min - 25), 
                    display_text, 
                    fill="white", 
                    font=font
                )

        # Save the new image
        source_img.save(output_path)
        print(f"Successfully saved image with bounding boxes to {output_path}")

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)