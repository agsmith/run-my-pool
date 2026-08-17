import { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import ProtectedRoute from '../../../components/ProtectedRoute';
import { PoolWorkspaceNav, WorkspaceHeader } from '../../../components/ProductWorkspace';

const headers = () => ({ Authorization: `Bearer ${localStorage.getItem('access_token')}` });

export default function PoolLeaderboardPage() {
  const router = useRouter();
  const { id } = router.query;
  const [pool, setPool] = useState(null);
  const [entries, setEntries] = useState(null);
  const [adminStatus, setAdminStatus] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!id) return;
    Promise.all([
      fetch(`${process.env.NEXT_PUBLIC_API_URL}/pools/${id}`, { headers: headers() }),
      fetch(`${process.env.NEXT_PUBLIC_API_URL}/picks/pool/${id}/leaderboard`, { headers: headers() }),
      fetch(`${process.env.NEXT_PUBLIC_API_URL}/pools/${id}/is-admin`, { headers: headers() }),
    ]).then(async ([poolResponse, leaderboardResponse, adminResponse]) => {
      if (!poolResponse.ok || !leaderboardResponse.ok) throw new Error('Unable to load the leaderboard.');
      const poolData = await poolResponse.json();
      if (poolData.pool_type === 'squares') return router.replace(`/pool/${id}/squares`);
      setPool(poolData);
      setEntries(await leaderboardResponse.json());
      if (adminResponse.ok) setAdminStatus(await adminResponse.json());
    }).catch((loadError) => setError(loadError.message || 'Unable to load the leaderboard.'));
  }, [id]);

  const showAdmin = Boolean(adminStatus?.has_admin_access || adminStatus?.is_admin || adminStatus?.is_owner);

  return <ProtectedRoute><div className="product-page leaderboard-page"><main className="product-main leaderboard-main">
    {pool && <PoolWorkspaceNav poolId={id} poolName={pool.name} poolType={pool.pool_type} active="leaderboard" showAdmin={showAdmin} />}
    <WorkspaceHeader eyebrow="Pool standings" title="Leaderboard" description="Every entry, ranked by correct picks. Selections appear for everyone after the week locks or the result is final." meta={entries ? `${entries.length} ${entries.length === 1 ? 'entry' : 'entries'}` : null} />
    {error ? <div className="workspace-alert workspace-alert--error" role="alert">{error}</div> : !entries ? <div className="leaderboard-state">Loading leaderboard…</div> : entries.length === 0 ? <div className="leaderboard-state">No entries have been created yet.</div> : <section className="leaderboard-list" aria-label="Pool leaderboard">
      {entries.map((entry) => <article className="leaderboard-entry" key={entry.entry_id}>
        <div className="leaderboard-entry__rank" aria-label={`Rank ${entry.rank}`}>{entry.rank}</div>
        <div className="leaderboard-entry__identity"><strong>{entry.entry_name}</strong><span>{entry.user_email}</span></div>
        <div className="leaderboard-entry__score"><strong>{entry.correct_picks}</strong><span>Correct</span></div>
        <div className="leaderboard-entry__record"><strong>{entry.completed_picks}</strong><span>Final picks</span></div>
        <span className={`leaderboard-entry__status ${entry.alive ? 'is-alive' : 'is-eliminated'}`}>{entry.alive ? 'Remaining' : 'Eliminated'}</span>
        <div className="leaderboard-entry__picks" aria-label={`${entry.entry_name} revealed picks`}>
          {entry.picks.length ? entry.picks.map((pick, index) => <span className={`leaderboard-pick is-${pick.result || 'pending'}`} key={`${pick.week}-${pick.team}-${index}`}><b>W{pick.week}</b> {pick.team}</span>) : <span className="leaderboard-entry__empty">No revealed picks yet</span>}
        </div>
      </article>)}
    </section>}
  </main></div></ProtectedRoute>;
}
