import { useEffect, useMemo, useState } from 'react';
import { useRouter } from 'next/router';
import Link from 'next/link';
import Image from 'next/image';
import ProtectedRoute from '../../../components/ProtectedRoute';
import { PoolWorkspaceNav, WorkspaceHeader } from '../../../components/ProductWorkspace';

const apiUrl = () => process.env.NEXT_PUBLIC_API_URL;

export default function SurvivorPlannerPage() {
  const router = useRouter();
  const { id } = router.query;
  const [data, setData] = useState(null);
  const [entryId, setEntryId] = useState('');
  const [week, setWeek] = useState(1);
  const [error, setError] = useState('');
  const [saving, setSaving] = useState('');
  const [oddsStatus, setOddsStatus] = useState({});

  const load = async () => {
    const response = await fetch(`${apiUrl()}/survivor-planner/pools/${id}`, { headers: { Authorization: `Bearer ${localStorage.getItem('access_token')}` } });
    if (!response.ok) throw new Error((await response.json().catch(() => ({}))).detail || 'Unable to load the season planner.');
    const body = await response.json();
    setData(body);
    setEntryId((current) => current && body.entries.some((entry) => entry.id === current) ? current : body.entries[0]?.id || '');
    setWeek((current) => current === 1 ? body.current_week : current);
  };

  useEffect(() => { if (id) load().catch((reason) => setError(reason.message)); }, [id]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => {
    if (!id || !data || oddsStatus[week]) return;
    setOddsStatus((current) => ({ ...current, [week]: 'loading' }));
    fetch(`${apiUrl()}/survivor-planner/pools/${id}/weeks/${week}/odds`, { headers: { Authorization: `Bearer ${localStorage.getItem('access_token')}` } })
      .then(async (response) => {
        if (!response.ok) throw new Error((await response.json().catch(() => ({}))).detail || 'Odds are temporarily unavailable.');
        return response.json();
      })
      .then((odds) => {
        setData((current) => ({ ...current, weeks: current.weeks.map((item) => item.week !== week ? item : {
          ...item,
          games: item.games.map((game) => ({ ...game, ...(odds.games.find((line) => line.game_id === game.game_id) || {}) })),
        }) }));
        setOddsStatus((current) => ({ ...current, [week]: 'loaded' }));
      })
      .catch(() => setOddsStatus((current) => ({ ...current, [week]: 'unavailable' })));
  }, [id, data, week, oddsStatus]);
  const entry = data?.entries.find((item) => item.id === entryId);
  const teams = useMemo(() => {
    const map = new Map();
    data?.weeks.forEach(({ games }) => games.forEach((game) => [game.home_team, game.away_team].forEach((team) => map.set(team.id, team))));
    return [...map.values()].sort((a, b) => a.abbrv.localeCompare(b.abbrv));
  }, [data]);
  const weekData = (number) => data?.weeks.find((item) => item.week === number);
  const gameFor = (teamId, number) => weekData(number)?.games.find((game) => game.home_team.id === teamId || game.away_team.id === teamId);
  const pickFor = (number) => entry?.picks.find((pick) => pick.week === number);
  const planFor = (number) => entry?.plans.find((plan) => plan.week === number);
  const teamUnavailable = (teamId, number) => entry?.picks.some((pick) => pick.team_id === teamId && pick.week !== number) || entry?.plans.some((plan) => plan.team_id === teamId && plan.week !== number);
  const rankedTeams = useMemo(() => [...teams].sort((a, b) => {
    const gameDifference = Number(Boolean(gameFor(b.id, week))) - Number(Boolean(gameFor(a.id, week)));
    if (gameDifference) return gameDifference;
    const unavailableDifference = Number(teamUnavailable(a.id, week)) - Number(teamUnavailable(b.id, week));
    if (unavailableDifference) return unavailableDifference;
    return (winProbability(gameFor(b.id, week), b.id) ?? -1) - (winProbability(gameFor(a.id, week), a.id) ?? -1) || a.abbrv.localeCompare(b.abbrv);
  }), [teams, data, entry, week]); // eslint-disable-line react-hooks/exhaustive-deps

  const choose = async (team, number) => {
    if (!entry || saving || pickFor(number) || number < data.current_week || !entry.alive || teamUnavailable(team.id, number)) return;
    const selected = planFor(number)?.team_id === team.id;
    setSaving(`${number}-${team.id}`); setError('');
    try {
      const response = await fetch(`${apiUrl()}/survivor-planner/entries/${entry.id}/weeks/${number}`, {
        method: selected ? 'DELETE' : 'PUT',
        headers: { Authorization: `Bearer ${localStorage.getItem('access_token')}`, 'Content-Type': 'application/json' },
        ...(!selected && { body: JSON.stringify({ team: team.abbrv }) }),
      });
      if (!response.ok) throw new Error((await response.json().catch(() => ({}))).detail || 'Unable to save that plan.');
      await load();
    } catch (reason) { setError(reason.message); } finally { setSaving(''); }
  };

  const makeOfficial = async () => {
    setSaving('official'); setError('');
    try {
      const response = await fetch(`${apiUrl()}/survivor-planner/entries/${entry.id}/weeks/${data.current_week}/make-official`, { method: 'POST', headers: { Authorization: `Bearer ${localStorage.getItem('access_token')}` } });
      if (!response.ok) throw new Error((await response.json().catch(() => ({}))).detail || 'Unable to make this pick official.');
      await load();
    } catch (reason) { setError(reason.message); } finally { setSaving(''); }
  };

  if (!router.isReady) return null;
  return <ProtectedRoute><div className="product-page planner-page"><main className="product-main planner-main">
    {data && <PoolWorkspaceNav poolId={id} poolName={data.pool.name} poolType="survivor" active="planner" />}
    <WorkspaceHeader eyebrow="Private strategy workspace" title="Survivor Season Planner" description="Map a season path without changing your official picks. Your plans are visible only to you." />
    <p className="planner-note planner-note--prominent">Plans are private and never count as picks until you explicitly make the current week official. Official picks remain governed by server-side pool and kickoff locks.</p>
    {error && <div className="workspace-alert workspace-alert--error" role="alert">{error}</div>}
    {!data ? <p>Loading planner…</p> : data.entries.length === 0 ? <div className="planner-empty">Create an entry before planning your season. <Link href={`/pool/${id}/entries/create`}>Create entry</Link></div> : <>
      <div className="planner-controls"><label>Entry<select value={entryId} onChange={(event) => setEntryId(event.target.value)}>{data.entries.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label><span>Week {data.current_week} is current</span></div>
      {!entry?.alive && <div className="workspace-alert">This entry has been eliminated. Its season path is read-only.</div>}
      <section className="planner-path" aria-label="Season path">{data.weeks.map(({ week: number }) => { const choice = pickFor(number) || planFor(number); return <button key={number} type="button" className={week === number ? 'is-active' : ''} onClick={() => setWeek(number)}><small>W{number}</small><strong>{choice?.team || '—'}</strong><span>{pickFor(number) ? 'Official' : planFor(number) ? 'Planned' : 'Open'}</span></button>; })}</section>
      {planFor(data.current_week) && !pickFor(data.current_week) && <div className="planner-official"><div><strong>{planFor(data.current_week).team} is planned for Week {data.current_week}</strong><span>This is not your official pick yet.</span></div><button type="button" disabled={saving === 'official'} onClick={makeOfficial}>Make official pick</button></div>}
      <section className="planner-mobile" aria-label={`Week ${week} choices`}><div className="planner-week-heading"><h2>Week {week}</h2><OddsStatus status={oddsStatus[week]} /></div>{rankedTeams.filter((team) => gameFor(team.id, week)).map((team) => <TeamChoice key={team.id} team={team} game={gameFor(team.id, week)} selected={planFor(week)?.team_id === team.id} official={pickFor(week)?.team_id === team.id} disabled={teamUnavailable(team.id, week) || week < data.current_week || Boolean(pickFor(week)) || !entry.alive} onClick={() => choose(team, week)} />)}</section>
      <div className="planner-grid-heading"><strong>Season win-likelihood heat map</strong><span>Select a week to load its latest available odds. Brighter cells indicate a higher spread-implied win percentage.</span><OddsStatus status={oddsStatus[week]} /></div>
      <div className="planner-grid-wrap"><table className="planner-grid"><thead><tr><th>Team</th>{data.weeks.map(({ week: number }) => <th key={number}><button type="button" className={week === number ? 'is-active' : ''} onClick={() => setWeek(number)}>W{number}</button></th>)}</tr></thead><tbody>{rankedTeams.map((team) => <tr key={team.id}><th><span className="planner-team-label">{team.logo && <Image src={team.logo} alt="" width={26} height={26} unoptimized />}<abbr title={team.name}>{team.abbrv}</abbr></span></th>{data.weeks.map(({ week: number }) => { const game = gameFor(team.id, number); const selected = planFor(number)?.team_id === team.id; const official = pickFor(number)?.team_id === team.id; const disabled = !game || teamUnavailable(team.id, number) || number < data.current_week || Boolean(pickFor(number)) || !entry.alive; const probability = winProbability(game, team.id); return <td key={number}><button type="button" aria-label={`${team.name}, week ${number}${official ? ', official' : selected ? ', planned' : disabled && game ? ', unavailable' : ''}${probability != null ? `, ${probability}% implied win probability` : ''}`} className={`${official ? 'is-official' : selected ? 'is-planned' : ''} ${probability != null ? 'has-odds' : ''}`} style={heatStyle(probability)} disabled={disabled} onClick={() => choose(team, number)}>{game ? <><span>{opponentLabel(game, team.id)}</span><small>{probability != null ? `${probability}%` : 'Odds N/A'}</small></> : 'BYE'}</button></td>; })}</tr>)}</tbody></table></div>
    </>}
  </main></div></ProtectedRoute>;
}

function lineFor(game) { return game?.official_line || game?.live_line || null; }
function winProbability(game, teamId) {
  const line = lineFor(game);
  if (!line || line.spread == null || line.favorite_team_id == null) return null;
  const favoriteChance = 1 / (1 + Math.exp(-0.145 * Math.abs(Number(line.spread))));
  return Math.round((line.favorite_team_id === teamId ? favoriteChance : 1 - favoriteChance) * 100);
}
function heatStyle(probability) { if (probability == null) return undefined; const strength = Math.max(0.08, (probability - 35) / 90); return { '--planner-heat': `rgba(198, 255, 55, ${strength.toFixed(2)})` }; }
function opponentLabel(game, teamId) { const opponent = game.home_team.id === teamId ? game.away_team : game.home_team; const prefix = game.home_team.id === teamId ? 'vs' : '@'; const line = lineFor(game); return `${prefix} ${opponent.abbrv}${line?.spread != null ? ` · ${line.favorite_team_id === teamId ? '-' : '+'}${Math.abs(line.spread)}` : ''}`; }
function TeamChoice({ team, game, selected, official, disabled, onClick }) { const probability = winProbability(game, team.id); return <button type="button" className={`planner-team ${selected ? 'is-planned' : ''} ${official ? 'is-official' : ''} ${probability != null ? 'has-odds' : ''}`} style={heatStyle(probability)} disabled={disabled} onClick={onClick}><span className="planner-team-label">{team.logo && <Image src={team.logo} alt="" width={26} height={26} unoptimized />}<strong>{team.abbrv}</strong><span>{team.name}</span></span><span>{opponentLabel(game, team.id)}</span><b>{probability != null ? `${probability}% implied win` : 'Odds not available'}</b><small>{official ? 'Official pick' : selected ? 'Planned — tap to clear' : disabled ? 'Unavailable — already used or locked' : 'Tap to plan'}</small></button>; }
function OddsStatus({ status }) { return <small className="planner-odds-status">{status === 'loading' ? 'Loading latest odds…' : status === 'unavailable' ? 'Latest odds unavailable' : status === 'loaded' ? 'Latest available odds loaded' : ''}</small>; }
