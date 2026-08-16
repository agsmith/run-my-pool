// pages/api/ready.js
export default function handler(req, res) {
  try {
    // Set headers to prevent caching
    res.setHeader('Cache-Control', 'no-cache, no-store, must-revalidate');
    res.setHeader('Pragma', 'no-cache');
    res.setHeader('Expires', '0');
    
    // Check if the application is ready
    const isReady = true; // Could add more complex readiness checks here
    
    if (isReady) {
      res.status(200).json({
        status: 'ready',
        service: 'runmypool-frontend',
        timestamp: new Date().toISOString(),
        checks: {
          server: 'ok',
          environment: process.env.NODE_ENV || 'unknown'
        }
      });
    } else {
      res.status(503).json({
        status: 'not_ready',
        service: 'runmypool-frontend',
        timestamp: new Date().toISOString()
      });
    }
  } catch (error) {
    console.error('Readiness check error:', error);
    res.status(500).json({ 
      status: 'error', 
      message: 'Readiness check failed',
      timestamp: new Date().toISOString() 
    });
  }
}
