import os
import json
import time
import psycopg2
from psycopg2.extras import RealDictCursor

# PostgreSQL connection configuration (matching test-postgres.js)
def get_database_connection():
    """Get PostgreSQL database connection using same config as test-postgres.js"""
    try:
        pg_user = os.getenv('pg_user')
        pg_pw = os.getenv('pg_pw')
        
        if not pg_user or not pg_pw:
            print(f"❌ PostgreSQL credentials not configured:")
            print(f"  - pg_user: {'SET' if pg_user else 'NOT SET'}")
            print(f"  - pg_pw: {'SET' if pg_pw else 'NOT SET'}")
            return None
        
        print(f"🔍 Connecting to PostgreSQL with user: {pg_user}")
        
        conn = psycopg2.connect(
            host="mara.postgres.database.azure.com",
            database="postgres",
            user=pg_user,
            password=pg_pw,
            port=5432,
            sslmode='require'
        )
        print("✅ Database connection successful")
        return conn
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return None

def store_analysis_results(user_id, analysis_data):
    """Store analysis results in PostgreSQL using existing hairscan.picture_uploads table structure"""
    try:
        conn = get_database_connection()
        if not conn:
            print("❌ No database connection available")
            return None
            
        cursor = conn.cursor()
        
        # Generate unique upload_id and contact_id
        timestamp = int(time.time() * 1000)  # milliseconds
        upload_id = f"upload-{timestamp}"
        contact_id = user_id or f"contact-{timestamp}"
        
        # Prepare analysis results JSON (matching the structure from test-postgres.js)
        analysis_results_json = json.dumps({
            "density_results": analysis_data.get('density_results', {}),
            "thickness_results": analysis_data.get('thickness_results', {}),
            "combined_metrics": analysis_data.get('combined_metrics', {}),
            "model_parameters": analysis_data.get('model_parameters', {}),
            "image_metadata": analysis_data.get('image_metadata', {}),
            "processing_timestamp": time.time(),
            "upload_id": upload_id
        })
        
        # Insert into existing hairscan.picture_uploads table (matching test-postgres.js structure)
        insert_sql = """
        INSERT INTO hairscan.picture_uploads (
            upload_id, contact_id, filename, file_size, file_type, 
            url, density_model_run, thickness_model_run, processing_status, analysis_results
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING upload_id;
        """
        
        cursor.execute(insert_sql, (
            upload_id,
            contact_id,
            analysis_data.get('filename', 'camera-capture.jpg'),
            analysis_data.get('file_size', 0),
            analysis_data.get('file_type', 'image/jpeg'),
            analysis_data.get('url', ''),
            analysis_data.get('density_model_run', True),
            analysis_data.get('thickness_model_run', True),
            'completed',
            analysis_results_json
        ))
        
        result_upload_id = cursor.fetchone()[0]
        conn.commit()
        
        print(f"✅ Analysis results stored in database with upload_id: {result_upload_id}")
        
        cursor.close()
        conn.close()
        
        return result_upload_id
        
    except Exception as e:
        print(f"❌ Error storing analysis results: {e}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return None

# Test function to verify the integration works
def test_store_analysis():
    """Test function to verify the store_analysis_results function works"""
    try:
        test_data = {
            'filename': 'test-image.jpg',
            'file_size': 1024,
            'file_type': 'image/jpeg',
            'url': 'https://example.com/test-image.jpg',
            'density_model_run': True,
            'thickness_model_run': True,
            'density_results': {
                'follicular_metrics': {
                    'total_follicular_units': 25,
                    'follicular_density_per_cm2': 91.58,
                    'total_hairs': 35
                }
            },
            'thickness_results': {
                'thickness_metrics': {
                    'strong': 15,
                    'medium': 12,
                    'weak': 8,
                    'total_detections': 35
                }
            },
            'combined_metrics': {
                'overall_hair_score': 75.5,
                'hair_caliber_index': 89,
                'effective_hair_density': 128.2
            },
            'model_parameters': {
                'density_confidence': 0.20,
                'thickness_confidence': 0.10
            },
            'image_metadata': {
                'image_size_bytes': 1024,
                'processing_time': time.time()
            }
        }
        
        upload_id = store_analysis_results('test-user-123', test_data)
        if upload_id:
            print(f"✅ Test successful! Upload ID: {upload_id}")
            return True
        else:
            print("❌ Test failed!")
            return False
            
    except Exception as e:
        print(f"❌ Test error: {e}")
        return False

if __name__ == "__main__":
    # Run test when executed directly
    test_store_analysis()