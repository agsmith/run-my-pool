import { useEffect, useMemo, useState } from 'react';
import { useRouter } from 'next/router';
import Link from 'next/link';
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

  const load = async () => {
    const response = await fetch(`${apiUrl()}/survivor-planner/pools/${id}`, { headers: { Authorization: `Bearer ${localStorage.getItem('access_token')}` } });
    if (!response.ok) throw new Error((await response.json().catch(() => ({}))).detail || 'Unable to load the season planner.');
    const body = await response.json();
    setData(body);
    setEntryId((current) => current && body.entries.some((entry) => entry.id === current) ? current : body.entries[0]?.id || '');
    setWeek((current) => current === 1 ? body.current_week : current);
  };

  useEffect(() => { if (id) load().catch((reason) => setError(reason.message)); }, [id]); // eslint-disable-line react-hooks/exhaustive-deps
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
    {error && <div className="workspace-alert workspace-alert--error" role="alert">{error}</div>}
    {!data ? <p>Loading planner…</p> : data.entries.length === 0 ? <div className="planner-empty">Create an entry before planning your season. <Link href={`/pool/${id}/entries/create`}>Create entry</Link></div> : <>
      <div className="planner-controls"><label>Entry<select value={entryId} onChange={(event) => setEntryId(event.target.value)}>{data.entries.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label><span>Week {data.current_week} is current</span></div>
      {!entry?.alive && <div className="workspace-alert">This entry has been eliminated. Its season path is read-only.</div>}
      <section className="planner-path" aria-label="Season path">{data.weeks.map(({ week: number }) => { const choice = pickFor(number) || planFor(number); return <button key={number} type="button" className={week === number ? 'is-active' : ''} onClick={() => setWeek(number)}><small>W{number}</small><strong>{choice?.team || '—'}</strong><span>{pickFor(number) ? 'Official' : planFor(number) ? 'Planned' : 'Open'}</span></button>; })}</section>
      {planFor(data.current_week) && !pickFor(data.current_week) && <div className="planner-official"><div><strong>{planFor(data.current_week).team} is planned for Week {data.current_week}</strong><span>This is not your official pick yet.</span></div><button type="button" disabled={saving === 'official'} onClick={makeOfficial}>Make official pick</button></div>}
      <section className="planner-mobile" aria-label={`Week ${week} choices`}><h2>Week {week}</h2>{teams.filter((team) => gameFor(team.id, week)).map((team) => <TeamChoice key={team.id} team={team} game={gameFor(team.id, week)} selected={planFor(week)?.team_id === team.id} official={pickFor(week)?.team_id === team.id} disabled={teamUnavailable(team.id, week) || week < data.current_week || Boolean(pickFor(week)) || !entry.alive} onClick={() => choose(team, week)} />)}</section>
      <div className="planner-grid-wrap"><table className="planner-grid"><thead><tr><th>Team</th>{data.weeks.map(({ week: number }) => <th key={number}>W{number}</th>)}</tr></thead><tbody>{teams.map((team) => <tr key={team.id}><th>{team.abbrv}</th>{data.weeks.map(({ week: number }) => { const game = gameFor(team.id, number); const selected = planFor(number)?.team_id === team.id; const official = pickFor(number)?.team_id === team.id; const disabled = !game || teamUnavailable(team.id, number) || number < data.current_week || Boolean(pickFor(number)) || !entry.alive; return <td key={number}><button type="button" aria-label={`${team.name}, week ${number}${official ? ', official' : selected ? ', planned' : ''}`} className={official ? 'is-official' : selected ? 'is-planned' : ''} disabled={disabled} onClick={() => choose(team, number)}>{game ? opponentLabel(game, team.id) : 'BYE'}</button></td>; })}</tr>)}</tbody></table></div>
      <p className="planner-note">Plans are private and never count as picks until you explicitly make the current week official. Official picks remain governed by server-side pool and kickoff locks.</p>
    </>}
  </main></div></ProtectedRoute>;
}

function opponentLabel(game, teamId) { const opponent = game.home_team.id === teamId ? game.away_team : game.home_team; const prefix = game.home_team.id === teamId ? 'vs' : '@'; const line = game.official_line; return `${prefix} ${opponent.abbrv}${line?.spread != null ? ` ${Math.abs(line.spread)}` : ''}`; }
function TeamChoice({ team, game, selected, official, disabled, onClick }) { return <button type="button" className={`planner-team ${selected ? 'is-planned' : ''} ${official ? 'is-official' : ''}`} disabled={disabled} onClick={onClick}><strong>{team.name}</strong><span>{opponentLabel(game, team.id)}</span><small>{official ? 'Official pick' : selected ? 'Planned — tap to clear' : disabled ? 'Unavailable' : 'Tap to plan'}</small></button>; }
