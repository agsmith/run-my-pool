import { useMemo, useState } from 'react';

const textCollator = new Intl.Collator(undefined, { numeric: true, sensitivity: 'base' });
const sortValues = {
  email: (user) => user.email,
  admin_role: (user) => user.admin_role,
  dues_paid: (user) => Number(Boolean(user.dues_paid)),
  total_entries: (user) => user.total_entries,
  surviving_entries: (user) => user.surviving_entries,
  picked_entries: (user) => user.picked_entries,
};

function compareValues(left, right) {
  if (typeof left === 'number' && typeof right === 'number') return left - right;
  return textCollator.compare(String(left ?? ''), String(right ?? ''));
}

function SortableHeader({ column, label, sort, onSort }) {
  const active = sort.column === column;
  const direction = active ? sort.direction : 'none';
  const nextDirection = active && sort.direction === 'ascending' ? 'descending' : 'ascending';

  return <th scope="col" aria-sort={direction}>
    <button
      type="button"
      className="admin-user-overview__sort"
      onClick={() => onSort(column)}
      aria-label={`Sort by ${label}, ${nextDirection}`}
    >
      <span>{label}</span>
      <span className="admin-user-overview__sort-indicator" aria-hidden="true">
        {active ? (sort.direction === 'ascending' ? '▲' : '▼') : '↕'}
      </span>
    </button>
  </th>;
}

function pickStatus(user) {
  if (!user.surviving_entries) return { label: 'No survivors', tone: 'neutral' };
  if (user.all_surviving_entries_picked) return { label: 'Complete', tone: 'complete' };
  if (user.has_current_week_pick) return { label: 'Partial', tone: 'partial' };
  return { label: 'Missing', tone: 'missing' };
}

export default function AdminUserOverview({ overview, loading, error, onRefresh, onChangeEmail, onChangeDues }) {
  const [search, setSearch] = useState('');
  const [savingDuesFor, setSavingDuesFor] = useState('');
  const [sort, setSort] = useState({ column: '', direction: 'ascending' });
  const users = useMemo(() => {
    const query = search.trim().toLowerCase();
    const filtered = query
      ? (overview?.users || []).filter((user) => user.email.toLowerCase().includes(query))
      : (overview?.users || []);
    if (!sort.column) return filtered;

    const valueFor = sortValues[sort.column];
    const multiplier = sort.direction === 'ascending' ? 1 : -1;
    return filtered
      .map((user, index) => ({ user, index }))
      .sort((left, right) => {
        const comparison = compareValues(valueFor(left.user), valueFor(right.user));
        if (comparison) return comparison * multiplier;
        const emailComparison = textCollator.compare(left.user.email, right.user.email);
        return emailComparison || left.index - right.index;
      })
      .map(({ user }) => user);
  }, [overview, search, sort]);

  const handleSort = (column) => {
    setSort((current) => ({
      column,
      direction: current.column === column && current.direction === 'ascending'
        ? 'descending'
        : 'ascending',
    }));
  };

  return <section className="admin-user-overview" aria-labelledby="admin-user-overview-title">
    <div className="admin-user-overview__head">
      <div>
        <span>Pool participation</span>
        <h4 id="admin-user-overview-title">User overview</h4>
        <p>Entry totals and Week {overview?.current_week || '—'} completion. Individual picks remain private.</p>
      </div>
      <div className="admin-user-overview__tools">
        <label htmlFor="league-user-search">Search users</label>
        <div><input id="league-user-search" type="search" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="name@example.com" /><button type="button" onClick={onRefresh}>Refresh</button></div>
      </div>
    </div>

    {error && <div className="admin-user-overview__state is-error" role="alert">{error}</div>}
    {loading ? <div className="admin-user-overview__state">Loading pool users…</div> : !error && users.length === 0 ?
      <div className="admin-user-overview__state">No users match this search.</div> : !error &&
      <div className="admin-user-overview__table-wrap"><table className="admin-user-overview__table">
        <thead><tr>
          <SortableHeader column="email" label="User" sort={sort} onSort={handleSort} />
          <SortableHeader column="admin_role" label="Pool role" sort={sort} onSort={handleSort} />
          <SortableHeader column="dues_paid" label="Dues paid" sort={sort} onSort={handleSort} />
          <SortableHeader column="total_entries" label="Total entries" sort={sort} onSort={handleSort} />
          <SortableHeader column="surviving_entries" label="Surviving" sort={sort} onSort={handleSort} />
          <SortableHeader column="picked_entries" label={`Week ${overview?.current_week || '—'} picks`} sort={sort} onSort={handleSort} />
          <th scope="col">Actions</th>
        </tr></thead>
        <tbody>{users.map((user) => {
          const status = pickStatus(user);
          return <tr key={user.id}>
            <td data-label="User"><strong>{user.email}</strong></td>
            <td data-label="Pool role"><span className={`admin-user-role ${user.is_admin ? 'is-admin' : ''}`}>{user.admin_role}</span></td>
            <td data-label="Dues paid">
              <label>
                <input
                  type="checkbox"
                  checked={Boolean(user.dues_paid)}
                  disabled={savingDuesFor === user.id}
                  onChange={async (event) => {
                    setSavingDuesFor(user.id);
                    try { await onChangeDues(user, event.target.checked); }
                    finally { setSavingDuesFor(''); }
                  }}
                  aria-label={`Dues paid for ${user.email}`}
                />
                {user.dues_paid ? ' Paid' : ' Unpaid'}
              </label>
            </td>
            <td data-label="Total entries">{user.total_entries}</td>
            <td data-label="Surviving">{user.surviving_entries}</td>
            <td data-label={`Week ${overview?.current_week || ''} picks`}><span className={`admin-pick-status is-${status.tone}`}>{status.label}</span><small>{user.picked_entries} / {user.surviving_entries} picked</small></td>
            <td data-label="Actions"><button type="button" onClick={() => onChangeEmail(user)}>Change login email</button></td>
          </tr>;
        })}</tbody>
      </table></div>}
  </section>;
}
