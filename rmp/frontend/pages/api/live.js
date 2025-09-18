// pages/api/live.js
export default function handler(req, res) {
  try {
    // Very simple liveness check - just return OK
    res.setHeader('Cache-Control', 'no-cache, no-store, must-revalidate');
    res.status(200).json({ 
      status: 'alive',
      timestamp: new Date().toISOString()
    });
  } catch (error) {
    console.error('Liveness check error:', error);
    res.status(500).json({ 
      status: 'dead',
      timestamp: new Date().toISOString() 
    });
  }
}
