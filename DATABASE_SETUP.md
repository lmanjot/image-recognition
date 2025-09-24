# HairScan Database Integration

This document describes the PostgreSQL database integration for the HairScan application, which stores information about picture uploads, user data, and analysis results.

## Database Configuration

### Connection Details
- **Host**: `mara.postgres.database.azure.com`
- **Database**: `postgres`
- **Schema**: `hairscan`
- **Port**: `5432`
- **SSL**: Required

### Environment Variables
Set the following environment variables:
```bash
export pg_user="your_postgres_username"
export pg_pw="your_postgres_password"
```

## Database Schema

### Users Table
Stores user information:
```sql
CREATE TABLE hairscan.users (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255),
    name VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Picture Uploads Table
Stores picture upload records and analysis results:
```sql
CREATE TABLE hairscan.picture_uploads (
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
    FOREIGN KEY (user_id) REFERENCES hairscan.users(user_id) ON DELETE CASCADE
);
```

### Indexes
For optimal performance:
- `idx_picture_uploads_user_id`: User-based queries
- `idx_picture_uploads_timestamp`: Time-based queries
- `idx_picture_uploads_status`: Status-based queries

## API Endpoints

### Upload Picture with Database Storage
**POST** `/api/upload`

**Form Data:**
- `image`: Image file
- `userId`: User identifier (optional, generates UUID if not provided)
- `userEmail`: User email (optional)
- `userName`: User name (optional)
- `runDensityModel`: Boolean (true/false)
- `runThicknessModel`: Boolean (true/false)
- Model parameters (confidence, NMS, padding, max predictions)

**Response:**
```json
{
  "success": true,
  "upload_id": 123,
  "density_results": { ... },
  "thickness_results": { ... },
  "combined_metrics": { ... }
}
```

### Retrieve User Uploads
**GET** `/api/user_uploads?user_id={user_id}&limit={limit}&offset={offset}`

**Query Parameters:**
- `user_id`: Required user identifier
- `limit`: Optional, default 50, max 100
- `offset`: Optional, default 0

**Response:**
```json
{
  "success": true,
  "user_id": "user_123",
  "uploads": [
    {
      "id": 123,
      "filename": "image.jpg",
      "file_size": 1024000,
      "file_type": "image/jpeg",
      "gcs_url": "gs://hairscan-images/user_123/20240101_120000_image.jpg",
      "upload_timestamp": "2024-01-01T12:00:00",
      "analysis_results": { ... },
      "processing_status": "completed",
      "created_at": "2024-01-01T12:00:00",
      "updated_at": "2024-01-01T12:05:00"
    }
  ],
  "total_count": 1,
  "limit": 50,
  "offset": 0
}
```

## Database Operations

### Initialization
```bash
python api/init_db.py
```

### Testing
```bash
python api/test_db.py
```

## Data Flow

1. **User Upload**: User uploads image with optional user information
2. **User Record**: User information is stored/updated in `users` table
3. **Upload Record**: Initial upload record created in `picture_uploads` table with status 'processing'
4. **GCS Upload**: Image uploaded to Google Cloud Storage (mock implementation)
5. **Analysis**: AI models process the image
6. **Results Storage**: Analysis results stored in `analysis_results` JSONB field
7. **Status Update**: Record updated with status 'completed' or 'error'

## Error Handling

- Database connection failures are logged and handled gracefully
- Failed uploads are marked with status 'error' and error message
- Analysis continues even if database operations fail
- Comprehensive logging for debugging

## Performance Considerations

- Connection pooling for better performance
- Indexes on frequently queried columns
- JSONB for flexible analysis results storage
- Pagination for large result sets
- Lightweight storage (excludes large image data from database)

## Security

- SSL required for database connections
- Environment variables for credentials
- Input validation and sanitization
- CORS headers for API endpoints

## Future Enhancements

- Actual Google Cloud Storage integration
- Database connection pooling
- Caching layer for frequently accessed data
- Backup and recovery procedures
- Monitoring and alerting