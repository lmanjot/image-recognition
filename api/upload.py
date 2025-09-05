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

# Thickness Model Configuration
thickness_project_id = os.getenv('THICKNESS_PROJECT_ID', '27458468732')
thickness_endpoint_id = os.getenv('THICKNESS_ENDPOINT_ID', '8594040168418115584')
thickness_location = os.getenv('THICKNESS_LOCATION', 'europe-west4')

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

def compress_image(image_bytes, max_size_mb=0.8, quality=85):
    """
    Compress image to reduce file size while maintaining quality.
    
    Args:
        image_bytes: Original image bytes
        max_size_mb: Maximum size in MB (default 0.8MB for Vertex AI)
        quality: JPEG quality (1-100, default 85)
    
    Returns:
        Compressed image bytes
    """
    try:
        # Open image with Pillow
        image = Image.open(io.BytesIO(image_bytes))
        
        # Convert to RGB if necessary (for JPEG compatibility)
        if image.mode in ('RGBA', 'LA', 'P'):
            # Create white background for transparent images
            background = Image.new('RGB', image.size, (255, 255, 255))
            if image.mode == 'P':
                image = image.convert('RGBA')
            background.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
            image = background
        elif image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Check current size
        current_size_mb = len(image_bytes) / (1024 * 1024)
        print(f"📏 Original image size: {current_size_mb:.2f} MB")
        
        if current_size_mb <= max_size_mb:
            print(f"✅ Image size OK ({current_size_mb:.2f} MB <= {max_size_mb} MB)")
            return image_bytes
        
        # Compress the image
        output = io.BytesIO()
        
        # Try different quality levels if needed
        for attempt_quality in [quality, 75, 65, 55, 45]:
            output.seek(0)
            output.truncate(0)
            
            image.save(output, format='JPEG', quality=attempt_quality, optimize=True)
            compressed_size_mb = len(output.getvalue()) / (1024 * 1024)
            
            print(f"🔧 Compression attempt: quality={attempt_quality}, size={compressed_size_mb:.2f} MB")
            
            if compressed_size_mb <= max_size_mb:
                print(f"✅ Compression successful: {compressed_size_mb:.2f} MB (quality={attempt_quality})")
                return output.getvalue()
        
        # If still too large, resize the image
        print(f"⚠️ Still too large after compression, resizing image...")
        original_size = image.size
        scale_factor = 0.8
        
        while scale_factor > 0.3:  # Don't go below 30% of original size
            new_size = (int(original_size[0] * scale_factor), int(original_size[1] * scale_factor))
            resized_image = image.resize(new_size, Image.Resampling.LANCZOS)
            
            output.seek(0)
            output.truncate(0)
            resized_image.save(output, format='JPEG', quality=75, optimize=True)
            final_size_mb = len(output.getvalue()) / (1024 * 1024)
            
            print(f"🔧 Resize attempt: {new_size}, size={final_size_mb:.2f} MB")
            
            if final_size_mb <= max_size_mb:
                print(f"✅ Resize successful: {final_size_mb:.2f} MB (scale={scale_factor:.1f})")
                return output.getvalue()
            
            scale_factor -= 0.1
        
        # Last resort: return the smallest we could make it
        print(f"⚠️ Using smallest possible size: {final_size_mb:.2f} MB")
        return output.getvalue()
        
    except Exception as e:
        print(f"❌ Error compressing image: {e}")
        # Return original if compression fails
        return image_bytes

def calculate_follicular_metrics(predictions):
    """
    Calculate follicular unit density and hair metrics based on known area.
    
    Args:
        predictions: List of prediction dictionaries with displayName and confidence
    
    Returns:
        Dictionary with calculated metrics
    """
    # Known area: 7mm x 3.94mm = 0.273 cm²
    AREA_CM2 = 0.273
    
    # Initialize counters
    total_follicular_units = 0
    total_hairs = 0
    fu_with_one_hair = 0
    fu_with_multiple_hairs = 0
    class_counts = {}
    
    for pred in predictions:
        class_name = pred.get('displayName', 'Unknown')
        confidence = pred.get('confidence', 0.0)
        
        # Skip low confidence predictions
        if confidence < 0.1:  # Use same threshold as confidence filter
            continue
            
        # Extract class number (e.g., "1" -> 1, "2" -> 2, "class1" -> 1, "class2" -> 2)
        try:
            if class_name.lower().startswith('class'):
                class_number = int(class_name.lower().replace('class', ''))
            else:
                # Try to parse the class name directly as a number
                class_number = int(class_name)
        except:
            class_number = 1
        
        # Count follicular units and hairs
        total_follicular_units += 1
        total_hairs += class_number
        
        # Track class distribution
        if class_name not in class_counts:
            class_counts[class_name] = 0
        class_counts[class_name] += 1
    
    # Calculate FU breakdown from class counts
    for class_name, count in class_counts.items():
        try:
            if class_name.lower().startswith('class'):
                class_number = int(class_name.lower().replace('class', ''))
            else:
                # Try to parse the class name directly as a number
                class_number = int(class_name)
        except:
            class_number = 1
            

            
        if class_number == 1:
            fu_with_one_hair += count
        else:
            fu_with_multiple_hairs += count
    
    # Calculate metrics
    follicular_density = total_follicular_units / AREA_CM2 if AREA_CM2 > 0 else 0
    average_hair_per_unit = total_hairs / total_follicular_units if total_follicular_units > 0 else 0
    
    metrics = {
        'total_follicular_units': total_follicular_units,
        'total_hairs': total_hairs,
        'follicular_density_per_cm2': round(follicular_density, 2),
        'average_hair_per_unit': round(average_hair_per_unit, 2),
        'fu_with_one_hair': fu_with_one_hair,
        'fu_with_multiple_hairs': fu_with_multiple_hairs,
        'area_cm2': AREA_CM2,
        'class_distribution': class_counts
    }
    
    print(f"📊 Follicular Metrics:")
    print(f"  - Total FU: {total_follicular_units}")
    print(f"  - Total Hairs: {total_hairs}")
    print(f"  - FU Density: {follicular_density:.2f} per cm²")
    print(f"  - Avg Hairs/FU: {average_hair_per_unit:.2f}")
    print(f"  - FU with 1 Hair: {fu_with_one_hair}")
    print(f"  - FU with 2+ Hairs: {fu_with_multiple_hairs}")

    
    return metrics

def calculate_combined_metrics(density_predictions, thickness_predictions):
    """
    Calculate combined metrics from both density and thickness models.
    """
    if not density_predictions and not thickness_predictions:
        return {
            'terminal_to_vellus_ratio': 0.0,
            'percent_thick_hairs': 0.0,
            'hair_caliber_index': 0,
            'average_thickness_score': 0.0,
            'hairs_per_fu': 0.0,
            'hairs_per_cm2': 0.0,
            'effective_hair_density': 0.0
        }
    
    # Known area in cm²
    AREA_CM2 = 0.273
    
    # Calculate density metrics
    density_metrics = calculate_follicular_metrics(density_predictions) if density_predictions else {
        'total_follicular_units': 0,
        'total_hairs': 0
    }
    
    # Extract values from density model (ground truth for hair count)
    total_hairs = density_metrics['total_hairs']
    total_fu = density_metrics['total_follicular_units']
    
    # Calculate raw thickness metrics
    if thickness_predictions:
        strong_hairs_raw = sum(1 for p in thickness_predictions if p['displayName'] == 'strong')
        medium_hairs_raw = sum(1 for p in thickness_predictions if p['displayName'] == 'medium')
        weak_hairs_raw = sum(1 for p in thickness_predictions if p['displayName'] == 'weak')
        total_thickness_detections_raw = len(thickness_predictions)
    else:
        strong_hairs_raw = 0
        medium_hairs_raw = 0
        weak_hairs_raw = 0
        total_thickness_detections_raw = 0
    
    # Scale thickness model results proportionally to match density model hair count
    # This fixes the issue where models detect different numbers of hairs
    if total_thickness_detections_raw > 0 and total_hairs > 0:
        # Calculate percentages from thickness model
        strong_percentage = strong_hairs_raw / total_thickness_detections_raw
        medium_percentage = medium_hairs_raw / total_thickness_detections_raw
        weak_percentage = weak_hairs_raw / total_thickness_detections_raw
        
        # Scale to density model hair count
        strong_hairs = strong_percentage * total_hairs
        medium_hairs = medium_percentage * total_hairs
        weak_hairs = weak_percentage * total_hairs
        total_thickness_detections = total_hairs  # Use density model count as ground truth
        
        print(f"🔧 Scaling thickness results:")
        print(f"  - Raw thickness detections: {total_thickness_detections_raw} (strong: {strong_hairs_raw}, medium: {medium_hairs_raw}, weak: {weak_hairs_raw})")
        print(f"  - Density model hair count: {total_hairs}")
        print(f"  - Scaled thickness: strong: {strong_hairs:.1f}, medium: {medium_hairs:.1f}, weak: {weak_hairs:.1f}")
    else:
        # Fallback if no thickness detections
        strong_hairs = 0
        medium_hairs = 0
        weak_hairs = 0
        total_thickness_detections = 0
    
    # Calculate combined metrics
    # Terminal-to-Vellus Ratio = weak/strong (vellus/terminal) as percentage (return 0 if strong = 0)
    terminal_to_vellus_ratio = (weak_hairs / strong_hairs * 100) if strong_hairs > 0 else 0.0
    
    # % Thick Hairs = (strong_hairs / total_thickness_detections) * 100
    percent_thick_hairs = (strong_hairs / total_thickness_detections * 100) if total_thickness_detections > 0 else 0.0
    
    # Hair Caliber Index (HCI) = (strong_hairs * 3) + (medium_hairs * 1.5) + (weak_hairs * 1)
    hair_caliber_index = int((strong_hairs * 3) + (medium_hairs * 1.5) + (weak_hairs * 1))
    
    # Hair Caliber Index % (HCI%) = (HCI / (total_hairs * 3)) * 100
    # Normalizes the score on a 0-100 scale, assuming ideal case is all hairs = thick (weight 3)
    hair_caliber_index_percentage = (hair_caliber_index / (total_hairs * 3) * 100) if total_hairs > 0 else 0.0
    
    # Average Thickness Score = HCI / total_thickness_detections
    average_thickness_score = hair_caliber_index / total_thickness_detections if total_thickness_detections > 0 else 0.0
    
    # Hairs per FU = total_hairs / total_FU
    hairs_per_fu = total_hairs / total_fu if total_fu > 0 else 0.0
    
    # Hairs per cm2 = total_hairs / picture_area_cm2
    hairs_per_cm2 = total_hairs / AREA_CM2 if AREA_CM2 > 0 else 0.0
    
    # EHD = (hairs_per_cm2 * avg_thickness_score) / 3
    effective_hair_density = (hairs_per_cm2 * average_thickness_score) / 3.0
    
    # EHD_max = (220 * 3) / 3 = 220
    ehd_max = 220.0
    
    # EHD_percent = (EHD / EHD_max) * 100
    # Normalizes effective hair density to a 0-100 percentage scale
    ehd_percentage = (effective_hair_density / ehd_max * 100) if ehd_max > 0 else 0.0
    
    # Overall Hair Score (OHS) = (2 / ((1 / (HCI_percent/100)) + (1 / (EHD_percent/100)))) * 100
    # Harmonic mean of HCI% and EHD% for overall hair quality assessment
    hci_normalized = hair_caliber_index_percentage / 100.0
    ehd_normalized = ehd_percentage / 100.0
    
    # If either HCI_percent or EHD_percent is 0, set OHS = 0 to avoid division by zero
    if hci_normalized > 0 and ehd_normalized > 0:
        overall_hair_score = (2 / ((1 / hci_normalized) + (1 / ehd_normalized))) * 100
    else:
        overall_hair_score = 0.0
    
    # Define interpretation bands for OHS (Red: <50, Orange: 50-80, Green: ≥80)
    if overall_hair_score >= 80:
        ohs_interpretation = "Good"
        ohs_color = "success"
    elif overall_hair_score >= 50:
        ohs_interpretation = "Borderline"
        ohs_color = "warning"
    else:
        ohs_interpretation = "Poor Coverage/Density"
        ohs_color = "danger"
    
    # Define interpretation bands for HCI% (Red: <50, Orange: 50-80, Green: ≥80)
    if hair_caliber_index_percentage >= 80:
        hci_color = "success"
    elif hair_caliber_index_percentage >= 50:
        hci_color = "warning"
    else:
        hci_color = "danger"
    
    # Define interpretation bands for EHD% (Red: <50, Orange: 50-80, Green: ≥80)
    if ehd_percentage >= 80:
        ehd_color = "success"
    elif ehd_percentage >= 50:
        ehd_color = "warning"
    else:
        ehd_color = "danger"
    
    # Define interpretation bands for Hairs per cm² (Red: <110, Orange: 110-150, Green: ≥150)
    if hairs_per_cm2 >= 150:
        hairs_per_cm2_color = "success"
    elif hairs_per_cm2 >= 110:
        hairs_per_cm2_color = "warning"
    else:
        hairs_per_cm2_color = "danger"
    
    # Define interpretation bands for Terminal-to-Vellus Ratio (Red: <4, Orange: 4-7, Green: ≥7)
    if terminal_to_vellus_ratio >= 7:
        terminal_to_vellus_color = "success"
    elif terminal_to_vellus_ratio >= 4:
        terminal_to_vellus_color = "warning"
    else:
        terminal_to_vellus_color = "danger"
    
    # Define interpretation bands for Thick Hair % (Red: <75%, Orange: 75-90%, Green: ≥90%)
    if percent_thick_hairs >= 90:
        thick_hair_color = "success"
    elif percent_thick_hairs >= 75:
        thick_hair_color = "warning"
    else:
        thick_hair_color = "danger"
    
    print(f"📊 Combined Metrics (using density model hair count as ground truth):")
    print(f"  - Terminal-to-Vellus Ratio (weak/strong): {terminal_to_vellus_ratio:.1f}%")
    print(f"  - % Thick Hairs (strong/total): {percent_thick_hairs:.1f}%")
    print(f"  - Hair Caliber Index: {hair_caliber_index}")
    print(f"  - Hair Caliber Index %: {hair_caliber_index_percentage:.1f}%")
    print(f"  - Average Thickness Score: {average_thickness_score:.2f}")
    print(f"  - Hairs per FU: {hairs_per_fu:.2f}")
    print(f"  - Hairs per cm²: {hairs_per_cm2:.1f}")
    print(f"  - EHD = (hairs_per_cm² × avg_thickness_score) / 3: {effective_hair_density:.1f}")
    print(f"  - EHD_max: {ehd_max}")
    print(f"  - EHD% = (EHD / EHD_max) × 100: {ehd_percentage:.1f}%")
    print(f"  - Overall Hair Score (OHS) - Harmonic Mean: {overall_hair_score:.1f}% ({ohs_interpretation})")
    print(f"  - Final thickness breakdown: {strong_hairs:.1f} strong, {medium_hairs:.1f} medium, {weak_hairs:.1f} weak")
    
    return {
        'terminal_to_vellus_ratio': round(terminal_to_vellus_ratio, 1),  # Percentage, 1 decimal
        'terminal_to_vellus_color': terminal_to_vellus_color,  # Terminal-to-Vellus color class
        'percent_thick_hairs': round(percent_thick_hairs, 1),  # Percentage, 1 decimal
        'thick_hair_color': thick_hair_color,  # Thick Hair % color class
        'hair_caliber_index': hair_caliber_index,  # Integer
        'hair_caliber_index_percentage': round(hair_caliber_index_percentage, 1),  # Percentage, 1 decimal
        'hci_color': hci_color,  # HCI% color class for styling
        'average_thickness_score': round(average_thickness_score, 2),  # Score, 2 decimals
        'hairs_per_fu': round(hairs_per_fu, 2),  # Double digit, 2 decimals
        'hairs_per_cm2': round(hairs_per_cm2, 1),  # No comma, 1 decimal
        'hairs_per_cm2_color': hairs_per_cm2_color,  # Hairs per cm² color class
        'effective_hair_density': round(effective_hair_density, 1),  # 1 decimal
        'ehd_percentage': round(ehd_percentage, 1),  # EHD%, 1 decimal
        'ehd_color': ehd_color,  # EHD% color class for styling
        'overall_hair_score': round(overall_hair_score, 1),  # OHS%, 1 decimal
        'ohs_interpretation': ohs_interpretation,  # Interpretation text
        'ohs_color': ohs_color  # Color class for styling
    }

def get_mock_predictions():
    """Return empty predictions when Vertex AI is not available - no mock data"""
    print("⚠️ Returning empty predictions - Vertex AI not available")
    return []

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

def predict_image_object_detection_rest(image_bytes, confidence_threshold, iou_threshold, padding_factor, max_predictions):
    """Call Vertex AI endpoint using REST API (lightweight approach)"""
    print(f"\n🔍 Starting Vertex AI prediction process...")
    print(f"  - Original image size: {len(image_bytes)} bytes")
    print(f"  - Confidence threshold: {confidence_threshold}")
    print(f"  - NMS threshold: {iou_threshold}")
    print(f"  - Padding factor: {padding_factor}")
    print(f"  - Max predictions: {max_predictions}")
    
    # Compress image if it's too large for Vertex AI
    compressed_image_bytes = compress_image(image_bytes, max_size_mb=0.8)
    print(f"  - Compressed image size: {len(compressed_image_bytes)} bytes")
    
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
        
        # Make actual API call to Vertex AI with high IoU threshold to get all raw detections
        # We'll apply our own NMS later
        predictions = call_vertex_ai_endpoint(
            compressed_image_bytes,  # Use compressed image
            confidence_threshold, 
            0.99,  # Very high IoU threshold to get all raw detections
            200,   # High max predictions to get all detections
            access_token
        )
        
        if predictions:
            print("🎉 Real Vertex AI predictions received!")
            print(f"  - Number of raw predictions: {len(predictions)}")
            for i, pred in enumerate(predictions):
                print(f"    {i+1}. {pred.get('displayName', 'Unknown')} - {pred.get('confidence', 0.0):.3f}")
            
            # Apply our own NMS to filter overlapping detections
            filtered_predictions = apply_nms(predictions, iou_threshold, padding_factor, max_predictions)
            print(f"  - Number of predictions after NMS: {len(filtered_predictions)}")
            return filtered_predictions
        else:
            print("⚠️ Vertex AI call failed, falling back to mock data")
            return get_mock_predictions()
        
    except Exception as e:
        print(f"❌ Error calling Vertex AI: {e}")
        import traceback
        traceback.print_exc()
        print("🔄 Falling back to mock data")
        return get_mock_predictions()

def predict_image_object_detection(image_bytes, confidence_threshold, iou_threshold, padding_factor, max_predictions):
    """Main prediction function - optimized to reduce redundant calls"""
    # Single call to the REST function - no more redundant calls
    return predict_image_object_detection_rest(
        image_bytes, confidence_threshold, iou_threshold, padding_factor, max_predictions
    )

def call_thickness_vertex_ai_endpoint(image_bytes, confidence_threshold, iou_threshold, max_predictions, access_token):
    """Make actual API call to Thickness Vertex AI endpoint - SAME AS DENSITY MODEL"""
    try:
        print("🚀 Making API call to Thickness Vertex AI endpoint...")
        
        # Construct the Thickness Vertex AI endpoint URL - ONLY DIFFERENCE FROM DENSITY MODEL
        endpoint_url = f"https://{thickness_location}-aiplatform.googleapis.com/v1/projects/{thickness_project_id}/locations/{thickness_location}/endpoints/{thickness_endpoint_id}:predict"
        print(f"  - Thickness Endpoint URL: {endpoint_url}")
        
        # Prepare the request payload - EXACT SAME AS DENSITY MODEL
        payload = {
            "instances": [
                {
                    "content": base64.b64encode(image_bytes).decode('utf-8')
                }
            ],
            "parameters": {
                "confidenceThreshold": confidence_threshold,
                "maxPredictions": max_predictions,
                "iouThreshold": iou_threshold
            }
        }
        
        # Make the API request - EXACT SAME AS DENSITY MODEL
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        print(f"  - Making request with confidence: {confidence_threshold}, max: {max_predictions}, IoU: {iou_threshold}")
        
        # Log the exact API call being made
        print(f"🔍 EXACT API CALL DETAILS:")
        print(f"  - URL: {endpoint_url}")
        print(f"  - Method: POST")
        print(f"  - Headers: {headers}")
        print(f"  - Payload: {payload}")
        
        # Generate curl command for debugging
        curl_command = f"""curl -X POST '{endpoint_url}' \\
  -H 'Authorization: Bearer {access_token}' \\
  -H 'Content-Type: application/json' \\
  -d '{json.dumps(payload)}'"""
        print(f"🔍 CURL COMMAND:")
        print(curl_command)
        
        response = requests.post(endpoint_url, json=payload, headers=headers, timeout=30)
        
        # Log response details
        print(f"🔍 API RESPONSE DETAILS:")
        print(f"  - Status Code: {response.status_code}")
        print(f"  - Response Headers: {dict(response.headers)}")
        print(f"  - Response Text: {response.text}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Thickness Vertex AI API call successful")
            print(f"  - Full Response JSON: {json.dumps(result, indent=2)}")
            
            # Parse predictions from response - THICKNESS MODEL FORMAT
            predictions = []
            if 'predictions' in result and result['predictions']:
                for pred in result['predictions']:
                    # Thickness model returns arrays: displayNames, bboxes, confidences
                    if 'displayNames' in pred and 'bboxes' in pred and 'confidences' in pred:
                        display_names = pred['displayNames']
                        bboxes = pred['bboxes']
                        confidences = pred['confidences']
                        
                        # Combine the arrays into individual predictions
                        for i in range(len(display_names)):
                            if confidences[i] >= confidence_threshold:
                                predictions.append({
                                    'displayName': display_names[i],
                                    'confidence': confidences[i],
                                    'bbox': bboxes[i]
                                })
                    # Fallback to density model format if needed
                    elif 'detections' in pred:
                        for detection in pred['detections']:
                            if detection.get('confidence', 0) >= confidence_threshold:
                                predictions.append({
                                    'displayName': detection.get('displayName', 'Unknown'),
                                    'confidence': detection.get('confidence', 0),
                                    'bbox': detection.get('bbox', [0, 0, 0, 0])
                                })
            
            print(f"  - Raw thickness predictions: {len(predictions)}")
            return predictions
            
        else:
            print(f"❌ Thickness Vertex AI API error: {response.status_code}")
            print(f"  - Response: {response.text}")
            return []
            
    except Exception as e:
        print(f"❌ Error calling thickness Vertex AI endpoint: {e}")
        import traceback
        traceback.print_exc()
        return []

def predict_thickness_model_rest(image_bytes, confidence_threshold, iou_threshold, padding_factor, max_predictions):
    """Call Thickness Vertex AI endpoint using REST API - EXACT SAME AS DENSITY MODEL"""
    print(f"\n🔍 Starting Thickness Vertex AI prediction process...")
    print(f"  - Original image size: {len(image_bytes)} bytes")
    print(f"  - Confidence threshold: {confidence_threshold}")
    print(f"  - NMS threshold: {iou_threshold}")
    print(f"  - Padding factor: {padding_factor}")
    print(f"  - Max predictions: {max_predictions}")
    
    # Compress image if it's too large for Vertex AI - SAME AS DENSITY MODEL
    compressed_image_bytes = compress_image(image_bytes, max_size_mb=0.8)
    print(f"  - Compressed image size: {len(compressed_image_bytes)} bytes")
    
    # Check Vertex AI configuration at runtime - SAME AS DENSITY MODEL
    vertex_ai_enabled = check_vertex_ai_enabled()
    
    if not vertex_ai_enabled:
        print("⚠️ Vertex AI not configured, using mock data for thickness model")
        print("  - Missing environment variables")
        return get_mock_thickness_predictions()
    
    try:
        print("🔍 Vertex AI configured - attempting real API call for thickness model")
        
        # Get the service account credentials from environment - SAME AS DENSITY MODEL
        credentials_json = os.getenv('GOOGLE_CREDENTIALS')
        if not credentials_json:
            print("❌ No credentials found in environment")
            return get_mock_thickness_predictions()
        
        print("✅ Credentials found in environment")
        print(f"  - Credentials length: {len(credentials_json)} characters")
        
        # Get access token - SAME AS DENSITY MODEL
        access_token = get_google_access_token(credentials_json)
        if not access_token:
            print("❌ Failed to get access token")
            return get_mock_thickness_predictions()
        
        print("✅ Access token obtained for thickness model")
        
        # Make actual API call to Thickness Vertex AI - SAME AS DENSITY MODEL
        predictions = call_thickness_vertex_ai_endpoint(
            compressed_image_bytes,  # Use compressed image
            confidence_threshold, 
            0.99,  # Very high IoU threshold to get all raw detections
            200,   # High max predictions to get all detections
            access_token
        )
        
        if predictions:
            print("🎉 Real Thickness Vertex AI predictions received!")
            print(f"  - Number of raw predictions: {len(predictions)}")
            for i, pred in enumerate(predictions):
                print(f"    {i+1}. {pred.get('displayName', 'Unknown')} - {pred.get('confidence', 0.0):.3f}")
            
            # Apply our own NMS to filter overlapping detections - SAME AS DENSITY MODEL
            filtered_predictions = apply_nms(predictions, iou_threshold, padding_factor, max_predictions)
            print(f"  - Number of predictions after NMS: {len(filtered_predictions)}")
            return filtered_predictions
        else:
            print("⚠️ Thickness Vertex AI call failed, falling back to mock data")
            return get_mock_thickness_predictions()
        
    except Exception as e:
        print(f"❌ Error calling Thickness Vertex AI: {e}")
        import traceback
        traceback.print_exc()
        print("🔄 Falling back to mock data for thickness model")
        return get_mock_thickness_predictions()

def get_mock_thickness_predictions():
    """Return mock thickness predictions for testing"""
    return [
        {'displayName': 'strong', 'confidence': 0.95, 'bbox': [0.1, 0.3, 0.1, 0.8]},
        {'displayName': 'medium', 'confidence': 0.87, 'bbox': [0.4, 0.9, 0.3, 0.7]},
        {'displayName': 'weak', 'confidence': 0.78, 'bbox': [0.6, 0.8, 0.2, 0.5]}
    ]

def create_combined_annotated_image(image_bytes, density_predictions, thickness_predictions, density_padding_factor, thickness_padding_factor):
    """Create a single image with both density and thickness overlays"""
    try:
        print("🎨 Creating combined annotated image...")
        
        # Load the original image
        image = Image.open(io.BytesIO(image_bytes))
        draw = ImageDraw.Draw(image)
        
        # Get image dimensions
        img_width, img_height = image.size
        print(f"  - Image dimensions: {img_width}x{img_height}")
        
        # Try to load a font
        try:
            # Try different font paths for different platforms
            font_paths = [
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                "/System/Library/Fonts/Arial.ttf",
                "C:/Windows/Fonts/arial.ttf",
                "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
            ]
            
            font = None
            for font_path in font_paths:
                try:
                    font = ImageFont.truetype(font_path, 16)
                    print(f"  - Using font: {font_path}")
                    break
                except:
                    continue
            
            if font is None:
                font = ImageFont.load_default()
                print("  - Using default font")
                
        except Exception as e:
            print(f"  - Font loading error: {e}")
            font = ImageFont.load_default()
        
        # Draw density predictions with consistent colors
        if density_predictions:
            print(f"  - Drawing {len(density_predictions)} density predictions with padding {density_padding_factor}")
            for pred in density_predictions:
                bbox = pred.get('bbox', [])
                if len(bbox) == 4:
                    # Apply density-specific padding to bounding box
                    padded_bbox = apply_padding_to_bbox(bbox, density_padding_factor)
                    
                    # Convert normalized coordinates to absolute pixels
                    x_min = int(padded_bbox[0] * img_width)
                    y_min = int(padded_bbox[2] * img_height)
                    x_max = int(padded_bbox[1] * img_width)
                    y_max = int(padded_bbox[3] * img_height)
                    
                    # Get class-specific color: 1=blue, 2=white
                    class_name = pred.get('displayName', 'Unknown')
                    if class_name == '1':
                        color = 'blue'
                    elif class_name == '2':
                        color = 'white'
                    else:
                        color = 'blue'  # default
                    
                    # Draw rectangle for density
                    draw.rectangle([x_min, y_min, x_max, y_max], outline=color, width=2)
                    
                    # Add label
                    confidence = pred.get('confidence', 0.0)
                    label = f"{class_name}: {confidence:.2f}"
                    
                    # Draw label background
                    bbox_text = draw.textbbox((x_min, y_min - 20), label, font=font)
                    draw.rectangle(bbox_text, fill=color)
                    draw.text((x_min, y_min - 20), label, fill='black' if color == 'white' else 'white', font=font)
        
        # Draw thickness predictions with consistent colors
        if thickness_predictions:
            print(f"  - Drawing {len(thickness_predictions)} thickness predictions with padding {thickness_padding_factor}")
            for pred in thickness_predictions:
                bbox = pred.get('bbox', [])
                if len(bbox) == 4:
                    # Apply thickness-specific padding to bounding box
                    padded_bbox = apply_padding_to_bbox(bbox, thickness_padding_factor)
                    
                    # Convert normalized coordinates to absolute pixels
                    x_min = int(padded_bbox[0] * img_width)
                    y_min = int(padded_bbox[2] * img_height)
                    x_max = int(padded_bbox[1] * img_width)
                    y_max = int(padded_bbox[3] * img_height)
                    
                    # Get class-specific color: weak=red, medium=yellow, strong=green
                    class_name = pred.get('displayName', 'Unknown')
                    if class_name == 'weak':
                        color = 'red'
                    elif class_name == 'medium':
                        color = 'yellow'
                    elif class_name == 'strong':
                        color = 'green'
                    else:
                        color = 'green'  # default
                    
                    # Draw rectangle for thickness
                    draw.rectangle([x_min, y_min, x_max, y_max], outline=color, width=2)
                    
                    # Add label
                    confidence = pred.get('confidence', 0.0)
                    label = f"{class_name}: {confidence:.2f}"
                    
                    # Draw label background
                    bbox_text = draw.textbbox((x_min, y_min - 20), label, font=font)
                    draw.rectangle(bbox_text, fill=color)
                    draw.text((x_min, y_min - 20), label, fill='black' if color == 'yellow' else 'white', font=font)
        
        # Convert to base64
        img_buffer = io.BytesIO()
        image.save(img_buffer, format='PNG')
        img_buffer.seek(0)
        
        # Encode as base64
        img_base64 = base64.b64encode(img_buffer.getvalue()).decode('utf-8')
        data_url = f"data:image/png;base64,{img_base64}"
        
        print("✅ Combined annotated image created successfully")
        return data_url
        
    except Exception as e:
        print(f"❌ Error creating combined annotated image: {e}")
        import traceback
        traceback.print_exc()
        return None

def calculate_iou(box1, box2):
    """
    Calculate Intersection over Union (IoU) of two bounding boxes.
    Boxes are in format [xMin, xMax, yMin, yMax] (normalized coordinates).
    """
    # Extract coordinates
    x1_min, x1_max, y1_min, y1_max = box1
    x2_min, x2_max, y2_min, y2_max = box2
    
    # Calculate intersection area
    x_left = max(x1_min, x2_min)
    y_top = max(y1_min, y2_min)
    x_right = min(x1_max, x2_max)
    y_bottom = min(y1_max, y2_max)
    
    if x_right < x_left or y_bottom < y_top:
        return 0.0
    
    intersection_area = (x_right - x_left) * (y_bottom - y_top)
    
    # Calculate union area
    box1_area = (x1_max - x1_min) * (y1_max - y1_min)
    box2_area = (x2_max - x2_min) * (y2_max - y2_min)
    union_area = box1_area + box2_area - intersection_area
    
    if union_area == 0:
        return 0.0
    
    return intersection_area / union_area

def apply_padding_to_bbox(bbox, padding_factor):
    """
    Apply padding to a bounding box.
    
    Args:
        bbox: [xMin, xMax, yMin, yMax] in normalized coordinates
        padding_factor: 0.0 = no padding, 1.0 = double size
    
    Returns:
        Padded bounding box [xMin, xMax, yMin, yMax]
    """
    if padding_factor == 0.0:
        return bbox
    
    x_min, x_max, y_min, y_max = bbox
    
    # Calculate center and dimensions
    center_x = (x_min + x_max) / 2
    center_y = (y_min + y_max) / 2
    width = x_max - x_min
    height = y_max - y_min
    
    # Apply padding
    new_width = width * (1 + padding_factor)
    new_height = height * (1 + padding_factor)
    
    # Calculate new coordinates
    new_x_min = max(0.0, center_x - new_width / 2)
    new_x_max = min(1.0, center_x + new_width / 2)
    new_y_min = max(0.0, center_y - new_height / 2)
    new_y_max = min(1.0, center_y + new_height / 2)
    
    return [new_x_min, new_x_max, new_y_min, new_y_max]

def get_class_number(class_name):
    """Extract class number from class name (e.g., 'class1' -> 1, 'class2' -> 2)"""
    try:
        if class_name.lower().startswith('class'):
            return int(class_name.lower().replace('class', ''))
        else:
            # For non-class names, use a default priority
            return 0
    except:
        return 0

def apply_nms(predictions, iou_threshold, padding_factor, max_predictions):
    """
    Apply Non-Maximum Suppression to filter overlapping bounding boxes.
    
    Args:
        predictions: List of prediction dictionaries
        iou_threshold: IoU threshold for NMS (0.0 to 1.0)
        padding_factor: Padding factor to apply before NMS (0.0 to 1.0)
        max_predictions: Maximum number of predictions to return
    
    Returns:
        List of filtered predictions
    """
    if not predictions:
        return []
    
    print(f"🔍 Applying NMS with IoU threshold: {iou_threshold}, padding: {padding_factor}, max predictions: {max_predictions}")
    
    # Sort predictions by class priority (higher class numbers first), then by confidence
    def sort_key(pred):
        class_name = pred.get('displayName', 'Unknown')
        # Extract class number from class name (e.g., "class1" -> 1, "class2" -> 2)
        try:
            if class_name.lower().startswith('class'):
                class_num = int(class_name.lower().replace('class', ''))
            else:
                # For non-class names, use a default priority
                class_num = 0
        except:
            class_num = 0
        
        confidence = pred.get('confidence', 0.0)
        # Sort by class number (descending), then by confidence (descending)
        return (-class_num, -confidence)
    
    sorted_predictions = sorted(predictions, key=sort_key)
    
    # Apply NMS across all classes (higher class numbers can override lower ones)
    filtered_predictions = []
    for i, pred in enumerate(sorted_predictions):
        should_keep = True
        bbox1 = pred.get('bbox', [0, 0, 0, 0])
        class_name1 = pred.get('displayName', 'Unknown')
        
        # Check against already selected predictions
        for selected_pred in filtered_predictions:
            bbox2 = selected_pred.get('bbox', [0, 0, 0, 0])
            class_name2 = selected_pred.get('displayName', 'Unknown')
            
            # Apply padding to both boxes for IoU calculation
            padded_bbox1 = apply_padding_to_bbox(bbox1, padding_factor)
            padded_bbox2 = apply_padding_to_bbox(bbox2, padding_factor)
            
            # Calculate IoU using padded boxes
            iou = calculate_iou(padded_bbox1, padded_bbox2)
            
            if iou > iou_threshold:
                # If boxes overlap, check class priority
                class_num1 = get_class_number(class_name1)
                class_num2 = get_class_number(class_name2)
                
                if class_num1 > class_num2:
                    # Current prediction has higher class priority, remove the selected one
                    filtered_predictions.remove(selected_pred)
                    print(f"  🔄 Replaced {class_name2} with higher priority {class_name1}")
                    break
                else:
                    # Selected prediction has higher or equal class priority, skip current
                    should_keep = False
                    break
        
        if should_keep:
            filtered_predictions.append(pred)
    
    print(f"  📊 Processed {len(sorted_predictions)} predictions, kept {len(filtered_predictions)}")
    
    # Limit to max_predictions
    if len(filtered_predictions) > max_predictions:
        filtered_predictions = filtered_predictions[:max_predictions]
    
    print(f"🎯 NMS complete: {len(filtered_predictions)} final predictions")
    return filtered_predictions

def create_annotated_image(image_bytes, predictions, padding_factor=0.0):
    """
    Create an annotated image with bounding boxes and labels.
    Properly handles Vertex AI normalized coordinates [xMin, xMax, yMin, yMax].
    Applies padding factor to expand bounding boxes before drawing.
    """
    try:
        print(f"🎨 Creating annotated image with {len(predictions)} predictions")
        
        # Open image and convert to RGB to ensure compatibility
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        draw = ImageDraw.Draw(image)
        img_width, img_height = image.size
        
        print(f"📐 Image dimensions: {img_width}x{img_height}")
        
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
        
        # Define consistent colors for different classes
        def get_class_color(class_name):
            # Density model colors: 1=blue, 2=white
            if class_name == '1':
                return 'blue'
            elif class_name == '2':
                return 'white'
            # Thickness model colors: weak=red, medium=yellow, strong=green
            elif class_name == 'weak':
                return 'red'
            elif class_name == 'medium':
                return 'yellow'
            elif class_name == 'strong':
                return 'green'
            else:
                return 'blue'  # default
        
        # Draw bounding boxes and labels
        for i, pred in enumerate(predictions):
            bbox = pred.get('bbox', [0, 0, 0, 0])
            class_name = pred.get('displayName', 'Unknown')
            confidence = pred.get('confidence', 0.0)
            
            print(f"🎯 Drawing box {i+1}: {class_name} ({confidence:.2f}) at {bbox}")
            
            # Apply padding factor to the bounding box before drawing
            padded_bbox = apply_padding_to_bbox(bbox, padding_factor)
            
            # Vertex AI returns normalized coordinates as [xMin, xMax, yMin, yMax]
            # Convert to absolute pixel coordinates
            x_min = padded_bbox[0] * img_width
            x_max = padded_bbox[1] * img_width
            y_min = padded_bbox[2] * img_height
            y_max = padded_bbox[3] * img_height
            
            # Ensure coordinates are within image bounds
            x_min = max(0, min(x_min, img_width))
            x_max = max(0, min(x_max, img_width))
            y_min = max(0, min(y_min, img_height))
            y_max = max(0, min(y_max, img_height))
            
            # Skip invalid bounding boxes
            if x_max <= x_min or y_max <= y_min:
                print(f"⚠️ Skipping invalid bounding box: {bbox}")
                continue
            
            # Get consistent color for class
            color = get_class_color(class_name)
            
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
            
            # Draw label text with appropriate color
            text_color = "black" if color in ['white', 'yellow'] else "white"
            draw.text(
                (x_min, y_min - 25), 
                display_text, 
                fill=text_color, 
                font=font
            )
            
            print(f"✅ Drew bounding box: {class_name} at ({x_min:.0f},{y_min:.0f})-({x_max:.0f},{y_max:.0f})")
        
        # Convert to base64 for sending to frontend
        buffer = io.BytesIO()
        image.save(buffer, format='JPEG', quality=95)
        img_str = base64.b64encode(buffer.getvalue()).decode('utf-8')
        
        print(f"✅ Annotated image created successfully")
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
        
        # Extract form data
        image_file = form.getfirst('image')
        
        # Model selection
        run_density_model = form.getfirst('runDensityModel', 'false').lower() == 'true'
        run_thickness_model = form.getfirst('runThicknessModel', 'false').lower() == 'true'
        
        print(f"🔍 Model selection from form:")
        print(f"  - runDensityModel raw: '{form.getfirst('runDensityModel', 'false')}'")
        print(f"  - runThicknessModel raw: '{form.getfirst('runThicknessModel', 'false')}'")
        print(f"  - run_density_model: {run_density_model}")
        print(f"  - run_thickness_model: {run_thickness_model}")
        
        # Density model parameters
        density_confidence = float(form.getfirst('densityConfidence', 0.2))
        density_iou_threshold = float(form.getfirst('densityNMS', 0.0))
        density_padding_factor = float(form.getfirst('densityPadding', 0.5))
        density_max_predictions = int(form.getfirst('densityMaxPred', 100))
        
        # Thickness model parameters
        thickness_confidence = float(form.getfirst('thicknessConfidence', 0.2))
        thickness_iou_threshold = float(form.getfirst('thicknessNMS', 0.0))
        thickness_padding_factor = float(form.getfirst('thicknessPadding', 0.5))
        thickness_max_predictions = int(form.getfirst('thicknessMaxPred', 100))
        
        return {
            'image': image_file,
            'run_density_model': run_density_model,
            'run_thickness_model': run_thickness_model,
            'density_confidence': density_confidence,
            'density_iou_threshold': density_iou_threshold,
            'density_padding_factor': density_padding_factor,
            'density_max_predictions': density_max_predictions,
            'thickness_confidence': thickness_confidence,
            'thickness_iou_threshold': thickness_iou_threshold,
            'thickness_padding_factor': thickness_padding_factor,
            'thickness_max_predictions': thickness_max_predictions
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
            
            # Get model selection and parameters
            run_density_model = form_data['run_density_model']
            run_thickness_model = form_data['run_thickness_model']
            
            print(f"🖼️ Processing image - Density: {run_density_model}, Thickness: {run_thickness_model}")
            
            # Convert image file to bytes
            if hasattr(form_data['image'], 'file'):
                image_bytes = form_data['image'].file.read()
            else:
                image_bytes = form_data['image']
            
            # Initialize response data
            response_data = {
                'success': True,
                'density_results': None,
                'thickness_results': None,
                'combined_annotated_image': None
            }
            
            # Store predictions for combined image
            density_predictions = None
            thickness_predictions = None
            
            # Process density model if selected
            if run_density_model:
                print("🔍 Running density model...")
                density_predictions = predict_image_object_detection(
                    image_bytes, 
                    form_data['density_confidence'], 
                    form_data['density_iou_threshold'],
                    form_data['density_padding_factor'],
                    form_data['density_max_predictions']
                )
                
                if density_predictions:
                    density_annotated_image = create_annotated_image(image_bytes, density_predictions, form_data['density_padding_factor'])
                    density_metrics = calculate_follicular_metrics(density_predictions)
                    
                    response_data['density_results'] = {
                        'annotated_image': density_annotated_image,
                        'predictions': density_predictions,
                        'follicular_metrics': density_metrics,
                        'total_predictions': len(density_predictions)
                    }
            
            # Process thickness model if selected
            if run_thickness_model:
                print("🔍 Running thickness model...")
                thickness_predictions = predict_thickness_model_rest(
                    image_bytes, 
                    form_data['thickness_confidence'], 
                    form_data['thickness_iou_threshold'],
                    form_data['thickness_padding_factor'],
                    form_data['thickness_max_predictions']
                )
                
                if thickness_predictions:
                    thickness_annotated_image = create_annotated_image(image_bytes, thickness_predictions, form_data['thickness_padding_factor'])
                    
                    # Calculate thickness metrics
                    thickness_metrics = {
                        'strong': sum(1 for p in thickness_predictions if p['displayName'] == 'strong'),
                        'medium': sum(1 for p in thickness_predictions if p['displayName'] == 'medium'),
                        'weak': sum(1 for p in thickness_predictions if p['displayName'] == 'weak'),
                        'total_detections': len(thickness_predictions)
                    }
                    
                    response_data['thickness_results'] = {
                        'annotated_image': thickness_annotated_image,
                        'predictions': thickness_predictions,
                        'thickness_metrics': thickness_metrics,
                        'total_predictions': len(thickness_predictions)
                    }
            
            # Create combined annotated image if both models were run
            if density_predictions and thickness_predictions:
                print("🎨 Creating combined image with both overlays...")
                combined_image = create_combined_annotated_image(
                    image_bytes, 
                    density_predictions, 
                    thickness_predictions, 
                    form_data['density_padding_factor'],
                    form_data['thickness_padding_factor']
                )
                if combined_image:
                    response_data['combined_annotated_image'] = combined_image
            
            # Calculate combined metrics if we have any predictions
            if density_predictions or thickness_predictions:
                print("📊 Calculating combined metrics...")
                combined_metrics = calculate_combined_metrics(density_predictions, thickness_predictions)
                response_data['combined_metrics'] = combined_metrics
            
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