import { useEffect, useMemo, useState } from 'react';
import { useRouter } from 'next/router';
import Link from 'next/link';
import ProtectedRoute from '../../../components/ProtectedRoute';
import { PoolWorkspaceNav, WorkspaceHeader } from '../../../components/ProductWorkspace';
import { useAuth } from '../../../context/AuthContext';

const authHeaders = () => ({ Authorization: `Bearer ${localStorage.getItem('access_token')}` });
const dollarsFromCents = (cents) => cents == null ? '' : (cents / 100).toFixed(2);

export default function SquaresPage() {
  const { query } = useRouter();
  const { user } = useAuth();
  const [board, setBoard] = useState(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [pot, setPot] = useState('');
  const [potMode, setPotMode] = useState('fixed');
  const [claimFor, setClaimFor] = useState('');
  const [manualBlock, setManualBlock] = useState('');
  const claims = useMemo(() => Object.fromEntries((board?.claims || []).map((c) => [`${c.row_index}-${c.column_index}`, c])), [board]);
  const reservations = useMemo(() => {
    const grouped = new Map();
    for (const claim of board?.claims || []) {
      const reservation = grouped.get(claim.user_id) || { user_id: claim.user_id, user_email: claim.user_email, count: 0, blocks: [] };
      reservation.count += 1;
      reservation.blocks.push(claim.block_number ?? (claim.row_index * 10 + claim.column_index + 1));
      grouped.set(claim.user_id, reservation);
    }
    return Array.from(grouped.values()).map((reservation) => ({ ...reservation, blocks: reservation.blocks.sort((a, b) => a - b) })).sort((a, b) => a.user_email.localeCompare(b.user_email));
  }, [board]);

  const load = async () => {
    const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/squares/${query.id}`, { headers: authHeaders() });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.detail || 'Unable to load the Squares board.');
    const mode = data.pot_mode || 'fixed';
    setBoard(data); setPotMode(mode); setPot(dollarsFromCents(mode === 'per_square' ? data.per_square_cents : data.total_pot_cents));
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
      return true;
    } catch (err) { setError(err.message); return false; } finally { setBusy(false); }
  };

  const assignBlock = async (event) => {
    event.preventDefault();
    const blockNumber = Number(manualBlock);
    if (!Number.isInteger(blockNumber) || blockNumber < 1 || blockNumber > 100) {
      setError('Enter a block number from 1 to 100.');
      return;
    }
    const row = Math.floor((blockNumber - 1) / 10);
    const column = (blockNumber - 1) % 10;
    const existing = claims[`${row}-${column}`];
    if (existing) {
      setError(`Block ${blockNumber} is already reserved by ${existing.display_name || existing.user_email}.`);
      return;
    }
    if (await choose(row, column)) setManualBlock('');
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
        body: JSON.stringify({
          pot_mode: potMode,
          total_pot_cents: potMode === 'fixed' && pot !== '' ? Math.round(Number(pot) * 100) : null,
          per_square_cents: potMode === 'per_square' && pot !== '' ? Math.round(Number(pot) * 100) : null,
          q1_percent: 25, halftime_percent: 25, q3_percent: 25, final_percent: 25,
        }),
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
    <WorkspaceHeader eyebrow={board.locked ? 'Board locked' : 'Choose your squares'} title={`${game.away_team.abbrv} at ${game.home_team.abbrv}`} description={`${new Date(game.start_time).toLocaleString()} · ${board.claims.length}/${board.block_limit ?? 100} plan blocks reserved`} actions={<div className="squares-screen-actions"><button type="button" onClick={() => window.print()}>Print / Save PDF</button>{board.permissions.is_admin && !board.locked && <button type="button" onClick={lock} disabled={busy}>Lock & randomize digits</button>}</div>} />
    <header className="squares-print-header">
      <span>Run My Pool · Squares</span>
      <h1>{board.pool_name}</h1>
      <p>{game.away_team.abbrv} at {game.home_team.abbrv} · {new Date(game.start_time).toLocaleString()}</p>
    </header>
    {error && <div className="workspace-alert workspace-alert--error">{error}</div>}
    {board.permissions.is_admin && board.plan === 'free' && <aside className="squares-upgrade"><div><span>Free Squares board</span><strong>{board.claims.length} of {board.block_limit ?? 25} included blocks reserved</strong><p>Upgrade to Squares Plus for all 100 self-service blocks. Commish also adds member assignment and per-reservation pots.</p></div><Link href="/pricing?checkout=squares-plus">Unlock 100 blocks for $10</Link></aside>}
    {board.permissions.is_admin && board.plan === 'squares-plus' && <aside className="squares-upgrade"><div><span>Squares Plus</span><strong>All 100 self-service blocks are open</strong><p>Upgrade to Commish for admin member assignment and per-reservation pots.</p></div><Link href="/pricing?checkout=commissioner">Upgrade to Commish for $29</Link></aside>}
    {!board.permissions.is_admin && board.plan === 'free' && !board.permissions.can_claim && !board.locked && <aside className="squares-upgrade squares-upgrade--member"><div><span>Reservation limit reached</span><strong>All {board.block_limit ?? 25} included blocks are reserved</strong><p>Ask the pool commissioner to upgrade before more blocks can be reserved.</p></div></aside>}
    {board.permissions.is_admin && !board.locked && board.permissions.can_admin_assign && <form className="squares-manual-assignment" onSubmit={assignBlock}><div><strong>Assign a block</strong><span>Choose a member, then enter any available number from 1–100. Grid clicks also assign to this member.</span></div><label>Member<select value={claimFor} onChange={(event) => setClaimFor(event.target.value)}><option value="">Myself</option>{(board.members || []).filter((member) => member.id !== user?.id).map((member) => <option key={member.id} value={member.id}>{member.email}</option>)}</select></label><label>Block number<input type="number" min="1" max="100" step="1" inputMode="numeric" value={manualBlock} onChange={(event) => setManualBlock(event.target.value)} placeholder="1–100" /></label><button type="submit" disabled={busy || !manualBlock}>Assign block</button></form>}
    <section className="squares-summary" aria-label="Squares pool summary">
      <div><span>Total pot</span><strong>{board.total_pot_cents == null ? 'Not set' : `$${(board.total_pot_cents / 100).toFixed(2)}`}</strong>{board.pot_mode === 'per_square' && board.per_square_cents != null && <small>${(board.per_square_cents / 100).toFixed(2)} per reserved block</small>}</div>
      <div><span>Reserved</span><strong>{board.claims.length}/{board.block_limit ?? 100} included</strong><small>100 blocks on the board</small></div>
      <div><span>Score digits</span><strong>{board.locked ? 'Randomized' : 'Hidden until lock'}</strong></div>
    </section>
    <p className="squares-instructions">Home score runs down the left. Away score runs across the top. {!board.locked && 'Score digits are generated randomly by the server when the board locks.'}</p>
    <div className="squares-scroll"><div className="squares-grid" role="grid" aria-label="10 by 10 Squares board">
      <div className="squares-corner">HOME ↓<br />AWAY →</div>
      {Array.from({ length: 10 }, (_, col) => <div className="squares-axis" key={`a${col}`}>{board.away_digits?.[col] ?? '?'}</div>)}
      {Array.from({ length: 10 }, (_, row) => <div className="squares-row" key={row}>
        <div className="squares-axis">{board.home_digits?.[row] ?? '?'}</div>
        {Array.from({ length: 10 }, (_, col) => { const claim = claims[`${row}-${col}`]; const blockNumber = row * 10 + col + 1; const mayRelease = claim?.user_id === user?.id || board.permissions.is_admin; const owner = claim?.display_name || claim?.user_email; return <button key={col} role="gridcell" aria-label={claim ? `Block ${blockNumber}, reserved by ${owner}` : `Block ${blockNumber}, available`} disabled={busy || board.locked || (!board.permissions.can_claim && !claim) || (claim && !mayRelease)} className={`squares-cell ${claim ? 'is-claimed' : ''} ${claim?.user_id === user?.id ? 'is-mine' : ''}`} onClick={() => choose(row, col)} title={claim ? `Block ${blockNumber} · Reserved by ${owner}` : `Block ${blockNumber} · Available`}><span className="squares-block-number">{blockNumber}</span>{claim && <span className="squares-block-owner">{claim.display_name || claim.user_email.split('@')[0]}</span>}</button>; })}
      </div>)}
    </div></div>
    <section className="squares-reservations" aria-labelledby="squares-reservations-heading">
      <div><h2 id="squares-reservations-heading">Reservations</h2><p>Everyone in the pool can see who has reserved squares.</p></div>
      {reservations.length ? <ul>{reservations.map((reservation) => <li key={reservation.user_id}><strong>{reservation.user_email}</strong><span>{reservation.count} {reservation.count === 1 ? 'square' : 'squares'} · Blocks {reservation.blocks.join(', ')}</span></li>)}</ul> : <p>No squares have been reserved yet.</p>}
    </section>
    <section className="squares-results"><h2>Quarter winners</h2><div>{['q1', 'halftime', 'q3', 'final'].map((name) => { const result = board.payouts.find((item) => item.checkpoint === name); return <article key={name}><strong>{name === 'q1' ? '1st Quarter' : name === 'q3' ? '3rd Quarter' : name[0].toUpperCase() + name.slice(1)}</strong>{result ? <><span>{result.away_score}–{result.home_score}</span><b>{result.winner_email || 'Unclaimed square'}</b>{result.amount_cents != null && <small>${(result.amount_cents / 100).toFixed(2)} recorded</small>}</> : <span>Pending</span>}</article>; })}</div></section>
    {board.permissions.is_admin && !board.locked && <form className="squares-pot" onSubmit={savePot}><div><h2>Admin payout setup</h2><p>Choose one fixed pot or let the total grow with every reserved block. Quarter payouts remain 25% each. Run My Pool records winners and amounts but does not move money.</p><fieldset><legend>Pot calculation</legend><label className={potMode === 'fixed' ? 'is-selected' : ''}><input type="radio" name="pot-mode" value="fixed" checked={potMode === 'fixed'} onChange={() => { setPotMode('fixed'); setPot(dollarsFromCents(board.pot_mode === 'fixed' ? board.total_pot_cents : null)); }} /> Fixed total</label><label className={potMode === 'per_square' ? 'is-selected' : ''} aria-disabled={!board.permissions.can_use_variable_pot}><input type="radio" name="pot-mode" value="per_square" checked={potMode === 'per_square'} disabled={!board.permissions.can_use_variable_pot} onChange={() => { setPotMode('per_square'); setPot(dollarsFromCents(board.per_square_cents)); }} /> Per reserved block {!board.permissions.can_use_variable_pot && <small>Commish</small>}</label></fieldset></div><label>{potMode === 'fixed' ? 'Total pot ($)' : 'Amount per reserved block ($)'}<input type="number" min="0" step="0.01" inputMode="decimal" value={pot} onChange={(event) => setPot(event.target.value)} placeholder={potMode === 'fixed' ? 'Optional' : 'Required'} required={potMode === 'per_square'} /></label><button disabled={busy}>Save payouts</button></form>}
  </main></ProtectedRoute>;
}
