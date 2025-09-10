import { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import ProtectedRoute from '../../../components/ProtectedRoute';
import { useAuth } from '../../../context/AuthContext';

// Mock NFL team data - in production this would come from an API
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

// Mock matchups for week 1
const MOCK_MATCHUPS = {
  1: [
    { home: 'KC', away: 'BAL', time: '8:20 PM ET', date: '09/05' },
    { home: 'ATL', away: 'PHI', time: '1:00 PM ET', date: '09/08' },
    { home: 'CIN', away: 'NE', time: '1:00 PM ET', date: '09/08' },
    { home: 'HOU', away: 'IND', time: '1:00 PM ET', date: '09/08' },
    { home: 'JAX', away: 'MIA', time: '1:00 PM ET', date: '09/08' },
    { home: 'NO', away: 'CAR', time: '1:00 PM ET', date: '09/08' },
    { home: 'PIT', away: 'SF', time: '1:00 PM ET', date: '09/08' },
    { home: 'TEN', away: 'CHI', time: '1:00 PM ET', date: '09/08' },
    { home: 'CLE', away: 'DAL', time: '4:25 PM ET', date: '09/08' },
    { home: 'GB', away: 'MIN', time: '4:25 PM ET', date: '09/08' },
    { home: 'LAR', away: 'DET', time: '8:20 PM ET', date: '09/08' },
    { home: 'TB', away: 'WAS', time: '4:25 PM ET', date: '09/08' },
    { home: 'BUF', away: 'NYJ', time: '8:15 PM ET', date: '09/09' },
    { home: 'LAC', away: 'LV', time: '4:05 PM ET', date: '09/08' },
    { home: 'NYG', away: 'ARI', time: '4:25 PM ET', date: '09/08' },
    { home: 'SEA', away: 'DEN', time: '4:05 PM ET', date: '09/08' }
  ]
};

export default function LeagueEntries() {
  const [league, setLeague] = useState(null);
  const [entries, setEntries] = useState([]);
  const [allPicks, setAllPicks] = useState({});
  const [scheduleData, setScheduleData] = useState({}); // Store schedule data by week
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [selectedWeek, setSelectedWeek] = useState(null);
  const [selectedEntry, setSelectedEntry] = useState(null);
  const [showMatchupOverlay, setShowMatchupOverlay] = useState(false);
  const [selectedTeam, setSelectedTeam] = useState(null);
  const [editingEntryId, setEditingEntryId] = useState(null);
  const [editingEntryName, setEditingEntryName] = useState('');
  const [showAccountMenu, setShowAccountMenu] = useState(false); // Track account dropdown state
  const router = useRouter();
  const { user } = useAuth();
  const { id } = router.query;

  useEffect(() => {
    if (id && user) {
      fetchLeagueAndEntries();
    }
  }, [id, user]);

  // Add escape key listener for closing overlay
  useEffect(() => {
    const handleEscapeKey = (event) => {
      if (event.key === 'Escape' && showMatchupOverlay) {
        setShowMatchupOverlay(false);
      }
    };

    document.addEventListener('keydown', handleEscapeKey);
    return () => {
      document.removeEventListener('keydown', handleEscapeKey);
    };
  }, [showMatchupOverlay]);

  // Close account menu when clicking outside or pressing escape
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (showAccountMenu && !event.target.closest('[data-account-menu]')) {
        setShowAccountMenu(false);
      }
    };

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

  const handleLogout = () => {
    localStorage.removeItem('access_token');
    router.push('/login');
  };

  const fetchLeagueAndEntries = async () => {
    try {
      const token = localStorage.getItem('access_token');
      
      // Fetch league details
      const leagueRes = await fetch(process.env.NEXT_PUBLIC_API_URL + `/pools/${id}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (leagueRes.ok) {
        const leagueData = await leagueRes.json();
        setLeague(leagueData);
      } else {
        setError('Failed to load league details');
        return;
      }

      // Fetch user's entries for this league
      const entriesRes = await fetch(process.env.NEXT_PUBLIC_API_URL + `/entries/pool/${id}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (entriesRes.ok) {
        const entriesData = await entriesRes.json();
        console.log('Fetched entries:', entriesData);
        setEntries(entriesData);
        
        // Fetch picks for all entries sequentially to avoid race conditions
        const picksData = {};
        for (const entry of entriesData) {
          try {
            const picksRes = await fetch(process.env.NEXT_PUBLIC_API_URL + `/picks/entry/${entry.id}`, {
              headers: { 'Authorization': `Bearer ${token}` }
            });
            if (picksRes.ok) {
              const picks = await picksRes.json();
              console.log(`Fetched picks for entry ${entry.id}:`, picks);
              picksData[entry.id] = picks;
            } else {
              console.log(`No picks found for entry ${entry.id}`);
              picksData[entry.id] = [];
            }
          } catch (err) {
            console.error(`Failed to fetch picks for entry ${entry.id}:`, err);
            picksData[entry.id] = [];
          }
        }
        console.log('All picks data:', picksData);
        
        // Check specifically for Entry 1 picks before setting state
        const entry1 = entriesData.find(e => e.name === 'Entry 1');
        if (entry1) {
          console.log('Entry 1 picks before setState:', picksData[entry1.id]);
        }
        
        setAllPicks(picksData);
      } else {
        setEntries([]);
        setAllPicks({});
      }
    } catch (err) {
      console.error('Failed to load data:', err);
      setError('Failed to load data');
    } finally {
      setLoading(false);
    }
  };

  const fetchScheduleForWeek = async (week) => {
    // Return early if we already have this week's data
    if (scheduleData[week]) {
      return scheduleData[week];
    }

    try {
      const token = localStorage.getItem('access_token');
      const res = await fetch(process.env.NEXT_PUBLIC_API_URL + `/schedule/week/${week}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (res.ok) {
        const weekSchedule = await res.json();
        console.log(`Fetched schedule for week ${week}:`, weekSchedule);
        
        // Store in state
        setScheduleData(prev => ({
          ...prev,
          [week]: weekSchedule
        }));
        
        return weekSchedule;
      } else {
        console.error(`Failed to fetch schedule for week ${week}`);
        return [];
      }
    } catch (err) {
      console.error(`Error fetching schedule for week ${week}:`, err);
      return [];
    }
  };

  const handlePickClick = async (entry, week) => {
    setSelectedEntry(entry);
    setSelectedWeek(week);
    setSelectedTeam(null);
    
    // Fetch schedule data for this week if we don't have it
    await fetchScheduleForWeek(week);
    setShowMatchupOverlay(true);
  };

  const handleTeamSelect = (team) => {
    setSelectedTeam(team);
  };

  const handleSubmitPick = async () => {
    if (!selectedTeam || !selectedWeek || !selectedEntry) return;

    console.log('Submitting pick:', {
      team: selectedTeam,
      week: selectedWeek,
      entry: selectedEntry.name,
      entryId: selectedEntry.id
    });

    try {
      const token = localStorage.getItem('access_token');
      const res = await fetch(process.env.NEXT_PUBLIC_API_URL + '/picks/create', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          entry_id: selectedEntry.id,
          week: selectedWeek,
          team: selectedTeam
        })
      });

      if (res.ok) {
        const newPick = await res.json();
        console.log('Pick created successfully:', newPick);
        
        // Update the picks state incrementally instead of refetching all data
        setAllPicks(prevPicks => ({
          ...prevPicks,
          [selectedEntry.id]: [
            ...(prevPicks[selectedEntry.id] || []).filter(p => p.week !== selectedWeek),
            newPick
          ]
        }));
        
        setShowMatchupOverlay(false);
      } else {
        const errorData = await res.json();
        console.error('Failed to create pick:', errorData);
        setError(errorData.detail || 'Failed to save pick');
      }
    } catch (err) {
      console.error('Failed to save pick:', err);
      setError('Failed to save pick');
    }
  };

  const getPickForEntryWeek = (entryId, week) => {
    const picks = allPicks[entryId] || [];
    const pick = picks.find(pick => pick.week === week);
    if (entryId && week === 1) {
      console.log(`Getting pick for entry ${entryId}, week ${week}:`, pick, 'from picks:', picks);
    }
    return pick;
  };

  const getUsedTeamsForEntry = (entryId) => {
    const picks = allPicks[entryId] || [];
    return picks.map(pick => pick.team);
  };

  const handleStartEditingEntryName = (entry) => {
    setEditingEntryId(entry.id);
    setEditingEntryName(entry.name);
  };

  const handleCancelEditingEntryName = () => {
    setEditingEntryId(null);
    setEditingEntryName('');
  };

  const handleSaveEntryName = async (entryId) => {
    if (!editingEntryName.trim()) {
      setError('Entry name cannot be empty');
      return;
    }

    try {
      const token = localStorage.getItem('access_token');
      const res = await fetch(process.env.NEXT_PUBLIC_API_URL + `/entries/${entryId}`, {
        method: 'PUT',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          name: editingEntryName.trim()
        })
      });

      if (res.ok) {
        setEditingEntryId(null);
        setEditingEntryName('');
        fetchLeagueAndEntries(); // Refresh all data
      } else {
        const errorData = await res.json();
        setError(errorData.detail || 'Failed to update entry name');
      }
    } catch (err) {
      console.error('Failed to update entry name:', err);
      setError('Failed to update entry name');
    }
  };

  const handleEntryNameKeyPress = (e, entryId) => {
    if (e.key === 'Enter') {
      handleSaveEntryName(entryId);
    } else if (e.key === 'Escape') {
      handleCancelEditingEntryName();
    }
  };

  const renderPickCircle = (entry, week) => {
    const pick = getPickForEntryWeek(entry.id, week);
    const hasTeam = pick && pick.team;
    
    if (entry.name === 'Entry 1' && week === 1) {
      console.log(`Rendering circle for Entry 1, Week 1:`, { pick, hasTeam, allPicks: allPicks[entry.id] });
    }

    return (
      <button
        key={week}
        onClick={() => handlePickClick(entry, week)}
        style={{
          width: '50px',
          height: '50px',
          borderRadius: '50%',
          border: '2px solid #ddd',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          cursor: 'pointer',
          backgroundColor: hasTeam ? '#ffffff' : '#f9f9f9',
          color: hasTeam ? '#333' : '#333',
          fontWeight: 'bold',
          fontSize: hasTeam ? '10px' : '12px',
          transition: 'all 0.2s ease',
          margin: '2px auto',
          position: 'relative',
          overflow: 'hidden'
        }}
        onMouseEnter={(e) => {
          e.target.style.transform = 'scale(1.1)';
          e.target.style.boxShadow = '0 2px 8px rgba(0,0,0,0.2)';
        }}
        onMouseLeave={(e) => {
          e.target.style.transform = 'scale(1)';
          e.target.style.boxShadow = 'none';
        }}
      >
        {hasTeam ? (
          <div style={{ 
            display: 'flex', 
            flexDirection: 'column', 
            alignItems: 'center',
            justifyContent: 'center' 
          }}>
            <img 
              src={`/nfl/${NFL_TEAMS[pick.team]?.logo}`} 
              alt={`${pick.team} logo`}
              style={{ 
                width: '24px', 
                height: '24px',
                marginBottom: '2px'
              }}
            />
            <span style={{ fontSize: '8px', lineHeight: '1' }}>{pick.team}</span>
          </div>
        ) : (
          week
        )}
      </button>
    );
  };

  const getTeamButtonStyle = (team, isSelected, isUsed) => {
    let backgroundColor = 'white';
    if (isUsed) {
      backgroundColor = '#f5f5f5';
    } else if (isSelected) {
      backgroundColor = '#e6f3ff';
    }

    return {
      padding: '12px 16px',
      border: isSelected ? '2px solid #0070f3' : '1px solid #ddd',
      borderRadius: '8px',
      backgroundColor,
      color: isUsed ? '#999' : '#333',
      cursor: isUsed ? 'not-allowed' : 'pointer',
      flex: 1,
      textAlign: 'left',
      display: 'flex',
      alignItems: 'center',
      gap: '8px',
      transition: 'all 0.2s ease'
    };
  };

  const renderMatchupOverlay = () => {
    if (!showMatchupOverlay || !selectedWeek || !selectedEntry) return null;

    // Use real schedule data instead of mock data
    const weekSchedule = scheduleData[selectedWeek] || [];
    const usedTeams = getUsedTeamsForEntry(selectedEntry.id);

    // Helper function to format date and time
    const formatGameTime = (startTime) => {
      if (!startTime) return { date: 'TBD', time: 'TBD' };
      
      try {
        const gameDate = new Date(startTime);
        const date = gameDate.toLocaleDateString('en-US', { month: '2-digit', day: '2-digit' });
        const time = gameDate.toLocaleTimeString('en-US', { 
          hour: 'numeric', 
          minute: '2-digit',
          timeZoneName: 'short'
        });
        return { date, time };
      } catch (err) {
        return { date: 'TBD', time: 'TBD' };
      }
    };

    return (
      <div style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'rgba(0,0,0,0.7)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 1000
      }}>
        <div style={{
          backgroundColor: 'white',
          borderRadius: '12px',
          maxWidth: '600px',
          maxHeight: '80vh',
          width: '90%',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden'
        }}>
          {/* Header */}
          <div style={{ padding: '2rem 2rem 1rem 2rem' }}>
            <h2>Week {selectedWeek} Matchups - {selectedEntry.name}</h2>
            <p style={{ color: '#666', marginBottom: '0' }}>
              Select a team for your pick. Teams you've already used are grayed out.
            </p>
          </div>

          {/* Scrollable Content */}
          <div style={{ 
            flex: 1, 
            overflowY: 'auto', 
            padding: '0 2rem',
            maxHeight: 'calc(80vh - 160px)' 
          }}>
            <div style={{ display: 'grid', gap: '1rem', paddingBottom: '1rem' }}>
              {weekSchedule.length === 0 ? (
                <div style={{ textAlign: 'center', color: '#666', padding: '2rem' }}>
                  No games scheduled for this week yet.
                </div>
              ) : (
                weekSchedule.map((game) => {
                  const gameTime = formatGameTime(game.start_time);
                  const awayTeam = game.away_team;
                  const homeTeam = game.home_team;
                  
                  return (
                    <div key={game.game_id} style={{
                      border: '1px solid #ddd',
                      borderRadius: '8px',
                      padding: '1rem',
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center'
                    }}>
                      <div style={{ display: 'flex', gap: '1rem', alignItems: 'center', flex: 1 }}>
                        <button
                          onClick={() => handleTeamSelect(awayTeam.abbrv)}
                          disabled={usedTeams.includes(awayTeam.abbrv)}
                          style={getTeamButtonStyle(awayTeam.abbrv, selectedTeam === awayTeam.abbrv, usedTeams.includes(awayTeam.abbrv))}
                        >
                          <img 
                            src={awayTeam.logo} 
                            alt={`${awayTeam.abbrv} logo`}
                            style={{ width: '24px', height: '24px' }}
                          />
                          <div>
                            <div style={{ fontWeight: 'bold', fontSize: '14px' }}>{awayTeam.abbrv}</div>
                            <div style={{ fontSize: '12px', color: '#666' }}>{awayTeam.name}</div>
                          </div>
                        </button>
                        <span style={{ color: '#666', fontWeight: 'bold' }}>@</span>
                        <button
                          onClick={() => handleTeamSelect(homeTeam.abbrv)}
                          disabled={usedTeams.includes(homeTeam.abbrv)}
                          style={getTeamButtonStyle(homeTeam.abbrv, selectedTeam === homeTeam.abbrv, usedTeams.includes(homeTeam.abbrv))}
                        >
                          <img 
                            src={homeTeam.logo} 
                            alt={`${homeTeam.abbrv} logo`}
                            style={{ width: '24px', height: '24px' }}
                          />
                          <div>
                            <div style={{ fontWeight: 'bold', fontSize: '14px' }}>{homeTeam.abbrv}</div>
                            <div style={{ fontSize: '12px', color: '#666' }}>{homeTeam.name}</div>
                          </div>
                        </button>
                      </div>
                      <div style={{ marginLeft: '1rem', color: '#666', fontSize: '14px', textAlign: 'right' }}>
                        <div>{gameTime.date}</div>
                        <div>{gameTime.time}</div>
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </div>

          {/* Sticky Footer with Buttons */}
          <div style={{ 
            padding: '1rem 2rem 2rem 2rem',
            borderTop: '1px solid #e5e7eb',
            backgroundColor: 'white',
            borderRadius: '0 0 12px 12px',
            display: 'flex', 
            gap: '1rem', 
            justifyContent: 'flex-end'
          }}>
            <button
              onClick={() => setShowMatchupOverlay(false)}
              style={{
                padding: '12px 24px',
                border: '1px solid #ddd',
                borderRadius: '8px',
                backgroundColor: 'white',
                cursor: 'pointer',
                fontSize: '14px',
                fontWeight: '600',
                transition: 'all 0.2s ease'
              }}
              onMouseEnter={(e) => {
                e.target.style.backgroundColor = '#f8f9fa';
                e.target.style.borderColor = '#adb5bd';
              }}
              onMouseLeave={(e) => {
                e.target.style.backgroundColor = 'white';
                e.target.style.borderColor = '#ddd';
              }}
            >
              Cancel
            </button>
            <button
              onClick={handleSubmitPick}
              disabled={!selectedTeam}
              style={{
                padding: '12px 24px',
                border: 'none',
                borderRadius: '8px',
                backgroundColor: selectedTeam ? '#0070f3' : '#ccc',
                color: 'white',
                cursor: selectedTeam ? 'pointer' : 'not-allowed',
                fontSize: '14px',
                fontWeight: '600',
                transition: 'all 0.2s ease',
                boxShadow: selectedTeam ? '0 2px 8px rgba(0, 112, 243, 0.3)' : 'none'
              }}
              onMouseEnter={(e) => {
                if (selectedTeam) {
                  e.target.style.backgroundColor = '#0056b3';
                  e.target.style.transform = 'translateY(-1px)';
                  e.target.style.boxShadow = '0 4px 12px rgba(0, 112, 243, 0.4)';
                }
              }}
              onMouseLeave={(e) => {
                if (selectedTeam) {
                  e.target.style.backgroundColor = '#0070f3';
                  e.target.style.transform = 'translateY(0)';
                  e.target.style.boxShadow = '0 2px 8px rgba(0, 112, 243, 0.3)';
                }
              }}
            >
              Save Pick
            </button>
          </div>
        </div>
      </div>
    );
  };

  const handleCreateEntry = async () => {
    try {
      const token = localStorage.getItem('access_token');
      
      // Generate default entry name: "Entry " + entry count
      const entryCount = entries.length + 1;
      const defaultName = `Entry ${entryCount}`;
      
      const res = await fetch(process.env.NEXT_PUBLIC_API_URL + '/entries/create', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          name: defaultName,
          pool_id: id
        })
      });

      if (res.ok) {
        const newEntry = await res.json();
        console.log('Created new entry:', newEntry);
        
        // Add the new entry to the existing entries
        setEntries(prevEntries => [...prevEntries, newEntry]);
        
        // Initialize picks for the new entry as empty
        setAllPicks(prevPicks => ({
          ...prevPicks,
          [newEntry.id]: []
        }));
      } else {
        const errorData = await res.json();
        setError(errorData.detail || 'Failed to create entry');
      }
    } catch (err) {
      console.error('Failed to create entry:', err);
      setError('Failed to create entry');
    }
  };

  const handleDeleteLastEntry = async () => {
    if (entries.length === 0) {
      setError('No entries to delete');
      return;
    }

    // Find the most recently created entry (highest created_at timestamp)
    const lastEntry = entries.reduce((latest, current) => {
      return new Date(current.created_at) > new Date(latest.created_at) ? current : latest;
    });

    try {
      const token = localStorage.getItem('access_token');
      const res = await fetch(process.env.NEXT_PUBLIC_API_URL + `/entries/${lastEntry.id}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (res.ok) {
        fetchLeagueAndEntries(); // Refresh the list
      } else {
        const errorData = await res.json();
        setError(errorData.detail || 'Failed to delete entry');
      }
    } catch (err) {
      console.error('Failed to delete entry:', err);
      setError('Failed to delete entry');
    }
  };

  if (!router.isReady || loading) {
    return (
      <div style={{ 
        minHeight: '100vh', 
        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center'
      }}>
        <div style={{ 
          color: 'white',
          fontSize: '1.5rem',
          fontWeight: '600',
          textShadow: '0 2px 4px rgba(0, 0, 0, 0.5)'
        }}>
          Loading...
        </div>
      </div>
    );
  }

  return (
    <ProtectedRoute>
      <div style={{ 
        minHeight: '100vh', 
        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        display: 'flex',
        flexDirection: 'column'
      }}>
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
          maxWidth: '1400px', 
          margin: '0 auto',
          padding: '2rem'
        }}>
          {/* Header */}
          <div style={{ 
            textAlign: 'center',
            marginBottom: '2rem'
          }}>
            <h1 style={{ 
              fontSize: '3rem', 
              fontWeight: '800', 
              marginBottom: '1rem', 
              color: 'white',
              textShadow: '0 4px 8px rgba(0, 0, 0, 0.5)'
            }}>
              {league?.name} - Entries
            </h1>
            <p style={{ 
              color: 'rgba(255, 255, 255, 0.9)',
              fontSize: '1.2rem',
              fontWeight: '400',
              margin: 0
            }}>
              Click on any week circle to make or change picks
            </p>
          </div>

          {/* Main Content Card */}
          <div style={{ 
            background: 'white', 
            borderRadius: '20px', 
            padding: '2.5rem',
            boxShadow: '0 20px 40px rgba(0, 0, 0, 0.15)',
            border: '1px solid rgba(255, 255, 255, 0.2)'
          }}>
            {/* Error Message */}
            {error && (
              <div style={{ 
                backgroundColor: '#fed7d7',
                color: '#742a2a',
                padding: '0.75rem 1rem',
                borderRadius: '8px',
                marginBottom: '2rem',
                border: '1px solid #fc8181',
                fontSize: '0.875rem'
              }}>
                {typeof error === 'string' ? error : JSON.stringify(error)}
              </div>
            )}

            {/* Action Buttons */}
            <div style={{ 
              marginBottom: '2rem', 
              display: 'flex', 
              gap: '1rem', 
              flexWrap: 'wrap'
            }}>
              <button 
                onClick={handleCreateEntry}
                style={{ 
                  backgroundColor: '#667eea', 
                  color: 'white', 
                  padding: '0.75rem 1.5rem', 
                  border: 'none', 
                  borderRadius: '8px', 
                  cursor: 'pointer',
                  fontSize: '1rem',
                  fontWeight: '600',
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
                Create New Entry
              </button>
              {entries.length > 0 && (
                <button 
                  onClick={handleDeleteLastEntry}
                  style={{ 
                    backgroundColor: '#e53e3e', 
                    color: 'white', 
                    padding: '0.75rem 1.5rem', 
                    border: 'none', 
                    borderRadius: '8px', 
                    cursor: 'pointer',
                    fontSize: '1rem',
                    fontWeight: '600',
                    transition: 'all 0.2s ease',
                    boxShadow: '0 4px 12px rgba(229, 62, 62, 0.4)'
                  }}
                  onMouseEnter={(e) => {
                    e.target.style.backgroundColor = '#c53030';
                    e.target.style.transform = 'translateY(-1px)';
                    e.target.style.boxShadow = '0 6px 16px rgba(229, 62, 62, 0.5)';
                  }}
                  onMouseLeave={(e) => {
                    e.target.style.backgroundColor = '#e53e3e';
                    e.target.style.transform = 'translateY(0)';
                    e.target.style.boxShadow = '0 4px 12px rgba(229, 62, 62, 0.4)';
                  }}
                >
                  Delete Entry
                </button>
              )}
            </div>

        {entries.length === 0 ? (
          <div style={{
            textAlign: 'center',
            padding: '4rem 2rem',
            backgroundColor: 'white',
            borderRadius: '16px',
            border: '2px dashed #e2e8f0',
            boxShadow: '0 8px 32px rgba(102, 126, 234, 0.1)',
            background: 'linear-gradient(135deg, rgba(255,255,255,0.9) 0%, rgba(248,250,252,0.9) 100%)'
          }}>
            <div style={{
              fontSize: '3rem',
              marginBottom: '1rem',
              background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
              backgroundClip: 'text'
            }}>
              📋
            </div>
            <h3 style={{
              color: '#2d3748',
              fontSize: '1.5rem',
              fontWeight: '600',
              marginBottom: '0.5rem'
            }}>No entries yet</h3>
            <p style={{ 
              color: '#718096', 
              marginBottom: '2rem',
              fontSize: '1.1rem',
              lineHeight: '1.6'
            }}>
              You haven't created any entries for this pool yet.
            </p>
            <button 
              onClick={handleCreateEntry}
              style={{ 
                background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                color: 'white', 
                padding: '1rem 2rem', 
                border: 'none', 
                borderRadius: '12px', 
                cursor: 'pointer',
                fontSize: '1.1rem',
                fontWeight: '600',
                transition: 'all 0.3s ease',
                boxShadow: '0 8px 24px rgba(102, 126, 234, 0.4)',
                textTransform: 'none',
                letterSpacing: '0.5px'
              }}
              onMouseEnter={(e) => {
                e.target.style.transform = 'translateY(-2px)';
                e.target.style.boxShadow = '0 12px 32px rgba(102, 126, 234, 0.5)';
              }}
              onMouseLeave={(e) => {
                e.target.style.transform = 'translateY(0)';
                e.target.style.boxShadow = '0 8px 24px rgba(102, 126, 234, 0.4)';
              }}
            >
              Create Your First Entry
            </button>
          </div>
        ) : (
          <div style={{ 
            overflowX: 'auto',
            borderRadius: '12px',
            boxShadow: '0 8px 32px rgba(102, 126, 234, 0.15)',
            backgroundColor: 'white'
          }}>
            <table style={{ 
              width: '100%', 
              borderCollapse: 'collapse',
              backgroundColor: 'white',
              borderRadius: '12px',
              overflow: 'hidden'
            }}>
              <thead>
                <tr style={{ 
                  background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                  color: 'white'
                }}>
                  <th style={{ 
                    padding: '16px 20px', 
                    textAlign: 'left', 
                    fontWeight: '600',
                    fontSize: '14px',
                    letterSpacing: '0.5px',
                    textTransform: 'uppercase'
                  }}>Entry Name</th>
                  {Array.from({ length: 18 }, (_, i) => i + 1).map(week => (
                    <th key={week} style={{ 
                      padding: '16px 12px', 
                      textAlign: 'center', 
                      fontWeight: '600',
                      fontSize: '12px',
                      letterSpacing: '0.5px',
                      textTransform: 'uppercase',
                      minWidth: '55px'
                    }}>
                      W{week}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {entries
                  .sort((a, b) => a.name.localeCompare(b.name))
                  .map((entry, index) => (
                  <tr key={entry.id} style={{ 
                    borderBottom: '1px solid #f1f3f4',
                    backgroundColor: index % 2 === 0 ? '#ffffff' : '#fafbfc',
                    transition: 'all 0.2s ease'
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.backgroundColor = '#f8f9ff';
                    e.currentTarget.style.transform = 'scale(1.005)';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.backgroundColor = index % 2 === 0 ? '#ffffff' : '#fafbfc';
                    e.currentTarget.style.transform = 'scale(1)';
                  }}>
                    <td style={{ 
                      padding: '16px 20px', 
                      fontWeight: '600',
                      color: '#2d3748',
                      fontSize: '15px'
                    }}>
                      {editingEntryId === entry.id ? (
                        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                          <input
                            type="text"
                            value={editingEntryName}
                            onChange={(e) => setEditingEntryName(e.target.value)}
                            onKeyDown={(e) => handleEntryNameKeyPress(e, entry.id)}
                            onBlur={() => handleSaveEntryName(entry.id)}
                            autoFocus
                            style={{
                              border: '2px solid #667eea',
                              borderRadius: '8px',
                              padding: '8px 12px',
                              fontSize: '14px',
                              minWidth: '140px',
                              outline: 'none',
                              transition: 'all 0.2s ease',
                              backgroundColor: 'white'
                            }}
                          />
                          <button
                            onClick={() => handleSaveEntryName(entry.id)}
                            style={{
                              backgroundColor: '#48bb78',
                              color: 'white',
                              border: 'none',
                              borderRadius: '6px',
                              padding: '8px 12px',
                              cursor: 'pointer',
                              fontSize: '12px',
                              fontWeight: '600',
                              transition: 'all 0.2s ease',
                              boxShadow: '0 2px 8px rgba(72, 187, 120, 0.3)'
                            }}
                          >
                            ✓
                          </button>
                          <button
                            onClick={handleCancelEditingEntryName}
                            style={{
                              backgroundColor: '#e53e3e',
                              color: 'white',
                              border: 'none',
                              borderRadius: '6px',
                              padding: '8px 12px',
                              cursor: 'pointer',
                              fontSize: '12px',
                              fontWeight: '600',
                              transition: 'all 0.2s ease',
                              boxShadow: '0 2px 8px rgba(229, 62, 62, 0.3)'
                            }}
                          >
                            ✕
                          </button>
                        </div>
                      ) : (
                        <button 
                          onClick={() => handleStartEditingEntryName(entry)}
                          style={{ 
                            background: 'none',
                            border: 'none',
                            cursor: 'pointer',
                            padding: '8px 16px',
                            borderRadius: '8px',
                            transition: 'all 0.2s ease',
                            fontSize: 'inherit',
                            fontWeight: 'inherit',
                            fontFamily: 'inherit',
                            textAlign: 'left',
                            width: '100%'
                          }}
                          onMouseEnter={(e) => {
                            e.target.style.backgroundColor = '#f0f4ff';
                            e.target.style.transform = 'translateX(4px)';
                          }}
                          onMouseLeave={(e) => {
                            e.target.style.backgroundColor = 'transparent';
                            e.target.style.transform = 'translateX(0)';
                          }}
                          onFocus={(e) => e.target.style.backgroundColor = '#f0f4ff'}
                          onBlur={(e) => e.target.style.backgroundColor = 'transparent'}
                          title="Click to edit entry name"
                        >
                          {entry.name}
                        </button>
                      )}
                    </td>
                    {Array.from({ length: 18 }, (_, i) => i + 1).map(week => (
                      <td key={week} style={{ 
                        padding: '12px 8px', 
                        textAlign: 'center',
                        borderLeft: '1px solid #f1f3f4',
                        fontSize: '14px'
                      }}>
                        {renderPickCircle(entry, week)}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

            {/* Footer Navigation */}
            <div style={{ 
              marginTop: '2rem', 
              paddingTop: '2rem',
              borderTop: '1px solid #e5e7eb',
              textAlign: 'center'
            }}>
              <button 
                onClick={() => router.push('/dashboard')}
                style={{ 
                  backgroundColor: '#6b7280', 
                  color: 'white', 
                  padding: '0.75rem 1.5rem', 
                  border: 'none', 
                  borderRadius: '8px', 
                  cursor: 'pointer',
                  fontSize: '1rem',
                  fontWeight: '600',
                  transition: 'all 0.2s ease',
                  boxShadow: '0 4px 12px rgba(107, 114, 128, 0.4)'
                }}
                onMouseEnter={(e) => {
                  e.target.style.backgroundColor = '#4b5563';
                  e.target.style.transform = 'translateY(-1px)';
                  e.target.style.boxShadow = '0 6px 16px rgba(107, 114, 128, 0.5)';
                }}
                onMouseLeave={(e) => {
                  e.target.style.backgroundColor = '#6b7280';
                  e.target.style.transform = 'translateY(0)';
                  e.target.style.boxShadow = '0 4px 12px rgba(107, 114, 128, 0.4)';
                }}
              >
                Back to Dashboard
              </button>
            </div>

            {renderMatchupOverlay()}
          </div>
        </main>
      </div>
    </ProtectedRoute>
  );
}
