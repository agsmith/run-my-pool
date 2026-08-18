import { useEffect, useMemo, useState } from 'react';
import { useRouter } from 'next/router';
import ProtectedRoute from '../../../components/ProtectedRoute';
import { PoolWorkspaceNav, WorkspaceHeader } from '../../../components/ProductWorkspace';

export default function PoolMembersPage() {
  const router = useRouter();
  const { id } = router.query;
  const [pool, setPool] = useState(null);
  const [directory, setDirectory] = useState(null);
  const [adminStatus, setAdminStatus] = useState(null);
  const [error, setError] = useState('');
  const [sort, setSort] = useState({ field: 'name', direction: 'asc' });

  useEffect(() => {
    if (!id) return;
    const token = localStorage.getItem('access_token');
    const headers = { Authorization: `Bearer ${token}` };
    Promise.all([
      fetch(`${process.env.NEXT_PUBLIC_API_URL}/pools/${id}`, { headers }),
      fetch(`${process.env.NEXT_PUBLIC_API_URL}/pools/${id}/members`, { headers }),
      fetch(`${process.env.NEXT_PUBLIC_API_URL}/pools/${id}/is-admin`, { headers }),
    ]).then(async ([poolResponse, membersResponse, adminResponse]) => {
      if (!poolResponse.ok || !membersResponse.ok) throw new Error('Unable to load pool members.');
      setPool(await poolResponse.json());
      setDirectory(await membersResponse.json());
      if (adminResponse.ok) setAdminStatus(await adminResponse.json());
    }).catch((loadError) => setError(loadError.message || 'Unable to load pool members.'));
  }, [id]);

  const sortedMembers = useMemo(() => {
    if (!directory) return [];
    return [...directory.users].sort((left, right) => {
      const comparison = sort.field === 'remaining'
        ? left.remaining_entry_count - right.remaining_entry_count
        : left.display_name.localeCompare(right.display_name, undefined, { sensitivity: 'base' });
      return sort.direction === 'asc' ? comparison : -comparison;
    });
  }, [directory, sort]);
  const changeSort = (field) => setSort((current) => current.field === field
    ? { field, direction: current.direction === 'asc' ? 'desc' : 'asc' }
    : { field, direction: field === 'remaining' ? 'desc' : 'asc' });
  if (!router.isReady) return null;
  const showAdmin = Boolean(adminStatus?.has_admin_access || adminStatus?.is_admin || adminStatus?.is_owner);

  return <ProtectedRoute><div className="product-page pool-members-page"><main className="product-main pool-members-main">
    {pool && <PoolWorkspaceNav poolId={id} poolName={pool.name} poolType={pool.pool_type} active="members" showAdmin={showAdmin} />}
    <WorkspaceHeader eyebrow="Pool roster" title="Members" description="Everyone currently participating in this pool." meta={directory ? `${directory.total_users} ${directory.total_users === 1 ? 'member' : 'members'}` : null} />
    {error ? <div className="workspace-alert workspace-alert--error" role="alert">{error}</div> : !directory ? <div className="pool-members-state">Loading members…</div> : directory.users.length === 0 ? <div className="pool-members-state">No members have joined this pool yet.</div> : <>
      <div className="pool-members-sort" aria-label="Sort pool members">
        <span>Sort by</span>
        <button type="button" aria-pressed={sort.field === 'name'} onClick={() => changeSort('name')}>Name {sort.field === 'name' ? (sort.direction === 'asc' ? 'A–Z' : 'Z–A') : ''}</button>
        <button type="button" aria-pressed={sort.field === 'remaining'} onClick={() => changeSort('remaining')}>Picks Remaining {sort.field === 'remaining' ? (sort.direction === 'asc' ? 'Low–High' : 'High–Low') : ''}</button>
      </div>
      <section className="pool-members-list" aria-label="Pool members">
      {sortedMembers.map((member) => <article key={member.id} className="pool-member-card">
        <div className="pool-member-card__avatar" aria-hidden="true">{member.display_name.slice(0, 1).toUpperCase()}</div>
        <div><strong>{member.display_name}</strong><span>{member.pool_role}</span></div>
        <div className="pool-member-card__entries" aria-label={`${member.remaining_entry_count} of ${member.total_entry_count} entries remaining`}><strong>{member.remaining_entry_count}/{member.total_entry_count}</strong><span>Remaining / Total</span></div>
      </article>)}
      </section>
    </>}
  </main></div></ProtectedRoute>;
}
