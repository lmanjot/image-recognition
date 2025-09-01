#!/bin/bash

# Vercel Deployment Script for Image Recognition API
# Optimized for minimal bundle size and fast deployment

set -e  # Exit on any error

echo "🚀 Starting Vercel deployment..."

# Check if Vercel CLI is installed
if ! command -v vercel &> /dev/null; then
    echo "❌ Vercel CLI not found. Installing..."
    npm install -g vercel
fi

# Clean up any previous builds
echo "🧹 Cleaning up previous builds..."
rm -rf .vercel
rm -rf __pycache__
rm -rf api/__pycache__

# Create optimized requirements for deployment
echo "📦 Creating optimized requirements..."
cat > requirements.txt << EOF
# Lightweight requirements for Vercel deployment
Pillow>=9.0.0
requests>=2.25.0
google-auth>=2.23.0
EOF

# Create optimized API requirements
cat > api/requirements.txt << EOF
Pillow>=9.0.0
requests>=2.25.0
google-auth>=2.23.0
EOF

echo "✅ Requirements optimized for minimal bundle size"

# Check bundle size before deployment
echo "📊 Checking current bundle size..."
du -sh api/ 2>/dev/null || echo "⚠️ Could not check API directory size"
du -sh . 2>/dev/null | head -1

# Deploy to Vercel
echo "🌐 Deploying to Vercel..."
vercel --prod --yes

echo "✅ Deployment completed!"
echo ""
echo "🔗 Your app should be available at the URL shown above"
echo "💡 Use the 'Test Connection' button to verify the API is working"
echo "📱 Check the Vercel dashboard for deployment details"