#!/bin/bash

# Vercel Deployment Script for Vertex AI Image Recognition Tester
# This script automates the deployment process to Vercel

set -e

echo "🚀 Starting Vercel deployment for Vertex AI Image Recognition Tester..."
echo ""

# Check if Vercel CLI is installed
if ! command -v vercel &> /dev/null; then
    echo "❌ Vercel CLI is not installed. Installing now..."
    npm install -g vercel
fi

# Check if user is logged in to Vercel
if ! vercel whoami &> /dev/null; then
    echo "🔐 Please log in to Vercel..."
    vercel login
fi

echo "📋 Checking project configuration..."

# Check if vercel.json exists
if [ ! -f "vercel.json" ]; then
    echo "❌ vercel.json not found. Please ensure you're in the correct directory."
    exit 1
fi

# Check if api/upload.py exists
if [ ! -f "api/upload.py" ]; then
    echo "❌ api/upload.py not found. Please ensure the API directory structure is correct."
    exit 1
fi

echo "✅ Project structure looks good!"
echo ""

# Deploy to Vercel
echo "🚀 Deploying to Vercel..."
vercel --yes

echo ""
echo "🎉 Initial deployment complete!"
echo ""

# Prompt for environment variables
echo "🔧 Now let's configure your environment variables..."
echo ""

read -p "Enter your Google Cloud Project ID: " GOOGLE_CLOUD_PROJECT
read -p "Enter your Vertex AI Endpoint ID: " VERTEX_ENDPOINT_ID
read -p "Enter your Vertex AI Location (e.g., europe-west4): " VERTEX_LOCATION

echo ""
echo "📝 Setting environment variables..."

# Set environment variables
vercel env add GOOGLE_CLOUD_PROJECT production <<< "$GOOGLE_CLOUD_PROJECT"
vercel env add VERTEX_ENDPOINT_ID production <<< "$VERTEX_ENDPOINT_ID"
vercel env add VERTEX_LOCATION production <<< "$VERTEX_LOCATION"

echo ""
echo "🔐 Setting up Google Cloud authentication..."
echo ""

echo "Choose your authentication method:"
echo "1. Service Account Key (Recommended for production)"
echo "2. Application Default Credentials (Good for development)"
echo "3. Skip for now (use mock data)"

read -p "Enter your choice (1-3): " AUTH_CHOICE

case $AUTH_CHOICE in
    1)
        echo ""
        echo "🔑 Service Account Key Setup:"
        echo "1. Go to Google Cloud Console → IAM & Admin → Service Accounts"
        echo "2. Create a new service account or select existing one"
        echo "3. Create a new key (JSON format)"
        echo "4. Download the key file"
        echo ""
        read -p "Enter the path to your service account key file: " KEY_PATH
        
        if [ -f "$KEY_PATH" ]; then
            # Read the key file content and set it as environment variable
            KEY_CONTENT=$(cat "$KEY_PATH")
            vercel env add GOOGLE_APPLICATION_CREDENTIALS production <<< "$KEY_CONTENT"
            echo "✅ Service account key configured!"
        else
            echo "❌ Key file not found. Please check the path and try again."
        fi
        ;;
    2)
        echo ""
        echo "🔐 Application Default Credentials Setup:"
        echo "Run 'gcloud auth application-default login' in your terminal"
        echo "Then set the credentials path:"
        read -p "Enter the path to your credentials (usually ~/.config/gcloud/application_default_credentials.json): " CREDS_PATH
        
        if [ -f "$CREDS_PATH" ]; then
            CREDS_CONTENT=$(cat "$CREDS_PATH")
            vercel env add GOOGLE_APPLICATION_DEFAULT_CREDENTIALS production <<< "$CREDS_CONTENT"
            echo "✅ Application default credentials configured!"
        else
            echo "❌ Credentials file not found. Please check the path and try again."
        fi
        ;;
    3)
        echo "⏭️  Skipping authentication setup. The app will use mock data."
        ;;
    *)
        echo "❌ Invalid choice. Skipping authentication setup."
        ;;
esac

echo ""
echo "🔄 Redeploying with environment variables..."

# Redeploy to production with environment variables
vercel --prod --yes

echo ""
echo "🎉 Deployment complete!"
echo ""

# Get the deployment URL
DEPLOYMENT_URL=$(vercel ls | grep "vertex-ai-image-tester" | head -1 | awk '{print $2}')

if [ ! -z "$DEPLOYMENT_URL" ]; then
    echo "🌐 Your app is now live at: $DEPLOYMENT_URL"
else
    echo "🌐 Your app has been deployed! Check your Vercel dashboard for the URL."
fi

echo ""
echo "📚 Next steps:"
echo "1. Visit your deployed app"
echo "2. Upload an image to test"
echo "3. Adjust parameters as needed"
echo "4. Click 'Run Detection' to test your Vertex AI endpoint"
echo ""
echo "🔧 To make changes:"
echo "- Edit your code locally"
echo "- Run 'vercel --prod' to redeploy"
echo ""
echo "📖 For more information, see VERCEL_DEPLOYMENT.md"
echo ""
echo "🚀 Happy detecting!"