const { Pool } = require('pg');

// PostgreSQL connection configuration (same as test-postgres.js)
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

// Store analysis results in PostgreSQL
async function storeAnalysisResults(userId, analysisData) {
    try {
        console.log(`🔍 storeAnalysisResults called with userId: ${userId}`);
        console.log(`🔍 analysisData keys: ${Object.keys(analysisData)}`);
        
        const client = await pool.connect();
        console.log('✅ Connected to PostgreSQL database for analysis storage');
        
        // Generate unique upload_id and contact_id
        const timestamp = Date.now();
        const uploadId = `upload-${timestamp}`;
        const contactId = userId || `contact-${timestamp}`;
        
        console.log(`🔍 Generated uploadId: ${uploadId}, contactId: ${contactId}`);
        
        // Prepare analysis results JSON (matching the structure from test-postgres.js)
        const analysisResultsJson = JSON.stringify({
            density_results: analysisData.density_results || {},
            thickness_results: analysisData.thickness_results || {},
            combined_metrics: analysisData.combined_metrics || {},
            model_parameters: analysisData.model_parameters || {},
            image_metadata: analysisData.image_metadata || {},
            processing_timestamp: Date.now(),
            upload_id: uploadId
        });
        
        console.log(`🔍 Analysis results JSON length: ${analysisResultsJson.length}`);
        
        // Insert into existing hairscan.picture_uploads table (matching test-postgres.js structure)
        const insertQuery = `
            INSERT INTO hairscan.picture_uploads (
                upload_id, contact_id, filename, file_size, file_type, 
                url, density_model_run, thickness_model_run, processing_status, analysis_results
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            RETURNING upload_id;
        `;
        
        const insertValues = [
            uploadId,
            contactId,
            analysisData.filename || `camera-capture-${timestamp}.jpg`,
            analysisData.file_size || 0,
            analysisData.file_type || 'image/jpeg',
            analysisData.url || '',
            analysisData.density_model_run || true,
            analysisData.thickness_model_run || true,
            'completed',
            analysisResultsJson
        ];
        
        console.log(`🔍 Executing insert query with ${insertValues.length} parameters`);
        
        const insertResult = await client.query(insertQuery, insertValues);
        
        const resultUploadId = insertResult.rows[0].upload_id;
        
        client.release();
        
        console.log(`✅ Analysis results stored in database with upload_id: ${resultUploadId}`);
        return resultUploadId;
        
    } catch (error) {
        console.error('❌ Error storing analysis results:', error);
        console.error('❌ Error details:', error.message);
        console.error('❌ Error stack:', error.stack);
        throw error;
    }
}

// Main handler function
module.exports = async (req, res) => {
    console.log(`🔍 Store Analysis API called: ${req.method} ${req.url}`);
    console.log(`🔍 Headers: ${JSON.stringify(req.headers, null, 2)}`);
    
    // Set CORS headers
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');
    
    if (req.method === 'OPTIONS') {
        console.log('🔍 Handling OPTIONS request');
        res.status(200).end();
        return;
    }
    
    try {
        console.log('💾 Starting analysis results storage...');
        
        // Parse request body
        let body = '';
        req.on('data', chunk => {
            body += chunk.toString();
        });
        
        req.on('end', async () => {
            try {
                console.log(`🔍 Request body: ${body}`);
                
                const data = JSON.parse(body);
                console.log(`🔍 Parsed data: ${JSON.stringify(data, null, 2)}`);
                
                const { user_id, analysis_data } = data;
                
                if (!user_id || !analysis_data) {
                    console.log(`❌ Missing required fields: user_id=${!!user_id}, analysis_data=${!!analysis_data}`);
                    res.status(400).json({
                        status: 'error',
                        message: 'Missing user_id or analysis_data'
                    });
                    return;
                }
                
                console.log(`🔍 Storing analysis for user_id: ${user_id}`);
                
                // Store analysis results
                const uploadId = await storeAnalysisResults(user_id, analysis_data);
                
                const response = {
                    status: 'success',
                    upload_id: uploadId,
                    message: 'Analysis results stored successfully',
                    timestamp: new Date().toISOString()
                };
                
                console.log(`✅ Analysis storage completed with upload_id: ${uploadId}`);
                console.log(`🔍 Response: ${JSON.stringify(response, null, 2)}`);
                res.status(200).json(response);
                
            } catch (parseError) {
                console.error('❌ Error parsing request:', parseError);
                res.status(400).json({
                    status: 'error',
                    message: 'Invalid JSON in request body',
                    error: parseError.message
                });
            }
        });
        
    } catch (error) {
        console.error('❌ Storage failed:', error);
        res.status(500).json({
            status: 'error',
            message: 'Storage execution failed',
            error: error.message
        });
    }
};