import { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import ProtectedRoute from '../components/ProtectedRoute';
import { useAuth } from '../context/AuthContext';
import { WorkspaceHeader } from '../components/ProductWorkspace';
import { baseStyles, createHoverHandlers, hoverEffects, mobileStyles, getResponsiveStyle, touchStyles } from '../styles/globalStyles';

// NFL team data for logos and team info
const NFL_TEAMS = {
  'ARI': { name: 'Arizona Cardinals', color: '#97233F', logo: 'ari.svg' },
  'ATL': { name: 'Atlanta Falcons', color: '#A71930', logo: 'atl.svg' },
  'BAL': { name: 'Baltimore Ravens', color: '#241773', logo: 'bal.svg' },
  'BUF': { name: 'Buffalo Bills', color: '#00338D', logo: 'buf.svg' },
  'CAR': { name: 'Carolina Panthers', color: '#0085CA', logo: 'car.svg' },
  'CHI': { name: 'Chicago Bears', color: '#0B162A', logo: 'chi.svg' },
  'CIN': { name: 'Cincinnati Bengals', color: '#FB4F14', logo: 'cin.svg' },
  'CLE': { name: 'Cleveland Browns', color: '#311D00', logo: 'cle.svg' },
  'DAL': { name: 'Dallas Cowboys', color: '#003594', logo: 'dal.svg' },
  'DEN': { name: 'Denver Broncos', color: '#FB4F14', logo: 'den.svg' },
  'DET': { name: 'Detroit Lions', color: '#0076B6', logo: 'det.svg' },
  'GB': { name: 'Green Bay Packers', color: '#203731', logo: 'gb.svg' },
  'HOU': { name: 'Houston Texans', color: '#03202F', logo: 'hou.svg' },
  'IND': { name: 'Indianapolis Colts', color: '#002C5F', logo: 'ind.svg' },
  'JAX': { name: 'Jacksonville Jaguars', color: '#006778', logo: 'jax.svg' },
  'KC': { name: 'Kansas City Chiefs', color: '#E31837', logo: 'kc.svg' },
  'LV': { name: 'Las Vegas Raiders', color: '#000000', logo: 'lv.svg' },
  'LAC': { name: 'Los Angeles Chargers', color: '#0080C6', logo: 'lac.svg' },
  'LAR': { name: 'Los Angeles Rams', color: '#003594', logo: 'lar.svg' },
  'MIA': { name: 'Miami Dolphins', color: '#008E97', logo: 'mia.svg' },
  'MIN': { name: 'Minnesota Vikings', color: '#4F2683', logo: 'min.svg' },
  'NE': { name: 'New England Patriots', color: '#002244', logo: 'ne.svg' },
  'NO': { name: 'New Orleans Saints', color: '#D3BC8D', logo: 'no.svg' },
  'NYG': { name: 'New York Giants', color: '#0B2265', logo: 'nyg.svg' },
  'NYJ': { name: 'New York Jets', color: '#125740', logo: 'nyj.svg' },
  'PHI': { name: 'Philadelphia Eagles', color: '#004C54', logo: 'phi.svg' },
  'PIT': { name: 'Pittsburgh Steelers', color: '#FFB612', logo: 'pit.svg' },
  'SF': { name: 'San Francisco 49ers', color: '#AA0000', logo: 'sf.svg' },
  'SEA': { name: 'Seattle Seahawks', color: '#002244', logo: 'sea.svg' },
  'TB': { name: 'Tampa Bay Buccaneers', color: '#D50A0A', logo: 'tb.svg' },
  'TEN': { name: 'Tennessee Titans', color: '#0C2340', logo: 'ten.svg' },
  'WAS': { name: 'Washington Commanders', color: '#5A1414', logo: 'was.svg' }
};

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
  const [draggedPoolId, setDraggedPoolId] = useState(null); // Track which pool is being dragged
  const [poolOrder, setPoolOrder] = useState([]); // Track custom pool ordering
  const [isMobile, setIsMobile] = useState(false); // Track mobile device

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
    const checkDevice = () => {
      setIsMobile(window.innerWidth <= 767);
    };
    
    checkDevice();
    window.addEventListener('resize', checkDevice);
    return () => window.removeEventListener('resize', checkDevice);
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
        if (data.length === 0) {
          router.replace('/leagues');
          return;
        }
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
                
                // Load saved pool order from localStorage
                try {
                  const savedOrder = localStorage.getItem('poolOrder');
                  if (savedOrder) {
                    const parsedOrder = JSON.parse(savedOrder);
                    // Filter to only include pools that still exist
                    const validOrder = parsedOrder.filter(poolId => 
                      data.some(league => league.id === poolId)
                    );
                    if (validOrder.length > 0) {
                      setPoolOrder(validOrder);
                    }
                  }
                } catch (err) {
                  console.warn('Could not load pool order from localStorage:', err);
                }
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
      // Calculate stats manually from entries
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

  // Drag and drop handlers
  const handleDragStart = (e, poolId) => {
    setDraggedPoolId(poolId);
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('text/html', poolId);
    // Add visual feedback
    e.target.style.opacity = '0.5';
  };

  const handleDragEnd = (e) => {
    setDraggedPoolId(null);
    e.target.style.opacity = '1';
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
    // Add visual feedback for drop zone
    if (e.target.closest('[draggable="true"]')) {
      const tile = e.target.closest('[draggable="true"]');
      if (!tile.classList.contains('drag-over')) {
        tile.style.backgroundColor = '#f0f9ff';
        tile.style.borderColor = '#3b82f6';
        tile.classList.add('drag-over');
      }
    }
  };

  const handleDragLeave = (e) => {
    // Remove visual feedback when leaving drop zone
    if (e.target.closest('[draggable="true"]')) {
      const tile = e.target.closest('[draggable="true"]');
      if (tile.classList.contains('drag-over')) {
        tile.style.backgroundColor = '#fafafa';
        tile.style.borderColor = '#e5e7eb';
        tile.classList.remove('drag-over');
      }
    }
  };

  const handleDrop = (e, targetPoolId) => {
    e.preventDefault();
    
    // Remove visual feedback
    const tile = e.target.closest('[draggable="true"]');
    if (tile && tile.classList.contains('drag-over')) {
      tile.style.backgroundColor = '#fafafa';
      tile.style.borderColor = '#e5e7eb';
      tile.classList.remove('drag-over');
    }
    
    if (!draggedPoolId || draggedPoolId === targetPoolId) {
      return;
    }

    // Reorder the pools
    const currentOrder = poolOrder.length > 0 ? poolOrder : leagues.map(l => l.id);
    const draggedIndex = currentOrder.indexOf(draggedPoolId);
    const targetIndex = currentOrder.indexOf(targetPoolId);
    
    if (draggedIndex === -1 || targetIndex === -1) return;

    const newOrder = [...currentOrder];
    // Remove dragged item
    newOrder.splice(draggedIndex, 1);
    // Insert at target position
    newOrder.splice(targetIndex, 0, draggedPoolId);
    
    setPoolOrder(newOrder);
    
    // Save to localStorage
    try {
      localStorage.setItem('poolOrder', JSON.stringify(newOrder));
    } catch (err) {
      console.warn('Could not save pool order to localStorage:', err);
    }
  };

  // Function to get ordered pools
  const getOrderedPools = () => {
    if (poolOrder.length === 0) {
      return leagues;
    }
    
    // Create a map for quick lookup
    const poolMap = new Map(leagues.map(pool => [pool.id, pool]));
    
    // Order pools according to poolOrder, then add any new pools not in the order
    const orderedPools = [];
    
    // Add pools in the stored order
    poolOrder.forEach(poolId => {
      if (poolMap.has(poolId)) {
        orderedPools.push(poolMap.get(poolId));
        poolMap.delete(poolId);
      }
    });
    
    // Add any remaining pools (new ones not in the order)
    poolMap.forEach(pool => orderedPools.push(pool));
    
    return orderedPools;
  };

  const renderPoolStats = (league) => {
    const stats = poolStatsData[league.id];
    
    if (!stats || stats.totalEntries === 0) {
      return (
        <div className="pool-card__stats pool-card__stats--empty" style={{
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
      <div className="pool-card__stats" style={{
        backgroundColor: '#f8f9fa',
        borderRadius: '8px',
        padding: '1rem',
        marginBottom: '1rem',
        border: '1px solid #e5e7eb'
      }}>
        <h4 className="pool-card__stats-title" style={{
          margin: '0 0 0.75rem 0',
          fontSize: '0.875rem',
          fontWeight: '600',
          color: '#374151',
          textAlign: 'center'
        }}>
          Pool Statistics
        </h4>
        <div className="pool-card__stat-grid" style={{
          display: 'grid',
          gridTemplateColumns: '1fr 1fr',
          gap: '0.75rem'
        }}>
          <div className="pool-card__stat pool-card__stat--surviving" style={{
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
          <div className="pool-card__stat pool-card__stat--eliminated" style={{
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
        <div className="pool-card__stat-total" style={{
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

  const renderWeekSelector = (league) => {
    const leaguePicksData = poolPicksData[league.id] || {};
    const activeWeek = activeTabs[league.id] || getCurrentWeek();
    
    // Always show weeks 1-18 for NFL season
    const allWeeks = Array.from({ length: 18 }, (_, i) => i + 1);
    
    return (
      <div className="pool-card__week">
        {/* Week Selector Dropdown */}
        <div className="pool-card__week-controls" style={{
          display: 'flex',
          alignItems: 'center',
          gap: '0.75rem',
          marginBottom: '1rem',
          padding: '0.75rem',
          backgroundColor: '#f8f9fa',
          borderRadius: '8px',
          border: '1px solid #e5e7eb'
        }}>
          <label 
            htmlFor={`week-selector-${league.id}`} 
            style={{ 
              fontSize: '0.875rem',
              fontWeight: '600',
              color: '#374151',
              minWidth: 'fit-content'
            }}
          >
            Select Week:
          </label>
          <select
            id={`week-selector-${league.id}`}
            value={activeWeek}
            onChange={(e) => handleTabChange(league.id, parseInt(e.target.value))}
            style={{
              flex: 1,
              padding: '0.5rem 0.75rem',
              border: '1px solid #d1d5db',
              borderRadius: '6px',
              backgroundColor: 'white',
              color: '#374151',
              fontSize: '0.875rem',
              fontWeight: '500',
              cursor: 'pointer',
              outline: 'none',
              transition: 'all 0.2s ease'
            }}
            onFocus={(e) => {
              e.target.style.borderColor = '#3b82f6';
              e.target.style.boxShadow = '0 0 0 3px rgba(59, 130, 246, 0.1)';
            }}
            onBlur={(e) => {
              e.target.style.borderColor = '#d1d5db';
              e.target.style.boxShadow = 'none';
            }}
          >
            {allWeeks.map(week => (
              <option key={week} value={week}>
                Week {week} - {getCurrentWeek() === week ? '(Current)' : 
                             getCurrentWeek() > week ? '(Past)' : 
                             '(Future)'}
              </option>
            ))}
          </select>
          
          {/* Quick Navigation Buttons */}
          <div className="pool-card__week-nav" style={{ display: 'flex', gap: '0.25rem' }}>
            <button
              onClick={() => handleTabChange(league.id, Math.max(1, activeWeek - 1))}
              disabled={activeWeek === 1}
              style={{
                padding: '0.5rem',
                border: '1px solid #d1d5db',
                borderRadius: '4px',
                backgroundColor: activeWeek === 1 ? '#f3f4f6' : 'white',
                color: activeWeek === 1 ? '#9ca3af' : '#374151',
                cursor: activeWeek === 1 ? 'not-allowed' : 'pointer',
                fontSize: '0.75rem',
                transition: 'all 0.2s ease'
              }}
              onMouseEnter={(e) => {
                if (activeWeek !== 1) {
                  e.target.style.backgroundColor = '#f9fafb';
                }
              }}
              onMouseLeave={(e) => {
                if (activeWeek !== 1) {
                  e.target.style.backgroundColor = 'white';
                }
              }}
              title="Previous Week"
            >
              ◀
            </button>
            <button
              onClick={() => handleTabChange(league.id, Math.min(18, activeWeek + 1))}
              disabled={activeWeek === 18}
              style={{
                padding: '0.5rem',
                border: '1px solid #d1d5db',
                borderRadius: '4px',
                backgroundColor: activeWeek === 18 ? '#f3f4f6' : 'white',
                color: activeWeek === 18 ? '#9ca3af' : '#374151',
                cursor: activeWeek === 18 ? 'not-allowed' : 'pointer',
                fontSize: '0.75rem',
                transition: 'all 0.2s ease'
              }}
              onMouseEnter={(e) => {
                if (activeWeek !== 18) {
                  e.target.style.backgroundColor = '#f9fafb';
                }
              }}
              onMouseLeave={(e) => {
                if (activeWeek !== 18) {
                  e.target.style.backgroundColor = 'white';
                }
              }}
              title="Next Week"
            >
              ▶
            </button>
            <button
              onClick={() => handleTabChange(league.id, getCurrentWeek())}
              style={{
                padding: '0.5rem 0.75rem',
                border: '1px solid #3b82f6',
                borderRadius: '4px',
                backgroundColor: activeWeek === getCurrentWeek() ? '#3b82f6' : 'white',
                color: activeWeek === getCurrentWeek() ? 'white' : '#3b82f6',
                cursor: 'pointer',
                fontSize: '0.75rem',
                fontWeight: '500',
                transition: 'all 0.2s ease'
              }}
              onMouseEnter={(e) => {
                if (activeWeek !== getCurrentWeek()) {
                  e.target.style.backgroundColor = '#eff6ff';
                }
              }}
              onMouseLeave={(e) => {
                if (activeWeek !== getCurrentWeek()) {
                  e.target.style.backgroundColor = 'white';
                }
              }}
              title="Go to Current Week"
            >
              Current
            </button>
          </div>
        </div>

        {/* Team Counts for Active Week */}
        <div className="pool-card__picks" style={{
          minHeight: '120px',
          maxHeight: '300px',
          backgroundColor: '#f8f9fa',
          borderRadius: '8px',
          padding: '0.75rem',
          overflowY: 'auto',
          overflowX: 'hidden'
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
      <div className="pool-card__pick-list" style={{
        display: 'flex',
        flexDirection: 'column',
        gap: '0.5rem'
      }}>
        {teamNames.map((team, index) => (
          <div className="pool-card__pick-row"
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
              <span className="pool-card__pick-rank" style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                width: '24px',
                height: '24px',
                backgroundColor: '#64748b',
                color: 'white',
                borderRadius: '50%',
                fontSize: '0.75rem',
                fontWeight: '700'
              }}>
                {index + 1}
              </span>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                {NFL_TEAMS[team] && (
                  <img 
                    src={`/nfl/${NFL_TEAMS[team].logo}`}
                    alt={`${team} logo`}
                    style={{
                      width: '24px',
                      height: '24px',
                      objectFit: 'contain'
                    }}
                    onError={(e) => {
                      e.target.style.display = 'none';
                    }}
                  />
                )}
                <span className="pool-card__team-code" style={{ fontWeight: '600', color: '#374151' }}>{team}</span>
              </div>
            </div>
            <span className="pool-card__pick-count" style={{
              backgroundColor: '#64748b',
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
          <div className={`pool-card__pick-row pool-card__pick-row--open${isWeekInPast ? ' pool-card__pick-row--missed' : ''}`}
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: '0.75rem',
              backgroundColor: isWeekInPast ? '#fee2e2' : '#f1f5f9',
              borderRadius: '8px',
              border: isWeekInPast ? '1px solid #ef4444' : '1px solid #cbd5e1',
              fontSize: '0.875rem',
              boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)'
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
              <span className="pool-card__pick-rank" style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                width: '24px',
                height: '24px',
                backgroundColor: isWeekInPast ? '#ef4444' : '#64748b',
                color: 'white',
                borderRadius: '50%',
                fontSize: '0.75rem',
                fontWeight: '700'
              }}>
                {teamNames.length + 1}
              </span>
              <span className="pool-card__team-code" style={{ fontWeight: '600', color: isWeekInPast ? '#dc2626' : '#475569' }}>
                {isWeekInPast ? 'No Selection' : 'Unlocked'}
              </span>
            </div>
            <span className="pool-card__pick-count" style={{
              backgroundColor: isWeekInPast ? '#ef4444' : '#64748b',
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
      <div className="product-page dashboard-page" style={{ minHeight: '100vh', background: 'linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%)', display: 'flex', flexDirection: 'column' }}>
        {/* Header */}
        <header className="legacy-page-header" style={{
          display: 'flex', 
          justifyContent: 'space-between', 
          alignItems: 'center', 
          padding: '1.5rem 2rem', 
          background: 'rgba(255, 255, 255, 0.8)',
          backdropFilter: 'blur(10px)',
          borderBottom: '1px solid #e2e8f0'
        }}>
          <div style={{ color: '#1e293b', fontSize: '1.5rem', fontWeight: '700' }}>
            🏈 Run My Pool
          </div>
          <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
            <span style={{ color: '#64748b', fontSize: '0.9rem' }}>
              Welcome, {user?.email}
            </span>
            <div style={{ position: 'relative' }} data-account-menu>
              <button 
                onClick={() => setShowAccountMenu(!showAccountMenu)}
                style={{ 
                  fontWeight: '500', 
                  color: '#475569', 
                  backgroundColor: '#f1f5f9', 
                  border: '1px solid #cbd5e1', 
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
                  e.target.style.backgroundColor = '#e2e8f0';
                  e.target.style.borderColor = '#94a3b8';
                }}
                onMouseLeave={(e) => {
                  e.target.style.backgroundColor = '#f1f5f9';
                  e.target.style.borderColor = '#cbd5e1';
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
        <main className="product-main" style={{
          flex: 1, 
          display: 'flex', 
          flexDirection: 'column', 
          alignItems: 'center', 
          padding: '2rem',
          background: 'transparent'
        }}>
          <WorkspaceHeader
            eyebrow="Pool control room"
            title="Your pools, one clear view"
            description="See what needs a pick, what is locked, and where every entry stands this week."
            meta={user?.email}
          />
          <h1 className="legacy-page-title" style={{
            fontSize: '3rem', 
            fontWeight: '800', 
            marginBottom: '1rem', 
            color: '#1e293b',
            textAlign: 'center'
          }}>
            Dashboard
          </h1>
          
          {/* Leagues Section */}
          <div className="product-panel dashboard-pools" style={{
            background: 'white', 
            borderRadius: '12px', 
            padding: '2rem',
            maxWidth: '1400px',
            width: '100%',
            boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)',
            border: '1px solid #e2e8f0'
          }}>
            <div style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              marginBottom: '2rem'
            }}>
              <h2 className="section-title" style={{
                fontSize: '2rem', 
                fontWeight: '700', 
                color: '#1a202c',
                margin: 0
              }}>
                My Pools
              </h2>
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
                  You haven't joined any pools yet. Browse the Pool Directory to join one.
                </p>
                <button
                  type="button"
                  onClick={() => router.push('/leagues')}
                  style={{
                    marginLeft: '0.75rem',
                    backgroundColor: '#84cc16',
                    color: '#17210b',
                    padding: '0.75rem 2rem',
                    border: 'none',
                    borderRadius: '8px',
                    fontSize: '1rem',
                    fontWeight: '700',
                    cursor: 'pointer'
                  }}
                >
                  Browse Pools
                </button>
              </div>
            ) : (
              <>
                {leagues.length > 1 && (
                  <div style={{
                    backgroundColor: '#f0f9ff',
                    border: '1px solid #bfdbfe',
                    borderRadius: '8px',
                    padding: '0.75rem',
                    marginBottom: '1.5rem',
                    textAlign: 'center',
                    fontSize: '0.875rem',
                    color: '#1e40af'
                  }}>
                    💡 <strong>Tip:</strong> You can drag and drop the pool tiles to rearrange them in your preferred order!
                  </div>
                )}
                <div className="pool-card-grid" style={{
                  display: 'grid', 
                  gap: '2rem', 
                  gridTemplateColumns: 'repeat(auto-fit, minmax(min(350px, 100%), 1fr))',
                  width: '100%',
                  padding: '0'
                }}>
                {getOrderedPools().map(league => (
                  <div className={`pool-card${draggedPoolId === league.id ? ' pool-card--dragging' : ''}`}
                    key={league.id} 
                    draggable
                    onDragStart={(e) => handleDragStart(e, league.id)}
                    onDragEnd={handleDragEnd}
                    onDragOver={handleDragOver}
                    onDragLeave={handleDragLeave}
                    onDrop={(e) => handleDrop(e, league.id)}
                    style={{ 
                      border: draggedPoolId === league.id ? '2px dashed #3b82f6' : '1px solid #e5e7eb', 
                      borderRadius: '12px', 
                      padding: '1.5rem',
                      backgroundColor: '#fafafa',
                      transition: 'all 0.2s ease',
                      boxShadow: '0 2px 8px rgba(0, 0, 0, 0.05)',
                      minWidth: '0',
                      minHeight: '280px',
                      position: 'relative',
                      display: 'flex',
                      flexDirection: 'column',
                      cursor: 'move'
                    }}
                    onMouseEnter={(e) => {
                      if (draggedPoolId !== league.id) {
                        e.target.style.boxShadow = '0 8px 25px rgba(0, 0, 0, 0.1)';
                        e.target.style.transform = 'translateY(-2px)';
                      }
                    }}
                    onMouseLeave={(e) => {
                      if (draggedPoolId !== league.id) {
                        e.target.style.boxShadow = '0 2px 8px rgba(0, 0, 0, 0.05)';
                        e.target.style.transform = 'translateY(0)';
                      }
                    }}
                  >
                    {/* Drag Handle - Top Left */}
                    <div className="pool-card__drag" style={{
                      position: 'absolute',
                      top: '0.75rem',
                      left: '0.75rem',
                      color: '#9ca3af',
                      fontSize: '1rem',
                      cursor: 'move',
                      padding: '0.5rem',
                      borderRadius: '6px',
                      transition: 'all 0.2s ease',
                      backgroundColor: 'rgba(255, 255, 255, 0.8)',
                      border: '1px solid rgba(156, 163, 175, 0.3)',
                      lineHeight: '1',
                      userSelect: 'none'
                    }}
                    onMouseEnter={(e) => {
                      e.target.style.color = '#6b7280';
                      e.target.style.backgroundColor = 'rgba(255, 255, 255, 1)';
                      e.target.style.borderColor = 'rgba(107, 114, 128, 0.5)';
                    }}
                    onMouseLeave={(e) => {
                      e.target.style.color = '#9ca3af';
                      e.target.style.backgroundColor = 'rgba(255, 255, 255, 0.8)';
                      e.target.style.borderColor = 'rgba(156, 163, 175, 0.3)';
                    }}
                    title="Drag to reorder pools"
                    >
                      ⋮⋮
                    </div>

                    {/* Privacy Badge - Top Right */}
                    <span className={`pool-card__privacy pool-card__privacy--${league.is_private ? 'private' : 'public'}`} style={{
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
                    
                    <h3 className="pool-card__title" style={{
                      fontSize: '1.25rem', 
                      fontWeight: '700', 
                      marginBottom: '0.5rem', 
                      color: '#1a202c' 
                    }}>
                      {league.name}
                    </h3>
                    
                    {/* Action Buttons */}
                    <div className="pool-card__actions" style={{
                      display: 'grid', 
                      gridTemplateColumns: isMobile ? '1fr 1fr' : 'repeat(auto-fit, minmax(120px, 1fr))', 
                      gap: '0.75rem', 
                      marginBottom: '1rem' 
                    }}>
                      <button className="pool-card__action pool-card__action--primary"
                        onClick={() => router.push(`/pool/${league.id}/entries`)}
                        style={{ 
                          backgroundColor: '#8b5cf6', 
                          color: 'white', 
                          padding: '0.75rem 1rem', 
                          border: 'none', 
                          borderRadius: '6px', 
                          cursor: 'pointer',
                          fontSize: '0.875rem',
                          fontWeight: '500',
                          transition: 'all 0.2s ease',
                          minHeight: '44px',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          textAlign: 'center'
                        }}
                        onMouseEnter={(e) => e.target.style.backgroundColor = '#7c3aed'}
                        onMouseLeave={(e) => e.target.style.backgroundColor = '#8b5cf6'}
                      >
                        My Entries
                      </button>
                      <button className="pool-card__action"
                        onClick={() => router.push(`/pool/${league.id}`)}
                        style={{ 
                          backgroundColor: '#10b981', 
                          color: 'white', 
                          padding: '0.75rem 1rem', 
                          border: 'none', 
                          borderRadius: '6px', 
                          cursor: 'pointer',
                          fontSize: '0.875rem',
                          fontWeight: '500',
                          transition: 'all 0.2s ease',
                          minHeight: '44px',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          textAlign: 'center'
                        }}
                        onMouseEnter={(e) => e.target.style.backgroundColor = '#059669'}
                        onMouseLeave={(e) => e.target.style.backgroundColor = '#10b981'}
                      >
                        Pool Home
                      </button>
                      <button className="pool-card__action"
                        onClick={() => router.push(`/pool/${league.id}/messages`)}
                        style={{ 
                          backgroundColor: '#3b82f6', 
                          color: 'white', 
                          padding: '0.75rem 1rem', 
                          border: 'none', 
                          borderRadius: '6px', 
                          cursor: 'pointer',
                          fontSize: '0.875rem',
                          fontWeight: '500',
                          transition: 'all 0.2s ease',
                          minHeight: '44px',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          textAlign: 'center'
                        }}
                        onMouseEnter={(e) => e.target.style.backgroundColor = '#2563eb'}
                        onMouseLeave={(e) => e.target.style.backgroundColor = '#3b82f6'}
                      >
                        Forum
                      </button>
                      {(poolAdminStatus[league.id]?.has_admin_access || league.created_by === user.id) && (
                        <button className="pool-card__action pool-card__action--admin"
                          onClick={() => router.push(`/admin/league/${league.id}`)}
                          style={{ 
                            backgroundColor: '#f59e0b', 
                            color: 'white', 
                            padding: '0.75rem 1rem', 
                            border: 'none', 
                            borderRadius: '6px', 
                            cursor: 'pointer',
                            fontSize: '0.875rem',
                            fontWeight: '500',
                            transition: 'all 0.2s ease',
                            minHeight: '44px',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            textAlign: 'center'
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
                    
                    {/* Week Selector Section */}
                    <div style={{ 
                      marginBottom: '1rem',
                      width: '100%',
                      overflow: 'hidden'
                    }}>
                      {renderWeekSelector(league)}
                    </div>
                  </div>
                ))}
                </div>
              </>
            )}
          </div>
        </main>
      </div>
    </ProtectedRoute>
  );
}
