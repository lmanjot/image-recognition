#!/usr/bin/env python3
"""
Database initialization script for HairScan application.
This script creates the necessary database schema and tables.
"""

import os
import sys
from database import initialize_database, get_database_manager

def main():
    """Initialize the database schema"""
    print("🚀 Initializing HairScan database...")
    
    # Check if database credentials are available
    db_manager = get_database_manager()
    
    if not db_manager.user or not db_manager.password:
        print("❌ Database credentials not found!")
        print("Please set the following environment variables:")
        print("  - pg_user: PostgreSQL username")
        print("  - pg_pw: PostgreSQL password")
        sys.exit(1)
    
    print(f"📊 Connecting to database:")
    print(f"  - Host: {db_manager.host}")
    print(f"  - Database: {db_manager.database}")
    print(f"  - Schema: {db_manager.schema}")
    print(f"  - User: {db_manager.user}")
    
    # Test database connection
    connection = db_manager.get_connection()
    if not connection:
        print("❌ Failed to connect to database!")
        sys.exit(1)
    
    print("✅ Database connection successful!")
    
    # Initialize database tables
    success = initialize_database()
    
    if success:
        print("✅ Database initialization completed successfully!")
        print("\n📋 Created tables:")
        print("  - users: Stores user information")
        print("  - picture_uploads: Stores picture upload records and analysis results")
        print("\n🔍 Created indexes:")
        print("  - idx_picture_uploads_user_id: For user-based queries")
        print("  - idx_picture_uploads_timestamp: For time-based queries")
        print("  - idx_picture_uploads_status: For status-based queries")
    else:
        print("❌ Database initialization failed!")
        sys.exit(1)
    
    # Close database connection
    db_manager.close_connection()
    print("🔒 Database connection closed.")

if __name__ == "__main__":
    main()