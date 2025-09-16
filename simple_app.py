import os
from flask import Flask, render_template, request, jsonify
import tempfile
import datetime

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/camera')
def camera():
    return render_template('camera.html')

@app.route('/debug')
def debug():
    return render_template('debug.html')

@app.route('/snapshot', methods=['POST'])
def save_snapshot():
    """Save a snapshot from the camera"""
    try:
        if 'image' not in request.files:
            return jsonify({'error': 'No image file provided'}), 400
        
        file = request.files['image']
        if file.filename == '':
            return jsonify({'error': 'No image file selected'}), 400
        
        # Create snapshots directory if it doesn't exist
        snapshots_dir = os.path.join(os.getcwd(), 'static', 'snapshots')
        os.makedirs(snapshots_dir, exist_ok=True)
        
        # Generate unique filename with timestamp
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'trichoscope_snapshot_{timestamp}.jpg'
        filepath = os.path.join(snapshots_dir, filename)
        
        # Save the file
        file.save(filepath)
        
        # Return success response with file info
        return jsonify({
            'success': True,
            'filename': filename,
            'filepath': f'/static/snapshots/{filename}',
            'message': 'Snapshot saved successfully'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=3000)