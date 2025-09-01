# Image Recognition API - Optimized for Vercel

A lightweight, high-performance image recognition API built for Vercel serverless deployment. Features modern UI design inspired by Mara.care and optimized bundle sizes for fast deployments.

## ✨ Features

- **Fast Deployment**: Optimized for minimal bundle size (reduced from 15MB to ~2MB)
- **Modern UI**: Clean, professional design with Mara.care-inspired color scheme
- **Smart Caching**: Access token caching for improved performance
- **Error Handling**: Comprehensive error handling with connection testing
- **Responsive Design**: Optimized for desktop with mobile support
- **Real-time Processing**: Live image recognition with Vertex AI integration

## 🚀 Quick Deploy

### Option 1: One-Click Deploy
[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https://github.com/yourusername/image-recognition-api)

### Option 2: Manual Deploy
```bash
# Clone the repository
git clone <your-repo-url>
cd image-recognition-api

# Deploy to Vercel
./deploy-vercel.sh
```

## 📦 Bundle Size Optimization

The API has been optimized to reduce deployment size:

- **Before**: 4 functions × 15MB each = 60MB total
- **After**: 1 function × ~2MB = 2MB total

### Optimizations Applied:
- Removed heavy dependencies (numpy, flask, google-cloud-aiplatform)
- Conditional imports for Google Auth
- Lightweight requirements.txt
- Optimized Vercel configuration

## 🎨 Design System

### Color Palette (Mara.care inspired):
- **Primary Blue**: `#4d65ff` - Main brand color
- **Secondary Blue**: `#6b7cff` - Accent color  
- **Gold**: `#C79653` - Highlight color
- **Dark Gray**: `#333333` - Text color
- **Light Gray**: `#fafafa` - Background color

### Typography:
- **Font**: Inter (Google Fonts)
- **Weights**: 400, 500, 600, 700
- **Modern**: Clean, professional appearance

## 🔧 Configuration

### Environment Variables:
```bash
GOOGLE_CLOUD_PROJECT=your-project-id
VERTEX_ENDPOINT_ID=your-endpoint-id
VERTEX_LOCATION=europe-west4
GOOGLE_CREDENTIALS=your-service-account-key
```

### API Endpoints:
- `GET /api/upload` - Health check and connection test
- `POST /api/upload` - Image recognition processing
- `OPTIONS /api/upload` - CORS preflight

## 🧪 Testing

1. **Connection Test**: Use the "Test Connection" button to verify API health
2. **Image Upload**: Drag & drop or browse for images
3. **Real-time Processing**: Watch live recognition results
4. **Error Handling**: Comprehensive error messages and debugging

## 📱 Browser Support

- Chrome 80+
- Firefox 75+
- Safari 13+
- Edge 80+

## 🚀 Performance

- **Cold Start**: ~2-3 seconds
- **Warm Start**: ~500ms
- **Image Processing**: 1-5 seconds (depending on image size)
- **Bundle Size**: ~2MB (down from 60MB)

## 🔍 Troubleshooting

### Common Issues:

1. **Network Error**: Use "Test Connection" button to diagnose
2. **Large Bundle**: Ensure you're using the optimized requirements.txt
3. **Slow Deployment**: Check Vercel dashboard for build logs

### Debug Steps:
1. Test connection first
2. Check environment variables
3. Verify Google Cloud credentials
4. Review Vercel deployment logs

## 📚 Development

### Local Development:
```bash
# Install dependencies
pip install -r requirements.txt

# Run locally
python -m http.server 8000
```

### File Structure:
```
├── api/
│   ├── upload.py          # Main API handler
│   └── requirements.txt   # API dependencies
├── index.html             # Frontend UI
├── vercel.json            # Vercel configuration
├── requirements.txt       # Main dependencies
└── deploy-vercel.sh      # Deployment script
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

MIT License - see LICENSE file for details

## 🆘 Support

- **Issues**: GitHub Issues
- **Documentation**: This README
- **Deployment**: Vercel Dashboard
- **API**: Use "Test Connection" button

---

**Built with ❤️ for fast, reliable image recognition**
