import { useEffect, useState } from 'react';

export default function PoolPickBreakdown({ poolId, currentWeek }) {
  const [selectedWeek, setSelectedWeek] = useState(null);
  const week = selectedWeek || currentWeek;
  const [state, setState] = useState({ rows: [], loading: true, error: false });
  const [refresh, setRefresh] = useState(0);
  useEffect(() => {
    if (!poolId || !week) return undefined;
    let active = true;
    let sequence = 0;
    const controller = new AbortController();
    setState({ rows: [], loading: true, error: false });
    async function load() {
      const request = ++sequence;
      try {
        const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/picks/pool/${poolId}/week/${week}/breakdown`, {
          headers: { Authorization: `Bearer ${localStorage.getItem('access_token')}` },
          signal: controller.signal,
        });
        if (!response.ok) throw new Error('Unable to load picks');
        const rows = await response.json();
        if (!Array.isArray(rows)) throw new Error('Invalid breakdown');
        if (active && request === sequence) setState({ rows, loading: false, error: false });
      } catch {
        if (active && request === sequence) setState({ rows: [], loading: false, error: true });
      }
    }
    load();
    const timer = setInterval(load, 30000);
    window.addEventListener('focus', load);
    return () => { active = false; controller.abort(); clearInterval(timer); window.removeEventListener('focus', load); };
  }, [poolId, week, refresh]);
  const total = state.rows.reduce((sum, row) => sum + row.count, 0);
  return (
    <section className="pick-breakdown" aria-labelledby="pool-picks-title">
      <div className="heading">
        <h2 id="pool-picks-title">Who picked whom</h2>
        <label>Week <select aria-label="Pick breakdown week" value={week || ''} onChange={(event) => setSelectedWeek(Number(event.target.value))}>
          {!week && <option value="">Choose week</option>}
          {Array.from({ length: 18 }, (_, index) => <option key={index + 1} value={index + 1}>{index + 1}</option>)}
        </select></label>
        <button type="button" onClick={() => setRefresh((value) => value + 1)}>Refresh</button>
      </div>
      <p>Picks on either team lock and appear here when their game starts, even before the pool’s weekly deadline. All remaining picks are revealed at that deadline.</p>
      {!week ? <p>Choose a week to see its picks.</p> : state.loading ? <p role="status">Loading picks…</p> : state.error ? <p role="alert">Couldn’t load picks. Tap Refresh to try again.</p> : !total ? <p>No active entries have revealed picks yet.</p> : <>
        <p><strong>{total}</strong> active {total === 1 ? 'entry with a revealed pick' : 'entries with revealed picks'}. Tap a team to see entry names.</p>
        <div className="teams">{state.rows.map((row) => <details key={row.team}>
          <summary><span>{row.team_name || row.team}</span><strong>{row.count} {row.count === 1 ? 'entry' : 'entries'}</strong></summary>
          <ul>{(row.entries || []).map((entry) => <li key={entry.entry_id}>{entry.entry_name}</li>)}</ul>
        </details>)}</div>
      </>}
      <style jsx>{`
        .pick-breakdown { margin: 20px 0; padding: clamp(16px, 3vw, 28px); border: 1px solid #34464b; background: #101c20; color: #e9eeee; min-width: 0; }
        .heading { display: flex; align-items: center; flex-wrap: wrap; gap: 12px; }
        h2 { flex: 1 1 180px; margin: 0; font-size: 1.5rem; }
        p { line-height: 1.6; color: #c1ced1; overflow-wrap: anywhere; }
        button, select { min-height: 44px; padding: 8px 12px; background: #192b31; border: 1px solid #61757b; color: white; border-radius: 6px; font: inherit; }
        .teams { display: grid; gap: 10px; }
        details { border: 1px solid #34464b; min-width: 0; }
        summary { display: flex; justify-content: space-between; align-items: center; gap: 12px; min-height: 48px; padding: 12px; cursor: pointer; }
        summary span { overflow-wrap: anywhere; min-width: 0; }
        summary strong { color: #d9ff3f; white-space: nowrap; }
        summary::before { content: '+'; }
        details[open] summary::before { content: '−'; }
        li { padding: 6px 12px 6px 0; overflow-wrap: anywhere; }
      `}</style>
    </section>
  );
}
