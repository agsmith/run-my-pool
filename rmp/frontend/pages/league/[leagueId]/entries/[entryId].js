import { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import ProtectedRoute from '../../../../components/ProtectedRoute';

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
    { home: 'KC', away: 'BAL', time: '8:20 PM ET' },
    { home: 'ATL', away: 'PHI', time: '1:00 PM ET' },
    { home: 'CIN', away: 'NE', time: '1:00 PM ET' },
    { home: 'HOU', away: 'IND', time: '1:00 PM ET' },
    { home: 'JAX', away: 'MIA', time: '1:00 PM ET' },
    { home: 'NO', away: 'CAR', time: '1:00 PM ET' },
    { home: 'PIT', away: 'SF', time: '1:00 PM ET' },
    { home: 'TEN', away: 'CHI', time: '1:00 PM ET' },
    { home: 'CLE', away: 'DAL', time: '4:25 PM ET' },
    { home: 'GB', away: 'MIN', time: '4:25 PM ET' },
    { home: 'LAR', away: 'DET', time: '8:20 PM ET' },
    { home: 'TB', away: 'WAS', time: '4:25 PM ET' },
    { home: 'BUF', away: 'NYJ', time: '8:15 PM ET' },
    { home: 'LAC', away: 'LV', time: '4:05 PM ET' },
    { home: 'NYG', away: 'ARI', time: '4:25 PM ET' },
    { home: 'SEA', away: 'DEN', time: '4:05 PM ET' }
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
  const { leagueId, entryId } = router.query;

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
        fetchEntryAndPicks();
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
    const isEntryAlive = entry?.alive !== false;
    let backgroundColor = '#f9f9f9';
    let borderColor = '#ddd';
    let cursor = 'pointer';
    if (!isEntryAlive) {
      backgroundColor = '#dc3545';
      borderColor = '#dc3545';
      cursor = 'not-allowed';
    } else if (hasTeam) {
      if (pick.result === 'win') {
        backgroundColor = '#28a745';
        borderColor = '#28a745';
      } else if (pick.result === 'loss') {
        backgroundColor = '#dc3545';
        borderColor = '#dc3545';
      } else {
        backgroundColor = NFL_TEAMS[pick.team]?.color || '#f0f0f0';
        borderColor = '#ddd';
      }
    }
    // TODO: Implement the actual rendering logic for the pick circle here
    return null;
  };

  // ...existing code for rendering the rest of the component...
}
