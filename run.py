#!/usr/bin/env python3
"""
Startup script for Vertex AI Image Recognition Tester
Loads environment variables and starts the Flask application
"""

import os
from dotenv import load_dotenv
from app import app

def main():
    # Load environment variables from .env file
    load_dotenv()
    
    # Check if required environment variables are set
    required_vars = ['GOOGLE_CLOUD_PROJECT', 'VERTEX_ENDPOINT_ID', 'VERTEX_LOCATION']
    missing_vars = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print("⚠️  Warning: The following environment variables are not set:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\nThe application will use default values or fallback to mock data.")
        print("For production use, please set all required environment variables.\n")
    
    # Check if Google Cloud credentials are configured
    if not os.getenv('GOOGLE_APPLICATION_CREDENTIALS') and not os.getenv('GOOGLE_APPLICATION_DEFAULT_CREDENTIALS'):
        print("⚠️  Warning: Google Cloud credentials not configured.")
        print("The application will use mock data for testing.")
        print("To use real Vertex AI endpoints, configure authentication.\n")
    
    print("🚀 Starting Vertex AI Image Recognition Tester...")
    print(f"📍 Project ID: {os.getenv('GOOGLE_CLOUD_PROJECT', 'Not set')}")
    print(f"🔗 Endpoint ID: {os.getenv('VERTEX_ENDPOINT_ID', 'Not set')}")
    print(f"🌍 Location: {os.getenv('VERTEX_LOCATION', 'Not set')}")
    print("\n🌐 Open your browser and navigate to: http://localhost:5000")
    print("⏹️  Press Ctrl+C to stop the application\n")
    
    # Start the Flask application
    app.run(debug=True, host='0.0.0.0', port=5000)

if __name__ == '__main__':
    main()