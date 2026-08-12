import { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import ProtectedRoute from '../../components/ProtectedRoute';
import { useAuth } from '../../context/AuthContext';
import { PoolWorkspaceNav, WorkspaceHeader } from '../../components/ProductWorkspace';

const DAYS_OF_WEEK = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];

function formatClockTime(value) {
  const [hour = 0, minute = '00'] = String(value || '').split(':');
  const numericHour = Number(hour);
  if (!Number.isFinite(numericHour)) return null;
  return `${numericHour % 12 || 12}:${minute} ${numericHour < 12 ? 'AM' : 'PM'}`;
}

export function formatPickLock(pool) {
  if (pool?.lock_day_of_week != null && pool?.lock_time_of_day) {
    const day = DAYS_OF_WEEK[pool.lock_day_of_week];
    const time = formatClockTime(pool.lock_time_of_day);
    const timezone = pool.lock_timezone || 'UTC';
    if (day && time) return `${day} at ${time} · ${timezone}`;
  }
  if (pool?.lock_time) {
    const lockDate = new Date(pool.lock_time);
    if (!Number.isNaN(lockDate.getTime())) return lockDate.toLocaleString();
  }
  return 'Not scheduled';
}

export default function PoolDetail() {
  const [pool, setPool] = useState(null);
  const [adminStatus, setAdminStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [successMessage, setSuccessMessage] = useState('');
  const router = useRouter();
  const { user } = useAuth();
  const { id } = router.query;

  useEffect(() => {
    if (router.query.message) setSuccessMessage(router.query.message);
  }, [router.query.message]);

  useEffect(() => {
    if (!id) return;
    const loadPool = async () => {
      try {
        const token = localStorage.getItem('access_token');
        const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/pools/${id}`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!response.ok) throw new Error('Failed to load pool details');
        setPool(await response.json());
        try {
          const adminResponse = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/pools/${id}/is-admin`, {
            headers: { Authorization: `Bearer ${token}` },
          });
          if (adminResponse.ok) setAdminStatus(await adminResponse.json());
        } catch {
          setAdminStatus(null);
        }
      } catch (err) {
        setError(err.message || 'Failed to load pool details');
      } finally {
        setLoading(false);
      }
    };
    loadPool();
  }, [id]);

  const deletePool = async () => {
    if (!confirm('Delete this pool and all of its data? This cannot be undone.')) return;
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/pools/${id}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || 'Failed to delete pool');
      router.push('/dashboard?message=Pool deleted successfully');
    } catch (err) {
      setError(err.message || 'Failed to delete pool');
    }
  };

  if (!router.isReady) return null;

  const isOwner = pool?.owner_id === user?.id;
  const isAdmin = Boolean(adminStatus?.is_admin);
  const hasAdminAccess = isOwner || isAdmin;
  const userRole = isOwner ? 'Commissioner' : isAdmin ? 'Admin' : 'Player';

  return (
    <ProtectedRoute>
      <div className="product-page pool-home-page">
        <main className="product-main pool-home-main">
          {loading ? (
            <div className="pool-home-state">Loading pool…</div>
          ) : error && !pool ? (
            <div className="pool-home-state pool-home-state--error">{error}</div>
          ) : pool ? (
            <>
              <PoolWorkspaceNav poolId={id} poolName={pool.name} active="overview" showAdmin={hasAdminAccess} />
              <WorkspaceHeader
                eyebrow="Pool headquarters"
                title={pool.name}
                description={pool.description || 'Everything your pool needs for the week, organized in one place.'}
                meta={`${pool.is_private ? 'Private' : 'Public'} pool`}
                actions={<button className="workspace-primary-action" onClick={() => router.push(`/pool/${id}/entries`)}>Make picks</button>}
              />

              {successMessage && <div className="pool-home-notice pool-home-notice--success">{successMessage}</div>}
              {error && <div className="pool-home-notice pool-home-notice--error">{error}</div>}

              <section className="pool-home-actions" aria-label="Pool shortcuts">
                <button onClick={() => router.push(`/pool/${id}/entries`)}><span>01</span><strong>My Entries</strong><small>Make selections and review entries</small></button>
                <button onClick={() => router.push(`/pool/${id}/matchups`)}><span>02</span><strong>Weekly Matchups</strong><small>Review this week’s board</small></button>
                <button onClick={() => router.push(`/pool/${id}/messages`)}><span>03</span><strong>Forum</strong><small>Talk with pool members</small></button>
              </section>

              <section className="pool-home-details">
                <div className="pool-home-details__heading">
                  <span>At a glance</span>
                  <h2>Pool Information</h2>
                </div>
                <dl>
                  <div><dt>Access</dt><dd>{pool.is_private ? 'Private · Password required' : 'Public · Open joining'}</dd></div>
                  <div><dt>Pick lock</dt><dd>{formatPickLock(pool)}</dd></div>
                  <div><dt>Your role</dt><dd>{userRole}</dd></div>
                  <div><dt>Season format</dt><dd>Weekly survivor</dd></div>
                </dl>
              </section>

              <footer className="pool-home-footer">
                <button onClick={() => router.push('/dashboard')}>Back to Dashboard</button>
                {hasAdminAccess && (
                  <div>
                    <button onClick={() => router.push(`/admin/league/${id}`)}>Commissioner Settings</button>
                    {isOwner && <button className="pool-home-delete" onClick={deletePool}>Delete Pool</button>}
                  </div>
                )}
              </footer>
            </>
          ) : (
            <div className="pool-home-state">Pool not found.</div>
          )}
        </main>
      </div>
    </ProtectedRoute>
  );
}
