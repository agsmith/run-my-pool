import { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import ProtectedRoute from '../../../components/ProtectedRoute';
import { useAuth } from '../../../context/AuthContext';

// Mock NFL team data - in production this would come from an API
const NFL_TEAMS = {
  'ARI': { name: 'Arizona Cardinals', color: '#97233F' },
  'ATL': { name: 'Atlanta Falcons', color: '#A71930' },
  'BAL': { name: 'Baltimore Ravens', color: '#241773' },
  'BUF': { name: 'Buffalo Bills', color: '#00338D' },
  'CAR': { name: 'Carolina Panthers', color: '#0085CA' },
  'CHI': { name: 'Chicago Bears', color: '#0B162A' },
  'CIN': { name: 'Cincinnati Bengals', color: '#FB4F14' },
  'CLE': { name: 'Cleveland Browns', color: '#311D00' },
  'DAL': { name: 'Dallas Cowboys', color: '#003594' },
  'DEN': { name: 'Denver Broncos', color: '#FB4F14' },
  'DET': { name: 'Detroit Lions', color: '#0076B6' },
  'GB': { name: 'Green Bay Packers', color: '#203731' },
  'HOU': { name: 'Houston Texans', color: '#03202F' },
  'IND': { name: 'Indianapolis Colts', color: '#002C5F' },
  'JAX': { name: 'Jacksonville Jaguars', color: '#006778' },
  'KC': { name: 'Kansas City Chiefs', color: '#E31837' },
  'LV': { name: 'Las Vegas Raiders', color: '#000000' },
  'LAC': { name: 'Los Angeles Chargers', color: '#0080C6' },
  'LAR': { name: 'Los Angeles Rams', color: '#003594' },
  'MIA': { name: 'Miami Dolphins', color: '#008E97' },
  'MIN': { name: 'Minnesota Vikings', color: '#4F2683' },
  'NE': { name: 'New England Patriots', color: '#002244' },
  'NO': { name: 'New Orleans Saints', color: '#D3BC8D' },
  'NYG': { name: 'New York Giants', color: '#0B2265' },
  'NYJ': { name: 'New York Jets', color: '#125740' },
  'PHI': { name: 'Philadelphia Eagles', color: '#004C54' },
  'PIT': { name: 'Pittsburgh Steelers', color: '#FFB612' },
  'SF': { name: 'San Francisco 49ers', color: '#AA0000' },
  'SEA': { name: 'Seattle Seahawks', color: '#002244' },
  'TB': { name: 'Tampa Bay Buccaneers', color: '#D50A0A' },
  'TEN': { name: 'Tennessee Titans', color: '#0C2340' },
  'WAS': { name: 'Washington Commanders', color: '#5A1414' }
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
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [selectedWeek, setSelectedWeek] = useState(null);
  const [selectedEntry, setSelectedEntry] = useState(null);
  const [showMatchupOverlay, setShowMatchupOverlay] = useState(false);
  const [selectedTeam, setSelectedTeam] = useState(null);
  const [editingEntryId, setEditingEntryId] = useState(null);
  const [editingEntryName, setEditingEntryName] = useState('');
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
      const entriesRes = await fetch(process.env.NEXT_PUBLIC_API_URL + `/entries/league/${id}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (entriesRes.ok) {
        const entriesData = await entriesRes.json();
        setEntries(entriesData);
        
        // Fetch picks for all entries
        const picksData = {};
        for (const entry of entriesData) {
          try {
            const picksRes = await fetch(process.env.NEXT_PUBLIC_API_URL + `/picks/entry/${entry.id}`, {
              headers: { 'Authorization': `Bearer ${token}` }
            });
            if (picksRes.ok) {
              const picks = await picksRes.json();
              picksData[entry.id] = picks;
            } else {
              picksData[entry.id] = [];
            }
          } catch (err) {
            console.error(`Failed to fetch picks for entry ${entry.id}:`, err);
            picksData[entry.id] = [];
          }
        }
        setAllPicks(picksData);
      } else {
        setEntries([]);
      }
    } catch (err) {
      console.error('Failed to load data:', err);
      setError('Failed to load data');
    } finally {
      setLoading(false);
    }
  };

  const handlePickClick = (entry, week) => {
    setSelectedEntry(entry);
    setSelectedWeek(week);
    setSelectedTeam(null);
    setShowMatchupOverlay(true);
  };

  const handleTeamSelect = (team) => {
    setSelectedTeam(team);
  };

  const handleSubmitPick = async () => {
    if (!selectedTeam || !selectedWeek || !selectedEntry) return;

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
        setShowMatchupOverlay(false);
        fetchLeagueAndEntries(); // Refresh all data
      } else {
        const errorData = await res.json();
        setError(errorData.detail || 'Failed to save pick');
      }
    } catch (err) {
      console.error('Failed to save pick:', err);
      setError('Failed to save pick');
    }
  };

  const getPickForEntryWeek = (entryId, week) => {
    const picks = allPicks[entryId] || [];
    return picks.find(pick => pick.week === week);
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

    return (
      <button
        key={`${entry.id}-${week}`}
        onClick={() => handlePickClick(entry, week)}
        style={{
          width: '40px',
          height: '40px',
          borderRadius: '50%',
          border: '1px solid #ddd',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          cursor: 'pointer',
          backgroundColor: hasTeam ? NFL_TEAMS[pick.team]?.color || '#f0f0f0' : '#f9f9f9',
          color: hasTeam ? 'white' : '#333',
          fontWeight: 'bold',
          fontSize: hasTeam ? '10px' : '12px',
          transition: 'all 0.2s ease',
          margin: '2px'
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
        {hasTeam ? pick.team : week}
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
      padding: '8px 16px',
      border: isSelected ? '2px solid #0070f3' : '1px solid #ddd',
      borderRadius: '6px',
      backgroundColor,
      color: isUsed ? '#999' : '#333',
      cursor: isUsed ? 'not-allowed' : 'pointer',
      flex: 1,
      textAlign: 'center'
    };
  };

  const renderMatchupOverlay = () => {
    if (!showMatchupOverlay || !selectedWeek || !selectedEntry) return null;

    const matchups = MOCK_MATCHUPS[selectedWeek] || [];
    const usedTeams = getUsedTeamsForEntry(selectedEntry.id);

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
          padding: '2rem',
          maxWidth: '600px',
          maxHeight: '80vh',
          overflow: 'auto',
          width: '90%'
        }}>
          <h2>Week {selectedWeek} Matchups - {selectedEntry.name}</h2>
          <p style={{ color: '#666', marginBottom: '1.5rem' }}>
            Select a team for your pick. Teams you've already used are grayed out.
          </p>

          <div style={{ display: 'grid', gap: '1rem', marginBottom: '2rem' }}>
            {matchups.map((matchup) => (
              <div key={`${matchup.away}-${matchup.home}`} style={{
                border: '1px solid #ddd',
                borderRadius: '8px',
                padding: '1rem',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center'
              }}>
                <div style={{ display: 'flex', gap: '1rem', alignItems: 'center', flex: 1 }}>
                  <button
                    onClick={() => handleTeamSelect(matchup.away)}
                    disabled={usedTeams.includes(matchup.away)}
                    style={getTeamButtonStyle(matchup.away, selectedTeam === matchup.away, usedTeams.includes(matchup.away))}
                  >
                    {matchup.away} - {NFL_TEAMS[matchup.away]?.name}
                  </button>
                  <span style={{ color: '#666' }}>@</span>
                  <button
                    onClick={() => handleTeamSelect(matchup.home)}
                    disabled={usedTeams.includes(matchup.home)}
                    style={getTeamButtonStyle(matchup.home, selectedTeam === matchup.home, usedTeams.includes(matchup.home))}
                  >
                    {matchup.home} - {NFL_TEAMS[matchup.home]?.name}
                  </button>
                </div>
                <div style={{ marginLeft: '1rem', color: '#666', fontSize: '14px', textAlign: 'right' }}>
                  <div>{matchup.date}</div>
                  <div>{matchup.time}</div>
                </div>
              </div>
            ))}
          </div>

          <div style={{ display: 'flex', gap: '1rem', justifyContent: 'flex-end' }}>
            <button
              onClick={() => setShowMatchupOverlay(false)}
              style={{
                padding: '10px 20px',
                border: '1px solid #ddd',
                borderRadius: '6px',
                backgroundColor: 'white',
                cursor: 'pointer'
              }}
            >
              Cancel
            </button>
            <button
              onClick={handleSubmitPick}
              disabled={!selectedTeam}
              style={{
                padding: '10px 20px',
                border: 'none',
                borderRadius: '6px',
                backgroundColor: selectedTeam ? '#0070f3' : '#ccc',
                color: 'white',
                cursor: selectedTeam ? 'pointer' : 'not-allowed'
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
          league_id: id
        })
      });

      if (res.ok) {
        fetchLeagueAndEntries(); // Refresh the list to show the new entry
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
    return <div>Loading...</div>;
  }

  return (
    <ProtectedRoute>
      <main style={{ padding: '2rem', maxWidth: '1400px', margin: '0 auto' }}>
        <div style={{ marginBottom: '2rem' }}>
          <h1>{league?.name} - Entries</h1>
          <p style={{ color: '#666' }}>Click on any week circle to make or change picks</p>
        </div>

        {error && (
          <div style={{ 
            color: 'red', 
            backgroundColor: '#fee', 
            padding: '10px', 
            borderRadius: '4px',
            marginBottom: '1rem'
          }}>
            {error}
          </div>
        )}

        <div style={{ marginBottom: '2rem', display: 'flex', gap: '1rem' }}>
          <button 
            onClick={handleCreateEntry}
            style={{ 
              backgroundColor: '#0070f3', 
              color: 'white', 
              padding: '10px 20px', 
              border: 'none', 
              borderRadius: '5px', 
              cursor: 'pointer',
              fontSize: '16px'
            }}
          >
            Create New Entry
          </button>
          {entries.length > 0 && (
            <button 
              onClick={handleDeleteLastEntry}
              style={{ 
                backgroundColor: '#dc3545', 
                color: 'white', 
                padding: '10px 20px', 
                border: 'none', 
                borderRadius: '5px', 
                cursor: 'pointer',
                fontSize: '16px'
              }}
            >
              Delete Entry
            </button>
          )}
        </div>

        {entries.length === 0 ? (
          <div style={{
            textAlign: 'center',
            padding: '3rem',
            backgroundColor: '#f8f9fa',
            borderRadius: '8px',
            border: '1px dashed #ddd'
          }}>
            <h3>No entries yet</h3>
            <p style={{ color: '#666', marginBottom: '1rem' }}>
              You haven't created any entries for this league yet.
            </p>
            <button 
              onClick={handleCreateEntry}
              style={{ 
                backgroundColor: '#0070f3', 
                color: 'white', 
                padding: '10px 20px', 
                border: 'none', 
                borderRadius: '5px', 
                cursor: 'pointer',
                fontSize: '16px'
              }}
            >
              Create Your First Entry
            </button>
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ 
              width: '100%', 
              borderCollapse: 'collapse',
              backgroundColor: 'white',
              boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
              borderRadius: '8px'
            }}>
              <thead>
                <tr style={{ backgroundColor: '#f8f9fa' }}>
                  <th style={{ padding: '12px', textAlign: 'left', borderBottom: '2px solid #dee2e6' }}>Entry Name</th>
                  {Array.from({ length: 18 }, (_, i) => i + 1).map(week => (
                    <th key={week} style={{ 
                      padding: '12px', 
                      textAlign: 'center', 
                      borderBottom: '2px solid #dee2e6',
                      minWidth: '50px'
                    }}>
                      W{week}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {entries
                  .sort((a, b) => a.name.localeCompare(b.name))
                  .map(entry => (
                  <tr key={entry.id} style={{ borderBottom: '1px solid #dee2e6' }}>
                    <td style={{ padding: '12px', fontWeight: 'bold' }}>
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
                              border: '1px solid #ddd',
                              borderRadius: '4px',
                              padding: '4px 8px',
                              fontSize: '14px',
                              minWidth: '120px'
                            }}
                          />
                          <button
                            onClick={() => handleSaveEntryName(entry.id)}
                            style={{
                              backgroundColor: '#28a745',
                              color: 'white',
                              border: 'none',
                              borderRadius: '4px',
                              padding: '4px 8px',
                              cursor: 'pointer',
                              fontSize: '12px'
                            }}
                          >
                            ✓
                          </button>
                          <button
                            onClick={handleCancelEditingEntryName}
                            style={{
                              backgroundColor: '#dc3545',
                              color: 'white',
                              border: 'none',
                              borderRadius: '4px',
                              padding: '4px 8px',
                              cursor: 'pointer',
                              fontSize: '12px'
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
                            padding: '4px',
                            borderRadius: '4px',
                            transition: 'background-color 0.2s',
                            fontSize: 'inherit',
                            fontWeight: 'inherit',
                            fontFamily: 'inherit',
                            textAlign: 'left',
                            width: '100%'
                          }}
                          onMouseEnter={(e) => e.target.style.backgroundColor = '#f8f9fa'}
                          onMouseLeave={(e) => e.target.style.backgroundColor = 'transparent'}
                          onFocus={(e) => e.target.style.backgroundColor = '#f8f9fa'}
                          onBlur={(e) => e.target.style.backgroundColor = 'transparent'}
                          title="Click to edit entry name"
                        >
                          {entry.name}
                        </button>
                      )}
                    </td>
                    {Array.from({ length: 18 }, (_, i) => i + 1).map(week => (
                      <td key={week} style={{ padding: '8px', textAlign: 'center' }}>
                        {renderPickCircle(entry, week)}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        <div style={{ marginTop: '2rem', display: 'flex', gap: '1rem' }}>
          <button 
            onClick={() => router.push(`/league/${id}`)}
            style={{ 
              backgroundColor: '#6c757d', 
              color: 'white', 
              padding: '10px 20px', 
              border: 'none', 
              borderRadius: '5px', 
              cursor: 'pointer',
              fontSize: '16px'
            }}
          >
            Back to League
          </button>
          <button 
            onClick={() => router.push('/dashboard')}
            style={{ 
              backgroundColor: '#6c757d', 
              color: 'white', 
              padding: '10px 20px', 
              border: 'none', 
              borderRadius: '5px', 
              cursor: 'pointer',
              fontSize: '16px'
            }}
          >
            Back to Dashboard
          </button>
        </div>

        {renderMatchupOverlay()}
      </main>
    </ProtectedRoute>
  );
}
