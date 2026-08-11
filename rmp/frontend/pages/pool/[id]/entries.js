
import { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import ProtectedRoute from '../../../components/ProtectedRoute';
import { useAuth } from '../../../context/AuthContext';
import { PoolWorkspaceNav, WorkspaceHeader } from '../../../components/ProductWorkspace';
import { getPickAvailability } from '../../../utils/pickAvailability';
import { isLeagueJoinLocked } from '../../../utils/leagueLock';

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

function PickBreakdownPanel({ data, week }) {
  if (!data || data.length === 0) return null;
  const total = data.reduce((sum, item) => sum + item.count, 0);
  if (total === 0) return null;

  return (
    <div className="entries-breakdown" style={{
      backgroundColor: '#10191c',
      border: '1px solid #314449',
      borderRadius: '0',
      padding: '1rem 1.25rem',
      marginBottom: '1.5rem',
    }}>
      <div className="entries-breakdown__header" style={{ display: 'flex', alignItems: 'center', marginBottom: '0.75rem', gap: '0.5rem', flexWrap: 'wrap' }}>
        <h3 style={{ margin: 0, fontSize: '1rem', fontWeight: '600' }}>
          Week {week} Pick Breakdown
        </h3>
        <span style={{
          fontSize: '0.75rem',
          backgroundColor: '#dc3545',
          color: '#fff',
          padding: '2px 8px',
          borderRadius: '10px',
          fontWeight: '500',
        }}>
          🔒 Locked
        </span>
        <span style={{ fontSize: '0.8rem', color: '#666', marginLeft: 'auto' }}>
          {total} alive {total === 1 ? 'entry' : 'entries'}
        </span>
      </div>

      {data.map((item) => {
        const pct = Math.round((item.count / total) * 100);
        return (
          <div className="entries-breakdown__row" key={item.team_id} style={{ marginBottom: '0.4rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <img
              src={`/nfl/${item.team_abbrv.toLowerCase()}.svg`}
              alt={item.team_abbrv}
              style={{ width: '20px', height: '20px', objectFit: 'contain', flexShrink: 0 }}
              onError={(e) => { e.target.style.display = 'none'; }}
            />
            <span style={{ width: '36px', fontSize: '0.8rem', fontWeight: '500', flexShrink: 0 }}>
              {item.team_abbrv}
            </span>
            <div style={{ flex: 1, backgroundColor: '#e9ecef', borderRadius: '4px', height: '18px', overflow: 'hidden' }}>
              <div style={{
                width: `${pct}%`,
                minWidth: pct > 0 ? '4px' : '0',
                height: '100%',
                backgroundColor: '#d7ff3f',
                borderRadius: '4px',
                transition: 'width 0.3s ease',
              }} />
            </div>
            <span style={{ width: '64px', fontSize: '0.8rem', color: '#555', textAlign: 'right', flexShrink: 0 }}>
              {item.count} ({pct}%)
            </span>
          </div>
        );
      })}
    </div>
  );
}

export default function LeagueEntries() {
  // Helper to check if pool lock time is in the past
  const isPoolLocked = () => {
    return isLeagueJoinLocked(league, new Date(lockClock));
  };
  const [league, setLeague] = useState(null);
  const [entries, setEntries] = useState([]);
  const [allPicks, setAllPicks] = useState({});
  const [weekLockStatus, setWeekLockStatus] = useState({});
  const [scheduleData, setScheduleData] = useState({}); // Store schedule data by week
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [lockClock, setLockClock] = useState(() => Date.now());
  const [selectedWeek, setSelectedWeek] = useState(null);
  const [breakdownData, setBreakdownData] = useState([]);
  const [breakdownLoading, setBreakdownLoading] = useState(false);
  const [selectedEntry, setSelectedEntry] = useState(null);
  const [showMatchupOverlay, setShowMatchupOverlay] = useState(false);
  const [selectedTeam, setSelectedTeam] = useState(null);

  useEffect(() => {
    const timer = window.setInterval(() => setLockClock(Date.now()), 30000);
    return () => window.clearInterval(timer);
  }, []);
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

      const lockStatusRes = await fetch(
        process.env.NEXT_PUBLIC_API_URL + `/pools/${id}/lock-status`,
        { headers: { 'Authorization': `Bearer ${token}` } }
      );
      if (lockStatusRes.ok) {
        const lockStatus = await lockStatusRes.json();
        setWeekLockStatus(lockStatus.weeks || {});
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

  const fetchBreakdown = async (week) => {
    if (!week || !id) return;
    setBreakdownLoading(true);
    try {
      const token = localStorage.getItem('access_token');
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/picks/pool/${id}/week/${week}/breakdown`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      if (res.ok) {
        setBreakdownData(await res.json());
      } else {
        setBreakdownData([]);
      }
    } catch {
      setBreakdownData([]);
    } finally {
      setBreakdownLoading(false);
    }
  };

  useEffect(() => {
    if (selectedWeek) fetchBreakdown(selectedWeek);
  }, [selectedWeek, id]);

  const handlePickClick = async (entry, week) => {
    if (weekLockStatus[String(week)]?.locked) {
      setError(`Week ${week} is locked. Picks can no longer be added or changed.`);
      return;
    }
    setSelectedEntry(entry);
    setSelectedWeek(week);
    const { currentPick } = getPickAvailability(allPicks[entry.id] || [], week);
    setSelectedTeam(currentPick?.team || null);
    
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
    const isEntryAlive = entry.alive !== false; // Default to true if undefined
    const isWeekLocked = Boolean(weekLockStatus[String(week)]?.locked || pick?.locked);
    
    // More visible outlined style for pick circles
    let backgroundColor = '#fff';
    let borderColor = '#ccc';
    let textColor = '#666';
    let cursor = 'pointer';
    let borderWidth = '2px';
    let opacity = 1;
    if (pick?.result === 'win') {
      backgroundColor = '#e8f5e9';
      borderColor = '#4caf50';
      textColor = '#1b5e20';
      borderWidth = '2.5px';
      cursor = 'not-allowed';
      opacity = 1;
    } else if (pick?.result === 'loss') {
      backgroundColor = '#ffebee';
      borderColor = '#f44336';
      textColor = '#b71c1c';
      borderWidth = '2.5px';
      cursor = 'not-allowed';
      opacity = 1;
    } else if (!isEntryAlive) {
      borderColor = '#f19999';
      textColor = '#d32f2f';
      cursor = 'not-allowed';
      borderWidth = '2px';
      opacity = 0.7;
    } else if (isWeekLocked) {
      borderColor = '#66757a';
      textColor = '#66757a';
      cursor = 'not-allowed';
      opacity = 0.72;
    } else if (hasTeam) {
      borderColor = '#bbb';
      textColor = '#666';
    }

    return (
      <button
        key={week}
        onClick={() => isEntryAlive && !isWeekLocked ? handlePickClick(entry, week) : null}
        disabled={!isEntryAlive || isWeekLocked}
        style={{
          width: '36px',
          height: '36px',
          borderRadius: '50%',
          border: `${borderWidth} solid ${borderColor}`,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          cursor: cursor,
          backgroundColor: backgroundColor,
          color: textColor,
          fontWeight: 500,
          fontSize: hasTeam ? '10px' : '12px',
          transition: 'all 0.2s ease',
          margin: '2px auto',
          position: 'relative',
          overflow: 'hidden',
          opacity: opacity
        }}
        title={pick?.result
          ? `${pick.team} - ${pick.result}`
          : !isEntryAlive
          ? 'Entry eliminated - no remaining picks available'
          : isWeekLocked
            ? `Week ${week} is locked${hasTeam ? ` — ${pick.team}` : ''}`
            : (pick?.result ? `${pick.team} - ${pick.result}` : '')}
      >
        {hasTeam ? (
          <img
            src={`/nfl/${NFL_TEAMS[pick.team]?.logo}`}
            alt={`${pick.team} logo`}
            style={{
              width: '20px',
              height: '20px',
              marginRight: '0',
              opacity: 1,
              display: 'block',
              margin: '0 auto 2px auto'
            }}
          />
        ) : (
          week
        )}
        {isWeekLocked && !pick?.result && (
          <span aria-hidden="true" style={{
            position: 'absolute', right: '-1px', bottom: '-2px', fontSize: '11px',
            lineHeight: 1, background: '#fff', borderRadius: '50%'
          }}>🔒</span>
        )}
      </button>
    );
  };

  const getTeamButtonStyle = (team, isSelected, isUsed, isCurrentPick) => {
    let backgroundColor = 'white';
    let border = '1px solid #ddd';
    let textColor = '#333';
    if (isUsed) {
      backgroundColor = '#f5f5f5';
      textColor = '#999';
    } else if (isCurrentPick) {
      backgroundColor = '#efffc0';
      border = '2px solid #9fca00';
    } else if (isSelected) {
      backgroundColor = '#e6f3ff';
      border = '2px solid #0070f3';
    }

    return {
      padding: '12px 16px',
      border,
      borderRadius: '8px',
      backgroundColor,
      color: textColor,
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
    const { currentPick, usedInOtherWeeks, usedWeekByTeam } = getPickAvailability(
      allPicks[selectedEntry.id] || [],
      selectedWeek
    );

    // Helper function to format date and time
    const formatGameTime = (startTime) => {
      if (!startTime) return { date: 'TBD', time: 'TBD' };
      
      try {
        const gameDate = new Date(startTime);
        const date = gameDate.toLocaleDateString('en-US', { month: '2-digit', day: '2-digit', timeZone: 'America/New_York' });
        const time = gameDate.toLocaleTimeString('en-US', { 
          hour: 'numeric', 
          minute: '2-digit',
          timeZone: 'America/New_York',
          timeZoneName: 'short'
        });
        return { date, time };
      } catch (err) {
        return { date: 'TBD', time: 'TBD' };
      }
    };

    return (
      <div className="entries-overlay" style={{
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
        <div className="entries-overlay__dialog" style={{
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
          <div className="entries-overlay__header" style={{ padding: '2rem 2rem 1rem 2rem' }}>
            <h2>Week {selectedWeek} Matchups - {selectedEntry.name}</h2>
            <p style={{ color: '#666', marginBottom: '0' }}>
              Teams used in other weeks are unavailable. Your saved pick for this week is highlighted in lime.
            </p>
          </div>

          {/* Scrollable Content */}
          <div className="entries-overlay__content" style={{
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
                  const awayUsed = usedInOtherWeeks.has(awayTeam.abbrv);
                  const homeUsed = usedInOtherWeeks.has(homeTeam.abbrv);
                  const awayCurrent = currentPick?.team === awayTeam.abbrv;
                  const homeCurrent = currentPick?.team === homeTeam.abbrv;
                  
                  return (
                    <div className="entries-overlay__game" key={game.game_id} style={{
                      border: '1px solid #ddd',
                      borderRadius: '8px',
                      padding: '1rem',
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center'
                    }}>
                      <div className="entries-overlay__teams" style={{ display: 'flex', gap: '1rem', alignItems: 'center', flex: 1 }}>
                        <button
                          className={`entries-team-option${awayUsed ? ' entries-team-option--used' : ''}${awayCurrent ? ' entries-team-option--current' : ''}${selectedTeam === awayTeam.abbrv ? ' entries-team-option--selected' : ''}`}
                          onClick={() => handleTeamSelect(awayTeam.abbrv)}
                          disabled={awayUsed}
                          aria-label={`${awayTeam.name}${awayUsed ? ', used in another week' : awayCurrent ? ', current week pick' : ''}`}
                          style={getTeamButtonStyle(awayTeam.abbrv, selectedTeam === awayTeam.abbrv, awayUsed, awayCurrent)}
                        >
                          <img 
                            src={awayTeam.logo} 
                            alt={`${awayTeam.abbrv} logo`}
                            style={{ width: '24px', height: '24px' }}
                          />
                          <div>
                            <div style={{ fontWeight: 'bold', fontSize: '14px' }}>{awayTeam.abbrv}</div>
                            <div style={{ fontSize: '12px', color: '#666' }}>{awayTeam.name}</div>
                            {awayCurrent && <div style={{ fontSize: '11px', color: '#526900', fontWeight: 800 }}>CURRENT PICK</div>}
                            {awayUsed && <div className="entries-team-option__used">USED · WEEK {usedWeekByTeam.get(awayTeam.abbrv)}</div>}
                          </div>
                        </button>
                        <span style={{ color: '#666', fontWeight: 'bold' }}>@</span>
                        <button
                          className={`entries-team-option${homeUsed ? ' entries-team-option--used' : ''}${homeCurrent ? ' entries-team-option--current' : ''}${selectedTeam === homeTeam.abbrv ? ' entries-team-option--selected' : ''}`}
                          onClick={() => handleTeamSelect(homeTeam.abbrv)}
                          disabled={homeUsed}
                          aria-label={`${homeTeam.name}${homeUsed ? ', used in another week' : homeCurrent ? ', current week pick' : ''}`}
                          style={getTeamButtonStyle(homeTeam.abbrv, selectedTeam === homeTeam.abbrv, homeUsed, homeCurrent)}
                        >
                          <img 
                            src={homeTeam.logo} 
                            alt={`${homeTeam.abbrv} logo`}
                            style={{ width: '24px', height: '24px' }}
                          />
                          <div>
                            <div style={{ fontWeight: 'bold', fontSize: '14px' }}>{homeTeam.abbrv}</div>
                            <div style={{ fontSize: '12px', color: '#666' }}>{homeTeam.name}</div>
                            {homeCurrent && <div style={{ fontSize: '11px', color: '#526900', fontWeight: 800 }}>CURRENT PICK</div>}
                            {homeUsed && <div className="entries-team-option__used">USED · WEEK {usedWeekByTeam.get(homeTeam.abbrv)}</div>}
                          </div>
                        </button>
                      </div>
                      <div className="entries-overlay__kickoff" style={{ marginLeft: '1rem', color: '#666', fontSize: '14px', textAlign: 'right' }}>
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
          <div className="entries-overlay__footer" style={{
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
    if (isPoolLocked()) {
      setError('Pool is locked. No new entries can be created.');
      return;
    }
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
    if (isPoolLocked()) {
      setError('Pool is locked. Entries cannot be deleted.');
      return;
    }
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
      <div className="product-page entries-page" style={{
        minHeight: '100vh', 
        background: '#080d0f',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center'
      }}>
        <div style={{ 
          color: '#d7ff3f',
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
      <div className="product-page entries-page" style={{
        minHeight: '100vh', 
        background: '#080d0f',
        display: 'flex',
        flexDirection: 'column'
      }}>
        {/* Header */}
        <header className="legacy-page-header" style={{
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
        <main className="product-main" style={{
          flex: 1,
          maxWidth: '1400px', 
          margin: '0 auto',
          padding: '2rem'
        }}>
          <PoolWorkspaceNav poolId={id} poolName={league?.name} active="entries" />
          <WorkspaceHeader
            eyebrow="Picks desk"
            title={league?.name || 'Pool picks'}
            description="Make selections, review every entry, and track the season week by week."
            meta={`${entries.length} ${entries.length === 1 ? 'entry' : 'entries'}`}
          />
          {/* Header */}
          <div className="legacy-page-title" style={{
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
              margin: '0 0 1rem 0'
            }}>
              Click on any week circle to make or change picks
            </p>
            
          </div>

          {/* Main Content Card */}
          <div className="product-panel entries-board" style={{
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
            {Object.values(weekLockStatus).some((week) => week.locked) && (
              <div className="entries-lock-notice" role="status">
                Locked weeks are read-only. A lock icon means picks can no longer be added or changed.
              </div>
            )}
            <div className="entries-action-bar">
              <div className="entries-action-bar__primary">
                {!isPoolLocked() && (
                  <>
                  <button className="entries-action entries-action--create"
                    onClick={handleCreateEntry}
                  >
                    <span aria-hidden="true">+</span> Create New Entry
                  </button>
                  {entries.length > 0 && (
                    <button className="entries-action entries-action--delete"
                      onClick={handleDeleteLastEntry}
                    >
                      <span aria-hidden="true">−</span> Delete Entry
                    </button>
                  )}
                  </>
                )}
              </div>
              <button className="entries-action entries-action--back" onClick={() => router.push('/dashboard')}>
                Back to Dashboard <span aria-hidden="true">→</span>
              </button>
            </div>

        {entries.length === 0 ? (
          <div className="entries-empty-state" style={{
            textAlign: 'center',
            padding: '4rem 2rem',
            backgroundColor: '#0d1618',
            borderRadius: '0',
            border: '1px dashed #3a5055',
            boxShadow: 'none',
            background: '#0d1618'
          }}>
            <div style={{
              fontSize: '3rem',
              marginBottom: '1rem',
              background: 'none',
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
            {!isPoolLocked() && (
              <button className="entries-action entries-action--create"
                onClick={handleCreateEntry}
                style={{ 
                  background: '#d7ff3f',
                  color: 'white', 
                  padding: '1rem 2rem', 
                  border: 'none', 
                  borderRadius: '12px', 
                  cursor: 'pointer',
                  fontSize: '1.1rem',
                  fontWeight: '600',
                  transition: 'all 0.3s ease',
                  boxShadow: '0 8px 24px rgba(215, 255, 63, 0.14)',
                  textTransform: 'none',
                  letterSpacing: '0.5px'
                }}
                onMouseEnter={(e) => {
                  e.target.style.transform = 'translateY(-2px)';
                  e.target.style.boxShadow = '0 12px 32px rgba(215, 255, 63, 0.2)';
                }}
                onMouseLeave={(e) => {
                  e.target.style.transform = 'translateY(0)';
                  e.target.style.boxShadow = '0 8px 24px rgba(215, 255, 63, 0.14)';
                }}
              >
                Create Your First Entry
              </button>
            )}
          </div>
        ) : (
          <>
            <PickBreakdownPanel data={breakdownData} week={selectedWeek} />
            <div className="entries-table-scroll" style={{
              overflowX: 'auto',
              borderRadius: '12px',
            boxShadow: 'none',
            backgroundColor: '#11191c'
          }}>
            <table className="entries-season-table" style={{
              width: '100%', 
              borderCollapse: 'collapse',
              backgroundColor: 'white',
              borderRadius: '12px',
              overflow: 'hidden'
            }}>
              <thead>
                <tr style={{ 
                  background: '#0c1416',
                  color: 'white'
                }}>
                  <th className="entries-season-table__name" style={{
                    padding: '16px 20px', 
                    textAlign: 'left', 
                    fontWeight: '600',
                    fontSize: '14px',
                    letterSpacing: '0.5px',
                    textTransform: 'uppercase'
                  }}>Entry Name</th>
                  {Array.from({ length: 18 }, (_, i) => i + 1).map(week => (
                    <th className="entries-season-table__week" key={week} style={{
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
                    <td className="entries-season-table__name" style={{
                      padding: '16px 20px', 
                      fontWeight: '600',
                      color: '#2d3748',
                      fontSize: '15px'
                    }}>
                      {editingEntryId === entry.id ? (
                        <div className="entries-name-editor" style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                          <input
                            type="text"
                            value={editingEntryName}
                            onChange={(e) => setEditingEntryName(e.target.value)}
                            onKeyDown={(e) => handleEntryNameKeyPress(e, entry.id)}
                            onBlur={() => handleSaveEntryName(entry.id)}
                            autoFocus
                            style={{
                              border: '2px solid #9fefff',
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
                        <button className="entries-name-button"
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
                          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                            {entry.alive === false && (
                              <span style={{ 
                                color: '#dc3545', 
                                fontSize: '12px', 
                                fontWeight: 'bold',
                                backgroundColor: '#f8d7da',
                                padding: '2px 6px',
                                borderRadius: '4px'
                              }}>
                                ❌ ELIMINATED
                              </span>
                            )}
                            <span>{entry.name}</span>
                          </div>
                        </button>
                      )}
                    </td>
                    {Array.from({ length: 18 }, (_, i) => i + 1).map(week => (
                      <td className="entries-season-table__week" key={week} style={{
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
          </>
        )}

            {renderMatchupOverlay()}
          </div>
        </main>
      </div>
    </ProtectedRoute>
  );
}
