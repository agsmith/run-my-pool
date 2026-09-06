import { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import ProtectedRoute from '../../../../components/ProtectedRoute';

const authHeaders = () => ({ Authorization: `Bearer ${localStorage.getItem('access_token')}` });

export default function PickEmPrintablePage() {
  const router = useRouter();
  const { id } = router.query;
  const week = Math.min(18, Math.max(1, Number(router.query.week) || 1));
  const [sheet, setSheet] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!id) return;
    setError('');
    fetch(`${process.env.NEXT_PUBLIC_API_URL}/admin/pools/${id}/pickem-printable/${week}`, { headers: authHeaders() })
      .then(async (response) => {
        const data = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(data.detail || 'Unable to load weekly printable');
        return data;
      })
      .then(setSheet)
      .catch((err) => setError(err.message || 'Unable to load weekly printable'));
  }, [id, week]);

  return <ProtectedRoute>
    <main className="pickem-print-page">
      <div className="pickem-print-controls">
        <button type="button" onClick={() => router.push(`/admin/league/${id}`)}>← Commissioner</button>
        <label>Week <select aria-label="Printable week" value={week} onChange={(event) => router.push(`/admin/league/${id}/pickem-printable?week=${event.target.value}`)}>{Array.from({ length: 18 }, (_, index) => <option key={index + 1}>{index + 1}</option>)}</select></label>
        <button type="button" onClick={() => window.print()} disabled={!sheet}>Print / Save PDF</button>
      </div>
      {error && <div className="pickem-print-error" role="alert">{error}</div>}
      {sheet && <article className="pickem-paper-sheet">
        <header>
          <div><span>RUN MY POOL</span><h1>{sheet.pool_name}</h1></div>
          <strong>WEEK {sheet.week} PICK &apos;EM</strong>
        </header>
        <section className="pickem-paper-fields">
          <label>Participant <span /></label>
          <label>Entry name <span /></label>
        </section>
        <p className="pickem-paper-directions">
          Select {sheet.required_picks === sheet.games.length ? 'one winner for every matchup' : `${sheet.required_picks} matchup${sheet.required_picks === 1 ? '' : 's'}`} below.
        </p>
        {sheet.games.length ? <section className="pickem-paper-games">
          {sheet.games.map((game) => <div className="pickem-paper-game" key={game.game_id}>
            <time>{new Date(game.start_time).toLocaleString('en-US', { timeZone: 'America/New_York', weekday: 'short', month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit', timeZoneName: 'short' })}</time>
            <label><i /> <b>{game.away_team.abbrv}</b> {game.away_team.name}</label>
            <span>at</span>
            <label><i /> <b>{game.home_team.abbrv}</b> {game.home_team.name}</label>
          </div>)}
        </section> : <p className="pickem-paper-empty">No games are currently scheduled in this pool&apos;s Week {sheet.week} slate.</p>}
        {sheet.requires_tiebreaker && <section className="pickem-paper-tiebreaker"><b>Monday Night combined-score tiebreaker</b><span /></section>}
        <footer>Return this completed sheet to your pool commissioner before the pool&apos;s weekly deadline.</footer>
      </article>}
    </main>
    <style jsx global>{`
      .pickem-print-page { min-height: 100vh; background: #17223a; padding: 24px; color: #111827; }
      .pickem-print-controls { max-width: 850px; margin: 0 auto 18px; display: flex; gap: 12px; align-items: center; justify-content: flex-end; color: white; }
      .pickem-print-controls button, .pickem-print-controls select { padding: 9px 12px; border-radius: 6px; border: 1px solid #94a3b8; }
      .pickem-print-controls button { background: #26d07c; color: #082116; border: 0; font-weight: 700; cursor: pointer; }
      .pickem-print-controls button:first-child { margin-right: auto; background: #e2e8f0; color: #17223a; }
      .pickem-print-error { max-width: 850px; margin: auto; background: #fee2e2; color: #991b1b; padding: 16px; border-radius: 8px; }
      .pickem-paper-sheet { box-sizing: border-box; width: 8.5in; min-height: 11in; margin: auto; padding: .38in .45in; background: white; border-top: 10px solid #26d07c; font-family: Arial, sans-serif; }
      .pickem-paper-sheet header { display: flex; justify-content: space-between; align-items: end; border-bottom: 3px solid #17223a; padding-bottom: 10px; }
      .pickem-paper-sheet header span { color: #0f766e; font-weight: 900; letter-spacing: .16em; font-size: 11px; }
      .pickem-paper-sheet h1 { margin: 2px 0 0; font-size: 25px; }
      .pickem-paper-sheet header > strong { font-size: 20px; color: #17223a; }
      .pickem-paper-fields { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; margin: 14px 0; }
      .pickem-paper-fields label { display: flex; align-items: end; gap: 8px; font-size: 12px; font-weight: 700; }
      .pickem-paper-fields span { flex: 1; height: 18px; border-bottom: 1px solid #111827; }
      .pickem-paper-directions { font-size: 12px; margin: 0 0 10px; }
      .pickem-paper-games { display: grid; grid-template-columns: 1fr 1fr; gap: 7px 12px; }
      .pickem-paper-game { display: grid; grid-template-columns: 1fr auto 1fr; align-items: center; gap: 6px; border: 1px solid #cbd5e1; border-radius: 5px; padding: 6px 8px; break-inside: avoid; }
      .pickem-paper-game time { grid-column: 1 / -1; color: #475569; font-size: 9px; }
      .pickem-paper-game label { display: flex; align-items: center; gap: 4px; font-size: 10px; min-width: 0; }
      .pickem-paper-game label:last-child { justify-content: flex-end; text-align: right; }
      .pickem-paper-game i { width: 12px; height: 12px; border: 1.5px solid #111827; border-radius: 2px; flex: 0 0 auto; }
      .pickem-paper-game > span { font-size: 9px; color: #64748b; text-transform: uppercase; }
      .pickem-paper-tiebreaker { display: flex; gap: 10px; align-items: end; margin-top: 14px; font-size: 12px; }
      .pickem-paper-tiebreaker span { width: 100px; height: 20px; border-bottom: 1px solid #111827; }
      .pickem-paper-empty { border: 1px dashed #94a3b8; padding: 24px; text-align: center; }
      .pickem-paper-sheet footer { margin-top: 14px; border-top: 1px solid #cbd5e1; padding-top: 8px; color: #475569; font-size: 9px; text-align: center; }
      @media (max-width: 900px) { .pickem-paper-sheet { width: 100%; min-height: auto; } .pickem-paper-games { grid-template-columns: 1fr; } }
      @media print {
        @page { size: letter portrait; margin: 0; }
        body { background: white !important; }
        .pickem-print-page { padding: 0; background: white; }
        .pickem-print-controls, .pickem-print-error { display: none !important; }
        .pickem-paper-sheet { width: 8.5in; height: 11in; min-height: 11in; margin: 0; box-shadow: none; overflow: hidden; }
        .pickem-paper-games { grid-template-columns: 1fr 1fr; }
      }
    `}</style>
  </ProtectedRoute>;
}
