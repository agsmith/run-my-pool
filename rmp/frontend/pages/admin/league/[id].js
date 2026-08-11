import { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import ProtectedRoute from '../../../components/ProtectedRoute';
import { useAuth } from '../../../context/AuthContext';
import { PoolWorkspaceNav, WorkspaceHeader } from '../../../components/ProductWorkspace';
import AdminUserOverview from '../../../components/AdminUserOverview';
import { getAuditUsername } from '../../../utils/auditDisplay';

const TIMEZONES = [
  { label: 'Eastern Time (ET)',   iana: 'America/New_York' },
  { label: 'Central Time (CT)',   iana: 'America/Chicago' },
  { label: 'Mountain Time (MT)',  iana: 'America/Denver' },
  { label: 'Pacific Time (PT)',   iana: 'America/Los_Angeles' },
  { label: 'UTC',                 iana: 'UTC' },
];
const DAYS_OF_WEEK = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];

function toUtcIso(dateStr, timeStr, ianaTimezone) {
  // Build a local datetime string and convert to UTC using Intl
  if (!dateStr || !timeStr) return null;
  const localDt = new Date(`${dateStr}T${timeStr}:00`);
  if (isNaN(localDt.getTime())) return null;
  // Use the timezone to get the UTC offset at that moment
  const utcMs = localDt.getTime();
  // Get the local time in the target timezone
  const fmt = new Intl.DateTimeFormat('en-CA', {
    timeZone: ianaTimezone,
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', second: '2-digit',
    hour12: false,
  });
  const parts = fmt.formatToParts(localDt);
  const p = {};
  parts.forEach(({ type, value }) => { p[type] = value; });
  const tzLocalMs = new Date(`${p.year}-${p.month}-${p.day}T${p.hour}:${p.minute}:${p.second}`).getTime();
  const offsetMs = utcMs - (tzLocalMs - utcMs + utcMs - tzLocalMs);
  // Simpler: re-interpret the dateStr+timeStr as if it's in the given tz
  // Build the ISO by asking what UTC time corresponds to this local time in the tz
  const guessUtc = new Date(localDt.getTime());
  const tzTime = new Date(localDt.toLocaleString('en-US', { timeZone: ianaTimezone }));
  const diff = localDt - tzTime;
  const utcDate = new Date(localDt.getTime() + diff);
  // Format as YYYY-MM-DD HH:MM:SS
  const pad = n => String(n).padStart(2, '0');
  return `${utcDate.getUTCFullYear()}-${pad(utcDate.getUTCMonth()+1)}-${pad(utcDate.getUTCDate())} ${pad(utcDate.getUTCHours())}:${pad(utcDate.getUTCMinutes())}:${pad(utcDate.getUTCSeconds())}`;
}

export default function AdminPortal() {
  const [activeSection, setActiveSection] = useState('league-management');
  const [league, setLeague] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const router = useRouter();
  const { user } = useAuth();
  const { id: leagueId } = router.query;

  // League Management State
  const [leagues, setLeagues] = useState([]);
  const [leagueSearch, setLeagueSearch] = useState('');
  const [accessSettings, setAccessSettings] = useState({ is_private: false, join_password: '' });
  const [accessMessage, setAccessMessage] = useState('');
  const [savingAccess, setSavingAccess] = useState(false);
  
  // User Management State
  const [resetPasswordData, setResetPasswordData] = useState({ username: '' });
  const [resetPasswordMessage, setResetPasswordMessage] = useState('');
  const [userLockData, setUserLockData] = useState({ email: '', reason: '' });
  const [userLockStatus, setUserLockStatus] = useState(null);
  const [userLockMessage, setUserLockMessage] = useState('');
  const [userOverview, setUserOverview] = useState(null);
  const [userOverviewLoading, setUserOverviewLoading] = useState(false);
  const [userOverviewError, setUserOverviewError] = useState('');

  // Lock time state
  const [lockTimeData, setLockTimeData] = useState({ day: 6, time: '13:00', timezone: 'America/New_York' });
  const [joinLockData, setJoinLockData] = useState({ date: '', time: '13:00', timezone: 'America/New_York' });
  const [lockTimeMessage, setLockTimeMessage] = useState('');
  
  // User lock state
  const [lockMessage, setLockMessage] = useState('');

  const [updateEmailData, setUpdateEmailData] = useState({ username: '', newEmail: '' });
  const [deleteUserData, setDeleteUserData] = useState({ username: '' });
  const [assignAdminData, setAssignAdminData] = useState({ username: '' });
  
  // Entry Management State
  const [transferEntryData, setTransferEntryData] = useState({ entryId: '', fromUser: '', toUser: '' });
  const [deleteEntryData, setDeleteEntryData] = useState({ entryId: '', username: '' });
  const [correctPickData, setCorrectPickData] = useState({ entryId: '', weekNum: '', teamAbbr: '', reason: '' });
  const [entryLookupData, setEntryLookupData] = useState({ username: '', entryName: '' });
  const [lookupResults, setLookupResults] = useState([]);
  const [entryActionMessage, setEntryActionMessage] = useState('');
  
  // Audit Log State
  const [auditSearch, setAuditSearch] = useState({ 
    username: '',
    dateFrom: '', 
    dateTo: '', 
    actionSearch: '' 
  });
  const [auditLogs, setAuditLogs] = useState([]);
  const [auditLoading, setAuditLoading] = useState(false);
  const [auditError, setAuditError] = useState('');

  useEffect(() => {
    if (leagueId) {
      fetchLeagueData();
      fetchAllLeagues();
    }
  }, [leagueId]);

  useEffect(() => {
    if (activeSection === 'audit-log' && leagueId) {
      fetchAuditLogs();
    }
  }, [activeSection, leagueId]);

  useEffect(() => {
    if (activeSection === 'user-management' && leagueId) fetchUserOverview();
  }, [activeSection, leagueId]);

  const fetchUserOverview = async () => {
    setUserOverviewLoading(true);
    setUserOverviewError('');
    try {
      const token = localStorage.getItem('access_token');
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/admin/pools/${leagueId}/users-overview`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || 'Unable to load league users');
      setUserOverview(data);
    } catch (err) {
      setUserOverviewError(err.message || 'Unable to load league users');
    } finally {
      setUserOverviewLoading(false);
    }
  };

  const fetchAuditLogs = async (search = auditSearch) => {
    setAuditLoading(true);
    setAuditError('');
    try {
      const token = localStorage.getItem('access_token');
      const params = new URLSearchParams({ pool_id: leagueId, limit: '500' });
      if (search.username) params.set('username', search.username.trim());
      if (search.actionSearch) params.set('action', search.actionSearch.trim());
      if (search.dateFrom) params.set('date_from', `${search.dateFrom}T00:00:00`);
      if (search.dateTo) params.set('date_to', `${search.dateTo}T23:59:59`);

      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/audit/?${params}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (!res.ok) throw new Error('Unable to load audit events');
      setAuditLogs(await res.json());
    } catch (err) {
      setAuditLogs([]);
      setAuditError(err.message || 'Unable to load audit events');
    } finally {
      setAuditLoading(false);
    }
  };

  const parseAuditDetails = (details) => {
    if (!details) return null;
    try { return JSON.parse(details); } catch { return { description: details }; }
  };

  const fetchLeagueData = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const res = await fetch(process.env.NEXT_PUBLIC_API_URL + `/pools/${leagueId}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (res.ok) {
        const data = await res.json();
        setLeague(data);
        setAccessSettings({ is_private: data.is_private, join_password: '' });
        if (data.lock_day_of_week !== null && data.lock_day_of_week !== undefined) {
          setLockTimeData({
            day: data.lock_day_of_week,
            time: (data.lock_time_of_day || '13:00').slice(0, 5),
            timezone: data.lock_timezone || 'America/New_York',
          });
        }
      } else {
        setError('Failed to load league details');
      }
    } catch (err) {
      setError('Failed to load league details');
    } finally {
      setLoading(false);
    }
  };

  const fetchAllLeagues = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const res = await fetch(process.env.NEXT_PUBLIC_API_URL + `/pools`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (res.ok) {
        const data = await res.json();
        setLeagues(data);
      }
    } catch (err) {
      console.error('Failed to load all leagues');
    }
  };

  const handleEntryLookup = async () => {
    if (!entryLookupData.username && !entryLookupData.entryName) {
      setError('Please enter either username or entry name to search');
      return;
    }

    try {
      const token = localStorage.getItem('access_token');
      const params = new URLSearchParams();
      if (entryLookupData.username.trim()) params.set('username', entryLookupData.username.trim());
      if (entryLookupData.entryName.trim()) params.set('entry_name', entryLookupData.entryName.trim());
      const res = await fetch(process.env.NEXT_PUBLIC_API_URL + `/admin/pools/${leagueId}/entries?${params}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (res.ok) {
        setLookupResults(await res.json());
        setEntryActionMessage('Search complete.');
      } else {
        const data = await res.json();
        setEntryActionMessage(data.detail || 'Failed to fetch entries');
      }
    } catch (err) {
      setEntryActionMessage('Error performing lookup');
      console.error('Entry lookup error:', err);
    }
  };

  const handleSaveAccess = async () => {
    setSavingAccess(true);
    setAccessMessage('');
    try {
      const token = localStorage.getItem('access_token');
      const payload = { is_private: accessSettings.is_private };
      if (accessSettings.is_private && accessSettings.join_password) {
        payload.join_password = accessSettings.join_password;
      }
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/pools/${leagueId}`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(payload),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || 'Unable to update pool access');
      setLeague(data);
      setAccessSettings({ is_private: data.is_private, join_password: '' });
      setAccessMessage(data.is_private ? 'Private access saved.' : 'Pool is now public. No password is required.');
    } catch (err) {
      setAccessMessage(err.message || 'Unable to update pool access');
    } finally {
      setSavingAccess(false);
    }
  };

  const handleTransferEntry = async () => {
    if (!transferEntryData.entryId || !transferEntryData.toUser) {
      setEntryActionMessage('Please enter both entry ID and new owner email');
      return;
    }

    try {
      const token = localStorage.getItem('access_token');
      const res = await fetch(process.env.NEXT_PUBLIC_API_URL + `/admin/pools/${leagueId}/transfer-entry`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          entry_id: transferEntryData.entryId,
          to_email: transferEntryData.toUser
        })
      });
      
      if (res.ok) {
        const result = await res.json();
        setEntryActionMessage(result.message);
        // Clear the form
        setTransferEntryData({ entryId: '', fromUser: '', toUser: '' });
      } else {
        const errorData = await res.json();
        setEntryActionMessage(`Transfer failed: ${errorData.detail}`);
      }
    } catch (err) {
      setEntryActionMessage('Error transferring entry');
      console.error('Transfer error:', err);
    }
  };

  const renderSidebar = () => (
    <aside className="admin-sidebar">
      <div className="admin-sidebar__heading">
        <span className="admin-sidebar__eyebrow">Commissioner tools</span>
        <h2>Admin Portal</h2>
      </div>
      
      {league && (
        <div className="admin-sidebar__league">
          <span>Managing league</span>
          <strong>{league.name}</strong>
        </div>
      )}
      
      <nav aria-label="Admin sections">
        {[
          { id: 'league-management', label: 'League Management', marker: 'LG' },
          { id: 'user-management', label: 'User Management', marker: 'US' },
          { id: 'entry-management', label: 'Entry Management', marker: 'EN' },
          { id: 'audit-log', label: 'Audit Log', marker: 'AU' }
        ].map(section => (
          <button
            key={section.id}
            onClick={() => setActiveSection(section.id)}
            className={`admin-sidebar__item${activeSection === section.id ? ' admin-sidebar__item--active' : ''}`}
            aria-current={activeSection === section.id ? 'page' : undefined}
          >
            <span className="admin-sidebar__marker" aria-hidden="true">{section.marker}</span>
            <span>{section.label}</span>
          </button>
        ))}
      </nav>
      
      <div className="admin-sidebar__footer">
        <button
          onClick={() => router.push('/dashboard')}
          className="admin-sidebar__back"
        >
          ← Back to Dashboard
        </button>
      </div>
    </aside>
  );

  const handleSetLockTime = async () => {
    const joinUtcIso = joinLockData.date
      ? toUtcIso(joinLockData.date, joinLockData.time, joinLockData.timezone)
      : null;
    if (joinLockData.date && !joinUtcIso) {
      setLockTimeMessage('Please enter a valid league lock date and time.');
      return;
    }
    setLockTimeMessage('');
    try {
      const token = localStorage.getItem('access_token');
      const res = await fetch(
        process.env.NEXT_PUBLIC_API_URL + `/pools/${leagueId}`,
        {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
          body: JSON.stringify({
            lock_day_of_week: Number(lockTimeData.day),
            lock_time_of_day: lockTimeData.time,
            lock_timezone: lockTimeData.timezone,
            ...(joinUtcIso ? { join_lock_time: joinUtcIso } : {}),
          }),
        }
      );
      if (!res.ok) throw new Error('Failed to update lock time');
      setLockTimeMessage('Weekly pick lock and league registration deadline saved.');
    } catch {
      setLockTimeMessage('Failed to set lock time.');
    }
  };

  const handleDeleteEntry = async () => {
    if (!deleteEntryData.entryId.trim()) {
      setEntryActionMessage('Enter an entry ID to delete.');
      return;
    }
    try {
      const token = localStorage.getItem('access_token');
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/admin/pools/${leagueId}/entries/${deleteEntryData.entryId.trim()}`, {
        method: 'DELETE', headers: { Authorization: `Bearer ${token}` },
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Unable to delete entry');
      setEntryActionMessage(data.message);
      setDeleteEntryData({ entryId: '', username: '' });
      setLookupResults((current) => current.filter((entry) => entry.id !== deleteEntryData.entryId.trim()));
    } catch (err) { setEntryActionMessage(err.message || 'Unable to delete entry'); }
  };

  const handleCorrectPick = async () => {
    if (!correctPickData.entryId.trim() || !correctPickData.weekNum || !correctPickData.teamAbbr.trim()) {
      setEntryActionMessage('Entry ID, week, and team are required.');
      return;
    }
    try {
      const token = localStorage.getItem('access_token');
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/admin/pools/${leagueId}/entries/${correctPickData.entryId.trim()}/weeks/${correctPickData.weekNum}/pick`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ team: correctPickData.teamAbbr.trim().toUpperCase(), reason: correctPickData.reason.trim() || null }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Unable to correct pick');
      setEntryActionMessage(`Week ${data.week} pick corrected to ${data.team}.`);
      setCorrectPickData({ entryId: '', weekNum: '', teamAbbr: '', reason: '' });
    } catch (err) { setEntryActionMessage(err.message || 'Unable to correct pick'); }
  };

  const handleToggleUserLock = async (userId, currentlyLocked) => {
    setLockMessage('');
    try {
      const token = localStorage.getItem('token');
      const method = currentlyLocked ? 'DELETE' : 'POST';
      const res = await fetch(
        process.env.NEXT_PUBLIC_API_URL + `/admin/pools/${leagueId}/users/${userId}/lock`,
        {
          method,
          headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
          body: method === 'POST' ? JSON.stringify({ reason: 'Unpaid fees' }) : undefined,
        }
      );
      if (!res.ok) throw new Error('Failed to toggle lock');
      setLockMessage(currentlyLocked ? 'User unlocked.' : 'User locked.');
    } catch {
      setLockMessage('Failed to update lock status.');
    }
  };

  const renderLeagueManagement = () => (
    <div className="admin-section admin-section--league" style={{ flex: 1 }}>
      <h3 style={{ color: '#1a202c', marginTop: 0, marginBottom: '2rem' }}>
        League Management
      </h3>

      <div className="admin-access-panel">
        <div>
          <span>Player access</span>
          <h4>Pool Visibility</h4>
          <p>Public pools can be joined by anyone. Private pools require the commissioner password.</p>
        </div>
        <div className="admin-access-panel__options">
          <label className={!accessSettings.is_private ? 'is-selected' : ''}>
            <input
              type="radio"
              name="pool-visibility"
              checked={!accessSettings.is_private}
              onChange={() => setAccessSettings((current) => ({ ...current, is_private: false, join_password: '' }))}
            />
            <span><strong>Public</strong><small>No password required</small></span>
          </label>
          <label className={accessSettings.is_private ? 'is-selected' : ''}>
            <input
              type="radio"
              name="pool-visibility"
              checked={accessSettings.is_private}
              onChange={() => setAccessSettings((current) => ({ ...current, is_private: true }))}
            />
            <span><strong>Private</strong><small>Password required</small></span>
          </label>
        </div>
        {accessSettings.is_private && (
          <div className="admin-access-panel__password">
            <label htmlFor="admin-join-password">Join password</label>
            <input
              id="admin-join-password"
              type="password"
              minLength={6}
              maxLength={72}
              value={accessSettings.join_password}
              onChange={(event) => setAccessSettings((current) => ({ ...current, join_password: event.target.value }))}
              placeholder={league?.is_private ? 'Leave blank to keep current password' : 'At least 6 characters'}
              autoComplete="new-password"
            />
            <small>{league?.is_private ? 'Enter a value only when you want to replace the current password.' : 'A password is required when switching from public to private.'}</small>
          </div>
        )}
        <div className="admin-access-panel__footer">
          <button type="button" onClick={handleSaveAccess} disabled={savingAccess}>
            {savingAccess ? 'Saving…' : 'Save access settings'}
          </button>
          {accessMessage && <span role="status">{accessMessage}</span>}
        </div>
      </div>
      
      {/* View/Search Leagues */}
      <div style={{ marginBottom: '3rem' }}>
        <h4 style={{ color: '#2d3748', marginBottom: '1rem' }}>View Leagues</h4>
        <div style={{ 
          backgroundColor: 'white', 
          padding: '1.5rem', 
          borderRadius: '8px',
          border: '1px solid #e2e8f0'
        }}>
          <div style={{ marginBottom: '1rem' }}>
            <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '500', color: '#374151' }}>
              Search Leagues
            </label>
            <input
              type="text"
              value={leagueSearch}
              onChange={(e) => setLeagueSearch(e.target.value)}
              placeholder="Search by league name..."
              style={{
                width: '100%',
                padding: '0.75rem',
                border: '1px solid #d1d5db',
                borderRadius: '6px',
                fontSize: '1rem'
              }}
            />
          </div>
          <div style={{ maxHeight: '300px', overflowY: 'auto' }}>
            {leagues.filter(l => l.name.toLowerCase().includes(leagueSearch.toLowerCase())).map(league => (
              <div key={league.id} style={{
                padding: '1rem',
                backgroundColor: '#f9fafb',
                borderRadius: '6px',
                marginBottom: '0.5rem',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center'
              }}>
                <div>
                  <div style={{ fontWeight: '600', color: '#1f2937' }}>{league.name}</div>
                  <div style={{ fontSize: '0.875rem', color: '#6b7280' }}>
                    Created: {new Date(league.created_at).toLocaleDateString()}
                  </div>
                </div>
                <button
                  onClick={() => router.push(`/admin/league/${league.id}`)}
                  style={{
                    backgroundColor: '#667eea',
                    color: 'white',
                    padding: '0.5rem 1rem',
                    border: 'none',
                    borderRadius: '4px',
                    cursor: 'pointer',
                    fontSize: '0.875rem'
                  }}
                >
                  Manage
                </button>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Weekly Pick and League Join Locks */}
      <div style={{ marginBottom: '3rem' }}>
        <h4 style={{ color: '#2d3748', marginBottom: '1rem' }}>Pool Lock Time</h4>
        <div style={{ backgroundColor: 'white', padding: '1.5rem', borderRadius: '8px', border: '1px solid #e2e8f0' }}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '1rem', marginBottom: '1rem' }}>
            <div>
              <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '500', color: '#374151' }}>Day of Week</label>
              <select
                value={lockTimeData.day}
                onChange={e => setLockTimeData({ ...lockTimeData, day: Number(e.target.value) })}
                style={{ width: '100%', padding: '0.75rem', border: '1px solid #d1d5db', borderRadius: '6px', fontSize: '1rem' }}
              >
                {DAYS_OF_WEEK.map((day, index) => <option key={day} value={index}>{day}</option>)}
              </select>
            </div>
            <div>
              <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '500', color: '#374151' }}>Time</label>
              <select
                value={lockTimeData.time}
                onChange={e => setLockTimeData({ ...lockTimeData, time: e.target.value })}
                style={{ width: '100%', padding: '0.75rem', border: '1px solid #d1d5db', borderRadius: '6px', fontSize: '1rem' }}
              >
                {Array.from({ length: 48 }, (_, i) => {
                  const h = Math.floor(i / 2);
                  const m = i % 2 === 0 ? '00' : '30';
                  const hh = String(h).padStart(2, '0');
                  const ampm = h < 12 ? 'AM' : 'PM';
                  const h12 = h === 0 ? 12 : h > 12 ? h - 12 : h;
                  return (
                    <option key={i} value={`${hh}:${m}`}>
                      {`${h12}:${m} ${ampm}`}
                    </option>
                  );
                })}
              </select>
            </div>
            <div>
              <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '500', color: '#374151' }}>Timezone</label>
              <select
                value={lockTimeData.timezone}
                onChange={e => setLockTimeData({ ...lockTimeData, timezone: e.target.value })}
                style={{ width: '100%', padding: '0.75rem', border: '1px solid #d1d5db', borderRadius: '6px', fontSize: '1rem' }}
              >
                {TIMEZONES.map(tz => (
                  <option key={tz.iana} value={tz.iana}>{tz.label}</option>
                ))}
              </select>
            </div>
          </div>
          <div style={{ marginTop: '1.4rem', paddingTop: '1.2rem', borderTop: '1px solid #314449' }}>
            <h4 style={{ margin: '0 0 .35rem' }}>League Lock Time</h4>
            <p style={{ margin: '0 0 1rem' }}>After this registration deadline, no new users may join or create their first entry.</p>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '1rem', marginBottom: '1rem' }}>
              <div>
                <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '500' }}>Date</label>
                <input type="date" value={joinLockData.date} onChange={e => setJoinLockData({ ...joinLockData, date: e.target.value })} />
              </div>
              <div>
                <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '500' }}>Time</label>
                <input type="time" value={joinLockData.time} onChange={e => setJoinLockData({ ...joinLockData, time: e.target.value })} />
              </div>
              <div>
                <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '500' }}>Timezone</label>
                <select value={joinLockData.timezone} onChange={e => setJoinLockData({ ...joinLockData, timezone: e.target.value })}>
                  {TIMEZONES.map(tz => <option key={tz.iana} value={tz.iana}>{tz.label}</option>)}
                </select>
              </div>
            </div>
          </div>
          <button
            onClick={handleSetLockTime}
            style={{ backgroundColor: '#3b82f6', color: 'white', padding: '0.75rem 1.5rem', border: 'none', borderRadius: '6px', cursor: 'pointer', fontSize: '1rem', fontWeight: '500' }}
          >
            Save Lock Settings
          </button>
          {lockTimeMessage && <p style={{ marginTop: '0.75rem', fontSize: '0.875rem', color: '#374151' }}>{lockTimeMessage}</p>}
        </div>
      </div>

      {/* Create League */}
      <div style={{ marginBottom: '3rem' }}>
        <h4 style={{ color: '#2d3748', marginBottom: '1rem' }}>Create League</h4>
        <div style={{ 
          backgroundColor: 'white', 
          padding: '1.5rem', 
          borderRadius: '8px',
          border: '1px solid #e2e8f0'
        }}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1rem' }}>
            <div>
              <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '500', color: '#374151' }}>
                League Name
              </label>
              <input
                type="text"
                placeholder="Enter league name"
                style={{
                  width: '100%',
                  padding: '0.75rem',
                  border: '1px solid #d1d5db',
                  borderRadius: '6px',
                  fontSize: '1rem'
                }}
              />
            </div>
            <div>
              <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '500', color: '#374151' }}>
                Lock Time and Date
              </label>
              <input
                type="datetime-local"
                style={{
                  width: '100%',
                  padding: '0.75rem',
                  border: '1px solid #d1d5db',
                  borderRadius: '6px',
                  fontSize: '1rem'
                }}
              />
            </div>
          </div>
          <div style={{ marginBottom: '1rem' }}>
            <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '500', color: '#374151' }}>
              League Settings
            </label>
            <textarea
              placeholder="Enter league settings..."
              rows={3}
              style={{
                width: '100%',
                padding: '0.75rem',
                border: '1px solid #d1d5db',
                borderRadius: '6px',
                fontSize: '1rem',
                resize: 'vertical'
              }}
            />
          </div>
          <div style={{ marginBottom: '1rem' }}>
            <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '500', color: '#374151' }}>
              League Description
            </label>
            <textarea
              placeholder="Enter league description..."
              rows={3}
              style={{
                width: '100%',
                padding: '0.75rem',
                border: '1px solid #d1d5db',
                borderRadius: '6px',
                fontSize: '1rem',
                resize: 'vertical'
              }}
            />
          </div>
          <button
            style={{
              backgroundColor: '#10b981',
              color: 'white',
              padding: '0.75rem 1.5rem',
              border: 'none',
              borderRadius: '6px',
              cursor: 'pointer',
              fontSize: '1rem',
              fontWeight: '500'
            }}
          >
            Create League
          </button>
        </div>
      </div>

      {/* Modify League */}
      <div style={{ marginBottom: '3rem' }}>
        <h4 style={{ color: '#2d3748', marginBottom: '1rem' }}>Modify League</h4>
        <div style={{ 
          backgroundColor: 'white', 
          padding: '1.5rem', 
          borderRadius: '8px',
          border: '1px solid #e2e8f0'
        }}>
          <div style={{ marginBottom: '1rem' }}>
            <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '500', color: '#374151' }}>
              Select League to Modify
            </label>
            <select
              style={{
                width: '100%',
                padding: '0.75rem',
                border: '1px solid #d1d5db',
                borderRadius: '6px',
                fontSize: '1rem'
              }}
            >
              <option value="">Select a league...</option>
              {leagues.map(league => (
                <option key={league.id} value={league.id}>{league.name}</option>
              ))}
            </select>
          </div>
          <button
            style={{
              backgroundColor: '#f59e0b',
              color: 'white',
              padding: '0.75rem 1.5rem',
              border: 'none',
              borderRadius: '6px',
              cursor: 'pointer',
              fontSize: '1rem',
              fontWeight: '500'
            }}
          >
            Modify Selected League
          </button>
        </div>
      </div>

      {/* Delete League */}
      <div style={{ marginBottom: '3rem' }}>
        <h4 style={{ color: '#2d3748', marginBottom: '1rem' }}>Delete League</h4>
        <div style={{ 
          backgroundColor: '#fef2f2', 
          padding: '1.5rem', 
          borderRadius: '8px',
          border: '1px solid #fecaca'
        }}>
          <div style={{ marginBottom: '1rem' }}>
            <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '500', color: '#374151' }}>
              Select League to Delete
            </label>
            <select
              style={{
                width: '100%',
                padding: '0.75rem',
                border: '1px solid #d1d5db',
                borderRadius: '6px',
                fontSize: '1rem'
              }}
            >
              <option value="">Select a league...</option>
              {leagues.map(league => (
                <option key={league.id} value={league.id}>{league.name}</option>
              ))}
            </select>
          </div>
          <div style={{ 
            backgroundColor: '#fee2e2', 
            color: '#991b1b', 
            padding: '1rem', 
            borderRadius: '6px', 
            marginBottom: '1rem',
            fontSize: '0.875rem'
          }}>
            ⚠️ Warning: This action cannot be undone. All entries and data associated with this league will be permanently deleted.
          </div>
          <button
            style={{
              backgroundColor: '#dc2626',
              color: 'white',
              padding: '0.75rem 1.5rem',
              border: 'none',
              borderRadius: '6px',
              cursor: 'pointer',
              fontSize: '1rem',
              fontWeight: '500'
            }}
          >
            Delete Selected League
          </button>
        </div>
      </div>
    </div>
  );

  const handleResetPassword = async () => {
    if (!resetPasswordData.username.trim()) return;
    setResetPasswordMessage('');
    try {
      const res = await fetch(
        process.env.NEXT_PUBLIC_API_URL + '/auth/forgot-password',
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email: resetPasswordData.username.trim() }),
        }
      );
      if (!res.ok) throw new Error('Failed');
      setResetPasswordMessage('Password reset link sent. The user will receive an email with instructions.');
    } catch {
      setResetPasswordMessage('Failed to send reset link. Check that the email address is correct.');
    }
  };

  const handleUserLockLookup = async () => {
    if (!userLockData.email.trim()) return;
    setUserLockMessage('');
    try {
      const token = localStorage.getItem('access_token');
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/admin/pools/${leagueId}/user-lock?email=${encodeURIComponent(userLockData.email.trim())}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Unable to find user');
      setUserLockStatus(data);
      setUserLockData((current) => ({ ...current, email: data.email, reason: data.reason || '' }));
      setUserLockMessage(data.locked ? 'This user is locked in this league.' : 'This user is active in this league.');
    } catch (err) { setUserLockStatus(null); setUserLockMessage(err.message || 'Unable to find user'); }
  };

  const handleSetUserLock = async (locked) => {
    try {
      const token = localStorage.getItem('access_token');
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/admin/pools/${leagueId}/user-lock`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ email: userLockData.email.trim(), locked, reason: userLockData.reason.trim() || null }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Unable to update user lock');
      setUserLockStatus(data);
      setUserLockMessage(locked ? 'User locked in this league.' : 'User unlocked in this league.');
    } catch (err) { setUserLockMessage(err.message || 'Unable to update user lock'); }
  };

  const renderUserManagement = () => (
    <div className="admin-section admin-section--users" style={{ flex: 1 }}>
      <h3 style={{ color: '#1a202c', marginTop: 0, marginBottom: '2rem' }}>
        User Management
      </h3>

      <AdminUserOverview overview={userOverview} loading={userOverviewLoading} error={userOverviewError} onRefresh={fetchUserOverview} />

      <div style={{ marginBottom: '3rem' }}>
        <h4>Lock User Account</h4>
        <div>
          <p>Prevent a user from creating, deleting, or changing entries and picks in this league. Their login and other leagues remain available.</p>
          <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '1rem', marginBottom: '1rem' }}>
            <div>
              <label>Email Address</label>
              <input type="email" value={userLockData.email} onChange={(e) => { setUserLockData({ ...userLockData, email: e.target.value }); setUserLockStatus(null); }} placeholder="player@example.com" />
            </div>
            <div>
              <label>Reason</label>
              <input type="text" value={userLockData.reason} onChange={(e) => setUserLockData({ ...userLockData, reason: e.target.value })} placeholder="Optional reason" />
            </div>
          </div>
          <div style={{ display: 'flex', gap: '.6rem', flexWrap: 'wrap' }}>
            <button type="button" onClick={handleUserLockLookup}>Find User</button>
            <button type="button" disabled={!userLockStatus || userLockStatus.locked} onClick={() => handleSetUserLock(true)}>Lock User</button>
            <button type="button" disabled={!userLockStatus || !userLockStatus.locked} onClick={() => handleSetUserLock(false)}>Unlock User</button>
          </div>
          {userLockMessage && <p role="status" style={{ marginTop: '.8rem' }}>{userLockMessage}</p>}
        </div>
      </div>
      
      {/* Reset User Password */}
      <div style={{ marginBottom: '3rem' }}>
        <h4 style={{ color: '#2d3748', marginBottom: '1rem' }}>Reset User Password</h4>
        <div style={{ 
          backgroundColor: 'white', 
          padding: '1.5rem', 
          borderRadius: '8px',
          border: '1px solid #e2e8f0'
        }}>
          <div style={{ marginBottom: '1rem' }}>
            <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '500', color: '#374151' }}>
              Username
            </label>
            <input
              type="text"
              value={resetPasswordData.username}
              onChange={(e) => setResetPasswordData({...resetPasswordData, username: e.target.value})}
              placeholder="Enter username or email"
              style={{
                width: '100%',
                padding: '0.75rem',
                border: '1px solid #d1d5db',
                borderRadius: '6px',
                fontSize: '1rem'
              }}
            />
          </div>
          <button
            onClick={handleResetPassword}
            style={{
              backgroundColor: '#3b82f6',
              color: 'white',
              padding: '0.75rem 1.5rem',
              border: 'none',
              borderRadius: '6px',
              cursor: 'pointer',
              fontSize: '1rem',
              fontWeight: '500'
            }}
          >
            Reset Password
          </button>
          {resetPasswordMessage && (
            <p style={{ marginTop: '0.75rem', fontSize: '0.875rem', color: '#374151' }}>
              {resetPasswordMessage}
            </p>
          )}
        </div>
      </div>

      {/* Update User Email */}
      <div style={{ marginBottom: '3rem' }}>
        <h4 style={{ color: '#2d3748', marginBottom: '1rem' }}>Update User Email</h4>
        <div style={{ 
          backgroundColor: 'white', 
          padding: '1.5rem', 
          borderRadius: '8px',
          border: '1px solid #e2e8f0'
        }}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1rem' }}>
            <div>
              <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '500', color: '#374151' }}>
                Username
              </label>
              <input
                type="text"
                value={updateEmailData.username}
                onChange={(e) => setUpdateEmailData({...updateEmailData, username: e.target.value})}
                placeholder="Enter username"
                style={{
                  width: '100%',
                  padding: '0.75rem',
                  border: '1px solid #d1d5db',
                  borderRadius: '6px',
                  fontSize: '1rem'
                }}
              />
            </div>
            <div>
              <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '500', color: '#374151' }}>
                New Email Address
              </label>
              <input
                type="email"
                value={updateEmailData.newEmail}
                onChange={(e) => setUpdateEmailData({...updateEmailData, newEmail: e.target.value})}
                placeholder="Enter new email address"
                style={{
                  width: '100%',
                  padding: '0.75rem',
                  border: '1px solid #d1d5db',
                  borderRadius: '6px',
                  fontSize: '1rem'
                }}
              />
            </div>
          </div>
          <button
            style={{
              backgroundColor: '#10b981',
              color: 'white',
              padding: '0.75rem 1.5rem',
              border: 'none',
              borderRadius: '6px',
              cursor: 'pointer',
              fontSize: '1rem',
              fontWeight: '500'
            }}
          >
            Update Email
          </button>
        </div>
      </div>

      {/* Delete User */}
      <div style={{ marginBottom: '3rem' }}>
        <h4 style={{ color: '#2d3748', marginBottom: '1rem' }}>Delete User</h4>
        <div style={{ 
          backgroundColor: '#fef2f2', 
          padding: '1.5rem', 
          borderRadius: '8px',
          border: '1px solid #fecaca'
        }}>
          <div style={{ 
            backgroundColor: '#fee2e2', 
            color: '#991b1b', 
            padding: '1rem', 
            borderRadius: '6px', 
            marginBottom: '1rem',
            fontSize: '0.875rem'
          }}>
            ⚠️ Warning: This will permanently delete the user and all their entries. This action cannot be undone.
          </div>
          <div style={{ marginBottom: '1rem' }}>
            <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '500', color: '#374151' }}>
              Username
            </label>
            <input
              type="text"
              value={deleteUserData.username}
              onChange={(e) => setDeleteUserData({...deleteUserData, username: e.target.value})}
              placeholder="Enter username to delete"
              style={{
                width: '100%',
                padding: '0.75rem',
                border: '1px solid #d1d5db',
                borderRadius: '6px',
                fontSize: '1rem'
              }}
            />
          </div>
          <button
            style={{
              backgroundColor: '#dc2626',
              color: 'white',
              padding: '0.75rem 1.5rem',
              border: 'none',
              borderRadius: '6px',
              cursor: 'pointer',
              fontSize: '1rem',
              fontWeight: '500'
            }}
          >
            Delete User
          </button>
        </div>
      </div>

      {/* Assign Administrator Access */}
      <div style={{ marginBottom: '3rem' }}>
        <h4 style={{ color: '#2d3748', marginBottom: '1rem' }}>Assign Administrator Access</h4>
        <div style={{ 
          backgroundColor: 'white', 
          padding: '1.5rem', 
          borderRadius: '8px',
          border: '1px solid #e2e8f0'
        }}>
          <div style={{ marginBottom: '1rem' }}>
            <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '500', color: '#374151' }}>
              Username
            </label>
            <input
              type="text"
              value={assignAdminData.username}
              onChange={(e) => setAssignAdminData({...assignAdminData, username: e.target.value})}
              placeholder="Enter username to grant admin access"
              style={{
                width: '100%',
                padding: '0.75rem',
                border: '1px solid #d1d5db',
                borderRadius: '6px',
                fontSize: '1rem'
              }}
            />
          </div>
          <div style={{ 
            backgroundColor: '#fef3c7', 
            color: '#92400e', 
            padding: '1rem', 
            borderRadius: '6px', 
            marginBottom: '1rem',
            fontSize: '0.875rem'
          }}>
            ⚠️ Confirm: This user should have administrator access to this league.
          </div>
          <button
            style={{
              backgroundColor: '#f59e0b',
              color: 'white',
              padding: '0.75rem 1.5rem',
              border: 'none',
              borderRadius: '6px',
              cursor: 'pointer',
              fontSize: '1rem',
              fontWeight: '500'
            }}
          >
            Grant Admin Access
          </button>
        </div>
      </div>
    </div>
  );

  const renderEntryManagement = () => (
    <div className="admin-section admin-section--entries" style={{ flex: 1 }}>
      <h3 style={{ color: '#1a202c', marginTop: 0, marginBottom: '2rem' }}>
        Entry Management
      </h3>
      {entryActionMessage && <div className="admin-entry-feedback" role="status">{entryActionMessage}</div>}
      
      {/* CSV Export */}
      <div style={{ marginBottom: '3rem' }}>
        <h4 style={{ color: '#2d3748', marginBottom: '1rem' }}>Export Entries</h4>
        <div style={{ backgroundColor: 'white', padding: '1.5rem', borderRadius: '8px', border: '1px solid #e2e8f0' }}>
          <p style={{ color: '#4a5568', marginBottom: '1rem' }}>Download a CSV of all participant emails and entry names for this pool.</p>
          <button
            onClick={async () => {
              setEntryActionMessage('Preparing export…');
              const token = localStorage.getItem('access_token');
              const res = await fetch(
                process.env.NEXT_PUBLIC_API_URL + `/admin/pools/${leagueId}/export/entries.csv`,
                { headers: { Authorization: `Bearer ${token}` } }
              );
              if (res.ok) {
                const blob = await res.blob();
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = 'entries.csv';
                a.click();
                URL.revokeObjectURL(url);
                setEntryActionMessage('Entries CSV downloaded.');
              } else {
                const data = await res.json();
                setEntryActionMessage(data.detail || 'Unable to export entries.');
              }
            }}
            style={{ backgroundColor: '#059669', color: 'white', padding: '0.75rem 1.5rem', border: 'none', borderRadius: '6px', cursor: 'pointer', fontSize: '1rem', fontWeight: '500' }}
          >
            Export CSV
          </button>
        </div>
      </div>

      {/* Entry ID Lookup */}
      <div style={{ marginBottom: '3rem' }}>
        <h4 style={{ color: '#2d3748', marginBottom: '1rem' }}>Entry ID Lookup</h4>
        <div style={{ 
          backgroundColor: 'white', 
          padding: '1.5rem', 
          borderRadius: '8px',
          border: '1px solid #e2e8f0'
        }}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1rem' }}>
            <div>
              <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '500', color: '#374151' }}>
                Username (optional)
              </label>
              <input
                type="text"
                value={entryLookupData.username}
                onChange={(e) => setEntryLookupData({...entryLookupData, username: e.target.value})}
                placeholder="Enter username to search by"
                style={{
                  width: '100%',
                  padding: '0.75rem',
                  border: '1px solid #d1d5db',
                  borderRadius: '6px',
                  fontSize: '1rem'
                }}
              />
            </div>
            <div>
              <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '500', color: '#374151' }}>
                Entry Name (optional)
              </label>
              <input
                type="text"
                value={entryLookupData.entryName}
                onChange={(e) => setEntryLookupData({...entryLookupData, entryName: e.target.value})}
                placeholder="Enter entry name to search by"
                style={{
                  width: '100%',
                  padding: '0.75rem',
                  border: '1px solid #d1d5db',
                  borderRadius: '6px',
                  fontSize: '1rem'
                }}
              />
            </div>
          </div>
          
          <div style={{ marginBottom: '1rem' }}>
            <button
              onClick={handleEntryLookup}
              style={{
                backgroundColor: '#059669',
                color: 'white',
                padding: '0.75rem 1.5rem',
                border: 'none',
                borderRadius: '6px',
                cursor: 'pointer',
                fontSize: '1rem',
                fontWeight: '500',
                marginRight: '1rem'
              }}
            >
              Search Entries
            </button>
            
            <button
              onClick={() => {
                setEntryLookupData({ username: '', entryName: '' });
                setLookupResults([]);
              }}
              style={{
                backgroundColor: '#6b7280',
                color: 'white',
                padding: '0.75rem 1.5rem',
                border: 'none',
                borderRadius: '6px',
                cursor: 'pointer',
                fontSize: '1rem',
                fontWeight: '500'
              }}
            >
              Clear
            </button>
          </div>

          {/* Search Results */}
          {lookupResults.length > 0 && (
            <div style={{ 
              backgroundColor: '#f9fafb', 
              padding: '1rem', 
              borderRadius: '6px',
              border: '1px solid #e5e7eb'
            }}>
              <h5 style={{ margin: '0 0 1rem 0', color: '#374151', fontWeight: '600' }}>
                Search Results ({lookupResults.length} found):
              </h5>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                {lookupResults.map((entry) => (
                  <div 
                    key={entry.id}
                    style={{
                      backgroundColor: 'white',
                      padding: '0.75rem',
                      borderRadius: '4px',
                      border: '1px solid #d1d5db',
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center'
                    }}
                  >
                    <div>
                      <strong>Entry ID:</strong> <code style={{ backgroundColor: '#f3f4f6', padding: '2px 6px', borderRadius: '3px' }}>{entry.id}</code><br/>
                      <strong>Entry Name:</strong> {entry.name}<br/>
                      <strong>Owner:</strong> {entry.owner_email}
                      <div style={{ marginTop: '0.5rem' }}>
                        <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
                          <input
                            type="checkbox"
                            checked={entry.locked || false}
                            onChange={() => handleToggleUserLock(entry.user_id, entry.locked || false)}
                          />
                          <span style={{ fontSize: '0.875rem', color: '#374151' }}>Lock user in this pool</span>
                        </label>
                        {lockMessage && <p style={{ fontSize: '0.75rem', color: '#6b7280', marginTop: '0.25rem' }}>{lockMessage}</p>}
                      </div>
                    </div>
                    <button
                      onClick={() => {
                        navigator.clipboard.writeText(entry.id);
                        // Could add a toast notification here
                      }}
                      style={{
                        backgroundColor: '#3b82f6',
                        color: 'white',
                        padding: '0.25rem 0.5rem',
                        border: 'none',
                        borderRadius: '4px',
                        cursor: 'pointer',
                        fontSize: '0.75rem'
                      }}
                    >
                      Copy ID
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}

          {lookupResults.length === 0 && entryLookupData.username || entryLookupData.entryName ? (
            <div style={{ 
              backgroundColor: '#fef3c7', 
              color: '#92400e', 
              padding: '1rem', 
              borderRadius: '6px',
              fontSize: '0.875rem'
            }}>
              No entries found matching the search criteria.
            </div>
          ) : null}
        </div>
      </div>
      
      {/* Transfer Entries */}
      <div style={{ marginBottom: '3rem' }}>
        <h4 style={{ color: '#2d3748', marginBottom: '1rem' }}>Transfer Entries</h4>
        <div style={{ 
          backgroundColor: 'white', 
          padding: '1.5rem', 
          borderRadius: '8px',
          border: '1px solid #e2e8f0'
        }}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '1rem', marginBottom: '1rem' }}>
            <div>
              <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '500', color: '#374151' }}>
                Entry ID
              </label>
              <input
                type="text"
                value={transferEntryData.entryId}
                onChange={(e) => setTransferEntryData({...transferEntryData, entryId: e.target.value})}
                placeholder="Enter entry ID"
                style={{
                  width: '100%',
                  padding: '0.75rem',
                  border: '1px solid #d1d5db',
                  borderRadius: '6px',
                  fontSize: '1rem'
                }}
              />
            </div>
            <div>
              <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '500', color: '#374151' }}>
                Current Owner (reference)
              </label>
              <input
                type="text"
                value={transferEntryData.fromUser}
                onChange={(e) => setTransferEntryData({...transferEntryData, fromUser: e.target.value})}
                placeholder="Current owner username"
                style={{
                  width: '100%',
                  padding: '0.75rem',
                  border: '1px solid #d1d5db',
                  borderRadius: '6px',
                  fontSize: '1rem'
                }}
              />
            </div>
            <div>
              <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '500', color: '#374151' }}>
                New Owner Email
              </label>
              <input
                type="text"
                value={transferEntryData.toUser}
                onChange={(e) => setTransferEntryData({...transferEntryData, toUser: e.target.value})}
                placeholder="new-owner@example.com"
                style={{
                  width: '100%',
                  padding: '0.75rem',
                  border: '1px solid #d1d5db',
                  borderRadius: '6px',
                  fontSize: '1rem'
                }}
              />
            </div>
          </div>
          <button
            onClick={handleTransferEntry}
            style={{
              backgroundColor: '#3b82f6',
              color: 'white',
              padding: '0.75rem 1.5rem',
              border: 'none',
              borderRadius: '6px',
              cursor: 'pointer',
              fontSize: '1rem',
              fontWeight: '500'
            }}
          >
            Transfer Entry
          </button>
        </div>
      </div>

      {/* Delete Entries */}
      <div style={{ marginBottom: '3rem' }}>
        <h4 style={{ color: '#2d3748', marginBottom: '1rem' }}>Delete Entries</h4>
        <div style={{ 
          backgroundColor: '#fef2f2', 
          padding: '1.5rem', 
          borderRadius: '8px',
          border: '1px solid #fecaca'
        }}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1rem' }}>
            <div>
              <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '500', color: '#374151' }}>
                Entry ID
              </label>
              <input
                type="text"
                value={deleteEntryData.entryId}
                onChange={(e) => setDeleteEntryData({...deleteEntryData, entryId: e.target.value})}
                placeholder="Enter entry ID"
                style={{
                  width: '100%',
                  padding: '0.75rem',
                  border: '1px solid #d1d5db',
                  borderRadius: '6px',
                  fontSize: '1rem'
                }}
              />
            </div>
            <div>
              <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '500', color: '#374151' }}>
                Owner Email (reference)
              </label>
              <input
                type="text"
                value={deleteEntryData.username}
                onChange={(e) => setDeleteEntryData({...deleteEntryData, username: e.target.value})}
                placeholder="Entry owner username"
                style={{
                  width: '100%',
                  padding: '0.75rem',
                  border: '1px solid #d1d5db',
                  borderRadius: '6px',
                  fontSize: '1rem'
                }}
              />
            </div>
          </div>
          <div style={{ 
            backgroundColor: '#fee2e2', 
            color: '#991b1b', 
            padding: '1rem', 
            borderRadius: '6px', 
            marginBottom: '1rem',
            fontSize: '0.875rem'
          }}>
            Warning: This will permanently delete the entry and all associated picks. This action cannot be undone.
          </div>
          <button
            onClick={handleDeleteEntry}
            style={{
              backgroundColor: '#dc2626',
              color: 'white',
              padding: '0.75rem 1.5rem',
              border: 'none',
              borderRadius: '6px',
              cursor: 'pointer',
              fontSize: '1rem',
              fontWeight: '500'
            }}
          >
            Delete Entry
          </button>
        </div>
      </div>

      {/* Correct Pick */}
      <div style={{ marginBottom: '3rem' }}>
        <h4 style={{ color: '#2d3748', marginBottom: '1rem' }}>Correct Pick</h4>
        <div style={{ 
          backgroundColor: 'white', 
          padding: '1.5rem', 
          borderRadius: '8px',
          border: '1px solid #e2e8f0'
        }}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '1rem', marginBottom: '1rem' }}>
            <div>
              <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '500', color: '#374151' }}>
                Entry ID
              </label>
              <input
                type="text"
                value={correctPickData.entryId}
                onChange={(e) => setCorrectPickData({...correctPickData, entryId: e.target.value})}
                placeholder="Enter entry ID"
                style={{
                  width: '100%',
                  padding: '0.75rem',
                  border: '1px solid #d1d5db',
                  borderRadius: '6px',
                  fontSize: '1rem'
                }}
              />
            </div>
            <div>
              <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '500', color: '#374151' }}>
                Week Number
              </label>
              <input
                type="number"
                min="1"
                max="18"
                value={correctPickData.weekNum}
                onChange={(e) => setCorrectPickData({...correctPickData, weekNum: e.target.value})}
                placeholder="1-18"
                style={{
                  width: '100%',
                  padding: '0.75rem',
                  border: '1px solid #d1d5db',
                  borderRadius: '6px',
                  fontSize: '1rem'
                }}
              />
            </div>
            <div>
              <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '500', color: '#374151' }}>
                Team Abbreviation
              </label>
              <input
                type="text"
                value={correctPickData.teamAbbr}
                onChange={(e) => setCorrectPickData({...correctPickData, teamAbbr: e.target.value})}
                placeholder="e.g., NE, GB, DAL"
                style={{
                  width: '100%',
                  padding: '0.75rem',
                  border: '1px solid #d1d5db',
                  borderRadius: '6px',
                  fontSize: '1rem'
                }}
              />
            </div>
          </div>
          <div style={{ marginBottom: '1rem' }}>
            <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '500', color: '#374151' }}>
              Reason for Correction
            </label>
            <textarea
              value={correctPickData.reason}
              onChange={(e) => setCorrectPickData({...correctPickData, reason: e.target.value})}
              placeholder="Enter reason for this pick correction..."
              rows={3}
              style={{
                width: '100%',
                padding: '0.75rem',
                border: '1px solid #d1d5db',
                borderRadius: '6px',
                fontSize: '1rem',
                resize: 'vertical'
              }}
            />
          </div>
          <button
            onClick={handleCorrectPick}
            style={{
              backgroundColor: '#f59e0b',
              color: 'white',
              padding: '0.75rem 1.5rem',
              border: 'none',
              borderRadius: '6px',
              cursor: 'pointer',
              fontSize: '1rem',
              fontWeight: '500'
            }}
          >
            Correct Pick
          </button>
        </div>
      </div>
    </div>
  );

  const renderAuditLog = () => (
    <div className="admin-section admin-section--audit" style={{ flex: 1 }}>
      <h3 style={{ color: '#1a202c', marginTop: 0, marginBottom: '2rem' }}>
        Audit Log
      </h3>
      
      {/* Search Audit Log */}
      <div style={{ marginBottom: '3rem' }}>
        <h4 style={{ color: '#2d3748', marginBottom: '1rem' }}>Search Audit Log</h4>
        <div style={{ 
          backgroundColor: 'white', 
          padding: '1.5rem', 
          borderRadius: '8px',
          border: '1px solid #e2e8f0'
        }}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1rem' }}>
            <div>
              <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '500', color: '#374151' }}>
                Username
              </label>
              <input
                type="text"
                value={auditSearch.username}
                onChange={(e) => setAuditSearch({...auditSearch, username: e.target.value})}
                placeholder="Enter username or email"
                style={{
                  width: '100%',
                  padding: '0.75rem',
                  border: '1px solid #d1d5db',
                  borderRadius: '6px',
                  fontSize: '1rem'
                }}
              />
            </div>
            <div>
              <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '500', color: '#374151' }}>
                Action Contains Text
              </label>
              <input
                type="text"
                value={auditSearch.actionSearch}
                onChange={(e) => setAuditSearch({...auditSearch, actionSearch: e.target.value})}
                placeholder="Fuzzy search in action description"
                style={{
                  width: '100%',
                  padding: '0.75rem',
                  border: '1px solid #d1d5db',
                  borderRadius: '6px',
                  fontSize: '1rem'
                }}
              />
            </div>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1rem' }}>
            <div>
              <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '500', color: '#374151' }}>
                Date From
              </label>
              <input
                type="date"
                value={auditSearch.dateFrom}
                onChange={(e) => setAuditSearch({...auditSearch, dateFrom: e.target.value})}
                style={{
                  width: '100%',
                  padding: '0.75rem',
                  border: '1px solid #d1d5db',
                  borderRadius: '6px',
                  fontSize: '1rem'
                }}
              />
            </div>
            <div>
              <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '500', color: '#374151' }}>
                Date To
              </label>
              <input
                type="date"
                value={auditSearch.dateTo}
                onChange={(e) => setAuditSearch({...auditSearch, dateTo: e.target.value})}
                style={{
                  width: '100%',
                  padding: '0.75rem',
                  border: '1px solid #d1d5db',
                  borderRadius: '6px',
                  fontSize: '1rem'
                }}
              />
            </div>
          </div>
          <button
            onClick={() => fetchAuditLogs()}
            disabled={auditLoading}
            style={{
              backgroundColor: '#3b82f6',
              color: 'white',
              padding: '0.75rem 1.5rem',
              border: 'none',
              borderRadius: '6px',
              cursor: 'pointer',
              fontSize: '1rem',
              fontWeight: '500',
              marginRight: '1rem'
            }}
          >
            {auditLoading ? 'Searching…' : 'Search Audit Log'}
          </button>
          <button
            onClick={() => {
              const emptySearch = { username: '', dateFrom: '', dateTo: '', actionSearch: '' };
              setAuditSearch(emptySearch);
              fetchAuditLogs(emptySearch);
            }}
            style={{
              backgroundColor: '#6b7280',
              color: 'white',
              padding: '0.75rem 1.5rem',
              border: 'none',
              borderRadius: '6px',
              cursor: 'pointer',
              fontSize: '1rem',
              fontWeight: '500'
            }}
          >
            Clear Search
          </button>
        </div>
      </div>

      {/* Audit Log Results */}
      <div style={{ marginBottom: '3rem' }}>
        <h4 style={{ color: '#2d3748', marginBottom: '1rem' }}>Audit Log Results</h4>
        <div style={{ 
          backgroundColor: 'white', 
          padding: '1.5rem', 
          borderRadius: '8px',
          border: '1px solid #e2e8f0'
        }}>
          {auditError ? (
            <div style={{ padding: '1rem', color: '#ef4444' }}>{auditError}</div>
          ) : auditLoading ? (
            <div style={{ padding: '2rem', textAlign: 'center' }}>Loading audit events…</div>
          ) : auditLogs.length === 0 ? (
            <div style={{
              textAlign: 'center',
              padding: '3rem',
              color: '#6b7280'
            }}>
              <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>📊</div>
              <h4 style={{ color: '#4a5568', marginBottom: '0.5rem' }}>No audit logs found</h4>
              <p>No pick activity matches this league and search.</p>
            </div>
          ) : (
            <div style={{ maxHeight: '400px', overflowY: 'auto' }}>
              {auditLogs.map((log) => {
                const details = parseAuditDetails(log.details);
                const data = details?.additional_data || {};
                const pickData = data.changes?.context || data;
                const teamChange = data.changes?.team;
                const pickedTeam = pickData.team_name || pickData.team;
                const oldTeam = pickData.old_team_name || data.changes?.old_team_name || teamChange?.old || data.changes?.old_team;
                const newTeam = pickData.new_team_name || data.changes?.new_team_name || teamChange?.new || data.changes?.new_team;
                const pickSummary = log.action === 'UPDATE_PICK' && oldTeam && newTeam
                  ? `Changed pick from ${oldTeam} to ${newTeam}`
                  : pickedTeam
                    ? `${log.action === 'DELETE_PICK' ? 'Deleted pick' : 'Picked'} ${pickedTeam}`
                    : null;
                return (
                <div key={log.id} style={{
                  padding: '1rem',
                  backgroundColor: '#f9fafb',
                  borderRadius: '6px',
                  marginBottom: '0.5rem',
                  borderLeft: '4px solid #3b82f6'
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.5rem' }}>
                    <div style={{ fontWeight: '600', color: '#1f2937' }}>
                      {log.action || 'Unknown Action'}
                    </div>
                    <div style={{ fontSize: '0.875rem', color: '#6b7280' }}>
                      {log.created_at ? new Date(log.created_at).toLocaleString() : 'Unknown Time'}
                    </div>
                  </div>
                  <div style={{ fontSize: '0.875rem', color: '#4b5563', marginBottom: '0.25rem' }}>
                    Username: {getAuditUsername(log, details)}
                  </div>
                  {pickData.entry_name && (
                    <div style={{ fontSize: '0.875rem', color: '#4b5563', marginBottom: '0.25rem' }}>
                      Entry: {pickData.entry_name}
                    </div>
                  )}
                  {pickSummary && (
                    <div style={{ fontSize: '0.9rem', color: '#1f2937', fontWeight: '600', marginTop: '0.4rem' }}>
                      {pickSummary}
                    </div>
                  )}
                  {details?.description && (
                    <div style={{ fontSize: '0.875rem', color: '#6b7280' }}>
                      {details.description}
                    </div>
                  )}
                  {pickData?.week && (
                    <div style={{ fontSize: '0.8rem', color: '#6b7280', marginTop: '0.4rem' }}>
                      Week {pickData.week}
                    </div>
                  )}
                </div>
              )})}
            </div>
          )}
        </div>
      </div>
    </div>
  );

  const renderContent = () => {
    switch (activeSection) {
      case 'league-management':
        return renderLeagueManagement();
      case 'user-management':
        return renderUserManagement();
      case 'entry-management':
        return renderEntryManagement();
      case 'audit-log':
        return renderAuditLog();
      default:
        return renderLeagueManagement();
    }
  };

  if (!router.isReady || loading) {
    return (
      <ProtectedRoute>
        <div style={{ 
          minHeight: '100vh', 
          background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center'
        }}>
          <div style={{ color: 'white', fontSize: '1.2rem' }}>Loading Admin Portal...</div>
        </div>
      </ProtectedRoute>
    );
  }

  return (
    <ProtectedRoute>
      <div className="product-page admin-page" style={{
        minHeight: '100vh', 
        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)', 
        padding: '2rem 1rem'
      }}>
        <main className="product-main admin-main" style={{ maxWidth: '1400px', margin: '0 auto' }}>
          <PoolWorkspaceNav poolId={leagueId} poolName={league?.name} active="admin" showAdmin />
          <WorkspaceHeader
            eyebrow="Commissioner control room"
            title={league?.name || 'Pool administration'}
            description="Run the pool, support players, manage entries, and review every recorded action."
            meta="Commissioner access"
          />
          {error && (
            <div style={{
              backgroundColor: '#fed7d7',
              color: '#742a2a',
              padding: '1rem',
              borderRadius: '8px',
              marginBottom: '2rem',
              border: '1px solid #fc8181'
            }}>
              {error}
            </div>
          )}
          
          <div className="admin-workspace" style={{ display: 'flex', gap: '2rem', alignItems: 'flex-start' }}>
            {renderSidebar()}
            <section className="product-panel admin-content" style={{
              flex: 1,
              backgroundColor: 'rgba(255, 255, 255, 0.1)',
              backdropFilter: 'blur(10px)',
              borderRadius: '12px',
              padding: '2rem',
              border: '1px solid rgba(255, 255, 255, 0.2)',
              color: 'white'
            }}>
              {renderContent()}
            </section>
          </div>
        </main>
      </div>
    </ProtectedRoute>
  );
}
