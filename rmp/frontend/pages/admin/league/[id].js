import { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import ProtectedRoute from '../../../components/ProtectedRoute';
import { useAuth } from '../../../context/AuthContext';
import { PoolWorkspaceNav, WorkspaceHeader } from '../../../components/ProductWorkspace';
import AdminUserOverview from '../../../components/AdminUserOverview';
import AdminAutoPickReport from '../../../components/AdminAutoPickReport';
import AdminAccessControl from '../../../components/AdminAccessControl';
import OwnershipTransferControl from '../../../components/OwnershipTransferControl';
import LeagueLockSettings from '../../../components/LeagueLockSettings';
import LeaguePasswordViewer from '../../../components/LeaguePasswordViewer';
import { getAuditUsername } from '../../../utils/auditDisplay';
import { downloadAuditCsv } from '../../../utils/auditCsv';

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
  const [passwordChanged, setPasswordChanged] = useState(0);
  
  // User Management State
  const [resetPasswordData, setResetPasswordData] = useState({ username: '' });
  const [resetPasswordMessage, setResetPasswordMessage] = useState('');
  const [userLockData, setUserLockData] = useState({ email: '', reason: '' });
  const [userLockStatus, setUserLockStatus] = useState(null);
  const [userLockMessage, setUserLockMessage] = useState('');
  const [userOverview, setUserOverview] = useState(null);
  const [userOverviewLoading, setUserOverviewLoading] = useState(false);
  const [userOverviewError, setUserOverviewError] = useState('');
  const [autoPickWeek, setAutoPickWeek] = useState(1);
  const [autoPicks, setAutoPicks] = useState([]);
  const [autoPicksLoading, setAutoPicksLoading] = useState(false);
  const [autoPicksError, setAutoPicksError] = useState('');

  // User lock state
  const [lockMessage, setLockMessage] = useState('');

  const [deleteUserData, setDeleteUserData] = useState({ username: '' });
  
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

  useEffect(() => {
    if (activeSection === 'user-management' && leagueId) fetchAutoPicks(autoPickWeek);
  }, [activeSection, leagueId, autoPickWeek]);

  const fetchUserOverview = async () => {
    setUserOverviewLoading(true);
    setUserOverviewError('');
    try {
      const token = localStorage.getItem('access_token');
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/admin/pools/${leagueId}/users-overview`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || 'Unable to load pool users');
      setUserOverview(data);
    } catch (err) {
      setUserOverviewError(err.message || 'Unable to load pool users');
    } finally {
      setUserOverviewLoading(false);
    }
  };

  const fetchAutoPicks = async (week) => {
    setAutoPicksLoading(true);
    setAutoPicksError('');
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/admin/pools/${leagueId}/auto-picks?week=${week}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await response.json().catch(() => []);
      if (!response.ok) throw new Error(data.detail || 'Unable to load autopicks');
      setAutoPicks(data);
    } catch (err) {
      setAutoPicks([]);
      setAutoPicksError(err.message || 'Unable to load autopicks');
    } finally {
      setAutoPicksLoading(false);
    }
  };

  const handleChangeUserEmail = async (account) => {
    const email = window.prompt('Enter the new login email address', account.email)?.trim().toLowerCase();
    if (!email || email === account.email) return;
    setUserOverviewError('');
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/admin/pools/${leagueId}/users/${account.id}/email?email=${encodeURIComponent(email)}`,
        { method: 'PATCH', headers: { Authorization: `Bearer ${token}` } },
      );
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.detail || 'Unable to change login email');
      await fetchUserOverview();
    } catch (err) {
      setUserOverviewError(err.message || 'Unable to change login email');
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
      } else {
        setError('Failed to load pool details');
      }
    } catch (err) {
      setError('Failed to load pool details');
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
      console.error('Failed to load all pools');
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
      const changedPassword = Boolean(accessSettings.is_private && accessSettings.join_password);
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
      if (changedPassword) setPasswordChanged((current) => current + 1);
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
          <span>Managing pool</span>
          <strong>{league.name}</strong>
        </div>
      )}
      
      <nav aria-label="Admin sections">
        {[
          { id: 'league-management', label: 'Pool Management', marker: 'PL' },
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

  const handleSaveLockSettings = async (updates) => {
    const token = localStorage.getItem('access_token');
    const res = await fetch(process.env.NEXT_PUBLIC_API_URL + `/pools/${leagueId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
      body: JSON.stringify(updates),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.detail || 'Unable to update lock settings.');
    setLeague(data);
    return data;
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
        Pool Management
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
            <LeaguePasswordViewer
              poolId={leagueId}
              isPrivate={accessSettings.is_private}
              passwordChanged={passwordChanged}
            />
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
        <h4 style={{ color: '#2d3748', marginBottom: '1rem' }}>View Pools</h4>
        <div style={{ 
          backgroundColor: 'white', 
          padding: '1.5rem', 
          borderRadius: '8px',
          border: '1px solid #e2e8f0'
        }}>
          <div style={{ marginBottom: '1rem' }}>
            <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '500', color: '#374151' }}>
              Search Pools
            </label>
            <input
              type="text"
              value={leagueSearch}
              onChange={(e) => setLeagueSearch(e.target.value)}
              placeholder="Search by pool name..."
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

      <LeagueLockSettings league={league} onSave={handleSaveLockSettings} />

      {/* Create League */}
      <div style={{ marginBottom: '3rem' }}>
        <h4 style={{ color: '#2d3748', marginBottom: '1rem' }}>Create Pool</h4>
        <div style={{ 
          backgroundColor: 'white', 
          padding: '1.5rem', 
          borderRadius: '8px',
          border: '1px solid #e2e8f0'
        }}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1rem' }}>
            <div>
              <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '500', color: '#374151' }}>
                Pool Name
              </label>
              <input
                type="text"
                placeholder="Enter pool name"
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
              Pool Settings
            </label>
            <textarea
              placeholder="Enter pool settings..."
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
              Pool Description
            </label>
            <textarea
              placeholder="Enter pool description..."
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
            Create Pool
          </button>
        </div>
      </div>

      {/* Modify League */}
      <div style={{ marginBottom: '3rem' }}>
        <h4 style={{ color: '#2d3748', marginBottom: '1rem' }}>Modify Pool</h4>
        <div style={{ 
          backgroundColor: 'white', 
          padding: '1.5rem', 
          borderRadius: '8px',
          border: '1px solid #e2e8f0'
        }}>
          <div style={{ marginBottom: '1rem' }}>
            <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '500', color: '#374151' }}>
              Select Pool to Modify
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
              <option value="">Select a pool...</option>
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
            Modify Selected Pool
          </button>
        </div>
      </div>

      {/* Delete League */}
      <div style={{ marginBottom: '3rem' }}>
        <h4 style={{ color: '#2d3748', marginBottom: '1rem' }}>Delete Pool</h4>
        <div style={{ 
          backgroundColor: '#fef2f2', 
          padding: '1.5rem', 
          borderRadius: '8px',
          border: '1px solid #fecaca'
        }}>
          <div style={{ marginBottom: '1rem' }}>
            <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '500', color: '#374151' }}>
              Select Pool to Delete
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
              <option value="">Select a pool...</option>
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
            ⚠️ Warning: This action cannot be undone. All entries and data associated with this pool will be permanently deleted.
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
            Delete Selected Pool
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
        process.env.NEXT_PUBLIC_API_URL + `/admin/pools/${leagueId}/users/password-reset`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${localStorage.getItem('access_token')}`,
          },
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
      setUserLockMessage(data.locked ? 'This user is locked in this pool.' : 'This user is active in this pool.');
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
      setUserLockMessage(locked ? 'User locked in this pool.' : 'User unlocked in this pool.');
    } catch (err) { setUserLockMessage(err.message || 'Unable to update user lock'); }
  };

  const renderUserManagement = () => (
    <div className="admin-section admin-section--users" style={{ flex: 1 }}>
      <h3 style={{ color: '#1a202c', marginTop: 0, marginBottom: '2rem' }}>
        User Management
      </h3>

      <AdminUserOverview overview={userOverview} loading={userOverviewLoading} error={userOverviewError} onRefresh={fetchUserOverview} onChangeEmail={handleChangeUserEmail} />

      <AdminAutoPickReport week={autoPickWeek} onWeekChange={setAutoPickWeek} records={autoPicks} loading={autoPicksLoading} error={autoPicksError} />

      <div style={{ marginBottom: '3rem' }}>
        <h4>Lock User Account</h4>
        <div>
          <p>Prevent a user from creating, deleting, or changing entries and picks in this pool. Their login and other pools remain available.</p>
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

      {league?.owner_id === user?.id && <>
        <AdminAccessControl poolId={leagueId} onChanged={fetchUserOverview} />
        <OwnershipTransferControl
          poolId={leagueId}
          poolName={league.name}
          onTransferred={async () => { await fetchLeagueData(); await fetchUserOverview(); }}
        />
      </>}
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
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '1rem', marginBottom: '1rem' }}>
          <h4 style={{ color: '#2d3748', margin: 0 }}>Audit Log Results</h4>
          <button
            type="button"
            disabled={auditLoading || auditLogs.length === 0}
            onClick={() => downloadAuditCsv(
              auditLogs,
              `${(league?.name || 'pool').replace(/[^a-z0-9]+/gi, '-').replace(/^-|-$/g, '').toLowerCase()}-audit-log.csv`,
            )}
          >
            Export CSV
          </button>
        </div>
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
              <p>No pick activity matches this pool and search.</p>
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
