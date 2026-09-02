import { useEffect, useMemo, useState, useTransition } from 'react';
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
  const [message, setMessage] = useState('');
  const [saving, setSaving] = useState('');
  const [lineStatus, setLineStatus] = useState({});
  const [lineLoadVersion, setLineLoadVersion] = useState(0);
  const [, startSpreadTransition] = useTransition();

  const load = async () => {
    const response = await fetch(`${apiUrl()}/survivor-planner/pools/${id}`, { headers: { Authorization: `Bearer ${localStorage.getItem('access_token')}` } });
    if (!response.ok) throw new Error((await response.json().catch(() => ({}))).detail || 'Unable to load the season planner.');
    const body = await response.json();
    setData(body);
    setLineStatus({});
    setLineLoadVersion((current) => current + 1);
    setEntryId((current) => current && body.entries.some((entry) => entry.id === current) ? current : body.entries[0]?.id || '');
    setWeek((current) => current === 1 ? body.current_week : current);
  };

  useEffect(() => { if (id) load().catch((reason) => setError(reason.message)); }, [id]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => {
    if (!id || !data || !lineLoadVersion) return undefined;
    let cancelled = false;
    const scheduledWeeks = data.weeks.filter((item) => item.games.length).map((item) => item.week);
    const prioritizedWeeks = [data.current_week, ...scheduledWeeks].filter((number, index, values) => scheduledWeeks.includes(number) && values.indexOf(number) === index);
    setLineStatus(Object.fromEntries(prioritizedWeeks.map((number) => [number, 'loading'])));

    const loadWeekLines = async (number) => {
      try {
        const response = await fetch(`${apiUrl()}/schedule/week/${number}/matchups?pool_id=${id}`);
        if (!response.ok) throw new Error((await response.json().catch(() => ({}))).detail || 'Point spreads are temporarily unavailable.');
        const matchups = await response.json();
        if (cancelled) return;
        const matchupsByGame = new Map(matchups.map((matchup) => [matchup.game_id, matchup]));
        startSpreadTransition(() => {
          setData((current) => ({ ...current, weeks: current.weeks.map((item) => item.week !== number ? item : {
            ...item,
            games: item.games.map((game) => ({ ...game, ...(matchupsByGame.get(game.game_id) || {}) })),
          }) }));
          setLineStatus((current) => ({ ...current, [number]: 'loaded' }));
        });
      } catch {
        if (!cancelled) setLineStatus((current) => ({ ...current, [number]: 'unavailable' }));
      }
    };

    const queue = [...prioritizedWeeks];
    const worker = async () => {
      while (!cancelled && queue.length) await loadWeekLines(queue.shift());
    };
    Promise.all(Array.from({ length: Math.min(3, queue.length) }, worker));
    return () => { cancelled = true; };
  }, [id, lineLoadVersion]); // eslint-disable-line react-hooks/exhaustive-deps
  const entry = data?.entries.find((item) => item.id === entryId);
  const teams = useMemo(() => {
    const map = new Map();
    data?.weeks.forEach(({ games }) => games.forEach((game) => [game.home_team, game.away_team].forEach((team) => map.set(team.id, team))));
    return [...map.values()].sort((a, b) => a.abbrv.localeCompare(b.abbrv));
  }, [data]);
  const gamesByWeekTeam = useMemo(() => {
    const map = new Map();
    data?.weeks.forEach(({ week: number, games }) => games.forEach((game) => {
      map.set(`${number}:${game.home_team.id}`, game);
      map.set(`${number}:${game.away_team.id}`, game);
    }));
    return map;
  }, [data]);
  const picksByWeek = useMemo(() => new Map(entry?.picks.map((pick) => [pick.week, pick]) || []), [entry]);
  const plansByWeek = useMemo(() => new Map(entry?.plans.map((plan) => [plan.week, plan]) || []), [entry]);
  const usageByTeam = useMemo(() => {
    const map = new Map();
    entry?.picks.forEach((pick) => map.set(pick.team_id, { week: pick.week, kind: 'Picked' }));
    entry?.plans.forEach((plan) => { if (!map.has(plan.team_id)) map.set(plan.team_id, { week: plan.week, kind: 'Planned' }); });
    return map;
  }, [entry]);
  const gameFor = (teamId, number) => gamesByWeekTeam.get(`${number}:${teamId}`);
  const pickFor = (number) => picksByWeek.get(number);
  const planFor = (number) => plansByWeek.get(number);
  const usageFor = (teamId, number) => { const usage = usageByTeam.get(teamId); return usage?.week !== number ? usage : null; };
  const teamUnavailable = (teamId, number) => Boolean(usageFor(teamId, number));
  const rankedTeams = useMemo(() => [...teams].sort((a, b) => {
    const gameDifference = Number(gamesByWeekTeam.has(`${week}:${b.id}`)) - Number(gamesByWeekTeam.has(`${week}:${a.id}`));
    if (gameDifference) return gameDifference;
    return spreadRank(gamesByWeekTeam.get(`${week}:${b.id}`), b.id) - spreadRank(gamesByWeekTeam.get(`${week}:${a.id}`), a.id) || a.abbrv.localeCompare(b.abbrv);
  }), [teams, gamesByWeekTeam, week]);

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

  const clearPlans = async () => {
    if (!entry || !window.confirm(`Reset all unlocked planned selections for ${entry.name}? Official picks and locked selections will remain.`)) return;
    setSaving('clear'); setError(''); setMessage('');
    try {
      const response = await fetch(`${apiUrl()}/survivor-planner/entries/${entry.id}/plans`, { method: 'DELETE', headers: { Authorization: `Bearer ${localStorage.getItem('access_token')}` } });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(body.detail || 'Unable to clear this plan.');
      setMessage(body.cleared ? `${body.cleared} unlocked planned selection${body.cleared === 1 ? '' : 's'} cleared. Official and locked picks were not changed.` : 'No unlocked planned selections were available to clear.');
      await load();
    } catch (reason) { setError(reason.message); } finally { setSaving(''); }
  };

  if (!router.isReady) return null;
  return <ProtectedRoute><div className="product-page planner-page"><main className="product-main planner-main">
    {data && <PoolWorkspaceNav poolId={id} poolName={data.pool.name} poolType="survivor" active="planner" />}
    <WorkspaceHeader eyebrow="Private strategy workspace" title="Survivor Season Planner" description="Map a season path without changing your official picks. Your plans are visible only to you." />
    <p className="planner-note planner-note--prominent">Plans are private and never count as picks until you explicitly make the current week official. Official picks remain governed by server-side pool and kickoff locks.</p>
    {error && <div className="workspace-alert workspace-alert--error" role="alert">{error}</div>}
    {message && <div className="workspace-alert" role="status">{message}</div>}
    {!data ? <p>Loading planner…</p> : data.entries.length === 0 ? <div className="planner-empty">Create an entry before planning your season. <Link href={`/pool/${id}/entries/create`}>Create entry</Link></div> : <>
      <div className="planner-controls"><label>Entry<select value={entryId} onChange={(event) => { setEntryId(event.target.value); setMessage(''); }}>{data.entries.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label><div className="planner-controls__actions"><span>Week {data.current_week} is current</span><button type="button" onClick={clearPlans} disabled={!entry?.plans.length || saving === 'clear'}>Reset</button></div></div>
      {!entry?.alive && <div className="workspace-alert">This entry has been eliminated. Its season path is read-only.</div>}
      <section className="planner-path" aria-label="Season path">{data.weeks.map(({ week: number }) => { const choice = pickFor(number) || planFor(number); return <button key={number} type="button" className={week === number ? 'is-active' : ''} onClick={() => setWeek(number)}><small>W{number}</small><strong>{choice?.team || '—'}</strong><span>{pickFor(number) ? 'Official' : planFor(number) ? 'Planned' : 'Open'}</span></button>; })}</section>
      {planFor(data.current_week) && !pickFor(data.current_week) && <div className="planner-official"><div><strong>{planFor(data.current_week).team} is planned for Week {data.current_week}</strong><span>This is not your official pick yet.</span></div><button type="button" disabled={saving === 'official'} onClick={makeOfficial}>Make official pick</button></div>}
      <section className="planner-mobile" aria-label={`Week ${week} choices`}><div className="planner-week-heading"><h2>Week {week}</h2><LineStatus status={lineStatus[week]} /></div>{rankedTeams.filter((team) => gameFor(team.id, week)).map((team) => <TeamChoice key={team.id} team={team} game={gameFor(team.id, week)} selected={planFor(week)?.team_id === team.id} official={pickFor(week)?.team_id === team.id} usage={usageFor(team.id, week)} disabled={teamUnavailable(team.id, week) || week < data.current_week || Boolean(pickFor(week)) || !entry.alive} onClick={() => choose(team, week)} />)}</section>
      <div className="planner-grid-heading"><strong>Season point spread heat map</strong><span>Every scheduled week is heatmapped from strongest favorite to largest underdog. Select a week to rank its teams. Green marks favorites, red marks underdogs, violet marks planned picks, and cyan marks official picks.</span><AllWeeksLineStatus weeks={data.weeks} lineStatus={lineStatus} /></div>
      <div className="planner-grid-wrap"><table className="planner-grid"><thead><tr><th>Team</th>{data.weeks.map(({ week: number }) => <th key={number}><button type="button" className={week === number ? 'is-active' : ''} onClick={() => setWeek(number)}>W{number}</button></th>)}</tr></thead><tbody>{rankedTeams.map((team) => <tr key={team.id}><th><span className="planner-team-label">{team.logo && <Image src={team.logo} alt="" width={26} height={26} unoptimized />}<abbr title={team.name}>{team.abbrv}</abbr></span></th>{data.weeks.map(({ week: number }) => { const game = gameFor(team.id, number); const selected = planFor(number)?.team_id === team.id; const official = pickFor(number)?.team_id === team.id; const usage = usageFor(team.id, number); const disabled = !game || Boolean(usage) || number < data.current_week || Boolean(pickFor(number)) || !entry.alive; const spread = teamSpread(game, team.id); return <td key={number}><button type="button" aria-label={`${team.name}, week ${number}${official ? ', official' : selected ? ', planned' : usage ? `, ${usage.kind.toLowerCase()} in week ${usage.week}, unavailable` : disabled && game ? ', unavailable' : ''}${spread ? `, point spread ${spread}` : ''}`} className={`${official ? 'is-official' : selected ? 'is-planned' : ''} ${usage ? 'is-used' : ''} ${spread ? 'has-spread' : ''}`} style={spreadHeatStyle(game, team.id)} disabled={disabled} onClick={() => choose(team, number)}>{game ? <><span>{opponentLabel(game, team.id)}</span><small>{usage ? `${usage.kind} W${usage.week}` : lineFor(game) ? (game.official_line ? 'Official line' : 'Current line') : 'Line pending'}</small></> : 'BYE'}</button></td>; })}</tr>)}</tbody></table></div>
    </>}
  </main></div></ProtectedRoute>;
}

function lineFor(game) { return game?.official_line || game?.live_line || null; }
function spreadRank(game, teamId) {
  const line = lineFor(game);
  if (!line || line.spread == null) return -1000;
  if (line.favorite_team_id == null) return 0;
  return (line.favorite_team_id === teamId ? 1 : -1) * Math.abs(Number(line.spread));
}
function spreadHeatStyle(game, teamId) { const rank = spreadRank(game, teamId); if (rank === -1000) return undefined; if (rank === 0) return { '--planner-heat': 'rgba(92, 116, 124, .3)' }; const alpha = Math.min(.78, .22 + (Math.abs(rank) / 20) * .56); return { '--planner-heat': rank > 0 ? `rgba(22, 163, 74, ${alpha.toFixed(2)})` : `rgba(220, 38, 38, ${alpha.toFixed(2)})` }; }
function teamSpread(game, teamId) { const line = lineFor(game); if (!line || line.spread == null) return ''; if (line.favorite_team_id == null) return 'PK'; return `${line.favorite_team_id === teamId ? '-' : '+'}${Math.abs(line.spread)}`; }
function opponentLabel(game, teamId) { const opponent = game.home_team.id === teamId ? game.away_team : game.home_team; const prefix = game.home_team.id === teamId ? 'vs' : '@'; const spread = teamSpread(game, teamId); return `${prefix} ${opponent.abbrv}${spread ? ` · ${spread}` : ''}`; }
function TeamChoice({ team, game, selected, official, usage, disabled, onClick }) { const spread = teamSpread(game, team.id); return <button type="button" className={`planner-team ${selected ? 'is-planned' : ''} ${official ? 'is-official' : ''} ${usage ? 'is-used' : ''} ${spread ? 'has-spread' : ''}`} style={spreadHeatStyle(game, team.id)} disabled={disabled} onClick={onClick}><span className="planner-team-label">{team.logo && <Image src={team.logo} alt="" width={26} height={26} unoptimized />}<strong>{team.abbrv}</strong><span>{team.name}</span></span><span>{opponentLabel(game, team.id)}</span><b>{spread ? `Point spread ${spread}` : 'Line pending'}</b><small>{official ? 'Official pick' : selected ? 'Planned — tap to clear' : usage ? `${usage.kind} Week ${usage.week} — unavailable` : disabled ? 'Unavailable — locked' : 'Tap to plan'}</small></button>; }
function LineStatus({ status }) { return <small className="planner-line-status">{status === 'loading' ? 'Loading point spreads…' : status === 'unavailable' ? 'Point spreads unavailable' : status === 'loaded' ? 'Current point spreads loaded' : ''}</small>; }
function AllWeeksLineStatus({ weeks, lineStatus }) { const scheduled = weeks.filter((item) => item.games.length).map((item) => item.week); const loaded = scheduled.filter((number) => lineStatus[number] === 'loaded').length; const unavailable = scheduled.filter((number) => lineStatus[number] === 'unavailable').length; return <small className="planner-line-status">{scheduled.length === 0 ? 'No scheduled matchups yet' : loaded < scheduled.length - unavailable ? `Loading point spreads for all weeks… ${loaded}/${scheduled.length}` : unavailable ? `Point spreads loaded for ${loaded}/${scheduled.length} weeks` : `Point spreads loaded for all ${loaded} scheduled weeks`}</small>; }
