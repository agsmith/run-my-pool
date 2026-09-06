import { useEffect, useMemo, useState } from 'react';
import { useRouter } from 'next/router';
import Link from 'next/link';
import ProtectedRoute from '../../../components/ProtectedRoute';
import { PoolWorkspaceNav, WorkspaceHeader } from '../../../components/ProductWorkspace';

const authHeaders = () => ({ Authorization: `Bearer ${localStorage.getItem('access_token')}` });

export default function PickEmPage() {
  const router = useRouter();
  const { id, entry: requestedEntryId, paper } = router.query;
  const [pool, setPool] = useState(null);
  const [entries, setEntries] = useState([]);
  const [entryId, setEntryId] = useState('');
  const [week, setWeek] = useState(1);
  const [games, setGames] = useState([]);
  const [picks, setPicks] = useState([]);
  const [standings, setStandings] = useState([]);
  const [weeklyStandings, setWeeklyStandings] = useState([]);
  const [tiebreaker, setTiebreaker] = useState('');
  const [savingTiebreaker, setSavingTiebreaker] = useState(false);
  const [error, setError] = useState('');
  const [savingGame, setSavingGame] = useState(null);

  const eligibleGames = useMemo(() => games.filter((game) => {
    if (!pool || !pool.pickem_slate || pool.pickem_slate === 'all') return true;
    const weekday = new Intl.DateTimeFormat('en-US', { weekday: 'short', timeZone: 'America/New_York' }).format(new Date(game.start_time));
    return pool.pickem_slate === 'sunday' ? weekday === 'Sun' : ['Sun', 'Mon'].includes(weekday);
  }), [games, pool]);
  const picksByGame = useMemo(() => Object.fromEntries(picks.filter((pick) => pick.week === week).map((pick) => [pick.game_id, pick])), [picks, week]);
  const weeklyTarget = Math.min(pool?.pickem_games_per_week || eligibleGames.length, eligibleGames.length);
  const targetReached = weeklyTarget > 0 && Object.keys(picksByGame).length >= weeklyTarget;

  useEffect(() => {
    if (!id) return;
    Promise.all([
      fetch(`${process.env.NEXT_PUBLIC_API_URL}/pools/${id}`, { headers: authHeaders() }).then((res) => res.json()),
      fetch(`${process.env.NEXT_PUBLIC_API_URL}/entries/pool/${id}`, { headers: authHeaders() }).then((res) => res.ok ? res.json() : []),
      fetch(`${process.env.NEXT_PUBLIC_API_URL}/picks/pool/${id}/standings`, { headers: authHeaders() }).then((res) => res.ok ? res.json() : []),
    ]).then(([poolData, entryData, standingData]) => {
      if (poolData.pool_type !== 'pickem') return router.replace(`/pool/${id}/entries`);
      const requestedEntry = entryData.find((entry) => entry.id === requestedEntryId);
      setPool(poolData); setEntries(entryData); setEntryId(requestedEntry?.id || entryData[0]?.id || ''); setStandings(standingData);
    }).catch(() => setError('Unable to load the Pick ’Em pool.'));
  }, [id, requestedEntryId]);

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

  useEffect(() => {
    if (!id || !pool) return;
    fetch(`${process.env.NEXT_PUBLIC_API_URL}/picks/pool/${id}/weekly-standings/${week}`, { headers: authHeaders() })
      .then((res) => res.ok ? res.json() : []).then(setWeeklyStandings);
    if (pool.pickem_slate !== 'sunday_monday' || !entryId) { setTiebreaker(''); return; }
    fetch(`${process.env.NEXT_PUBLIC_API_URL}/picks/entry/${entryId}/tiebreaker/${week}`, { headers: authHeaders() })
      .then((res) => res.ok ? res.json() : null)
      .then((data) => setTiebreaker(data?.predicted_total ?? ''))
      .catch(() => setError('Unable to load the Monday-night tiebreaker.'));
  }, [id, entryId, week, pool]);

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

  const saveTiebreaker = async () => {
    const total = Number(tiebreaker);
    if (!Number.isInteger(total) || total < 0 || total > 200) { setError('Enter a whole-number total from 0 to 200.'); return; }
    setSavingTiebreaker(true); setError('');
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/picks/entry/${entryId}/tiebreaker`, {
        method: 'PUT', headers: { ...authHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ week, predicted_total: total }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || 'Unable to save tiebreaker.');
      setTiebreaker(data.predicted_total);
    } catch (err) { setError(err.message); } finally { setSavingTiebreaker(false); }
  };

  return <ProtectedRoute><main className="product-page-shell pickem-page">
    <PoolWorkspaceNav poolId={id} poolName={pool?.name} poolType="pickem" active="entries" />
    <WorkspaceHeader eyebrow="Every pick counts" title={`Week ${week} Pick ’Em`} description={pool?.pickem_games_per_week ? `Choose any ${weeklyTarget} eligible games. No spread—each correct pick earns one point.` : "Pick the winner of every eligible game. No spread—each correct pick earns one point."} meta={`${Object.keys(picksByGame).length} / ${weeklyTarget} selected`} />
    {paper === '1' && entryId && <div className="workspace-alert" role="status">Paper entry ready. Enter this participant&apos;s Week {week} picks below; normal lock rules still apply.</div>}
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
      <>{pool?.pickem_slate === 'sunday_monday' && <section className="pickem-tiebreaker">
        <h2>Monday Night tiebreaker</h2>
        <p>Predict the combined score in the final Monday game. Closest prediction breaks a tie in weekly points.</p>
        <label>Combined score <input aria-label="Monday Night combined score" type="number" min="0" max="200" inputMode="numeric" value={tiebreaker} onChange={(event) => setTiebreaker(event.target.value)} /></label>
        <button type="button" disabled={savingTiebreaker || tiebreaker === ''} onClick={saveTiebreaker}>{savingTiebreaker ? 'Saving…' : 'Save tiebreaker'}</button>
      </section>}
      <section className="pickem-board">{eligibleGames.map((game) => <article key={game.game_id} className="pickem-game">
        <time>{new Date(game.start_time).toLocaleString()}</time>
        {[game.away_team, game.home_team].map((team) => <button key={team.id} disabled={savingGame === game.game_id || (targetReached && !picksByGame[game.game_id])} className={picksByGame[game.game_id]?.team === team.abbrv ? 'is-selected' : ''} onClick={() => selectWinner(game, team)}>
          <img src={`/nfl/${team.abbrv.toLowerCase()}.svg`} alt="" title={team.abbrv} /><span><strong>{team.abbrv}</strong><small>{team.name}</small></span>{picksByGame[game.game_id]?.team === team.abbrv && <b>✓</b>}
        </button>)}
      </article>)}</section></>}
    <section className="pickem-standings"><h2>Week {week} standings</h2><table><thead><tr><th>Rank</th><th>Entry</th><th>Points</th>{pool?.pickem_slate === 'sunday_monday' && <><th>Prediction</th><th>Difference</th></>}</tr></thead><tbody>{weeklyStandings.map((row) => <tr key={row.entry_id}><td>{row.rank}</td><td><strong>{row.entry_name}</strong><small>{row.user_display_name}</small></td><td>{row.points}</td>{pool?.pickem_slate === 'sunday_monday' && <><td>{row.predicted_total ?? 'Hidden until lock'}</td><td>{row.tiebreak_difference ?? '—'}</td></>}</tr>)}</tbody></table></section>
    <section className="pickem-standings"><h2>Season standings</h2><table><thead><tr><th>Rank</th><th>Entry</th><th>Points</th><th>Completed picks</th></tr></thead><tbody>{standings.map((row) => <tr key={row.entry_id}><td>{row.rank}</td><td><strong>{row.entry_name}</strong><small>{row.user_display_name}</small></td><td>{row.points}</td><td>{row.possible_points}</td></tr>)}</tbody></table></section>
  </main></ProtectedRoute>;
}
