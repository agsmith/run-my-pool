import { useEffect, useState } from 'react';
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

  if (!router.isReady) return null;
  const showAdmin = Boolean(adminStatus?.has_admin_access || adminStatus?.is_admin || adminStatus?.is_owner);

  return <ProtectedRoute><div className="product-page pool-members-page"><main className="product-main pool-members-main">
    {pool && <PoolWorkspaceNav poolId={id} poolName={pool.name} poolType={pool.pool_type} active="members" showAdmin={showAdmin} />}
    <WorkspaceHeader eyebrow="Pool roster" title="Members" description="Everyone currently participating in this pool." meta={directory ? `${directory.total_users} ${directory.total_users === 1 ? 'member' : 'members'}` : null} />
    {error ? <div className="workspace-alert workspace-alert--error" role="alert">{error}</div> : !directory ? <div className="pool-members-state">Loading members…</div> : directory.users.length === 0 ? <div className="pool-members-state">No members have joined this pool yet.</div> : <section className="pool-members-list" aria-label="Pool members">
      {directory.users.map((member) => <article key={member.id} className="pool-member-card">
        <div className="pool-member-card__avatar" aria-hidden="true">{member.display_name.slice(0, 1).toUpperCase()}</div>
        <div><strong>{member.display_name}</strong><span>{member.pool_role}</span></div>
        <div className="pool-member-card__entries" aria-label={`${member.remaining_entry_count} of ${member.total_entry_count} entries remaining`}><strong>{member.remaining_entry_count}/{member.total_entry_count}</strong><span>Remaining / Total</span></div>
      </article>)}
    </section>}
  </main></div></ProtectedRoute>;
}
