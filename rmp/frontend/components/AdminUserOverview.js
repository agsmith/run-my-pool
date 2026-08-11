import { useMemo, useState } from 'react';

function pickStatus(user) {
  if (!user.surviving_entries) return { label: 'No survivors', tone: 'neutral' };
  if (user.all_surviving_entries_picked) return { label: 'Complete', tone: 'complete' };
  if (user.has_current_week_pick) return { label: 'Partial', tone: 'partial' };
  return { label: 'Missing', tone: 'missing' };
}

export default function AdminUserOverview({ overview, loading, error, onRefresh }) {
  const [search, setSearch] = useState('');
  const users = useMemo(() => {
    const query = search.trim().toLowerCase();
    if (!query) return overview?.users || [];
    return (overview?.users || []).filter((user) => user.email.toLowerCase().includes(query));
  }, [overview, search]);

  return <section className="admin-user-overview" aria-labelledby="admin-user-overview-title">
    <div className="admin-user-overview__head">
      <div>
        <span>League participation</span>
        <h4 id="admin-user-overview-title">User overview</h4>
        <p>Entry totals and Week {overview?.current_week || '—'} completion. Individual picks remain private.</p>
      </div>
      <div className="admin-user-overview__tools">
        <label htmlFor="league-user-search">Search users</label>
        <div><input id="league-user-search" type="search" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="name@example.com" /><button type="button" onClick={onRefresh}>Refresh</button></div>
      </div>
    </div>

    {error && <div className="admin-user-overview__state is-error" role="alert">{error}</div>}
    {loading ? <div className="admin-user-overview__state">Loading league users…</div> : !error && users.length === 0 ?
      <div className="admin-user-overview__state">No users match this search.</div> : !error &&
      <div className="admin-user-overview__table-wrap"><table className="admin-user-overview__table">
        <thead><tr><th>User</th><th>League role</th><th>Total entries</th><th>Surviving</th><th>Week {overview?.current_week || '—'} picks</th></tr></thead>
        <tbody>{users.map((user) => {
          const status = pickStatus(user);
          return <tr key={user.id}>
            <td data-label="User"><strong>{user.email}</strong></td>
            <td data-label="League role"><span className={`admin-user-role ${user.is_admin ? 'is-admin' : ''}`}>{user.admin_role}</span></td>
            <td data-label="Total entries">{user.total_entries}</td>
            <td data-label="Surviving">{user.surviving_entries}</td>
            <td data-label={`Week ${overview?.current_week || ''} picks`}><span className={`admin-pick-status is-${status.tone}`}>{status.label}</span><small>{user.picked_entries} / {user.surviving_entries} picked</small></td>
          </tr>;
        })}</tbody>
      </table></div>}
  </section>;
}
