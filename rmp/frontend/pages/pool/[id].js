import { useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/router';
import ProtectedRoute from '../../components/ProtectedRoute';
import { useAuth } from '../../context/AuthContext';
import { PoolWorkspaceNav, WorkspaceHeader } from '../../components/ProductWorkspace';
import PoolLaunchChecklist from '../../components/PoolLaunchChecklist';
import MemberPoolWelcome from '../../components/MemberPoolWelcome';
import WeeklyActionCenter from '../../components/WeeklyActionCenter';
import MemberWeeklyRecap from '../../components/MemberWeeklyRecap';
import { trackLifecycleEvent } from '../../lib/lifecycleAnalytics';

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
  const [weeklySummary, setWeeklySummary] = useState(null);
  const [weeklySummaryError, setWeeklySummaryError] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [successMessage, setSuccessMessage] = useState('');
  const [showLaunchChecklist, setShowLaunchChecklist] = useState(false);
  const [showMemberWelcome, setShowMemberWelcome] = useState(false);
  const [showLeaveConfirmation, setShowLeaveConfirmation] = useState(false);
  const [leavingPool, setLeavingPool] = useState(false);
  const [seasonLocked, setSeasonLocked] = useState(false);
  const [memberRecapEnabled, setMemberRecapEnabled] = useState(null);
  const trackedLaunch = useRef(false);
  const trackedMemberWelcome = useRef(false);
  const trackedWeeklyAction = useRef(false);
  const router = useRouter();
  const { user } = useAuth();
  const { id } = router.query;

  useEffect(() => {
    if (router.query.message) setSuccessMessage(router.query.message);
  }, [router.query.message]);

  useEffect(() => {
    if (router.query.launched === '1') setShowLaunchChecklist(true);
    if (router.query.joined === '1') setShowMemberWelcome(true);
  }, [router.query.joined, router.query.launched]);

  useEffect(() => {
    if (!id) return;
    const loadPool = async () => {
      setWeeklySummary(null);
      setWeeklySummaryError(false);
      trackedWeeklyAction.current = false;
      try {
        const token = localStorage.getItem('access_token');
        const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/pools/${id}`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!response.ok) throw new Error('Failed to load pool details');
        const poolData = await response.json();
        setPool(poolData);
        setSeasonLocked(Boolean(poolData.lock_time && new Date(poolData.lock_time).getTime() <= Date.now()));
        try {
          const summaryResponse = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/pools/${id}/activity-summary`, {
            headers: { Authorization: `Bearer ${token}` },
          });
          if (!summaryResponse.ok) throw new Error('Failed to load weekly status');
          setWeeklySummary(await summaryResponse.json());
        } catch {
          setWeeklySummaryError(true);
        }
        try {
          const adminResponse = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/pools/${id}/is-admin`, {
            headers: { Authorization: `Bearer ${token}` },
          });
          if (adminResponse.ok) setAdminStatus(await adminResponse.json());
        } catch {
          setAdminStatus(null);
        }
        if (poolData.pool_type !== 'squares') {
          try {
            const recapResponse = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/pools/${id}/member-recap-preference`, {
              headers: { Authorization: `Bearer ${token}` },
            });
            if (recapResponse.ok) setMemberRecapEnabled((await recapResponse.json()).enabled);
          } catch {
            setMemberRecapEnabled(null);
          }
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

  const sendPoolInvite = async (email) => {
    const token = localStorage.getItem('access_token');
    const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/pools/${id}/invite-email`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      body: JSON.stringify({ email }),
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.detail || 'Unable to send the invitation.');
  };

  const leavePool = async () => {
    setLeavingPool(true);
    setError('');
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/pools/${id}/membership`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.detail || 'Unable to leave the pool.');
      router.push(`/dashboard?message=${encodeURIComponent(data.message || `You left ${pool.name}`)}`);
    } catch (err) {
      setError(err.message || 'Unable to leave the pool.');
      setShowLeaveConfirmation(false);
    } finally {
      setLeavingPool(false);
    }
  };

  const isOwner = pool?.owner_id === user?.id;
  const isAdmin = Boolean(adminStatus?.is_admin);
  const hasAdminAccess = isOwner || isAdmin || Boolean(adminStatus?.has_admin_access);
  const userRole = isOwner ? 'Commissioner' : isAdmin ? 'Admin' : 'Player';
  const mayLeavePool = adminStatus !== null && !hasAdminAccess;
  const picksHref = pool?.pool_type === 'pickem' ? `/pool/${id}/pickem` : pool?.pool_type === 'squares' ? `/pool/${id}/squares` : `/pool/${id}/entries`;

  useEffect(() => {
    if (!showLaunchChecklist || !isOwner || trackedLaunch.current) return;
    trackedLaunch.current = true;
    trackLifecycleEvent('pool_launch_checklist_view', { page: 'pool_home' });
  }, [isOwner, showLaunchChecklist]);

  useEffect(() => {
    if (!showMemberWelcome || isOwner || trackedMemberWelcome.current) return;
    trackedMemberWelcome.current = true;
    trackLifecycleEvent('member_onboarding_view', { page: 'pool_home' });
  }, [isOwner, showMemberWelcome]);

  useEffect(() => {
    if (!weeklySummary || trackedWeeklyAction.current) return;
    trackedWeeklyAction.current = true;
    trackLifecycleEvent('weekly_action_center_view', { page: 'pool_home' });
  }, [weeklySummary]);

  const openWeeklyAction = (createEntry = false) => {
    trackLifecycleEvent('weekly_picks_action_clicked', { page: 'pool_home' });
    router.push(createEntry ? `/pool/${id}/entries/create` : picksHref);
  };

  if (!router.isReady) return null;

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
              <PoolWorkspaceNav poolId={id} poolName={pool.name} poolType={pool.pool_type} active="overview" showAdmin={hasAdminAccess} />
              <WorkspaceHeader
                eyebrow="Pool headquarters"
                title={pool.name}
                description={pool.description || 'Everything your pool needs for the week, organized in one place.'}
                meta={`${pool.is_private ? 'Private' : 'Public'} pool`}
                actions={<button className="workspace-primary-action" onClick={() => router.push(picksHref)}>Make picks</button>}
              />

              {successMessage && <div className="pool-home-notice pool-home-notice--success">{successMessage}</div>}
              {error && <div className="pool-home-notice pool-home-notice--error">{error}</div>}

              {isOwner && showLaunchChecklist && (
                <PoolLaunchChecklist
                  pool={pool}
                  onClose={() => setShowLaunchChecklist(false)}
                  onNavigate={(destination) => router.push(destination)}
                  onInviteCopied={() => trackLifecycleEvent('pool_invite_link_copied', { page: 'pool_home' })}
                  onSendInvite={sendPoolInvite}
                />
              )}

              {!isOwner && showMemberWelcome && (
                <MemberPoolWelcome
                  pool={pool}
                  onCreateEntry={() => router.push(pool.pool_type === 'squares' ? `/pool/${id}/squares` : `/pool/${id}/entries/create`)}
                  onDismiss={() => setShowMemberWelcome(false)}
                />
              )}

              <WeeklyActionCenter
                summary={weeklySummary}
                loading={!weeklySummary && !weeklySummaryError}
                error={weeklySummaryError}
                onAction={openWeeklyAction}
              />

              <section className="pool-home-actions" aria-label="Pool shortcuts">
                <button onClick={() => router.push(picksHref)}><span>01</span><strong>{pool.pool_type === 'pickem' ? 'Pick ’Em Board' : pool.pool_type === 'squares' ? 'Squares Board' : 'My Entries'}</strong><small>{pool.pool_type === 'squares' ? 'Claim squares and follow quarter winners' : 'Make selections and review entries'}</small></button>
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
                  <div><dt>Season format</dt><dd>{pool.pool_type === 'pickem' ? 'Season-long Pick ’Em · one point per win' : pool.pool_type === 'squares' ? 'Multi-game 10×10 Squares' : 'Weekly survivor'}</dd></div>
                  {pool.pool_type === 'survivor' && <div><dt>Second chances</dt><dd>{pool.survivor_mulligans ? `${pool.survivor_mulligans} mulligan${pool.survivor_mulligans === 1 ? '' : 's'} per entry` : 'None · classic Survivor'}</dd></div>}
                </dl>
              </section>

              {memberRecapEnabled !== null && (
                <MemberWeeklyRecap
                  poolId={id}
                  enabled={memberRecapEnabled}
                  onChange={setMemberRecapEnabled}
                />
              )}

              <footer className="pool-home-footer">
                <button onClick={() => router.push('/dashboard')}>Back to Dashboard</button>
                {mayLeavePool && (
                  <button
                    className="pool-home-leave"
                    type="button"
                    disabled={seasonLocked}
                    title={seasonLocked ? 'This pool is locked for the season. Members can no longer leave.' : undefined}
                    onClick={() => setShowLeaveConfirmation(true)}
                  >
                    {seasonLocked ? 'Pool Locked · Cannot Leave' : 'Leave Pool'}
                  </button>
                )}
                {hasAdminAccess && (
                  <div>
                    {isOwner && <button onClick={() => setShowLaunchChecklist(true)}>Launch Checklist</button>}
                    <button onClick={() => router.push(`/admin/league/${id}`)}>Commissioner Settings</button>
                    {isOwner && <button className="pool-home-delete" onClick={deletePool}>Delete Pool</button>}
                  </div>
                )}
              </footer>
              {showLeaveConfirmation && (
                <div className="pool-leave-overlay" role="presentation" onMouseDown={(event) => {
                  if (event.target === event.currentTarget && !leavingPool) setShowLeaveConfirmation(false);
                }}>
                  <section className="pool-leave-dialog" role="dialog" aria-modal="true" aria-labelledby="leave-pool-title" aria-describedby="leave-pool-warning">
                    <span>Membership action</span>
                    <h2 id="leave-pool-title">Leave {pool.name}?</h2>
                    <p id="leave-pool-warning"><strong>Warning:</strong> Leaving this pool will permanently delete all of your entries and picks in this pool. Any Squares reservations you made will also be released. This cannot be undone.</p>
                    <div>
                      <button type="button" disabled={leavingPool} onClick={() => setShowLeaveConfirmation(false)}>Cancel</button>
                      <button type="button" className="pool-leave-dialog__confirm" disabled={leavingPool} onClick={leavePool}>{leavingPool ? 'Leaving…' : 'Leave Pool'}</button>
                    </div>
                  </section>
                </div>
              )}
            </>
          ) : (
            <div className="pool-home-state">Pool not found.</div>
          )}
        </main>
      </div>
    </ProtectedRoute>
  );
}
