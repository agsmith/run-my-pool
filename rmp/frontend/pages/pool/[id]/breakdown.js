import { useEffect, useMemo, useState } from 'react';
import { useRouter } from 'next/router';
import ProtectedRoute from '../../../components/ProtectedRoute';
import { PoolWorkspaceNav, WorkspaceHeader } from '../../../components/ProductWorkspace';

const headers = () => ({ Authorization: `Bearer ${localStorage.getItem('access_token')}` });

const weekIsLocked = (lock) => Boolean(
  lock?.locked || (lock?.deadline && Date.parse(lock.deadline) <= Date.now()),
);

export default function PickEmBreakdownPage() {
  const router = useRouter();
  const { id } = router.query;
  const [pool, setPool] = useState(null);
  const [week, setWeek] = useState(null);
  const [locks, setLocks] = useState(null);
  const [rows, setRows] = useState([]);
  const [standings, setStandings] = useState([]);
  const [adminStatus, setAdminStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [refresh, setRefresh] = useState(0);

  useEffect(() => {
    if (!id) return;
    let active = true;
    setError('');
    Promise.all([
      fetch(`${process.env.NEXT_PUBLIC_API_URL}/pools/${id}`, { headers: headers() }),
      fetch(`${process.env.NEXT_PUBLIC_API_URL}/pools/${id}/activity-summary`, { headers: headers() }),
      fetch(`${process.env.NEXT_PUBLIC_API_URL}/pools/${id}/lock-status`, { headers: headers() }),
      fetch(`${process.env.NEXT_PUBLIC_API_URL}/pools/${id}/is-admin`, { headers: headers() }),
    ]).then(async ([poolResponse, activityResponse, lockResponse, adminResponse]) => {
      if (!poolResponse.ok || !activityResponse.ok || !lockResponse.ok) {
        throw new Error('Unable to load Weekly Pick Breakdown.');
      }
      const poolData = await poolResponse.json();
      if (poolData.pool_type !== 'pickem') {
        router.replace(`/pool/${id}/entries`);
        return;
      }
      const [activity, lockData] = await Promise.all([
        activityResponse.json(),
        lockResponse.json(),
      ]);
      if (!active) return;
      setPool(poolData);
      setLocks(lockData.weeks || {});
      setWeek((current) => current || activity.week || 1);
      if (adminResponse.ok) setAdminStatus(await adminResponse.json());
    }).catch((loadError) => {
      if (active) {
        setError(loadError.message || 'Unable to load Weekly Pick Breakdown.');
        setLoading(false);
      }
    });
    return () => { active = false; };
  }, [id]);

  useEffect(() => {
    if (!id || !week || !pool || !locks) return;
    let active = true;
    const locked = weekIsLocked(locks[String(week)]);
    setError('');
    if (!locked) {
      setRows([]);
      setStandings([]);
      setLoading(false);
      return () => { active = false; };
    }
    setLoading(true);
    Promise.all([
      fetch(`${process.env.NEXT_PUBLIC_API_URL}/picks/pool/${id}/week/${week}/breakdown`, { headers: headers() }),
      fetch(`${process.env.NEXT_PUBLIC_API_URL}/picks/pool/${id}/weekly-standings/${week}`, { headers: headers() }),
    ]).then(async ([breakdownResponse, standingsResponse]) => {
      if (!breakdownResponse.ok || !standingsResponse.ok) {
        throw new Error(`Unable to load the Week ${week} Pick Breakdown.`);
      }
      const [breakdownData, standingData] = await Promise.all([
        breakdownResponse.json(),
        standingsResponse.json(),
      ]);
      if (active) {
        setRows(Array.isArray(breakdownData) ? breakdownData : []);
        setStandings(Array.isArray(standingData) ? standingData : []);
        setLoading(false);
      }
    }).catch((loadError) => {
      if (active) {
        setError(loadError.message || `Unable to load the Week ${week} Pick Breakdown.`);
        setLoading(false);
      }
    });
    return () => { active = false; };
  }, [id, week, pool, locks, refresh]);

  const teamsByEntry = useMemo(() => {
    const entries = new Map();
    rows.forEach((row) => (row.entries || []).forEach((entry) => {
      const picks = entries.get(entry.entry_id) || [];
      picks.push({ team: row.team_abbrv || row.team, result: row.result });
      entries.set(entry.entry_id, picks);
    }));
    return entries;
  }, [rows]);

  const locked = weekIsLocked(locks?.[String(week)]);
  const showAdmin = Boolean(adminStatus?.has_admin_access || adminStatus?.is_admin || adminStatus?.is_owner);

  return <ProtectedRoute><div className="product-page pick-breakdown-page"><main className="product-main pick-breakdown-main">
    {pool && <PoolWorkspaceNav poolId={id} poolName={pool.name} poolType="pickem" active="breakdown" showAdmin={showAdmin} />}
    <WorkspaceHeader eyebrow="Weekly results" title="Weekly Pick Breakdown" description="See every member’s revealed picks, weekly wins, and point-total tiebreaker after the weekly lock." meta={week ? `Week ${week}` : null} />
    {pool && <section className="matchup-toolbar" aria-label="Weekly Pick Breakdown week selector">
      <button type="button" disabled={week <= 1} onClick={() => setWeek((value) => value - 1)}>← Previous</button>
      <label>Week <select aria-label="Weekly Pick Breakdown week" value={week || ''} onChange={(event) => setWeek(Number(event.target.value))}>
        {Array.from({ length: 18 }, (_, index) => <option key={index + 1} value={index + 1}>Week {index + 1}</option>)}
      </select></label>
      <button type="button" onClick={() => setRefresh((value) => value + 1)}>Refresh</button>
      <button type="button" disabled={week >= 18} onClick={() => setWeek((value) => value + 1)}>Next →</button>
    </section>}
    {error ? <div className="workspace-alert workspace-alert--error" role="alert">{error}</div>
      : !pool || loading ? <div className="pick-breakdown-state" role="status">Loading Weekly Pick Breakdown…</div>
        : !locked ? <div className="pick-breakdown-state" role="status">Week {week} picks will appear after the weekly lock.</div>
          : standings.length === 0 ? <div className="pick-breakdown-state">No entries have revealed picks for Week {week}.</div>
            : <section className="pick-breakdown-list" aria-label={`Week ${week} Pick Breakdown`}>
              {standings.map((standing) => <article className="pick-breakdown-entry" key={standing.entry_id}>
                <div className="pick-breakdown-entry__header">
                  <div className="pick-breakdown-entry__rank" aria-label={`Rank ${standing.rank}`}>#{standing.rank}</div>
                  <div className="pick-breakdown-entry__member">
                    <strong>{standing.user_display_name}</strong>
                    <span>{standing.entry_name}</span>
                  </div>
                  <div className="pick-breakdown-entry__wins"><strong>{standing.points}</strong><span>{standing.points === 1 ? 'Win' : 'Wins'}</span></div>
                </div>
                <div className="pick-breakdown-entry__picks" aria-label={`${standing.entry_name} Week ${week} picks`}>
                  {(teamsByEntry.get(standing.entry_id) || []).map((pick, index) => <span className={`pick-breakdown-label is-${pick.result || 'pending'}`} key={`${pick.team}-${index}`}>
                    {pick.team} · {pick.result === 'win' ? 'W' : pick.result === 'loss' ? 'L' : '—'}
                  </span>)}
                  {standing.predicted_total != null && <span className="pick-breakdown-label is-tiebreaker">Total: {standing.predicted_total}</span>}
                  {standing.predicted_total == null && !(teamsByEntry.get(standing.entry_id) || []).length && <span className="pick-breakdown-entry__empty">No revealed picks</span>}
                </div>
              </article>)}
            </section>}
    <style jsx>{`
      .pick-breakdown-main { min-width: 0; }
      .pick-breakdown-state { padding: clamp(22px, 5vw, 48px); border: 1px solid var(--bn-line); background: var(--bn-panel); color: var(--bn-muted); text-align: center; }
      .pick-breakdown-list { display: grid; gap: 12px; }
      .pick-breakdown-entry { padding: 16px; border: 1px solid var(--bn-line); background: var(--bn-panel); min-width: 0; }
      .pick-breakdown-entry__header { display: grid; grid-template-columns: 42px minmax(0, 1fr) auto; gap: 12px; align-items: center; }
      .pick-breakdown-entry__rank { color: var(--bn-cyan); font-weight: 900; }
      .pick-breakdown-entry__member { min-width: 0; }
      .pick-breakdown-entry__member strong, .pick-breakdown-entry__member span { display: block; overflow-wrap: anywhere; }
      .pick-breakdown-entry__member strong { color: var(--bn-ink); font-size: 1rem; }
      .pick-breakdown-entry__member span { margin-top: 3px; color: var(--bn-muted); font-size: .78rem; }
      .pick-breakdown-entry__wins { text-align: right; color: var(--bn-lime); }
      .pick-breakdown-entry__wins strong, .pick-breakdown-entry__wins span { display: block; }
      .pick-breakdown-entry__wins strong { font-size: 1.3rem; }
      .pick-breakdown-entry__wins span { font-size: .68rem; font-weight: 900; letter-spacing: .08em; text-transform: uppercase; }
      .pick-breakdown-entry__picks { display: flex; flex-wrap: wrap; gap: 7px; margin: 12px 0 0 54px; }
      .pick-breakdown-label { padding: 5px 8px; border: 1px solid var(--bn-line); border-radius: 5px; color: var(--bn-muted); font-size: .75rem; font-weight: 800; }
      .pick-breakdown-label.is-win { border-color: #62c98b; color: #b9f6cf; }
      .pick-breakdown-label.is-loss { border-color: #f19aaf; color: #ffd0dd; }
      .pick-breakdown-label.is-tiebreaker { border-color: var(--bn-cyan); color: var(--bn-cyan); }
      .pick-breakdown-entry__empty { color: var(--bn-muted); font-size: .8rem; }
      @media (max-width: 640px) {
        .pick-breakdown-entry { padding: 13px; }
        .pick-breakdown-entry__header { grid-template-columns: 32px minmax(0, 1fr) auto; gap: 8px; }
        .pick-breakdown-entry__picks { margin-left: 40px; }
      }
    `}</style>
  </main></div></ProtectedRoute>;
}
