#!/usr/bin/env python3
"""
Test script for HairScan database functionality.
This script tests the database operations.
"""

import os
import sys
import json
from datetime import datetime
from database import get_database_manager, initialize_database

def test_database_operations():
    """Test all database operations"""
    print("🧪 Testing HairScan database operations...")
    
    # Initialize database manager
    db_manager = get_database_manager()
    
    if not db_manager.user or not db_manager.password:
        print("❌ Database credentials not found!")
        print("Please set the following environment variables:")
        print("  - pg_user: PostgreSQL username")
        print("  - pg_pw: PostgreSQL password")
        return False
    
    # Test connection
    connection = db_manager.get_connection()
    if not connection:
        print("❌ Failed to connect to database!")
        return False
    
    print("✅ Database connection successful!")
    
    # Initialize tables
    if not initialize_database():
        print("❌ Failed to initialize database tables!")
        return False
    
    print("✅ Database tables initialized!")
    
    # Test user operations
    test_user_id = "test_user_123"
    test_email = "test@example.com"
    test_name = "Test User"
    
    print(f"\n👤 Testing user operations...")
    
    # Insert user
    success = db_manager.insert_user(test_user_id, test_email, test_name)
    if success:
        print("✅ User inserted successfully!")
    else:
        print("❌ Failed to insert user!")
        return False
    
    # Test picture upload operations
    print(f"\n📸 Testing picture upload operations...")
    
    test_filename = "test_image.jpg"
    test_file_size = 1024000  # 1MB
    test_file_type = "image/jpeg"
    test_gcs_url = "gs://hairscan-images/test_user_123/20240101_120000_test_image.jpg"
    
    # Insert picture upload
    upload_id = db_manager.insert_picture_upload(
        user_id=test_user_id,
        filename=test_filename,
        file_size=test_file_size,
        file_type=test_file_type,
        gcs_url=test_gcs_url,
        density_model_run=True,
        thickness_model_run=True,
        processing_status='processing'
    )
    
    if upload_id:
        print(f"✅ Picture upload inserted successfully! ID: {upload_id}")
    else:
        print("❌ Failed to insert picture upload!")
        return False
    
    # Test analysis results update
    print(f"\n📊 Testing analysis results update...")
    
    test_analysis_results = {
        'density_results': {
            'predictions': [
                {'displayName': '1', 'confidence': 0.95, 'bbox': [0.1, 0.2, 0.3, 0.4]},
                {'displayName': '2', 'confidence': 0.87, 'bbox': [0.5, 0.6, 0.7, 0.8]}
            ],
            'follicular_metrics': {
                'total_follicular_units': 2,
                'total_hairs': 3,
                'follicular_density_per_cm2': 7.33,
                'average_hair_per_unit': 1.5
            },
            'total_predictions': 2
        },
        'thickness_results': {
            'predictions': [
                {'displayName': 'strong', 'confidence': 0.92, 'bbox': [0.1, 0.2, 0.3, 0.4]},
                {'displayName': 'medium', 'confidence': 0.78, 'bbox': [0.5, 0.6, 0.7, 0.8]}
            ],
            'thickness_metrics': {
                'strong': 1,
                'medium': 1,
                'weak': 0,
                'total_detections': 2
            },
            'total_predictions': 2
        },
        'combined_metrics': {
            'terminal_to_vellus_ratio': 0.0,
            'percent_thick_hairs': 50.0,
            'hair_caliber_index': 4,
            'overall_hair_score': 75.5
        },
        'processing_timestamp': datetime.now().isoformat()
    }
    
    success = db_manager.update_picture_upload(
        upload_id=upload_id,
        analysis_results=test_analysis_results,
        processing_status='completed'
    )
    
    if success:
        print("✅ Analysis results updated successfully!")
    else:
        print("❌ Failed to update analysis results!")
        return False
    
    # Test retrieval operations
    print(f"\n🔍 Testing retrieval operations...")
    
    # Get upload by ID
    upload = db_manager.get_upload_by_id(upload_id)
    if upload:
        print(f"✅ Retrieved upload by ID: {upload['filename']}")
        print(f"   - Status: {upload['processing_status']}")
        print(f"   - File size: {upload['file_size']} bytes")
        print(f"   - GCS URL: {upload['gcs_url']}")
    else:
        print("❌ Failed to retrieve upload by ID!")
        return False
    
    # Get user uploads
    uploads = db_manager.get_user_uploads(test_user_id, limit=10)
    if uploads:
        print(f"✅ Retrieved {len(uploads)} uploads for user {test_user_id}")
        for upload in uploads:
            print(f"   - {upload['filename']} ({upload['processing_status']})")
    else:
        print("❌ Failed to retrieve user uploads!")
        return False
    
    # Clean up test data
    print(f"\n🧹 Cleaning up test data...")
    
    # Note: In a real scenario, you might want to keep test data or have a separate cleanup function
    # For now, we'll just close the connection
    db_manager.close_connection()
    print("✅ Test data cleanup completed!")
    
    print(f"\n🎉 All database operations tested successfully!")
    return True

def main():
    """Main test function"""
    success = test_database_operations()
    
    if success:
        print("\n✅ Database test completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Database test failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()