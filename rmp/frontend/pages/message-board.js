import { useState, useEffect } from 'react';
import { ResponsiveCard, ResponsiveButton, ResponsiveInput } from '../components/ResponsiveComponents';
import { ResponsiveModal } from '../components/ResponsiveDataComponents';

export default function MessageBoard() {
  const [isMobile, setIsMobile] = useState(false);
  const [showNewMessageModal, setShowNewMessageModal] = useState(false);
  const [messages] = useState([
    {
      id: 1,
      title: "Week 15 Lock Picks Available",
      content: "Selling my guaranteed lock picks for Week 15. 12-2 record this season. $25 per week.",
      author: "PickMaster99",
      date: "2024-01-15",
      price: "$25"
    },
    {
      id: 2,
      title: "Premium Analysis Package",
      content: "Complete statistical analysis and predictions for remaining weeks. Includes injury reports and weather analysis.",
      author: "NFLAnalyst",
      date: "2024-01-14", 
      price: "$50"
    }
  ]);

  useEffect(() => {
    const checkDevice = () => {
      setIsMobile(window.innerWidth <= 767);
    };
    
    checkDevice();
    window.addEventListener('resize', checkDevice);
    return () => window.removeEventListener('resize', checkDevice);
  }, []);

  const containerStyles = {
    padding: isMobile ? '1rem' : '2rem',
    maxWidth: '1200px',
    margin: '0 auto'
  };

  const headerStyles = {
    textAlign: 'center',
    marginBottom: '2rem'
  };

  const titleStyles = {
    fontSize: isMobile ? '2rem' : '2.5rem',
    fontWeight: '800',
    color: '#1f2937',
    margin: '0 0 1rem 0'
  };

  const subtitleStyles = {
    fontSize: isMobile ? '1rem' : '1.2rem',
    color: '#6b7280',
    margin: '0 0 2rem 0',
    lineHeight: '1.5'
  };

  const messagesGridStyles = {
    display: 'grid',
    gridTemplateColumns: isMobile ? '1fr' : 'repeat(auto-fit, minmax(400px, 1fr))',
    gap: '1.5rem',
    marginTop: '1.5rem'
  };

  const messageCardStyles = {
    padding: isMobile ? '1rem' : '1.5rem',
    borderLeft: '4px solid #667eea'
  };

  return (
    <main style={containerStyles}>
      <div style={headerStyles}>
        <h1 style={titleStyles}>🏈 Message Board</h1>
        <p style={subtitleStyles}>
          Advertise picks for sale. Connect with other pool members. (No conversations allowed - contact info only)
        </p>
        
        <ResponsiveButton
          variant="primary"
          onClick={() => setShowNewMessageModal(true)}
          style={{ fontSize: isMobile ? '1rem' : '1.1rem' }}
        >
          📝 Post New Message
        </ResponsiveButton>
      </div>

      {messages.length === 0 ? (
        <ResponsiveCard style={{ textAlign: 'center', padding: '3rem 2rem' }}>
          <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>📋</div>
          <h3 style={{ color: '#6b7280', margin: '0 0 0.5rem 0' }}>No messages yet</h3>
          <p style={{ color: '#9ca3af', margin: 0 }}>
            Be the first to post a message on the board!
          </p>
        </ResponsiveCard>
      ) : (
        <div style={messagesGridStyles}>
          {messages.map((message) => (
            <ResponsiveCard key={message.id} style={messageCardStyles}>
              <div style={{ marginBottom: '1rem' }}>
                <div style={{ 
                  display: 'flex', 
                  justifyContent: 'space-between', 
                  alignItems: isMobile ? 'flex-start' : 'center',
                  flexDirection: isMobile ? 'column' : 'row',
                  gap: isMobile ? '0.5rem' : '1rem',
                  marginBottom: '0.5rem' 
                }}>
                  <h3 style={{ 
                    fontSize: isMobile ? '1.25rem' : '1.5rem',
                    fontWeight: '700',
                    color: '#1f2937',
                    margin: 0 
                  }}>
                    {message.title}
                  </h3>
                  <span style={{
                    backgroundColor: '#22c55e',
                    color: 'white',
                    padding: '0.25rem 0.75rem',
                    borderRadius: '20px',
                    fontSize: '0.875rem',
                    fontWeight: '600',
                    whiteSpace: 'nowrap'
                  }}>
                    {message.price}
                  </span>
                </div>
                
                <div style={{
                  display: 'flex',
                  gap: '1rem',
                  fontSize: '0.875rem',
                  color: '#6b7280',
                  marginBottom: '1rem',
                  flexWrap: 'wrap'
                }}>
                  <span>👤 {message.author}</span>
                  <span>📅 {new Date(message.date).toLocaleDateString()}</span>
                </div>
              </div>
              
              <p style={{
                color: '#374151',
                lineHeight: '1.6',
                margin: '0 0 1.5rem 0',
                fontSize: isMobile ? '0.95rem' : '1rem'
              }}>
                {message.content}
              </p>
              
              <div style={{
                display: 'flex',
                gap: '0.5rem',
                flexDirection: isMobile ? 'column' : 'row'
              }}>
                <ResponsiveButton
                  variant="secondary"
                  style={{ 
                    flex: 1,
                    fontSize: '0.875rem' 
                  }}
                >
                  💬 Contact Seller
                </ResponsiveButton>
                <ResponsiveButton
                  variant="secondary" 
                  style={{ 
                    flex: isMobile ? 1 : 'none',
                    fontSize: '0.875rem' 
                  }}
                >
                  🚩 Report
                </ResponsiveButton>
              </div>
            </ResponsiveCard>
          ))}
        </div>
      )}

      <ResponsiveModal
        isOpen={showNewMessageModal}
        onClose={() => setShowNewMessageModal(false)}
        title="Post New Message"
      >
        <form style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          <div>
            <label style={{ 
              display: 'block', 
              marginBottom: '0.5rem', 
              fontWeight: '600',
              color: '#374151'
            }}>
              Message Title
            </label>
            <ResponsiveInput 
              placeholder="Enter a clear title for your message"
              required
            />
          </div>
          
          <div>
            <label style={{ 
              display: 'block', 
              marginBottom: '0.5rem', 
              fontWeight: '600',
              color: '#374151'
            }}>
              Price
            </label>
            <ResponsiveInput 
              placeholder="e.g., $25"
              required
            />
          </div>
          
          <div>
            <label style={{ 
              display: 'block', 
              marginBottom: '0.5rem', 
              fontWeight: '600',
              color: '#374151'
            }}>
              Message Content
            </label>
            <textarea
              placeholder="Describe what you're offering. Include contact information for interested buyers."
              required
              style={{
                width: '100%',
                padding: '0.875rem 1rem',
                fontSize: isMobile ? '16px' : '1rem',
                border: '2px solid #e2e8f0',
                borderRadius: '8px',
                outline: 'none',
                minHeight: '120px',
                resize: 'vertical',
                fontFamily: 'inherit'
              }}
            />
          </div>
          
          <div style={{
            display: 'flex',
            gap: '1rem',
            flexDirection: isMobile ? 'column-reverse' : 'row',
            marginTop: '1rem'
          }}>
            <ResponsiveButton
              variant="secondary"
              onClick={() => setShowNewMessageModal(false)}
              style={{ flex: 1 }}
            >
              Cancel
            </ResponsiveButton>
            <ResponsiveButton
              variant="primary"
              type="submit"
              style={{ flex: 1 }}
            >
              Post Message
            </ResponsiveButton>
          </div>
        </form>
      </ResponsiveModal>
    </main>
  );
}
