import Link from 'next/link';
import { useCallback, useEffect, useState } from 'react';
import SuperAdminRoute from '../components/SuperAdminRoute';
import { useAuth } from '../context/AuthContext';
import { downloadAuditCsv } from '../utils/auditCsv';

const roleLabel = (role) => ({ SUPER_ADMIN: 'Platform admin', POOL_ADMIN: 'Pool admin', USER: 'Member' }[role] || role);
const apiUrl = (path) => `${process.env.NEXT_PUBLIC_API_URL}${path}`;

export default function Admin() {
  const { user } = useAuth();
  const [tab, setTab] = useState('users');
  const [summary, setSummary] = useState(null);
  const [overview, setOverview] = useState(null);
  const [records, setRecords] = useState([]);
  const [search, setSearch] = useState('');
  const [unassignedOnly, setUnassignedOnly] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const request = useCallback(async (path, options = {}) => {
    const token = localStorage.getItem('access_token');
    const response = await fetch(apiUrl(path), {
      ...options,
      headers: { Authorization: `Bearer ${token}`, ...(options.headers || {}) },
    });
    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      throw new Error(body.detail || 'Unable to complete the platform admin request.');
    }
    return response.status === 204 ? null : response.json();
  }, []);

  const load = useCallback(async (activeTab = tab, query = search, onlyUnassigned = unassignedOnly) => {
    if (user?.role !== 'SUPER_ADMIN') return;
    setLoading(true); setError('');
    try {
      const overviewPromise = request('/platform-admin/overview');
      if (activeTab === 'users' || activeTab === 'super-admins') {
        const params = new URLSearchParams({ limit: '500' });
        if (query.trim()) params.set('search', query.trim());
        if (activeTab === 'users' && onlyUnassigned) params.set('unassigned_only', 'true');
        const [nextOverview, users] = await Promise.all([overviewPromise, request(`/users/admin-dashboard?${params}`)]);
        setOverview(nextOverview); setSummary(users); setRecords(users.users || []);
      } else {
        const params = new URLSearchParams({ limit: '500' });
        if (query.trim()) params.set('search', query.trim());
        const endpoint = activeTab === 'audit' ? `/audit/?${params}` : `/platform-admin/${activeTab}?${params}`;
        const [nextOverview, nextRecords] = await Promise.all([overviewPromise, request(endpoint)]);
        setOverview(nextOverview); setRecords(nextRecords || []);
      }
    } catch (err) { setError(err.message); setRecords([]); }
    finally { setLoading(false); }
  }, [request, search, tab, unassignedOnly, user?.role]);

  useEffect(() => { load(tab, '', unassignedOnly); }, [tab, unassignedOnly]); // eslint-disable-line react-hooks/exhaustive-deps

  const changeTab = (nextTab) => { setSearch(''); setUnassignedOnly(false); setTab(nextTab); };
  const submitSearch = (event) => { event.preventDefault(); load(tab, search, unassignedOnly); };

  const updateAccount = async (account, action) => {
    let path; let method = 'PATCH';
    if (action === 'email') {
      const email = window.prompt('Enter the new login email address', account.email)?.trim().toLowerCase();
      if (!email || email === account.email) return;
      path = `/users/${account.id}/email?email=${encodeURIComponent(email)}`;
    } else if (action === 'super-admin') {
      const enabled = account.role !== 'SUPER_ADMIN';
      if (!window.confirm(`${enabled ? 'Grant' : 'Revoke'} super admin access ${enabled ? 'to' : 'from'} ${account.email}?`)) return;
      path = `/users/${account.id}/super-admin?enabled=${enabled}`;
    } else if (action === 'delete') {
      if (!window.confirm(`Permanently delete ${account.email}? This cannot be undone.`)) return;
      path = `/users/${account.id}`; method = 'DELETE';
    } else {
      const active = !account.is_active;
      if (!window.confirm(`${active ? 'Reactivate' : 'Deactivate'} ${account.email}?`)) return;
      path = `/users/${account.id}/status?active=${active}`;
    }
    try { setError(''); await request(path, { method }); await load(tab, search, unassignedOnly); }
    catch (err) { setError(err.message); }
  };

  const title = { users: unassignedOnly ? 'USERS WITHOUT A POOL' : 'ALL USERS', pools: 'ALL POOLS', entries: 'ALL ENTRIES', audit: 'AUDIT LOG', 'super-admins': 'SUPER ADMIN ACCESS' }[tab];
  const stats = [
    ['Users', overview?.users], ['Pools', overview?.pools], ['Entries', overview?.entries], ['Audit events', overview?.audit_events],
  ];

  return <SuperAdminRoute><main className="platform-admin-page">
    <header className="platform-admin-hero"><p>Platform operations</p><h1>PLATFORM ADMIN</h1><span>Signed in as {user?.email}</span></header>
    {error && <div className="workspace-alert workspace-alert--error" role="alert">{error}</div>}
    <section className="platform-admin-stats" aria-label="Platform totals">{stats.map(([label, value]) => <article key={label}><span>{label}</span><strong>{typeof value === 'number' ? value : '—'}</strong></article>)}</section>
    <nav className="platform-admin-tabs" aria-label="Platform administration">
      {[['users', 'Users'], ['pools', 'Pools'], ['entries', 'Entries'], ['audit', 'Audit Log'], ['super-admins', 'Super Admin Access']].map(([key, label]) =>
        <button key={key} type="button" className={tab === key ? 'is-active' : ''} onClick={() => changeTab(key)}>{label}</button>)}
    </nav>
    <section className="platform-admin-directory">
      <div className="platform-admin-directory__head"><div><p>Global administration</p><h2>{title}</h2></div>
        <form onSubmit={submitSearch} role="search"><label htmlFor="platform-search">Search {tab === 'users' || tab === 'super-admins' ? 'by email' : tab}</label><div><input id="platform-search" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search…" /><button type="submit">Search</button></div></form>
      </div>
      {tab === 'users' && <div className="platform-admin-filters"><button type="button" className={!unassignedOnly ? 'is-active' : ''} onClick={() => setUnassignedOnly(false)}>All users</button><button type="button" className={unassignedOnly ? 'is-active' : ''} onClick={() => setUnassignedOnly(true)}>Not in a pool ({summary?.unassigned ?? 0})</button></div>}
      {tab === 'audit' && <div className="platform-admin-filters"><button type="button" onClick={() => downloadAuditCsv(records, `platform-audit-${new Date().toISOString().slice(0, 10)}.csv`)}>Export CSV</button></div>}
      {loading ? <div className="platform-admin-state">Loading {tab}…</div> : <AdminTable tab={tab} records={records} currentUser={user} updateAccount={updateAccount} />}
    </section>
  </main></SuperAdminRoute>;
}

function AdminTable({ tab, records, currentUser, updateAccount }) {
  if (!records.length) return <div className="platform-admin-state">No records match that search.</div>;
  if (tab === 'pools') return <div className="platform-admin-table-wrap"><table className="platform-admin-table"><thead><tr><th>Pool</th><th>Visibility</th><th>Owner</th><th>Members</th><th>Entries</th><th>Actions</th></tr></thead><tbody>{records.map((pool) => <tr key={pool.id}><td><strong>{pool.name}</strong></td><td>{pool.is_private ? 'Private' : 'Public'}</td><td>{pool.owner_email || '—'}</td><td>{pool.member_count}</td><td>{pool.entry_count}</td><td><Link href={`/admin/league/${pool.id}`}>Manage pool</Link></td></tr>)}</tbody></table></div>;
  if (tab === 'entries') return <div className="platform-admin-table-wrap"><table className="platform-admin-table"><thead><tr><th>Entry</th><th>User</th><th>Pool</th><th>Status</th><th>Created</th></tr></thead><tbody>{records.map((entry) => <tr key={entry.id}><td><strong>{entry.name}</strong></td><td>{entry.user_email || '—'}</td><td><Link href={`/admin/league/${entry.pool_id}`}>{entry.pool_name || entry.pool_id}</Link></td><td>{entry.alive ? 'Alive' : 'Eliminated'}</td><td>{entry.created_at ? new Date(entry.created_at).toLocaleDateString() : '—'}</td></tr>)}</tbody></table></div>;
  if (tab === 'audit') return <div className="platform-admin-table-wrap"><table className="platform-admin-table"><thead><tr><th>When</th><th>Action</th><th>User</th><th>Details</th></tr></thead><tbody>{records.map((log) => <tr key={log.id}><td>{new Date(log.created_at).toLocaleString()}</td><td><strong>{log.action}</strong></td><td>{log.username || log.user_id || 'System'}</td><td>{log.details}</td></tr>)}</tbody></table></div>;
  const visible = records;
  if (!visible.length) return <div className="platform-admin-state">No records match that search.</div>;
  return <div className="platform-admin-table-wrap"><table className="platform-admin-table"><thead><tr><th>User</th><th>Role</th><th>Status</th><th>Pools</th><th>Joined</th><th>Actions</th></tr></thead><tbody>{visible.map((account) => {
    // Legacy or partially cached account payloads may not include a role.
    // Treat them as least-privileged members instead of crashing the console.
    const accountRole = typeof account.role === 'string' && account.role ? account.role : 'USER';
    return <tr key={account.id}><td><strong>{account.email}</strong></td><td><span className={`platform-admin-role platform-admin-role--${accountRole.toLowerCase()}`}>{roleLabel(accountRole)}</span></td><td><span className={`platform-admin-status ${account.is_active ? 'is-active' : 'is-locked'}`}>{account.is_active ? 'Active' : 'Locked'}</span></td><td>{account.pool_count ?? 0}</td><td>{account.created_at ? new Date(account.created_at).toLocaleDateString() : '—'}</td><td><div className="platform-admin-actions">{tab === 'users' && <><button type="button" onClick={() => updateAccount(account, 'email')}>Change login email</button><button type="button" onClick={() => updateAccount(account, 'status')}>{account.is_active ? 'Deactivate' : 'Reactivate'}</button><button type="button" className="is-danger" onClick={() => updateAccount(account, 'delete')}>Delete</button></>}<button type="button" disabled={account.id === currentUser?.id && accountRole === 'SUPER_ADMIN'} onClick={() => updateAccount({ ...account, role: accountRole }, 'super-admin')}>{accountRole === 'SUPER_ADMIN' ? 'Revoke super admin' : 'Grant super admin'}</button></div></td></tr>;
  })}</tbody></table></div>;
}
