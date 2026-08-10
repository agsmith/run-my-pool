import { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import ProtectedRoute from '../../../components/ProtectedRoute';
import { PoolWorkspaceNav, WorkspaceHeader } from '../../../components/ProductWorkspace';

function Team({ team }) {
  return <div className="matchup-team">
    <img src={`/nfl/${team.abbrv.toLowerCase()}.svg`} alt="" />
    <span><strong>{team.abbrv}</strong><small>{team.name}</small></span>
  </div>;
}

function Line({ game }) {
  const line = game.official_line || game.live_line;
  if (!line) return <span className="matchup-line matchup-line--pending">Line pending</span>;
  return <div className="matchup-line">
    <strong>{line.details || 'Pick’em'}</strong>
    <small>{game.official_line ? 'Official line at lock' : `Live · ${line.provider}`}</small>
  </div>;
}

export default function MatchupsPage() {
  const router = useRouter();
  const { id } = router.query;
  const [pool, setPool] = useState(null);
  const [week, setWeek] = useState(1);
  const [games, setGames] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!id) return;
    const token = localStorage.getItem('access_token');
    fetch(`${process.env.NEXT_PUBLIC_API_URL}/pools/${id}`, { headers: { Authorization: `Bearer ${token}` } })
      .then((res) => res.ok ? res.json() : Promise.reject())
      .then(setPool)
      .catch(() => setError('Unable to load pool.'));
  }, [id]);

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    setError('');
    fetch(`${process.env.NEXT_PUBLIC_API_URL}/schedule/week/${week}/matchups?pool_id=${id}`)
      .then((res) => res.ok ? res.json() : Promise.reject())
      .then(setGames)
      .catch(() => setError('Unable to load this week’s matchups.'))
      .finally(() => setLoading(false));
  }, [id, week]);

  return <ProtectedRoute><main className="product-page-shell">
    <PoolWorkspaceNav poolId={id} poolName={pool?.name} active="matchups" />
    <WorkspaceHeader
      eyebrow="Weekly board"
      title={`Week ${week} matchups`}
      description="Review the complete slate and current point spreads without entering the pick flow."
      meta={pool?.lock_time ? `Lines become official at ${new Date(pool.lock_time).toLocaleString()}` : 'Official lines freeze with picks'}
    />
    <section className="matchup-toolbar">
      <button disabled={week === 1} onClick={() => setWeek((value) => value - 1)}>← Previous</button>
      <label>Week <select value={week} onChange={(event) => setWeek(Number(event.target.value))}>
        {Array.from({ length: 18 }, (_, index) => index + 1).map((value) => <option key={value}>{value}</option>)}
      </select></label>
      <button disabled={week === 18} onClick={() => setWeek((value) => value + 1)}>Next →</button>
    </section>
    {error && <div className="workspace-alert workspace-alert--error">{error}</div>}
    {loading ? <div className="matchup-empty">Loading live lines…</div> : games.length === 0 ?
      <div className="matchup-empty">No matchups are scheduled for this week.</div> :
      <section className="matchup-board">{games.map((game) => <article className="matchup-card" key={game.game_id}>
        <time>{new Date(game.start_time).toLocaleString([], { weekday: 'short', month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' })}</time>
        <div className="matchup-card__teams"><Team team={game.away_team} /><span className="matchup-at">@</span><Team team={game.home_team} /></div>
        <Line game={game} />
      </article>)}</section>}
    <p className="matchup-disclaimer">Lines are informational and may move until the pool lock. The official line is preserved at lock and used for automatic picks.</p>
  </main></ProtectedRoute>;
}
