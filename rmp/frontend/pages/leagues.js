import { useState, useEffect } from 'react';
import Link from 'next/link';
import { ResponsiveCard, ResponsiveButton, ResponsiveInput } from '../components/ResponsiveComponents';
import { ResponsiveModal, ResponsiveTabs } from '../components/ResponsiveDataComponents';

export default function Leagues() {
  const [isMobile, setIsMobile] = useState(false);
  const [activeTab, setActiveTab] = useState('browse');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  
  const [leagues] = useState([
    {
      id: 1,
      name: "NFL Sunday Showdown",
      type: "Public",
      members: 24,
      maxMembers: 50,
      entryFee: "$25",
      prize: "$1,200",
      weeks: "1-18",
      status: "Open"
    },
    {
      id: 2,
      name: "Office Pool Champions",
      type: "Private",
      members: 12,
      maxMembers: 20,
      entryFee: "$50",
      prize: "$1,000",
      weeks: "1-17",
      status: "Invite Only"
    },
    {
      id: 3,
      name: "High Stakes Winners",
      type: "Public",
      members: 45,
      maxMembers: 50,
      entryFee: "$100",
      prize: "$4,500",
      weeks: "1-18",
      status: "Almost Full"
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

  const leaguesGridStyles = {
    display: 'grid',
    gridTemplateColumns: isMobile ? '1fr' : 'repeat(auto-fill, minmax(350px, 1fr))',
    gap: '1.5rem'
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'Open': return '#22c55e';
      case 'Almost Full': return '#f59e0b';
      case 'Invite Only': return '#667eea';
      default: return '#6b7280';
    }
  };

  const filteredLeagues = leagues.filter(league => 
    league.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    league.type.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const tabs = [
    {
      id: 'browse',
      label: '🔍 Browse Leagues',
      content: (
        <div>
          <div style={{ marginBottom: '1.5rem' }}>
            <ResponsiveInput
              placeholder="Search leagues..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              style={{ marginBottom: '1rem' }}
            />
            
            <div style={{
              display: 'flex',
              gap: '1rem',
              flexDirection: isMobile ? 'column' : 'row',
              alignItems: isMobile ? 'stretch' : 'center'
            }}>
              <ResponsiveButton
                variant="primary"
                onClick={() => setShowCreateModal(true)}
              >
                🏆 Create New League
              </ResponsiveButton>
              
              <div style={{
                display: 'flex',
                gap: '0.5rem',
                flex: 1,
                flexWrap: 'wrap'
              }}>
                <button style={{
                  padding: '0.5rem 1rem',
                  fontSize: '0.875rem',
                  borderRadius: '20px',
                  border: '1px solid #e5e7eb',
                  background: 'white',
                  cursor: 'pointer'
                }}>
                  All Types
                </button>
                <button style={{
                  padding: '0.5rem 1rem',
                  fontSize: '0.875rem',
                  borderRadius: '20px',
                  border: '1px solid #e5e7eb',
                  background: 'white',
                  cursor: 'pointer'
                }}>
                  Public Only
                </button>
                <button style={{
                  padding: '0.5rem 1rem',
                  fontSize: '0.875rem',
                  borderRadius: '20px',
                  border: '1px solid #e5e7eb',
                  background: 'white',
                  cursor: 'pointer'
                }}>
                  Private Only
                </button>
              </div>
            </div>
          </div>

          {filteredLeagues.length === 0 ? (
            <ResponsiveCard style={{ textAlign: 'center', padding: '3rem 2rem' }}>
              <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>🏈</div>
              <h3 style={{ color: '#6b7280', margin: '0 0 0.5rem 0' }}>No leagues found</h3>
              <p style={{ color: '#9ca3af', margin: '0 0 2rem 0' }}>
                Try adjusting your search or create a new league!
              </p>
              <ResponsiveButton
                variant="primary"
                onClick={() => setShowCreateModal(true)}
              >
                Create New League
              </ResponsiveButton>
            </ResponsiveCard>
          ) : (
            <div style={leaguesGridStyles}>
              {filteredLeagues.map((league) => (
                <ResponsiveCard key={league.id} style={{ position: 'relative' }}>
                  <div style={{
                    position: 'absolute',
                    top: '1rem',
                    right: '1rem',
                    backgroundColor: getStatusColor(league.status),
                    color: 'white',
                    padding: '0.25rem 0.75rem',
                    borderRadius: '12px',
                    fontSize: '0.75rem',
                    fontWeight: '600'
                  }}>
                    {league.status}
                  </div>
                  
                  <h3 style={{
                    fontSize: '1.25rem',
                    fontWeight: '700',
                    color: '#1f2937',
                    margin: '0 0 1rem 0',
                    paddingRight: '4rem'
                  }}>
                    {league.name}
                  </h3>
                  
                  <div style={{
                    display: 'grid',
                    gridTemplateColumns: isMobile ? '1fr' : '1fr 1fr',
                    gap: '0.75rem',
                    marginBottom: '1.5rem',
                    fontSize: '0.875rem'
                  }}>
                    <div>
                      <span style={{ color: '#6b7280' }}>Type: </span>
                      <span style={{ fontWeight: '600' }}>{league.type}</span>
                    </div>
                    <div>
                      <span style={{ color: '#6b7280' }}>Members: </span>
                      <span style={{ fontWeight: '600' }}>{league.members}/{league.maxMembers}</span>
                    </div>
                    <div>
                      <span style={{ color: '#6b7280' }}>Entry: </span>
                      <span style={{ fontWeight: '600' }}>{league.entryFee}</span>
                    </div>
                    <div>
                      <span style={{ color: '#6b7280' }}>Prize: </span>
                      <span style={{ fontWeight: '600', color: '#22c55e' }}>{league.prize}</span>
                    </div>
                  </div>
                  
                  <div style={{
                    display: 'flex',
                    gap: '0.5rem',
                    flexDirection: isMobile ? 'column' : 'row'
                  }}>
                    <ResponsiveButton
                      variant="primary"
                      style={{ flex: 1 }}
                    >
                      Join League
                    </ResponsiveButton>
                    <ResponsiveButton
                      variant="secondary"
                      style={{ flex: isMobile ? 1 : 'none' }}
                    >
                      View Details
                    </ResponsiveButton>
                  </div>
                </ResponsiveCard>
              ))}
            </div>
          )}
        </div>
      )
    },
    {
      id: 'my-leagues',
      label: '👥 My Leagues',
      content: (
        <ResponsiveCard style={{ textAlign: 'center', padding: '3rem 2rem' }}>
          <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>🏆</div>
          <h3 style={{ color: '#6b7280', margin: '0 0 0.5rem 0' }}>No leagues joined yet</h3>
          <p style={{ color: '#9ca3af', margin: '0 0 2rem 0' }}>
            Join or create a league to get started with your picks!
          </p>
          <Link href="/dashboard" passHref>
            <ResponsiveButton variant="primary">
              Go to Dashboard
            </ResponsiveButton>
          </Link>
        </ResponsiveCard>
      )
    }
  ];

  return (
    <main style={containerStyles}>
      <div style={headerStyles}>
        <h1 style={titleStyles}>🏈 NFL Leagues</h1>
        <p style={subtitleStyles}>
          Browse public leagues, join private ones with an invite, or create your own league with custom rules
        </p>
      </div>

      <ResponsiveTabs
        tabs={tabs}
        activeTab={activeTab}
        onTabChange={setActiveTab}
      />

      <ResponsiveModal
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        title="Create New League"
      >
        <form style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          <div>
            <label style={{ 
              display: 'block', 
              marginBottom: '0.5rem', 
              fontWeight: '600',
              color: '#374151'
            }}>
              League Name
            </label>
            <ResponsiveInput 
              placeholder="Enter league name"
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
              League Type
            </label>
            <select style={{
              width: '100%',
              padding: isMobile ? '0.875rem 1rem' : '0.75rem 1rem',
              fontSize: isMobile ? '16px' : '1rem',
              border: '2px solid #e2e8f0',
              borderRadius: '8px',
              outline: 'none',
              backgroundColor: 'white',
              minHeight: isMobile ? '48px' : '44px'
            }}>
              <option value="public">Public - Anyone can join</option>
              <option value="private">Private - Invite only</option>
            </select>
          </div>
          
          <div style={{
            display: 'grid',
            gridTemplateColumns: isMobile ? '1fr' : '1fr 1fr',
            gap: '1rem'
          }}>
            <div>
              <label style={{ 
                display: 'block', 
                marginBottom: '0.5rem', 
                fontWeight: '600',
                color: '#374151'
              }}>
                Entry Fee
              </label>
              <ResponsiveInput 
                placeholder="$25"
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
                Max Members
              </label>
              <ResponsiveInput 
                type="number"
                placeholder="50"
                required
              />
            </div>
          </div>
          
          <div style={{
            display: 'flex',
            gap: '1rem',
            flexDirection: isMobile ? 'column-reverse' : 'row',
            marginTop: '1rem'
          }}>
            <ResponsiveButton
              variant="secondary"
              onClick={() => setShowCreateModal(false)}
              style={{ flex: 1 }}
            >
              Cancel
            </ResponsiveButton>
            <ResponsiveButton
              variant="primary"
              type="submit"
              style={{ flex: 1 }}
            >
              Create League
            </ResponsiveButton>
          </div>
        </form>
      </ResponsiveModal>
    </main>
  );
}
