const { Pool } = require('pg');

// PostgreSQL connection configuration
const pool = new Pool({
    host: "mara.postgres.database.azure.com",
    database: "postgres",
    user: process.env.pg_user,
    password: process.env.pg_pw,
    port: 5432,
    ssl: { rejectUnauthorized: false },
    connectionTimeoutMillis: 10000,
    idleTimeoutMillis: 30000,
    max: 5
});

// Test database connection
async function testConnection() {
    try {
        const client = await pool.connect();
        console.log('✅ Connected to PostgreSQL database');
        
        // Test basic query
        const result = await client.query('SELECT NOW() as current_time');
        console.log('✅ Query successful:', result.rows[0]);
        
        client.release();
        return {
            success: true,
            message: 'Database connection successful',
            timestamp: result.rows[0].current_time
        };
    } catch (error) {
        console.error('❌ Database connection failed:', error);
        return {
            success: false,
            message: 'Database connection failed',
            error: error.message
        };
    }
}

// Test inserting data into hairscan.picture_uploads table
async function testPictureUploadsInsert() {
    try {
        const client = await pool.connect();
        
        // First, let's check what columns exist in the table
        const columnCheck = await client.query(`
            SELECT column_name, data_type, is_nullable 
            FROM information_schema.columns 
            WHERE table_schema = 'hairscan' AND table_name = 'picture_uploads'
            ORDER BY ordinal_position
        `);
        
        console.log('📋 Table columns:', columnCheck.rows);
        
        // Insert test data into picture_uploads table
        const testData = {
            upload_id: 'test-upload-' + Date.now(),
            contact_id: 'test-contact-' + Date.now(),
            filename: 'test-image.jpg',
            file_size: 1024,
            file_type: 'image/jpeg',
            url: 'https://example.com/test-image.jpg',
            density_model_run: true,
            thickness_model_run: true,
            processing_status: 'completed',
            analysis_results: JSON.stringify({
                test: true,
                timestamp: new Date().toISOString(),
                message: 'PostgreSQL connection test successful!'
            })
        };
        
        const insertResult = await client.query(`
            INSERT INTO hairscan.picture_uploads (
                upload_id, contact_id, filename, file_size, file_type, 
                url, density_model_run, thickness_model_run, processing_status, analysis_results
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            RETURNING *
        `, [
            testData.upload_id,
            testData.contact_id,
            testData.filename,
            testData.file_size,
            testData.file_type,
            testData.url,
            testData.density_model_run,
            testData.thickness_model_run,
            testData.processing_status,
            testData.analysis_results
        ]);
        
        // Query the inserted data
        const queryResult = await client.query(`
            SELECT * FROM hairscan.picture_uploads 
            WHERE upload_id = $1
        `, [testData.upload_id]);
        
        client.release();
        
        return {
            success: true,
            message: 'Data insertion into picture_uploads successful',
            table_columns: columnCheck.rows,
            inserted_data: insertResult.rows[0],
            queried_data: queryResult.rows[0]
        };
    } catch (error) {
        console.error('❌ Picture uploads insert failed:', error);
        return {
            success: false,
            message: 'Picture uploads insert failed',
            error: error.message
        };
    }
}

// Main handler function
module.exports = async (req, res) => {
    // Set CORS headers
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');
    
    if (req.method === 'OPTIONS') {
        res.status(200).end();
        return;
    }
    
    try {
        console.log('🧪 Starting PostgreSQL connection test...');
        
        // Test 1: Basic connection
        const connectionTest = await testConnection();
        console.log('Connection test result:', connectionTest);
        
        // Test 2: Insert data into picture_uploads table
        const pictureUploadsTest = await testPictureUploadsInsert();
        console.log('Picture uploads test result:', pictureUploadsTest);
        
        const response = {
            status: 'completed',
            timestamp: new Date().toISOString(),
            tests: {
                connection: connectionTest,
                picture_uploads_insert: pictureUploadsTest
            },
            credentials_configured: !!(process.env.pg_user && process.env.pg_pw)
        };
        
        console.log('✅ All tests completed');
        res.status(200).json(response);
        
    } catch (error) {
        console.error('❌ Test failed:', error);
        res.status(500).json({
            status: 'error',
            message: 'Test execution failed',
            error: error.message
        });
    } finally {
        // Close the pool
        await pool.end();
    }
};