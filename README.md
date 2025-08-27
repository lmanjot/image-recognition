# Vertex AI Image Recognition Tester

A modern web application for testing your custom Vertex AI object detection models with real-time image processing and visualization.

## Features

- 🖼️ **Image Upload**: Drag & drop or file picker for image selection
- ⚙️ **Parameter Control**: Adjust confidence threshold, IoU threshold, and max predictions
- 🔍 **Real-time Detection**: Process images through your Vertex AI endpoint
- 📊 **Visual Results**: Display annotated images with bounding boxes and labels
- 📈 **Statistics**: Summary of detected objects by class with counts
- 🎨 **Modern UI**: Responsive design with Bootstrap and custom styling
- ⚡ **Performance**: Processing time tracking and loading indicators

## Screenshots

The application provides a clean interface with:
- Left panel: Model parameters and controls
- Right panel: Image preview and detection results
- Real-time parameter adjustment with sliders
- Beautiful visualization of detection results

## Prerequisites

- Python 3.8 or higher
- Google Cloud Project with Vertex AI enabled
- Vertex AI endpoint for object detection
- Google Cloud service account with appropriate permissions

## Installation

1. **Clone or download this repository**
   ```bash
   git clone <repository-url>
   cd vertex-ai-image-tester
   ```

2. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up Google Cloud authentication**
   
   **Option A: Service Account Key (Recommended for production)**
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Navigate to IAM & Admin > Service Accounts
   - Create a new service account or select existing one
   - Create a new key (JSON format)
   - Download the key file to a secure location

   **Option B: Application Default Credentials (Good for development)**
   ```bash
   gcloud auth application-default login
   ```

4. **Configure environment variables**
   ```bash
   cp .env.example .env
   ```
   
   Edit `.env` file with your actual values:
   ```bash
   GOOGLE_APPLICATION_CREDENTIALS=/path/to/your/service-account-key.json
   GOOGLE_CLOUD_PROJECT=your-project-id
   VERTEX_ENDPOINT_ID=your-endpoint-id
   VERTEX_LOCATION=europe-west4
   ```

## Configuration

### Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `GOOGLE_APPLICATION_CREDENTIALS` | Path to service account key file | `/path/to/key.json` |
| `GOOGLE_CLOUD_PROJECT` | Your Google Cloud Project ID | `my-project-123` |
| `VERTEX_ENDPOINT_ID` | Your Vertex AI endpoint ID | `3349211374252195840` |
| `VERTEX_LOCATION` | Your Vertex AI location | `europe-west4` |

### Vertex AI Endpoint Setup

1. **Create a Vertex AI endpoint** (if you don't have one):
   ```bash
   gcloud ai endpoints create \
     --region=europe-west4 \
     --display-name="Object Detection Model"
   ```

2. **Deploy your model** to the endpoint:
   ```bash
   gcloud ai endpoints deploy-model \
     --endpoint=ENDPOINT_ID \
     --region=europe-west4 \
     --display-name="Object Detection" \
     --model=MODEL_ID
   ```

## Usage

1. **Start the application**
   ```bash
   python app.py
   ```

2. **Open your browser** and navigate to `http://localhost:5000`

3. **Upload an image** using the file picker or drag & drop

4. **Adjust parameters**:
   - **Confidence Threshold**: Minimum confidence score for detections (0.0 - 1.0)
   - **IoU Threshold**: Intersection over Union threshold for non-maximum suppression
   - **Max Predictions**: Maximum number of predictions to return

5. **Click "Run Detection"** to process the image

6. **View results**:
   - Annotated image with bounding boxes
   - Object count summary
   - Class distribution statistics

## API Endpoints

### POST `/upload`
Process an image through the Vertex AI model.

**Request:**
- `image`: Image file (JPG, PNG, GIF)
- `confidenceThreshold`: Float (0.0 - 1.0)
- `iouThreshold`: Float (0.0 - 1.0)
- `maxPredictions`: Integer (1 - 1000)

**Response:**
```json
{
  "success": true,
  "annotated_image": "data:image/jpeg;base64,...",
  "predictions": [...],
  "class_counts": {"person": 3, "car": 1},
  "total_predictions": 4
}
```

## Authentication Methods

### 1. Service Account Key (Recommended)
- Most secure for production environments
- Set `GOOGLE_APPLICATION_CREDENTIALS` environment variable
- Service account needs these roles:
  - `roles/aiplatform.user`
  - `roles/aiplatform.developer`

### 2. Application Default Credentials
- Good for development and testing
- Run `gcloud auth application-default login`
- Uses your personal Google Cloud credentials

### 3. Workload Identity (Advanced)
- For Kubernetes and cloud-native deployments
- Automatically handles authentication in cloud environments

## Troubleshooting

### Common Issues

1. **Authentication Error**
   ```
   google.auth.exceptions.DefaultCredentialsError
   ```
   - Check your service account key file path
   - Verify the key file has correct permissions
   - Ensure the service account has proper roles

2. **Endpoint Not Found**
   ```
   google.api_core.exceptions.NotFound: 404
   ```
   - Verify your endpoint ID is correct
   - Check the endpoint is in the specified location
   - Ensure the endpoint is active and deployed

3. **Permission Denied**
   ```
   google.api_core.exceptions.PermissionDenied: 403
   ```
   - Verify your service account has `aiplatform.user` role
   - Check if the endpoint allows your service account

4. **Image Processing Error**
   - Ensure the image file is valid and not corrupted
   - Check file size (max 16MB)
   - Verify image format is supported

### Debug Mode

Enable debug mode for detailed error information:
```bash
export FLASK_DEBUG=true
python app.py
```

## Development

### Project Structure
```
vertex-ai-image-tester/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── .env.example          # Environment variables template
├── templates/
│   └── index.html        # Main HTML template
├── static/
│   ├── css/
│   │   └── style.css     # Custom styles
│   └── js/
│       └── app.js        # Frontend JavaScript
└── README.md             # This file
```

### Adding New Features

1. **Backend**: Modify `app.py` for new API endpoints
2. **Frontend**: Update HTML, CSS, and JavaScript files
3. **Styling**: Customize `static/css/style.css`
4. **Behavior**: Modify `static/js/app.js`

### Testing

The application includes fallback mock data for testing when Vertex AI is not available. This allows you to test the UI and functionality without a live endpoint.

## Security Considerations

- **Service Account Keys**: Store securely, never commit to version control
- **Environment Variables**: Use `.env` file for local development
- **File Uploads**: Limited to 16MB, image files only
- **HTTPS**: Use HTTPS in production environments

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is open source and available under the [MIT License](LICENSE).

## Support

For issues related to:
- **This application**: Check the troubleshooting section above
- **Vertex AI**: Visit [Google Cloud Support](https://cloud.google.com/support)
- **Authentication**: Refer to [Google Cloud Auth documentation](https://cloud.google.com/docs/authentication)

## Changelog

### v1.0.0
- Initial release
- Image upload and processing
- Parameter adjustment
- Real-time detection results
- Modern responsive UI
- Drag & drop support
