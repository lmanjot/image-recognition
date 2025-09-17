export default async function handler(req, res) {
  // Set CORS headers
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  if (req.method === 'OPTIONS') {
    res.status(200).end();
    return;
  }

  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  const { contactid } = req.query;

  if (!contactid) {
    return res.status(400).json({ error: 'Contact ID is required' });
  }

  try {
    const hubspotToken = process.env.hubspot_token || process.env.HUBSPOT_TOKEN;
    
    if (!hubspotToken) {
      console.error('HubSpot token environment variable is not set');
      console.error('Available environment variables:', Object.keys(process.env).filter(key => key.toLowerCase().includes('hubspot')));
      return res.status(500).json({ 
        error: 'HubSpot configuration error',
        details: 'HubSpot token environment variable is not set',
        debug: {
          hasToken: !!hubspotToken,
          availableEnvVars: Object.keys(process.env).filter(key => key.toLowerCase().includes('hubspot'))
        }
      });
    }

    // Fetch contact from HubSpot
    const response = await fetch(`https://api.hubapi.com/crm/v3/objects/contacts/${contactid}`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${hubspotToken}`,
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      if (response.status === 404) {
        return res.status(404).json({ error: 'Contact not found' });
      }
      if (response.status === 401) {
        return res.status(401).json({ error: 'HubSpot authentication failed' });
      }
      throw new Error(`HubSpot API error: ${response.status} ${response.statusText}`);
    }

    const contactData = await response.json();
    
    // Extract contact information
    const contact = {
      id: contactData.id,
      firstName: contactData.properties?.firstname || '',
      lastName: contactData.properties?.lastname || '',
      email: contactData.properties?.email || '',
      fullName: `${contactData.properties?.firstname || ''} ${contactData.properties?.lastname || ''}`.trim(),
    };

    res.status(200).json({
      success: true,
      contact: contact
    });

  } catch (error) {
    console.error('Error fetching HubSpot contact:', error);
    res.status(500).json({ 
      error: 'Failed to fetch contact information',
      details: error.message 
    });
  }
}