import { useEffect, useMemo, useState } from 'react';
import { useRouter } from 'next/router';
import ProtectedRoute from '../../../components/ProtectedRoute';
import { PoolWorkspaceNav, WorkspaceHeader } from '../../../components/ProductWorkspace';
import { useAuth } from '../../../context/AuthContext';

const authHeaders = () => ({ Authorization: `Bearer ${localStorage.getItem('access_token')}` });

export default function SquaresPage() {
  const { query } = useRouter();
  const { user } = useAuth();
  const [board, setBoard] = useState(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [pot, setPot] = useState('');
  const [claimFor, setClaimFor] = useState('');
  const claims = useMemo(() => Object.fromEntries((board?.claims || []).map((c) => [`${c.row_index}-${c.column_index}`, c])), [board]);

  const load = async () => {
    const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/squares/${query.id}`, { headers: authHeaders() });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.detail || 'Unable to load the Squares board.');
    setBoard(data); setPot(data.total_pot_cents ?? '');
  };
  useEffect(() => { if (query.id) load().catch((err) => setError(err.message)); }, [query.id]);

  const choose = async (row, column) => {
    const claim = claims[`${row}-${column}`];
    setBusy(true); setError('');
    try {
      const response = await fetch(claim ? `${process.env.NEXT_PUBLIC_API_URL}/squares/${query.id}/claims/${claim.id}` : `${process.env.NEXT_PUBLIC_API_URL}/squares/${query.id}/claims`, {
        method: claim ? 'DELETE' : 'POST', headers: { ...authHeaders(), 'Content-Type': 'application/json' },
        body: claim ? undefined : JSON.stringify({ row_index: row, column_index: column, ...(claimFor ? { user_id: claimFor } : {}) }),
      });
      const data = response.status === 204 ? {} : await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.detail || 'Unable to update that square.');
      await load();
    } catch (err) { setError(err.message); } finally { setBusy(false); }
  };

  const lock = async () => {
    if (!confirm('Lock this board and permanently randomize both score axes?')) return;
    setBusy(true); setError('');
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/squares/${query.id}/lock`, { method: 'POST', headers: authHeaders() });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.detail || 'Unable to lock the board.');
      setBoard(data);
    } catch (err) { setError(err.message); } finally { setBusy(false); }
  };

  const savePot = async (event) => {
    event.preventDefault(); setBusy(true); setError('');
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/squares/${query.id}/payouts`, {
        method: 'PATCH', headers: { ...authHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ total_pot_cents: pot === '' ? null : Number(pot), q1_percent: 25, halftime_percent: 25, q3_percent: 25, final_percent: 25 }),
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.detail || 'Unable to save payout settings.');
      setBoard(data);
    } catch (err) { setError(err.message); } finally { setBusy(false); }
  };

  if (!board) return <ProtectedRoute><main className="product-page-shell"><p>{error || 'Loading Squares board…'}</p></main></ProtectedRoute>;
  const game = board.game;
  return <ProtectedRoute><main className="product-page-shell squares-page">
    <PoolWorkspaceNav poolId={query.id} poolName={board.pool_name} poolType="squares" active="entries" showAdmin={board.permissions.is_admin} />
    <WorkspaceHeader eyebrow={board.locked ? 'Board locked' : 'Choose your squares'} title={`${game.away_team.abbrv} at ${game.home_team.abbrv}`} description={`${new Date(game.start_time).toLocaleString()} · ${board.claims.length}/100 claimed`} actions={board.permissions.is_admin && !board.locked ? <button onClick={lock} disabled={busy}>Lock & randomize digits</button> : null} />
    {error && <div className="workspace-alert workspace-alert--error">{error}</div>}
    {board.permissions.is_admin && !board.locked && <label className="squares-claim-for">Claim available squares for <select value={claimFor} onChange={(event) => setClaimFor(event.target.value)}><option value="">Myself</option>{(board.members || []).filter((member) => member.id !== user?.id).map((member) => <option key={member.id} value={member.id}>{member.email}</option>)}</select></label>}
    <p className="squares-instructions">Home score runs down the left. Away score runs across the top. {!board.locked && 'Digits stay hidden until the board locks.'}</p>
    <div className="squares-scroll"><div className="squares-grid" role="grid" aria-label="10 by 10 Squares board">
      <div className="squares-corner">HOME ↓<br />AWAY →</div>
      {Array.from({ length: 10 }, (_, col) => <div className="squares-axis" key={`a${col}`}>{board.away_digits?.[col] ?? '?'}</div>)}
      {Array.from({ length: 10 }, (_, row) => <div className="squares-row" key={row}>
        <div className="squares-axis">{board.home_digits?.[row] ?? '?'}</div>
        {Array.from({ length: 10 }, (_, col) => { const claim = claims[`${row}-${col}`]; const mayRelease = claim?.user_id === user?.id || board.permissions.is_admin; return <button key={col} role="gridcell" disabled={busy || board.locked || (!board.permissions.can_claim && !claim) || (claim && !mayRelease)} className={`squares-cell ${claim ? 'is-claimed' : ''} ${claim?.user_id === user?.id ? 'is-mine' : ''}`} onClick={() => choose(row, col)} title={claim?.user_email || 'Available square'}>{claim ? (claim.display_name || claim.user_email.split('@')[0]) : '+'}</button>; })}
      </div>)}
    </div></div>
    <section className="squares-results"><h2>Quarter winners</h2><div>{['q1', 'halftime', 'q3', 'final'].map((name) => { const result = board.payouts.find((item) => item.checkpoint === name); return <article key={name}><strong>{name === 'q1' ? '1st Quarter' : name === 'q3' ? '3rd Quarter' : name[0].toUpperCase() + name.slice(1)}</strong>{result ? <><span>{result.away_score}–{result.home_score}</span><b>{result.winner_email || 'Unclaimed square'}</b>{result.amount_cents != null && <small>${(result.amount_cents / 100).toFixed(2)} recorded</small>}</> : <span>Pending</span>}</article>; })}</div></section>
    {board.permissions.is_admin && !board.locked && <form className="squares-pot" onSubmit={savePot}><div><h2>Payout setup</h2><p>Default: 25% after Q1, halftime, Q3, and final. Run My Pool records winners and amounts but does not move money.</p></div><label>Total pot in cents <input type="number" min="0" value={pot} onChange={(event) => setPot(event.target.value)} placeholder="Optional" /></label><button disabled={busy}>Save payouts</button></form>}
  </main></ProtectedRoute>;
}
