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

// Test creating a simple table
async function testTableCreation() {
    try {
        const client = await pool.connect();
        
        // Create a simple test table
        await client.query(`
            CREATE TABLE IF NOT EXISTS test_table (
                id SERIAL PRIMARY KEY,
                message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        `);
        
        // Insert test data
        await client.query(`
            INSERT INTO test_table (message) VALUES ('PostgreSQL connection test successful!')
        `);
        
        // Query test data
        const result = await client.query('SELECT * FROM test_table ORDER BY created_at DESC LIMIT 1');
        
        client.release();
        
        return {
            success: true,
            message: 'Table creation and data insertion successful',
            data: result.rows[0]
        };
    } catch (error) {
        console.error('❌ Table creation failed:', error);
        return {
            success: false,
            message: 'Table creation failed',
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
        
        // Test 2: Table creation and data insertion
        const tableTest = await testTableCreation();
        console.log('Table test result:', tableTest);
        
        const response = {
            status: 'completed',
            timestamp: new Date().toISOString(),
            tests: {
                connection: connectionTest,
                table_creation: tableTest
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