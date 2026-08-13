import { useEffect, useMemo, useState } from 'react';
import { useRouter } from 'next/router';
import Link from 'next/link';
import ProtectedRoute from '../../../components/ProtectedRoute';
import { PoolWorkspaceNav, WorkspaceHeader } from '../../../components/ProductWorkspace';

const authHeaders = () => ({ Authorization: `Bearer ${localStorage.getItem('access_token')}` });

export default function PickEmPage() {
  const router = useRouter();
  const { id } = router.query;
  const [pool, setPool] = useState(null);
  const [entries, setEntries] = useState([]);
  const [entryId, setEntryId] = useState('');
  const [week, setWeek] = useState(1);
  const [games, setGames] = useState([]);
  const [picks, setPicks] = useState([]);
  const [standings, setStandings] = useState([]);
  const [error, setError] = useState('');
  const [savingGame, setSavingGame] = useState(null);

  const picksByGame = useMemo(() => Object.fromEntries(picks.filter((pick) => pick.week === week).map((pick) => [pick.game_id, pick])), [picks, week]);
  const weeklyTarget = Math.min(pool?.pickem_games_per_week || games.length, games.length);
  const targetReached = weeklyTarget > 0 && Object.keys(picksByGame).length >= weeklyTarget;

  useEffect(() => {
    if (!id) return;
    Promise.all([
      fetch(`${process.env.NEXT_PUBLIC_API_URL}/pools/${id}`, { headers: authHeaders() }).then((res) => res.json()),
      fetch(`${process.env.NEXT_PUBLIC_API_URL}/entries/pool/${id}`, { headers: authHeaders() }).then((res) => res.ok ? res.json() : []),
      fetch(`${process.env.NEXT_PUBLIC_API_URL}/picks/pool/${id}/standings`, { headers: authHeaders() }).then((res) => res.ok ? res.json() : []),
    ]).then(([poolData, entryData, standingData]) => {
      if (poolData.pool_type !== 'pickem') return router.replace(`/pool/${id}/entries`);
      setPool(poolData); setEntries(entryData); setEntryId(entryData[0]?.id || ''); setStandings(standingData);
    }).catch(() => setError('Unable to load the Pick ’Em pool.'));
  }, [id]);

  useEffect(() => {
    if (!id) return;
    fetch(`${process.env.NEXT_PUBLIC_API_URL}/schedule/week/${week}`, { headers: authHeaders() })
      .then((res) => res.ok ? res.json() : Promise.reject()).then(setGames)
      .catch(() => setError(`Unable to load Week ${week}.`));
  }, [id, week]);

  useEffect(() => {
    if (!entryId) { setPicks([]); return; }
    fetch(`${process.env.NEXT_PUBLIC_API_URL}/picks/entry/${entryId}`, { headers: authHeaders() })
      .then((res) => res.ok ? res.json() : Promise.reject()).then(setPicks)
      .catch(() => setError('Unable to load this entry’s picks.'));
  }, [entryId]);

  const selectWinner = async (game, team) => {
    setSavingGame(game.game_id); setError('');
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/picks/create`, {
        method: 'POST', headers: { ...authHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ entry_id: entryId, week, game_id: game.game_id, team: team.abbrv }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || 'Unable to save pick.');
      setPicks((current) => [...current.filter((pick) => pick.id !== data.id && pick.game_id !== game.game_id), data]);
    } catch (err) { setError(err.message); } finally { setSavingGame(null); }
  };

  return <ProtectedRoute><main className="product-page-shell pickem-page">
    <PoolWorkspaceNav poolId={id} poolName={pool?.name} poolType="pickem" active="entries" />
    <WorkspaceHeader eyebrow="Every pick counts" title={`Week ${week} Pick ’Em`} description={pool?.pickem_games_per_week ? `Choose any ${weeklyTarget} games. No spread—each correct pick earns one point.` : "Pick the winner of every game. No spread—each correct pick earns one point."} meta={`${Object.keys(picksByGame).length} / ${weeklyTarget} selected`} />
    {error && <div className="workspace-alert workspace-alert--error">{error}</div>}
    <section className="matchup-toolbar">
      <button disabled={week === 1} onClick={() => setWeek((value) => value - 1)}>← Previous</button>
      {entries.length ? <label>Entry <select value={entryId} onChange={(event) => setEntryId(event.target.value)}>{entries.map((entry) => <option key={entry.id} value={entry.id}>{entry.name}</option>)}</select></label> : <span className="matchup-toolbar__status">No entries yet</span>}
      <label>Week <select value={week} onChange={(event) => setWeek(Number(event.target.value))}>{Array.from({ length: 18 }, (_, index) => <option key={index + 1}>{index + 1}</option>)}</select></label>
      <button disabled={week === 18} onClick={() => setWeek((value) => value + 1)}>Next →</button>
    </section>
    {!entries.length ? <section className="pickem-entry-required" aria-labelledby="pickem-entry-required-title">
      <div className="pickem-entry-required__icon" aria-hidden="true">+</div>
      <div>
        <span>ONE QUICK STEP</span>
        <h2 id="pickem-entry-required-title">Create an entry to start picking</h2>
        <p>Your entry is your Pick &apos;Em card for the season. Name it once, then choose a winner for every weekly matchup.</p>
      </div>
      <Link className="pickem-entry-required__cta" href={`/pool/${id}/entries/create`}>Create your first entry <b>→</b></Link>
    </section> :
      <section className="pickem-board">{games.map((game) => <article key={game.game_id} className="pickem-game">
        <time>{new Date(game.start_time).toLocaleString()}</time>
        {[game.away_team, game.home_team].map((team) => <button key={team.id} disabled={savingGame === game.game_id || (targetReached && !picksByGame[game.game_id])} className={picksByGame[game.game_id]?.team === team.abbrv ? 'is-selected' : ''} onClick={() => selectWinner(game, team)}>
          <img src={`/nfl/${team.abbrv.toLowerCase()}.svg`} alt="" /><span><strong>{team.abbrv}</strong><small>{team.name}</small></span>{picksByGame[game.game_id]?.team === team.abbrv && <b>✓</b>}
        </button>)}
      </article>)}</section>}
    <section className="pickem-standings"><h2>Season standings</h2><table><thead><tr><th>Rank</th><th>Entry</th><th>Points</th><th>Completed picks</th></tr></thead><tbody>{standings.map((row) => <tr key={row.entry_id}><td>{row.rank}</td><td><strong>{row.entry_name}</strong><small>{row.user_email}</small></td><td>{row.points}</td><td>{row.possible_points}</td></tr>)}</tbody></table></section>
  </main></ProtectedRoute>;
}
