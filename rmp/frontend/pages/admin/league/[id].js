import { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import ProtectedRoute from '../../../components/ProtectedRoute';
import { useAuth } from '../../../context/AuthContext';

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
  
  // User Management State
  const [resetPasswordData, setResetPasswordData] = useState({ username: '', forceChange: false });
  const [updateEmailData, setUpdateEmailData] = useState({ username: '', newEmail: '' });
  const [deleteUserData, setDeleteUserData] = useState({ username: '' });
  const [assignAdminData, setAssignAdminData] = useState({ username: '' });
  
  // Entry Management State
  const [transferEntryData, setTransferEntryData] = useState({ entryId: '', fromUser: '', toUser: '' });
  const [deleteEntryData, setDeleteEntryData] = useState({ entryId: '', username: '' });
  const [correctPickData, setCorrectPickData] = useState({ username: '', weekNum: '', teamAbbr: '', reason: '' });
  const [entryLookupData, setEntryLookupData] = useState({ username: '', entryName: '' });
  const [lookupResults, setLookupResults] = useState([]);
  
  // Audit Log State
  const [auditSearch, setAuditSearch] = useState({ 
    userId: '', 
    dateFrom: '', 
    dateTo: '', 
    actionSearch: '' 
  });
  const [auditLogs, setAuditLogs] = useState([]);

  useEffect(() => {
    if (leagueId) {
      fetchLeagueData();
      fetchAllLeagues();
    }
  }, [leagueId]);

  const fetchLeagueData = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const res = await fetch(process.env.NEXT_PUBLIC_API_URL + `/pools/${leagueId}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (res.ok) {
        const data = await res.json();
        setLeague(data);
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
      // Get all entries for this league
      const res = await fetch(process.env.NEXT_PUBLIC_API_URL + `/entries/pool/${leagueId}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (res.ok) {
        const entries = await res.json();
        
        // Filter entries based on search criteria
        let filteredEntries = entries;
        
        if (entryLookupData.username) {
          // Need to get user data for each entry to match username
          const entriesWithUsers = await Promise.all(
            entries.map(async (entry) => {
              try {
                const userRes = await fetch(process.env.NEXT_PUBLIC_API_URL + `/users/${entry.user_id}`, {
                  headers: { 'Authorization': `Bearer ${token}` }
                });
                if (userRes.ok) {
                  const userData = await userRes.json();
                  return { ...entry, user: userData };
                }
                return { ...entry, user: null };
              } catch {
                return { ...entry, user: null };
              }
            })
          );
          
          filteredEntries = entriesWithUsers.filter(entry => 
            entry.user && entry.user.username && 
            entry.user.username.toLowerCase().includes(entryLookupData.username.toLowerCase())
          );
        }
        
        if (entryLookupData.entryName) {
          filteredEntries = filteredEntries.filter(entry =>
            entry.name.toLowerCase().includes(entryLookupData.entryName.toLowerCase())
          );
        }
        
        setLookupResults(filteredEntries);
      } else {
        setError('Failed to fetch entries');
      }
    } catch (err) {
      setError('Error performing lookup');
      console.error('Entry lookup error:', err);
    }
  };

  const handleTransferEntry = async () => {
    if (!transferEntryData.entryId || !transferEntryData.toUser) {
      setError('Please enter both entry ID and new owner username');
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
          to_username: transferEntryData.toUser
        })
      });
      
      if (res.ok) {
        const result = await res.json();
        alert(`Success: ${result.message}`);
        // Clear the form
        setTransferEntryData({ entryId: '', fromUser: '', toUser: '' });
      } else {
        const errorData = await res.json();
        setError(`Transfer failed: ${errorData.detail}`);
      }
    } catch (err) {
      setError('Error transferring entry');
      console.error('Transfer error:', err);
    }
  };

  const renderSidebar = () => (
    <div style={{
      width: '300px',
      backgroundColor: 'white',
      borderRadius: '12px',
      padding: '2rem',
      boxShadow: '0 10px 25px rgba(0, 0, 0, 0.1)',
      height: 'fit-content'
    }}>
      <h2 style={{ 
        color: '#1a202c', 
        marginTop: 0, 
        marginBottom: '2rem',
        fontSize: '1.5rem',
        fontWeight: '700'
      }}>
        🛠️ Admin Portal
      </h2>
      
      {league && (
        <div style={{
          backgroundColor: '#f7fafc',
          padding: '1rem',
          borderRadius: '8px',
          marginBottom: '2rem',
          border: '1px solid #e2e8f0'
        }}>
          <div style={{ fontSize: '0.875rem', color: '#6b7280', marginBottom: '0.25rem' }}>
            Managing League:
          </div>
          <div style={{ fontWeight: '600', color: '#1a202c' }}>
            {league.name}
          </div>
        </div>
      )}
      
      <nav>
        {[
          { id: 'league-management', label: '🏈 League Management', icon: '🏈' },
          { id: 'user-management', label: '👥 User Management', icon: '👥' },
          { id: 'entry-management', label: '📝 Entry Management', icon: '📝' },
          { id: 'audit-log', label: '📊 Audit Log', icon: '📊' }
        ].map(section => (
          <button
            key={section.id}
            onClick={() => setActiveSection(section.id)}
            style={{
              width: '100%',
              textAlign: 'left',
              padding: '1rem',
              marginBottom: '0.5rem',
              backgroundColor: activeSection === section.id ? '#667eea' : 'transparent',
              color: activeSection === section.id ? 'white' : '#4a5568',
              border: 'none',
              borderRadius: '8px',
              cursor: 'pointer',
              fontSize: '1rem',
              fontWeight: '500',
              transition: 'all 0.2s ease',
              display: 'flex',
              alignItems: 'center',
              gap: '0.75rem'
            }}
            onMouseEnter={(e) => {
              if (activeSection !== section.id) {
                e.target.style.backgroundColor = '#f7fafc';
              }
            }}
            onMouseLeave={(e) => {
              if (activeSection !== section.id) {
                e.target.style.backgroundColor = 'transparent';
              }
            }}
          >
            <span>{section.icon}</span>
            {section.label.replace(section.icon + ' ', '')}
          </button>
        ))}
      </nav>
      
      <div style={{ marginTop: '2rem', paddingTop: '2rem', borderTop: '1px solid #e2e8f0' }}>
        <button
          onClick={() => router.push('/dashboard')}
          style={{
            width: '100%',
            backgroundColor: '#e2e8f0',
            color: '#4a5568',
            padding: '0.75rem',
            border: 'none',
            borderRadius: '8px',
            cursor: 'pointer',
            fontSize: '0.9rem',
            fontWeight: '500',
            transition: 'all 0.2s ease'
          }}
          onMouseEnter={(e) => e.target.style.backgroundColor = '#cbd5e0'}
          onMouseLeave={(e) => e.target.style.backgroundColor = '#e2e8f0'}
        >
          ← Back to Dashboard
        </button>
      </div>
    </div>
  );

  const renderLeagueManagement = () => (
    <div style={{ flex: 1 }}>
      <h3 style={{ color: '#1a202c', marginTop: 0, marginBottom: '2rem' }}>
        League Management
      </h3>
      
      {/* View/Search Leagues */}
      <div style={{ marginBottom: '3rem' }}>
        <h4 style={{ color: '#2d3748', marginBottom: '1rem' }}>📋 View Leagues</h4>
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

      {/* Create League */}
      <div style={{ marginBottom: '3rem' }}>
        <h4 style={{ color: '#2d3748', marginBottom: '1rem' }}>➕ Create League</h4>
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
        <h4 style={{ color: '#2d3748', marginBottom: '1rem' }}>✏️ Modify League</h4>
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
        <h4 style={{ color: '#2d3748', marginBottom: '1rem' }}>🗑️ Delete League</h4>
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

  const renderUserManagement = () => (
    <div style={{ flex: 1 }}>
      <h3 style={{ color: '#1a202c', marginTop: 0, marginBottom: '2rem' }}>
        User Management
      </h3>
      
      {/* Reset User Password */}
      <div style={{ marginBottom: '3rem' }}>
        <h4 style={{ color: '#2d3748', marginBottom: '1rem' }}>🔑 Reset User Password</h4>
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
          <div style={{ marginBottom: '1rem' }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={resetPasswordData.forceChange}
                onChange={(e) => setResetPasswordData({...resetPasswordData, forceChange: e.target.checked})}
              />
              <span style={{ fontWeight: '500', color: '#374151' }}>
                Force user to change password on next login
              </span>
            </label>
          </div>
          <button
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
        </div>
      </div>

      {/* Update User Email */}
      <div style={{ marginBottom: '3rem' }}>
        <h4 style={{ color: '#2d3748', marginBottom: '1rem' }}>✉️ Update User Email</h4>
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
        <h4 style={{ color: '#2d3748', marginBottom: '1rem' }}>🗑️ Delete User</h4>
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
        <h4 style={{ color: '#2d3748', marginBottom: '1rem' }}>👑 Assign Administrator Access</h4>
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
    <div style={{ flex: 1 }}>
      <h3 style={{ color: '#1a202c', marginTop: 0, marginBottom: '2rem' }}>
        Entry Management
      </h3>
      
      {/* Entry ID Lookup */}
      <div style={{ marginBottom: '3rem' }}>
        <h4 style={{ color: '#2d3748', marginBottom: '1rem' }}>🔍 Entry ID Lookup</h4>
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
                      {entry.user && (
                        <>
                          <strong>Owner:</strong> {entry.user.username} ({entry.user.email})
                        </>
                      )}
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
        <h4 style={{ color: '#2d3748', marginBottom: '1rem' }}>🔄 Transfer Entries</h4>
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
                From User
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
                To User
              </label>
              <input
                type="text"
                value={transferEntryData.toUser}
                onChange={(e) => setTransferEntryData({...transferEntryData, toUser: e.target.value})}
                placeholder="New owner username"
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
        <h4 style={{ color: '#2d3748', marginBottom: '1rem' }}>🗑️ Delete Entries</h4>
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
                Username
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
            ⚠️ Warning: This will permanently delete the entry and all associated picks. This action cannot be undone.
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
            Delete Entry
          </button>
        </div>
      </div>

      {/* Correct Pick */}
      <div style={{ marginBottom: '3rem' }}>
        <h4 style={{ color: '#2d3748', marginBottom: '1rem' }}>✏️ Correct Pick</h4>
        <div style={{ 
          backgroundColor: 'white', 
          padding: '1.5rem', 
          borderRadius: '8px',
          border: '1px solid #e2e8f0'
        }}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '1rem', marginBottom: '1rem' }}>
            <div>
              <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '500', color: '#374151' }}>
                Username
              </label>
              <input
                type="text"
                value={correctPickData.username}
                onChange={(e) => setCorrectPickData({...correctPickData, username: e.target.value})}
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
    <div style={{ flex: 1 }}>
      <h3 style={{ color: '#1a202c', marginTop: 0, marginBottom: '2rem' }}>
        Audit Log
      </h3>
      
      {/* Search Audit Log */}
      <div style={{ marginBottom: '3rem' }}>
        <h4 style={{ color: '#2d3748', marginBottom: '1rem' }}>🔍 Search Audit Log</h4>
        <div style={{ 
          backgroundColor: 'white', 
          padding: '1.5rem', 
          borderRadius: '8px',
          border: '1px solid #e2e8f0'
        }}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1rem' }}>
            <div>
              <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '500', color: '#374151' }}>
                User ID
              </label>
              <input
                type="text"
                value={auditSearch.userId}
                onChange={(e) => setAuditSearch({...auditSearch, userId: e.target.value})}
                placeholder="Enter user ID (optional)"
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
            Search Audit Log
          </button>
          <button
            onClick={() => setAuditSearch({ userId: '', dateFrom: '', dateTo: '', actionSearch: '' })}
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
        <h4 style={{ color: '#2d3748', marginBottom: '1rem' }}>📋 Audit Log Results</h4>
        <div style={{ 
          backgroundColor: 'white', 
          padding: '1.5rem', 
          borderRadius: '8px',
          border: '1px solid #e2e8f0'
        }}>
          {auditLogs.length === 0 ? (
            <div style={{
              textAlign: 'center',
              padding: '3rem',
              color: '#6b7280'
            }}>
              <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>📊</div>
              <h4 style={{ color: '#4a5568', marginBottom: '0.5rem' }}>No audit logs found</h4>
              <p>Run a search to view audit log entries.</p>
            </div>
          ) : (
            <div style={{ maxHeight: '400px', overflowY: 'auto' }}>
              {auditLogs.map((log, index) => (
                <div key={index} style={{
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
                      {log.timestamp ? new Date(log.timestamp).toLocaleString() : 'Unknown Time'}
                    </div>
                  </div>
                  <div style={{ fontSize: '0.875rem', color: '#4b5563', marginBottom: '0.25rem' }}>
                    User: {log.userId || 'Unknown User'}
                  </div>
                  {log.details && (
                    <div style={{ fontSize: '0.875rem', color: '#6b7280' }}>
                      Details: {log.details}
                    </div>
                  )}
                </div>
              ))}
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
      <div style={{ 
        minHeight: '100vh', 
        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)', 
        padding: '2rem 1rem'
      }}>
        <div style={{ maxWidth: '1400px', margin: '0 auto' }}>
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
          
          <div style={{ display: 'flex', gap: '2rem', alignItems: 'flex-start' }}>
            {renderSidebar()}
            <div style={{
              flex: 1,
              backgroundColor: 'rgba(255, 255, 255, 0.1)',
              backdropFilter: 'blur(10px)',
              borderRadius: '12px',
              padding: '2rem',
              border: '1px solid rgba(255, 255, 255, 0.2)',
              color: 'white'
            }}>
              {renderContent()}
            </div>
          </div>
        </div>
      </div>
    </ProtectedRoute>
  );
}
