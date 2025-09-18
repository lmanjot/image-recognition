const { Storage } = require('@google-cloud/storage');

module.exports = async (req, res) => {
  // Enable CORS
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  if (req.method === 'OPTIONS') {
    res.status(200).end();
    return;
  }

  try {
    // Debug environment variables
    console.log('Environment variables:');
    console.log('- GOOGLE_CREDENTIALS:', process.env.GOOGLE_CREDENTIALS ? 'Present' : 'Missing');
    console.log('- GCS_BUCKET_NAME:', process.env.GCS_BUCKET_NAME || 'Not set');
    console.log('- GOOGLE_CLOUD_PROJECT_ID:', process.env.GOOGLE_CLOUD_PROJECT_ID || 'Not set');
    
    const { fileName, contentType } = req.body;

    if (!fileName || !contentType) {
      return res.status(400).json({
        error: 'fileName and contentType are required.'
      });
    }

    // Initialize Storage client with explicit credentials
    let storage;
    
    if (process.env.GOOGLE_CREDENTIALS) {
      // Parse the JSON credentials from environment variable
      const credentials = JSON.parse(process.env.GOOGLE_CREDENTIALS);
      storage = new Storage({
        projectId: process.env.GOOGLE_CLOUD_PROJECT_ID || '27458468732',
        credentials: credentials
      });
      console.log('Using GOOGLE_CREDENTIALS from environment variable');
    } else {
      // Fallback to default credentials
      storage = new Storage({
        projectId: process.env.GOOGLE_CLOUD_PROJECT_ID || '27458468732'
      });
      console.log('Using default credentials');
    }

    const bucketName = process.env.GCS_BUCKET_NAME || 'mara-hair-fu-h';
    const file = storage.bucket(bucketName).file(fileName);

    // Generate signed URL for PUT request
    const [url] = await file.getSignedUrl({
      version: 'v4',
      action: 'write',
      expires: Date.now() + 15 * 60 * 1000, // 15 minutes
      contentType: contentType,
    });

    console.log('Generated signed URL for:', fileName);
    console.log('Content-Type:', contentType);

    res.status(200).json({ 
      url: url,
      fileName: fileName,
      contentType: contentType
    });

  } catch (error) {
    console.error('Error generating signed URL:', error);
    res.status(500).json({
      error: 'Failed to generate signed URL',
      details: error.message
    });
  }
};