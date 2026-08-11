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
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const loadUsers = useCallback(async (query = '') => {
    setLoading(true);
    setError('');
    try {
      const token = localStorage.getItem('access_token');
      const params = new URLSearchParams({ limit: '500' });
      if (query.trim()) params.set('search', query.trim());
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
  }, []);

  useEffect(() => { loadUsers(); }, [loadUsers]);

  const submitSearch = (event) => {
    event.preventDefault();
    loadUsers(search);
  };

  return <ProtectedRoute><main className="platform-admin-page">
    <header className="platform-admin-hero">
      <p>Platform operations</p>
      <h1>ADMIN DASHBOARD</h1>
      <span>Signed in as {user?.email}</span>
    </header>

    {error && <div className="workspace-alert workspace-alert--error">{error}</div>}

    <section className="platform-admin-stats" aria-label="User totals">
      <article><span>Total users</span><strong>{summary?.total ?? '—'}</strong></article>
      <article><span>Active</span><strong>{summary?.active ?? '—'}</strong></article>
      <article><span>Locked</span><strong>{summary?.locked ?? '—'}</strong></article>
      <article><span>Administrators</span><strong>{summary ? summary.pool_admins + summary.super_admins : '—'}</strong></article>
    </section>

    <section className="platform-admin-directory">
      <div className="platform-admin-directory__head">
        <div><p>User management</p><h2>ALL USERS</h2></div>
        <form onSubmit={submitSearch} role="search">
          <label htmlFor="admin-user-search">Search by email</label>
          <div><input id="admin-user-search" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="name@example.com" /><button type="submit">Search</button></div>
        </form>
      </div>

      {loading ? <div className="platform-admin-state">Loading users…</div> : summary?.users?.length ?
        <div className="platform-admin-table-wrap"><table className="platform-admin-table">
          <thead><tr><th>User</th><th>Role</th><th>Status</th><th>Joined</th><th>User ID</th></tr></thead>
          <tbody>{summary.users.map((account) => <tr key={account.id}>
            <td><strong>{account.email}</strong></td>
            <td><span className={`platform-admin-role platform-admin-role--${account.role.toLowerCase()}`}>{roleLabel(account.role)}</span></td>
            <td><span className={`platform-admin-status ${account.is_active ? 'is-active' : 'is-locked'}`}>{account.is_active ? 'Active' : 'Locked'}</span></td>
            <td>{account.created_at ? new Date(account.created_at).toLocaleDateString() : '—'}</td>
            <td><code>{account.id}</code></td>
          </tr>)}</tbody>
        </table></div> : <div className="platform-admin-state">No users match that search.</div>}
    </section>
  </main></ProtectedRoute>;
}
