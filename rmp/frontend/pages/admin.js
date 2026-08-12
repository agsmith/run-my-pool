import { useCallback, useEffect, useState } from 'react';
import ProtectedRoute from '../components/ProtectedRoute';
import { useAuth } from '../context/AuthContext';

const roleLabel = (role) => ({
  SUPER_ADMIN: 'Platform admin',
  POOL_ADMIN: 'Pool admin',
  USER: 'Member',
}[role] || role);

export default function Admin() {
  const { user } = useAuth();
  const [summary, setSummary] = useState(null);
  const [search, setSearch] = useState('');
  const [unassignedOnly, setUnassignedOnly] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const loadUsers = useCallback(async (query = '', onlyUnassigned = unassignedOnly) => {
    setLoading(true);
    setError('');
    try {
      const token = localStorage.getItem('access_token');
      const params = new URLSearchParams({ limit: '500' });
      if (query.trim()) params.set('search', query.trim());
      if (onlyUnassigned) params.set('unassigned_only', 'true');
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/users/admin-dashboard?${params}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!response.ok) {
        const body = await response.json().catch(() => ({}));
        throw new Error(body.detail || 'Unable to load the admin dashboard.');
      }
      setSummary(await response.json());
    } catch (err) {
      setError(err.message || 'Unable to load the admin dashboard.');
    } finally {
      setLoading(false);
    }
  }, [unassignedOnly]);

  useEffect(() => { loadUsers('', unassignedOnly); }, [loadUsers, unassignedOnly]);

  const submitSearch = (event) => {
    event.preventDefault();
    loadUsers(search);
  };

  const updateAccount = async (account, action) => {
    const token = localStorage.getItem('access_token');
    let url;
    let method = 'PATCH';
    if (action === 'email') {
      const email = window.prompt('Enter the corrected email address', account.email)?.trim().toLowerCase();
      if (!email || email === account.email) return;
      url = `${process.env.NEXT_PUBLIC_API_URL}/users/${account.id}/email?email=${encodeURIComponent(email)}`;
    } else if (action === 'super-admin') {
      const enabled = account.role !== 'SUPER_ADMIN';
      if (!window.confirm(`${enabled ? 'Grant' : 'Revoke'} super admin access ${enabled ? 'to' : 'from'} ${account.email}?`)) return;
      url = `${process.env.NEXT_PUBLIC_API_URL}/users/${account.id}/super-admin?enabled=${enabled}`;
    } else if (action === 'delete') {
      if (!window.confirm(`Permanently delete ${account.email}? This cannot be undone.`)) return;
      url = `${process.env.NEXT_PUBLIC_API_URL}/users/${account.id}`;
      method = 'DELETE';
    } else {
      const active = !account.is_active;
      if (!window.confirm(`${active ? 'Reactivate' : 'Deactivate'} ${account.email}?`)) return;
      url = `${process.env.NEXT_PUBLIC_API_URL}/users/${account.id}/status?active=${active}`;
    }
    setError('');
    const response = await fetch(url, { method, headers: { Authorization: `Bearer ${token}` } });
    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      setError(body.detail || 'Unable to update the account.');
      return;
    }
    await loadUsers(search);
  };

  return <ProtectedRoute><main className="platform-admin-page">
    <header className="platform-admin-hero">
      <p>{user?.role === 'SUPER_ADMIN' ? 'Platform operations' : 'League operations'}</p>
      <h1>ADMIN DASHBOARD</h1>
      <span>Signed in as {user?.email}</span>
    </header>

    {error && <div className="workspace-alert workspace-alert--error">{error}</div>}

    <section className="platform-admin-stats" aria-label="User totals">
      <article><span>Total users</span><strong>{summary?.total ?? '—'}</strong></article>
      <article><span>Active</span><strong>{summary?.active ?? '—'}</strong></article>
      <article><span>Locked</span><strong>{summary?.locked ?? '—'}</strong></article>
      <article><span>Unassigned</span><strong>{summary?.unassigned ?? '—'}</strong></article>
    </section>

    <section className="platform-admin-directory">
      <div className="platform-admin-directory__head">
        <div><p>User management</p><h2>{unassignedOnly ? 'USERS WITHOUT A POOL' : user?.role === 'SUPER_ADMIN' ? 'ALL USERS' : 'YOUR LEAGUE USERS'}</h2></div>
        <form onSubmit={submitSearch} role="search">
          <label htmlFor="admin-user-search">Search by email</label>
          <div><input id="admin-user-search" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="name@example.com" /><button type="submit">Search</button></div>
        </form>
      </div>

      {user?.role === 'SUPER_ADMIN' && <div className="platform-admin-filters">
        <button type="button" className={!unassignedOnly ? 'is-active' : ''} onClick={() => setUnassignedOnly(false)}>All users</button>
        <button type="button" className={unassignedOnly ? 'is-active' : ''} onClick={() => setUnassignedOnly(true)}>Not in a pool ({summary?.unassigned ?? 0})</button>
      </div>}

      {loading ? <div className="platform-admin-state">Loading users…</div> : summary?.users?.length ?
        <div className="platform-admin-table-wrap"><table className="platform-admin-table">
          <thead><tr><th>User</th><th>Role</th><th>Status</th><th>Pools</th><th>Joined</th>{user?.role === 'SUPER_ADMIN' && <th>Actions</th>}</tr></thead>
          <tbody>{summary.users.map((account) => <tr key={account.id}>
            <td><strong>{account.email}</strong></td>
            <td><span className={`platform-admin-role platform-admin-role--${account.role.toLowerCase()}`}>{roleLabel(account.role)}</span></td>
            <td><span className={`platform-admin-status ${account.is_active ? 'is-active' : 'is-locked'}`}>{account.is_active ? 'Active' : 'Locked'}</span></td>
            <td>{account.pool_count ?? 0}</td>
            <td>{account.created_at ? new Date(account.created_at).toLocaleDateString() : '—'}</td>
            {user?.role === 'SUPER_ADMIN' && <td><div className="platform-admin-actions">
              <button type="button" onClick={() => updateAccount(account, 'email')}>Edit email</button>
              <button type="button" onClick={() => updateAccount(account, 'super-admin')}>{account.role === 'SUPER_ADMIN' ? 'Revoke super admin' : 'Grant super admin'}</button>
              <button type="button" onClick={() => updateAccount(account, 'status')}>{account.is_active ? 'Deactivate' : 'Reactivate'}</button>
              <button type="button" className="is-danger" onClick={() => updateAccount(account, 'delete')}>Delete</button>
            </div></td>}
          </tr>)}</tbody>
        </table></div> : <div className="platform-admin-state">No users match that search.</div>}
    </section>
  </main></ProtectedRoute>;
}
