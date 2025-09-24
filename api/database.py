import os
import psycopg2
import psycopg2.extras
from datetime import datetime
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseManager:
    """Manages PostgreSQL database connections and operations"""
    
    def __init__(self):
        self.host = "mara.postgres.database.azure.com"
        self.database = "postgres"
        self.schema = "hairscan"
        self.user = os.getenv('pg_user')
        self.password = os.getenv('pg_pw')
        
        if not self.user or not self.password:
            logger.warning("PostgreSQL credentials not found in environment variables")
            self.connection = None
        else:
            self.connection = None
    
    def get_connection(self):
        """Get database connection with error handling"""
        if not self.user or not self.password:
            logger.error("PostgreSQL credentials not configured")
            return None
            
        try:
            if self.connection is None or self.connection.closed:
                self.connection = psycopg2.connect(
                    host=self.host,
                    database=self.database,
                    user=self.user,
                    password=self.password,
                    port=5432,
                    sslmode='require'
                )
                logger.info("Successfully connected to PostgreSQL database")
            return self.connection
        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL database: {e}")
            return None
    
    def create_tables(self):
        """Create necessary tables if they don't exist"""
        connection = self.get_connection()
        if not connection:
            return False
            
        try:
            cursor = connection.cursor()
            
            # Create schema if it doesn't exist
            cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {self.schema}")
            
            # Create users table
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS {self.schema}.users (
                    id SERIAL PRIMARY KEY,
                    user_id VARCHAR(255) UNIQUE NOT NULL,
                    email VARCHAR(255),
                    name VARCHAR(255),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create picture_uploads table
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS {self.schema}.picture_uploads (
                    id SERIAL PRIMARY KEY,
                    user_id VARCHAR(255) NOT NULL,
                    filename VARCHAR(255),
                    file_size INTEGER,
                    file_type VARCHAR(100),
                    gcs_url TEXT,
                    upload_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    analysis_results JSONB,
                    density_model_run BOOLEAN DEFAULT FALSE,
                    thickness_model_run BOOLEAN DEFAULT FALSE,
                    processing_status VARCHAR(50) DEFAULT 'pending',
                    error_message TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES {self.schema}.users(user_id) ON DELETE CASCADE
                )
            """)
            
            # Create indexes for better performance
            cursor.execute(f"""
                CREATE INDEX IF NOT EXISTS idx_picture_uploads_user_id 
                ON {self.schema}.picture_uploads(user_id)
            """)
            
            cursor.execute(f"""
                CREATE INDEX IF NOT EXISTS idx_picture_uploads_timestamp 
                ON {self.schema}.picture_uploads(upload_timestamp)
            """)
            
            cursor.execute(f"""
                CREATE INDEX IF NOT EXISTS idx_picture_uploads_status 
                ON {self.schema}.picture_uploads(processing_status)
            """)
            
            connection.commit()
            logger.info("Database tables created successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error creating database tables: {e}")
            connection.rollback()
            return False
        finally:
            if cursor:
                cursor.close()
    
    def insert_user(self, user_id, email=None, name=None):
        """Insert or update user information"""
        connection = self.get_connection()
        if not connection:
            return False
            
        try:
            cursor = connection.cursor()
            
            # Use UPSERT (INSERT ... ON CONFLICT) to handle existing users
            cursor.execute(f"""
                INSERT INTO {self.schema}.users (user_id, email, name, updated_at)
                VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (user_id) 
                DO UPDATE SET 
                    email = EXCLUDED.email,
                    name = EXCLUDED.name,
                    updated_at = CURRENT_TIMESTAMP
            """, (user_id, email, name))
            
            connection.commit()
            logger.info(f"User {user_id} inserted/updated successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error inserting user: {e}")
            connection.rollback()
            return False
        finally:
            if cursor:
                cursor.close()
    
    def insert_picture_upload(self, user_id, filename, file_size, file_type, gcs_url=None, 
                            analysis_results=None, density_model_run=False, 
                            thickness_model_run=False, processing_status='pending', 
                            error_message=None):
        """Insert picture upload record"""
        connection = self.get_connection()
        if not connection:
            return None
            
        try:
            cursor = connection.cursor()
            
            # Convert analysis_results to JSON string if it's a dict
            if isinstance(analysis_results, dict):
                analysis_results_json = json.dumps(analysis_results)
            else:
                analysis_results_json = analysis_results
            
            cursor.execute(f"""
                INSERT INTO {self.schema}.picture_uploads 
                (user_id, filename, file_size, file_type, gcs_url, analysis_results,
                 density_model_run, thickness_model_run, processing_status, error_message)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (user_id, filename, file_size, file_type, gcs_url, analysis_results_json,
                  density_model_run, thickness_model_run, processing_status, error_message))
            
            upload_id = cursor.fetchone()[0]
            connection.commit()
            
            logger.info(f"Picture upload record inserted with ID: {upload_id}")
            return upload_id
            
        except Exception as e:
            logger.error(f"Error inserting picture upload: {e}")
            connection.rollback()
            return None
        finally:
            if cursor:
                cursor.close()
    
    def update_picture_upload(self, upload_id, analysis_results=None, processing_status=None, 
                             error_message=None, gcs_url=None):
        """Update picture upload record with analysis results"""
        connection = self.get_connection()
        if not connection:
            return False
            
        try:
            cursor = connection.cursor()
            
            # Build dynamic update query
            update_fields = []
            update_values = []
            
            if analysis_results is not None:
                if isinstance(analysis_results, dict):
                    analysis_results_json = json.dumps(analysis_results)
                else:
                    analysis_results_json = analysis_results
                update_fields.append("analysis_results = %s")
                update_values.append(analysis_results_json)
            
            if processing_status is not None:
                update_fields.append("processing_status = %s")
                update_values.append(processing_status)
            
            if error_message is not None:
                update_fields.append("error_message = %s")
                update_values.append(error_message)
            
            if gcs_url is not None:
                update_fields.append("gcs_url = %s")
                update_values.append(gcs_url)
            
            if not update_fields:
                logger.warning("No fields to update")
                return False
            
            # Always update the updated_at timestamp
            update_fields.append("updated_at = CURRENT_TIMESTAMP")
            update_values.append(upload_id)
            
            query = f"""
                UPDATE {self.schema}.picture_uploads 
                SET {', '.join(update_fields)}
                WHERE id = %s
            """
            
            cursor.execute(query, update_values)
            connection.commit()
            
            logger.info(f"Picture upload record {upload_id} updated successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error updating picture upload: {e}")
            connection.rollback()
            return False
        finally:
            if cursor:
                cursor.close()
    
    def get_user_uploads(self, user_id, limit=50, offset=0):
        """Get picture uploads for a specific user"""
        connection = self.get_connection()
        if not connection:
            return []
            
        try:
            cursor = connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            
            cursor.execute(f"""
                SELECT id, filename, file_size, file_type, gcs_url, upload_timestamp,
                       analysis_results, density_model_run, thickness_model_run,
                       processing_status, error_message, created_at, updated_at
                FROM {self.schema}.picture_uploads
                WHERE user_id = %s
                ORDER BY upload_timestamp DESC
                LIMIT %s OFFSET %s
            """, (user_id, limit, offset))
            
            results = cursor.fetchall()
            
            # Convert RealDictRow to regular dict and parse JSON fields
            uploads = []
            for row in results:
                upload = dict(row)
                if upload['analysis_results']:
                    try:
                        upload['analysis_results'] = json.loads(upload['analysis_results'])
                    except json.JSONDecodeError:
                        pass  # Keep as string if not valid JSON
                uploads.append(upload)
            
            logger.info(f"Retrieved {len(uploads)} uploads for user {user_id}")
            return uploads
            
        except Exception as e:
            logger.error(f"Error retrieving user uploads: {e}")
            return []
        finally:
            if cursor:
                cursor.close()
    
    def get_upload_by_id(self, upload_id):
        """Get a specific picture upload by ID"""
        connection = self.get_connection()
        if not connection:
            return None
            
        try:
            cursor = connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            
            cursor.execute(f"""
                SELECT id, user_id, filename, file_size, file_type, gcs_url, upload_timestamp,
                       analysis_results, density_model_run, thickness_model_run,
                       processing_status, error_message, created_at, updated_at
                FROM {self.schema}.picture_uploads
                WHERE id = %s
            """, (upload_id,))
            
            result = cursor.fetchone()
            if result:
                upload = dict(result)
                if upload['analysis_results']:
                    try:
                        upload['analysis_results'] = json.loads(upload['analysis_results'])
                    except json.JSONDecodeError:
                        pass  # Keep as string if not valid JSON
                return upload
            
            return None
            
        except Exception as e:
            logger.error(f"Error retrieving upload by ID: {e}")
            return None
        finally:
            if cursor:
                cursor.close()
    
    def close_connection(self):
        """Close database connection"""
        if self.connection and not self.connection.closed:
            self.connection.close()
            logger.info("Database connection closed")

# Global database manager instance
db_manager = DatabaseManager()

def initialize_database():
    """Initialize database tables"""
    return db_manager.create_tables()

def get_database_manager():
    """Get the global database manager instance"""
    return db_manager