import { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import ProtectedRoute from '../../../../../components/ProtectedRoute';

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

export default function EntryDetail() {
  const [entry, setEntry] = useState(null);
  const [picks, setPicks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [selectedWeek, setSelectedWeek] = useState(null);
  const [showMatchupOverlay, setShowMatchupOverlay] = useState(false);
  const [selectedTeam, setSelectedTeam] = useState(null);
  const router = useRouter();
  const { id: leagueId, entryId } = router.query;

  useEffect(() => {
    if (entryId) {
      fetchEntryAndPicks();
    }
  }, [entryId]);

  const fetchEntryAndPicks = async () => {
    try {
      const token = localStorage.getItem('access_token');
      
      // Fetch entry details
      const entryRes = await fetch(process.env.NEXT_PUBLIC_API_URL + `/entries/${entryId}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (entryRes.ok) {
        const entryData = await entryRes.json();
        setEntry(entryData);
      } else {
        setError('Failed to load entry details');
        return;
      }

      // Fetch picks for this entry
      const picksRes = await fetch(process.env.NEXT_PUBLIC_API_URL + `/picks/entry/${entryId}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (picksRes.ok) {
        const picksData = await picksRes.json();
        setPicks(picksData);
      } else {
        // Picks endpoint might not exist yet, so just set empty array
        setPicks([]);
      }
    } catch (err) {
      console.error('Failed to load data:', err);
      setError('Failed to load data');
    } finally {
      setLoading(false);
    }
  };

  const handlePickClick = (week) => {
    setSelectedWeek(week);
    setSelectedTeam(null);
    setShowMatchupOverlay(true);
  };

  const handleTeamSelect = (team) => {
    setSelectedTeam(team);
  };

  const handleSubmitPick = async () => {
    if (!selectedTeam || !selectedWeek) return;

    try {
      const token = localStorage.getItem('access_token');
      const res = await fetch(process.env.NEXT_PUBLIC_API_URL + '/picks/create', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          entry_id: entryId,
          week: selectedWeek,
          team: selectedTeam
        })
      });

      if (res.ok) {
        setShowMatchupOverlay(false);
        fetchEntryAndPicks(); // Refresh picks
      } else {
        const errorData = await res.json();
        setError(errorData.detail || 'Failed to save pick');
      }
    } catch (err) {
      console.error('Failed to save pick:', err);
      setError('Failed to save pick');
    }
  };

  const getPickForWeek = (week) => {
    return picks.find(pick => pick.week === week);
  };

  const getUsedTeams = () => {
    return picks.map(pick => pick.team);
  };

  const isTeamUsed = (team) => {
    return getUsedTeams().includes(team);
  };

  const renderPickCircle = (week) => {
    const pick = getPickForWeek(week);
    const hasTeam = pick && pick.team;

    return (
      <button
        key={week}
        onClick={() => handlePickClick(week)}
        style={{
          width: '60px',
          height: '60px',
          borderRadius: '50%',
          border: '2px solid #ddd',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          cursor: 'pointer',
          backgroundColor: hasTeam ? NFL_TEAMS[pick.team]?.color || '#f0f0f0' : '#f9f9f9',
          color: hasTeam ? 'white' : '#333',
          fontWeight: 'bold',
          fontSize: hasTeam ? '12px' : '14px',
          transition: 'all 0.2s ease',
          margin: '5px'
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
    if (!showMatchupOverlay || !selectedWeek) return null;

    const matchups = MOCK_MATCHUPS[selectedWeek] || [];

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
          <h2>Week {selectedWeek} Matchups</h2>
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
                    disabled={isTeamUsed(matchup.away)}
                    style={getTeamButtonStyle(matchup.away, selectedTeam === matchup.away, isTeamUsed(matchup.away))}
                  >
                    <img 
                      src={`/nfl/${NFL_TEAMS[matchup.away]?.logo}`} 
                      alt={`${matchup.away} logo`}
                      style={{ width: '24px', height: '24px' }}
                    />
                    <div>
                      <div style={{ fontWeight: 'bold', fontSize: '14px' }}>{matchup.away}</div>
                      <div style={{ fontSize: '12px', color: '#666' }}>{NFL_TEAMS[matchup.away]?.name}</div>
                    </div>
                  </button>
                  <span style={{ color: '#666', fontWeight: 'bold' }}>@</span>
                  <button
                    onClick={() => handleTeamSelect(matchup.home)}
                    disabled={isTeamUsed(matchup.home)}
                    style={getTeamButtonStyle(matchup.home, selectedTeam === matchup.home, isTeamUsed(matchup.home))}
                  >
                    <img 
                      src={`/nfl/${NFL_TEAMS[matchup.home]?.logo}`} 
                      alt={`${matchup.home} logo`}
                      style={{ width: '24px', height: '24px' }}
                    />
                    <div>
                      <div style={{ fontWeight: 'bold', fontSize: '14px' }}>{matchup.home}</div>
                      <div style={{ fontSize: '12px', color: '#666' }}>{NFL_TEAMS[matchup.home]?.name}</div>
                    </div>
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

  if (!router.isReady || loading) {
    return <div>Loading...</div>;
  }

  if (error && !entry) {
    return (
      <ProtectedRoute>
        <main style={{ padding: '2rem', maxWidth: '1200px', margin: '0 auto' }}>
          <div style={{ color: 'red' }}>{error}</div>
        </main>
      </ProtectedRoute>
    );
  }

  if (!entry) {
    return (
      <ProtectedRoute>
        <main style={{ padding: '2rem', maxWidth: '1200px', margin: '0 auto' }}>
          <div>Entry not found</div>
        </main>
      </ProtectedRoute>
    );
  }

  return (
    <ProtectedRoute>
      <main style={{ padding: '2rem', maxWidth: '1200px', margin: '0 auto' }}>
        <div style={{ marginBottom: '2rem' }}>
          <h1>{entry.name}</h1>
          <p style={{ color: '#666' }}>Click on any week to make or change your pick</p>
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

        <div style={{ 
          display: 'grid', 
          gridTemplateColumns: 'repeat(auto-fit, minmax(70px, 1fr))', 
          gap: '10px', 
          marginBottom: '2rem',
          maxWidth: '800px'
        }}>
          {Array.from({ length: 18 }, (_, i) => i + 1).map(week => renderPickCircle(week))}
        </div>

        <div style={{ 
          backgroundColor: '#f8f9fa', 
          padding: '1rem', 
          borderRadius: '8px',
          marginBottom: '2rem'
        }}>
          <h3>Your Picks Summary</h3>
          <p>Teams used: {getUsedTeams().join(', ') || 'None yet'}</p>
          <p>Weeks remaining: {18 - picks.length}</p>
        </div>

        <button 
          onClick={() => router.push(`/league/${leagueId}/entries`)}
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
          Back to Entries
        </button>

        {renderMatchupOverlay()}
      </main>
    </ProtectedRoute>
  );
}
