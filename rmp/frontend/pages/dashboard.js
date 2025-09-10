import { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import ProtectedRoute from '../components/ProtectedRoute';
import { useAuth } from '../context/AuthContext';

export default function Dashboard() {
  const { user } = useAuth();
  const router = useRouter();
  const [leagues, setLeagues] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [activeTabs, setActiveTabs] = useState({}); // Track active tab for each pool
  const [poolPicksData, setPoolPicksData] = useState({}); // Store picks data for each pool
  const [poolStatsData, setPoolStatsData] = useState({}); // Store pool stats for each pool
  const [poolAdminStatus, setPoolAdminStatus] = useState({}); // Store admin status for each pool
  const [showAccountMenu, setShowAccountMenu] = useState(false); // Track account dropdown state

  // Calculate current NFL week based on date
  const getCurrentWeek = () => {
    const now = new Date();
    const currentYear = now.getFullYear();
    
    // Week 1 ends on 9/9 of the current year
    const week1End = new Date(currentYear, 8, 9); // Month is 0-indexed, so 8 = September
    
    // If we're before Week 1 ends, we're in Week 1
    if (now <= week1End) {
      return 1;
    }
    
    // Calculate how many days have passed since Week 1 ended
    const daysSinceWeek1End = Math.floor((now - week1End) / (1000 * 60 * 60 * 24));
    
    // Each week is 7 days, so calculate which week we're in
    const currentWeek = Math.floor(daysSinceWeek1End / 7) + 2; // +2 because we start from Week 2
    
    // Cap at Week 18 (NFL regular season)
    return Math.min(currentWeek, 18);
  };

  useEffect(() => {
    fetchUserLeagues();
  }, []);

  useEffect(() => {
    // Close account menu when clicking outside
    const handleClickOutside = (event) => {
      if (showAccountMenu && !event.target.closest('[data-account-menu]')) {
        setShowAccountMenu(false);
      }
    };

    // Close account menu when escape key is pressed
    const handleEscapeKey = (event) => {
      if (event.key === 'Escape' && showAccountMenu) {
        setShowAccountMenu(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    document.addEventListener('keydown', handleEscapeKey);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('keydown', handleEscapeKey);
    };
  }, [showAccountMenu]);

  const fetchUserLeagues = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const res = await fetch(process.env.NEXT_PUBLIC_API_URL + '/pools/my-pools', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (res.ok) {
        const data = await res.json();
        setLeagues(data);
        
        // Calculate current week for initial tab state
        const currentWeek = getCurrentWeek();
        
        // Initialize active tabs (default to current week) and fetch picks data
        const tabs = {};
        const picksData = {};
        const statsData = {};
        const adminStatus = {};
        
        for (const league of data) {
          tabs[league.id] = currentWeek; // Default to current week
          picksData[league.id] = await fetchLeaguePicksData(league.id, token);
          statsData[league.id] = await fetchPoolStats(league.id, token);
          adminStatus[league.id] = await fetchPoolAdminStatus(league.id, token);
        }
        
        setActiveTabs(tabs);
        setPoolPicksData(picksData);
        setPoolStatsData(statsData);
        setPoolAdminStatus(adminStatus);
      } else {
        setError('Failed to load leagues');
      }
    } catch (err) {
      setError('Failed to load leagues');
    } finally {
      setLoading(false);
    }
  };

  const fetchPoolStats = async (leagueId, token) => {
    try {
      const res = await fetch(process.env.NEXT_PUBLIC_API_URL + `/entries/pool/${leagueId}/stats`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (res.ok) {
        return await res.json();
      } else {
        // Fallback: get all entries and calculate stats manually
        const entriesRes = await fetch(process.env.NEXT_PUBLIC_API_URL + `/entries/pool/${leagueId}`, {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        
        if (entriesRes.ok) {
          const entries = await entriesRes.json();
          const totalEntries = entries.length;
          const eliminatedCount = entries.filter(entry => entry.status === 'eliminated').length;
          const survivorsCount = totalEntries - eliminatedCount;
          
          return {
            totalEntries,
            survivors: survivorsCount,
            eliminated: eliminatedCount,
            survivorsPercentage: totalEntries > 0 ? ((survivorsCount / totalEntries) * 100).toFixed(1) : 0,
            eliminatedPercentage: totalEntries > 0 ? ((eliminatedCount / totalEntries) * 100).toFixed(1) : 0
          };
        }
      }
      
      return { totalEntries: 0, survivors: 0, eliminated: 0, survivorsPercentage: 0, eliminatedPercentage: 0 };
    } catch (err) {
      console.error(`Failed to fetch pool stats for league ${leagueId}:`, err);
      return { totalEntries: 0, survivors: 0, eliminated: 0, survivorsPercentage: 0, eliminatedPercentage: 0 };
    }
  };

  const fetchPoolAdminStatus = async (poolId, token) => {
    try {
      const res = await fetch(process.env.NEXT_PUBLIC_API_URL + `/pools/${poolId}/is-admin`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (res.ok) {
        return await res.json();
      }
      
      return { has_admin_access: false, is_owner: false, is_admin: false };
    } catch (err) {
      console.error(`Failed to fetch admin status for pool ${poolId}:`, err);
      return { has_admin_access: false, is_owner: false, is_admin: false };
    }
  };

  const fetchLeaguePicksData = async (leagueId, token) => {
    try {
      // For now, we'll try to get picks data from a summary endpoint
      // If that doesn't exist, we'll use the existing user entries endpoint as a fallback
      try {
        const summaryRes = await fetch(process.env.NEXT_PUBLIC_API_URL + `/pools/${leagueId}/picks-summary`, {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        
        if (summaryRes.ok) {
          return await summaryRes.json();
        }
      } catch (err) {
        // Endpoint doesn't exist, fall back to user entries
      }
      
      // Fallback: get user's own entries only
      const entriesRes = await fetch(process.env.NEXT_PUBLIC_API_URL + `/entries/pool/${leagueId}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (!entriesRes.ok) {
        return {};
      }
      
      const userEntries = await entriesRes.json();
      const weeklyData = {};
      
      // Fetch picks for user's entries and organize by week
      for (const entry of userEntries) {
        try {
          const picksRes = await fetch(process.env.NEXT_PUBLIC_API_URL + `/picks/entry/${entry.id}`, {
            headers: { 'Authorization': `Bearer ${token}` }
          });
          
          if (picksRes.ok) {
            const picks = await picksRes.json();
            
            // Organize picks by week
            picks.forEach(pick => {
              if (!weeklyData[pick.week]) {
                weeklyData[pick.week] = { teams: {}, unlockedCount: 0 };
              }
              if (pick.team && pick.team.trim() !== '') {
                // Pick has a team selected
                if (!weeklyData[pick.week].teams[pick.team]) {
                  weeklyData[pick.week].teams[pick.team] = 0;
                }
                weeklyData[pick.week].teams[pick.team]++;
              } else {
                // Pick exists but no team selected (unlocked)
                weeklyData[pick.week].unlockedCount++;
              }
            });
            
            // Also check for weeks that should exist but don't have picks yet
            // For now, we'll assume 18 weeks and count missing picks as unlocked
            for (let week = 1; week <= 18; week++) {
              if (!weeklyData[week]) {
                weeklyData[week] = { teams: {}, unlockedCount: 1 }; // User hasn't made a pick for this week yet
              } else {
                // Check if this entry has a pick for this week
                const entryHasPickForWeek = picks.some(pick => pick.week === week);
                if (!entryHasPickForWeek) {
                  weeklyData[week].unlockedCount++;
                }
              }
            }
          } else {
            // If no picks data available, assume all weeks are unlocked for this entry
            for (let week = 1; week <= 18; week++) {
              if (!weeklyData[week]) {
                weeklyData[week] = { teams: {}, unlockedCount: 1 };
              } else {
                weeklyData[week].unlockedCount++;
              }
            }
          }
        } catch (err) {
          console.error(`Failed to fetch picks for entry ${entry.id}:`, err);
        }
      }
      
      return weeklyData;
    } catch (err) {
      console.error(`Failed to fetch league picks data for league ${leagueId}:`, err);
      return {};
    }
  };

  const handleCreateLeague = () => {
    router.push('/create-league');
  };

  const handleLogout = () => {
    localStorage.removeItem('access_token');
    router.push('/login');
  };

  const handleTabChange = (leagueId, week) => {
    setActiveTabs(prev => ({
      ...prev,
      [leagueId]: week
    }));
  };

  const renderPoolStats = (league) => {
    const stats = poolStatsData[league.id];
    
    if (!stats || stats.totalEntries === 0) {
      return (
        <div style={{ 
          backgroundColor: '#f8f9fa',
          borderRadius: '8px',
          padding: '1rem',
          marginBottom: '1rem',
          textAlign: 'center',
          color: '#6b7280',
          fontSize: '0.875rem'
        }}>
          No pool statistics available
        </div>
      );
    }

    return (
      <div style={{ 
        backgroundColor: '#f8f9fa',
        borderRadius: '8px',
        padding: '1rem',
        marginBottom: '1rem',
        border: '1px solid #e5e7eb'
      }}>
        <h4 style={{ 
          margin: '0 0 0.75rem 0',
          fontSize: '0.875rem',
          fontWeight: '600',
          color: '#374151',
          textAlign: 'center'
        }}>
          Pool Statistics
        </h4>
        <div style={{ 
          display: 'grid',
          gridTemplateColumns: '1fr 1fr',
          gap: '0.75rem'
        }}>
          <div style={{
            backgroundColor: '#dcfce7',
            borderRadius: '6px',
            padding: '0.75rem',
            border: '1px solid #16a34a',
            textAlign: 'center'
          }}>
            <div style={{ 
              fontSize: '1.25rem',
              fontWeight: '700',
              color: '#15803d',
              marginBottom: '0.25rem'
            }}>
              {stats.survivors}
            </div>
            <div style={{ 
              fontSize: '0.75rem',
              color: '#166534',
              fontWeight: '500',
              marginBottom: '0.25rem'
            }}>
              Survivors
            </div>
            <div style={{ 
              fontSize: '0.625rem',
              color: '#166534',
              opacity: 0.8
            }}>
              {stats.survivorsPercentage}%
            </div>
          </div>
          <div style={{
            backgroundColor: '#fee2e2',
            borderRadius: '6px',
            padding: '0.75rem',
            border: '1px solid #dc2626',
            textAlign: 'center'
          }}>
            <div style={{ 
              fontSize: '1.25rem',
              fontWeight: '700',
              color: '#dc2626',
              marginBottom: '0.25rem'
            }}>
              {stats.eliminated}
            </div>
            <div style={{ 
              fontSize: '0.75rem',
              color: '#991b1b',
              fontWeight: '500',
              marginBottom: '0.25rem'
            }}>
              Eliminated
            </div>
            <div style={{ 
              fontSize: '0.625rem',
              color: '#991b1b',
              opacity: 0.8
            }}>
              {stats.eliminatedPercentage}%
            </div>
          </div>
        </div>
        <div style={{ 
          textAlign: 'center',
          marginTop: '0.75rem',
          fontSize: '0.75rem',
          color: '#6b7280'
        }}>
          Total Entries: {stats.totalEntries}
        </div>
      </div>
    );
  };

  const renderWeekTabs = (league) => {
    const leaguePicksData = poolPicksData[league.id] || {};
    const activeWeek = activeTabs[league.id] || getCurrentWeek();
    
    // Always show weeks 1-18 for NFL season
    const allWeeks = Array.from({ length: 18 }, (_, i) => i + 1);
    
    return (
      <div>
        {/* Week Tabs */}
        <div style={{ 
          display: 'flex', 
          gap: '0.25rem', 
          marginBottom: '1rem',
          overflowX: 'auto',
          borderBottom: '1px solid #e5e7eb'
        }}>
          {allWeeks.map(week => (
            <button
              key={week}
              onClick={() => handleTabChange(league.id, week)}
              style={{
                padding: '0.5rem 0.75rem',
                border: 'none',
                backgroundColor: activeWeek === week ? '#667eea' : 'transparent',
                color: activeWeek === week ? 'white' : '#6b7280',
                borderRadius: '6px 6px 0 0',
                cursor: 'pointer',
                fontSize: '0.75rem',
                fontWeight: '500',
                transition: 'all 0.2s ease',
                whiteSpace: 'nowrap'
              }}
              onMouseEnter={(e) => {
                if (activeWeek !== week) {
                  e.target.style.backgroundColor = '#f3f4f6';
                }
              }}
              onMouseLeave={(e) => {
                if (activeWeek !== week) {
                  e.target.style.backgroundColor = 'transparent';
                }
              }}
            >
              Week {week}
            </button>
          ))}
        </div>

        {/* Team Counts for Active Week */}
        <div style={{ 
          minHeight: '120px',
          backgroundColor: '#f8f9fa',
          borderRadius: '8px',
          padding: '0.75rem'
        }}>
          {renderTeamCounts(leaguePicksData[activeWeek] || { teams: {}, unlockedCount: 1 }, activeWeek)}
        </div>
      </div>
    );
  };

  const renderTeamCounts = (weekData, currentWeek) => {
    if (!weekData) {
      return (
        <div style={{ 
          textAlign: 'center', 
          color: '#6b7280',
          fontSize: '0.875rem',
          padding: '2rem'
        }}>
          No data available
        </div>
      );
    }

    const { teams = {}, unlockedCount = 0 } = weekData;
    const teamNames = Object.keys(teams).sort((a, b) => teams[b] - teams[a]); // Sort by pick count (highest to lowest)
    const isWeekInPast = currentWeek < getCurrentWeek();
    
    if (teamNames.length === 0 && unlockedCount === 0) {
      return (
        <div style={{ 
          textAlign: 'center', 
          color: '#6b7280',
          fontSize: '0.875rem',
          padding: '2rem'
        }}>
          No picks for this week yet
        </div>
      );
    }

    return (
      <div style={{ 
        display: 'flex',
        flexDirection: 'column',
        gap: '0.5rem'
      }}>
        {teamNames.map((team, index) => (
          <div
            key={team}
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: '0.75rem',
              backgroundColor: 'white',
              borderRadius: '8px',
              border: '1px solid #e5e7eb',
              fontSize: '0.875rem',
              boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)'
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
              <span style={{ 
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                width: '24px',
                height: '24px',
                backgroundColor: '#667eea',
                color: 'white',
                borderRadius: '50%',
                fontSize: '0.75rem',
                fontWeight: '700'
              }}>
                {index + 1}
              </span>
              <span style={{ fontWeight: '600', color: '#374151' }}>{team}</span>
            </div>
            <span style={{ 
              backgroundColor: '#667eea',
              color: 'white',
              borderRadius: '12px',
              padding: '0.25rem 0.75rem',
              fontSize: '0.75rem',
              fontWeight: '700'
            }}>
              {teams[team]} {teams[team] === 1 ? 'pick' : 'picks'}
            </span>
          </div>
        ))}
        {unlockedCount > 0 && (
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: '0.75rem',
              backgroundColor: isWeekInPast ? '#fee2e2' : '#fef3c7',
              borderRadius: '8px',
              border: isWeekInPast ? '1px solid #ef4444' : '1px solid #f59e0b',
              fontSize: '0.875rem',
              boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)'
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
              <span style={{ 
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                width: '24px',
                height: '24px',
                backgroundColor: isWeekInPast ? '#ef4444' : '#f59e0b',
                color: 'white',
                borderRadius: '50%',
                fontSize: '0.75rem',
                fontWeight: '700'
              }}>
                {teamNames.length + 1}
              </span>
              <span style={{ fontWeight: '600', color: isWeekInPast ? '#dc2626' : '#92400e' }}>
                {isWeekInPast ? 'No Selection' : 'Unlocked'}
              </span>
            </div>
            <span style={{ 
              backgroundColor: isWeekInPast ? '#ef4444' : '#f59e0b',
              color: 'white',
              borderRadius: '12px',
              padding: '0.25rem 0.75rem',
              fontSize: '0.75rem',
              fontWeight: '700'
            }}>
              {unlockedCount} {unlockedCount === 1 ? 'pick' : 'picks'}
            </span>
          </div>
        )}
      </div>
    );
  };

  return (
    <ProtectedRoute>
      <div style={{ minHeight: '100vh', background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)', display: 'flex', flexDirection: 'column' }}>
        {/* Header */}
        <header style={{ 
          display: 'flex', 
          justifyContent: 'space-between', 
          alignItems: 'center', 
          padding: '1.5rem 2rem', 
          background: 'rgba(255, 255, 255, 0.1)',
          backdropFilter: 'blur(10px)'
        }}>
          <div style={{ color: 'white', fontSize: '1.5rem', fontWeight: '700' }}>
            🏈 Run My Pool
          </div>
          <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
            <span style={{ color: 'rgba(255, 255, 255, 0.9)', fontSize: '0.9rem' }}>
              Welcome, {user?.email}
            </span>
            <div style={{ position: 'relative' }} data-account-menu>
              <button 
                onClick={() => setShowAccountMenu(!showAccountMenu)}
                style={{ 
                  fontWeight: '500', 
                  color: 'white', 
                  backgroundColor: 'rgba(255, 255, 255, 0.1)', 
                  border: '1px solid rgba(255, 255, 255, 0.3)', 
                  borderRadius: '6px', 
                  padding: '0.5rem 0.75rem', 
                  transition: 'all 0.2s ease',
                  cursor: 'pointer',
                  fontSize: '1rem',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.5rem'
                }}
                onMouseEnter={(e) => {
                  e.target.style.backgroundColor = 'rgba(255, 255, 255, 0.2)';
                  e.target.style.borderColor = 'rgba(255, 255, 255, 0.5)';
                }}
                onMouseLeave={(e) => {
                  e.target.style.backgroundColor = 'rgba(255, 255, 255, 0.1)';
                  e.target.style.borderColor = 'rgba(255, 255, 255, 0.3)';
                }}
              >
                <span>👤</span>
                <span style={{ fontSize: '0.7rem' }}>▼</span>
              </button>
              
              {showAccountMenu && (
                <div style={{
                  position: 'absolute',
                  top: '100%',
                  right: '0',
                  marginTop: '0.5rem',
                  backgroundColor: 'white',
                  borderRadius: '8px',
                  boxShadow: '0 10px 25px rgba(0, 0, 0, 0.2)',
                  border: '1px solid #e5e7eb',
                  minWidth: '160px',
                  zIndex: 1000
                }}>
                  <button
                    onClick={() => {
                      router.push('/account');
                      setShowAccountMenu(false);
                    }}
                    style={{
                      width: '100%',
                      padding: '0.75rem 1rem',
                      border: 'none',
                      backgroundColor: 'transparent',
                      textAlign: 'left',
                      cursor: 'pointer',
                      fontSize: '0.875rem',
                      color: '#374151',
                      borderRadius: '8px 8px 0 0',
                      transition: 'background-color 0.2s ease'
                    }}
                    onMouseEnter={(e) => e.target.style.backgroundColor = '#f3f4f6'}
                    onMouseLeave={(e) => e.target.style.backgroundColor = 'transparent'}
                  >
                    Manage Account
                  </button>
                  <div style={{
                    height: '1px',
                    backgroundColor: '#e5e7eb',
                    margin: '0 0.5rem'
                  }}></div>
                  <button
                    onClick={() => {
                      handleLogout();
                      setShowAccountMenu(false);
                    }}
                    style={{
                      width: '100%',
                      padding: '0.75rem 1rem',
                      border: 'none',
                      backgroundColor: 'transparent',
                      textAlign: 'left',
                      cursor: 'pointer',
                      fontSize: '0.875rem',
                      color: '#dc2626',
                      borderRadius: '0 0 8px 8px',
                      transition: 'background-color 0.2s ease'
                    }}
                    onMouseEnter={(e) => e.target.style.backgroundColor = '#fef2f2'}
                    onMouseLeave={(e) => e.target.style.backgroundColor = 'transparent'}
                  >
                    Logout
                  </button>
                </div>
              )}
            </div>
          </div>
        </header>

        {/* Main Content */}
        <main style={{ 
          flex: 1, 
          display: 'flex', 
          flexDirection: 'column', 
          alignItems: 'center', 
          padding: '2rem',
          background: 'transparent'
        }}>
          <h1 style={{ 
            fontSize: '3rem', 
            fontWeight: '800', 
            marginBottom: '1rem', 
            color: 'white',
            textShadow: '0 4px 8px rgba(0, 0, 0, 0.5)',
            textAlign: 'center'
          }}>
            Dashboard
          </h1>
          
          {/* Leagues Section */}
          <div style={{ 
            background: 'white', 
            borderRadius: '20px', 
            padding: '2.5rem',
            maxWidth: '1200px',
            width: '100%',
            boxShadow: '0 20px 40px rgba(0, 0, 0, 0.15)',
            border: '1px solid rgba(255, 255, 255, 0.2)'
          }}>
            <div style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              marginBottom: '2rem'
            }}>
              <h2 style={{ 
                fontSize: '2rem', 
                fontWeight: '700', 
                color: '#1a202c',
                margin: 0
              }}>
                My Pools
              </h2>
              <button 
                onClick={handleCreateLeague}
                style={{ 
                  fontWeight: '600', 
                  color: 'white', 
                  textDecoration: 'none', 
                  border: 'none', 
                  borderRadius: '8px', 
                  padding: '0.75rem 1.5rem', 
                  background: '#667eea', 
                  transition: 'all 0.2s ease',
                  boxShadow: '0 4px 12px rgba(102, 126, 234, 0.4)',
                  cursor: 'pointer',
                  fontSize: '14px'
                }}
                onMouseEnter={(e) => {
                  e.target.style.transform = 'translateY(-2px)';
                  e.target.style.boxShadow = '0 6px 20px rgba(102, 126, 234, 0.6)';
                  e.target.style.background = '#5a67d8';
                }}
                onMouseLeave={(e) => {
                  e.target.style.transform = 'translateY(0)';
                  e.target.style.boxShadow = '0 4px 12px rgba(102, 126, 234, 0.4)';
                  e.target.style.background = '#667eea';
                }}
              >
                Create Pool
              </button>
            </div>
            
            {loading ? (
              <div style={{ textAlign: 'center', padding: '3rem', color: '#6b7280' }}>
                <p style={{ fontSize: '1.1rem' }}>Loading leagues...</p>
              </div>
            ) : error ? (
              <div style={{ 
                textAlign: 'center', 
                padding: '2rem',
                backgroundColor: '#fed7d7',
                color: '#742a2a',
                borderRadius: '12px',
                border: '1px solid #fc8181'
              }}>
                <p>{error}</p>
              </div>
            ) : leagues.length === 0 ? (
              <div style={{ 
                textAlign: 'center', 
                padding: '3rem', 
                backgroundColor: '#f8f9fa',
                borderRadius: '12px',
                border: '2px dashed #dee2e6'
              }}>
                <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>🏈</div>
                <h3 style={{ color: '#1a202c', marginBottom: '0.5rem' }}>No Pools Yet</h3>
                <p style={{ color: '#6b7280', marginBottom: '1.5rem' }}>
                  You haven't joined any pools yet. Create your first pool or join an existing one to get started!
                </p>
                <button 
                  onClick={handleCreateLeague}
                  style={{ 
                    backgroundColor: '#667eea',
                    color: 'white',
                    padding: '0.75rem 2rem',
                    border: 'none',
                    borderRadius: '8px',
                    fontSize: '1rem',
                    fontWeight: '600',
                    cursor: 'pointer',
                    transition: 'all 0.2s ease',
                    boxShadow: '0 4px 12px rgba(102, 126, 234, 0.4)'
                  }}
                  onMouseEnter={(e) => {
                    e.target.style.backgroundColor = '#5a67d8';
                    e.target.style.transform = 'translateY(-1px)';
                    e.target.style.boxShadow = '0 6px 16px rgba(102, 126, 234, 0.5)';
                  }}
                  onMouseLeave={(e) => {
                    e.target.style.backgroundColor = '#667eea';
                    e.target.style.transform = 'translateY(0)';
                    e.target.style.boxShadow = '0 4px 12px rgba(102, 126, 234, 0.4)';
                  }}
                >
                  Create Your First Pool
                </button>
              </div>
            ) : (
              <div style={{ 
                display: 'grid', 
                gap: '1.5rem', 
                gridTemplateColumns: 'repeat(auto-fit, minmax(350px, 1fr))',
                width: '100%',
                justifyItems: 'center'
              }}>
                {leagues.map(league => (
                  <div key={league.id} style={{ 
                    border: '1px solid #e5e7eb', 
                    borderRadius: '12px', 
                    padding: '1.5rem',
                    backgroundColor: '#fafafa',
                    transition: 'all 0.2s ease',
                    boxShadow: '0 2px 8px rgba(0, 0, 0, 0.05)',
                    width: '100%',
                    position: 'relative'
                  }}
                  onMouseEnter={(e) => {
                    e.target.style.boxShadow = '0 8px 25px rgba(0, 0, 0, 0.1)';
                    e.target.style.transform = 'translateY(-2px)';
                  }}
                  onMouseLeave={(e) => {
                    e.target.style.boxShadow = '0 2px 8px rgba(0, 0, 0, 0.05)';
                    e.target.style.transform = 'translateY(0)';
                  }}
                  >
                    {/* Privacy Badge - Top Right */}
                    <span style={{ 
                      position: 'absolute',
                      top: '1rem',
                      right: '1rem',
                      backgroundColor: league.is_private ? '#fef3c7' : '#dcfce7',
                      color: league.is_private ? '#92400e' : '#166534',
                      padding: '0.25rem 0.75rem',
                      borderRadius: '6px',
                      fontWeight: '500',
                      fontSize: '0.75rem'
                    }}>
                      {league.is_private ? 'Private' : 'Public'}
                    </span>
                    
                    <h3 style={{ 
                      fontSize: '1.25rem', 
                      fontWeight: '700', 
                      marginBottom: '0.5rem', 
                      color: '#1a202c' 
                    }}>
                      {league.name}
                    </h3>
                    
                    {/* Action Buttons */}
                    <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap', marginBottom: '1rem' }}>
                      <button 
                        onClick={() => router.push(`/pool/${league.id}`)}
                        style={{ 
                          backgroundColor: '#10b981', 
                          color: 'white', 
                          padding: '0.5rem 1rem', 
                          border: 'none', 
                          borderRadius: '6px', 
                          cursor: 'pointer',
                          fontSize: '0.875rem',
                          fontWeight: '500',
                          transition: 'all 0.2s ease'
                        }}
                        onMouseEnter={(e) => e.target.style.backgroundColor = '#059669'}
                        onMouseLeave={(e) => e.target.style.backgroundColor = '#10b981'}
                      >
                        View Pool
                      </button>
                      <button 
                        onClick={() => router.push(`/pool/${league.id}/entries`)}
                        style={{ 
                          backgroundColor: '#8b5cf6', 
                          color: 'white', 
                          padding: '0.5rem 1rem', 
                          border: 'none', 
                          borderRadius: '6px', 
                          cursor: 'pointer',
                          fontSize: '0.875rem',
                          fontWeight: '500',
                          transition: 'all 0.2s ease'
                        }}
                        onMouseEnter={(e) => e.target.style.backgroundColor = '#7c3aed'}
                        onMouseLeave={(e) => e.target.style.backgroundColor = '#8b5cf6'}
                      >
                        My Entries
                      </button>
                      <button 
                        onClick={() => router.push(`/message-board?pool=${league.id}`)}
                        style={{ 
                          backgroundColor: '#3b82f6', 
                          color: 'white', 
                          padding: '0.5rem 1rem', 
                          border: 'none', 
                          borderRadius: '6px', 
                          cursor: 'pointer',
                          fontSize: '0.875rem',
                          fontWeight: '500',
                          transition: 'all 0.2s ease'
                        }}
                        onMouseEnter={(e) => e.target.style.backgroundColor = '#2563eb'}
                        onMouseLeave={(e) => e.target.style.backgroundColor = '#3b82f6'}
                      >
                        Message Board
                      </button>
                      {(poolAdminStatus[league.id]?.has_admin_access || league.created_by === user.id) && (
                        <button 
                          onClick={() => router.push(`/admin/league/${league.id}`)}
                          style={{ 
                            backgroundColor: '#f59e0b', 
                            color: 'white', 
                            padding: '0.5rem 1rem', 
                            border: 'none', 
                            borderRadius: '6px', 
                            cursor: 'pointer',
                            fontSize: '0.875rem',
                            fontWeight: '500',
                            transition: 'all 0.2s ease'
                          }}
                          onMouseEnter={(e) => e.target.style.backgroundColor = '#d97706'}
                          onMouseLeave={(e) => e.target.style.backgroundColor = '#f59e0b'}
                        >
                          Admin
                        </button>
                      )}
                    </div>
                    
                    {/* Pool Stats Section */}
                    {renderPoolStats(league)}
                    
                    {/* Week Tabs Section */}
                    <div style={{ marginBottom: '1rem' }}>
                      {renderWeekTabs(league)}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </main>
      </div>
    </ProtectedRoute>
  );
}
