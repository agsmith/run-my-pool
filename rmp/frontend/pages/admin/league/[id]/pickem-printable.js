import { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import ProtectedRoute from '../../../../components/ProtectedRoute';
import { buildPoolJoinUrl } from '../../../../utils/poolJoinUrl';

const authHeaders = () => ({ Authorization: `Bearer ${localStorage.getItem('access_token')}` });

export default function PickEmPrintablePage() {
  const router = useRouter();
  const { id } = router.query;
  const week = Math.min(18, Math.max(1, Number(router.query.week) || 1));
  const [sheet, setSheet] = useState(null);
  const [qrDataUrl, setQrDataUrl] = useState('');
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

  useEffect(() => {
    if (!id) return;
    let cancelled = false;
    const origin = typeof window !== 'undefined'
      ? window.location.origin
      : (process.env.NEXT_PUBLIC_SITE_URL || 'https://runmypool.net');
    import('qrcode')
      .then((qrModule) => (qrModule.default || qrModule).toDataURL(buildPoolJoinUrl(id, origin), {
        errorCorrectionLevel: 'M', margin: 1, width: 256,
        color: { dark: '#000000', light: '#ffffff' },
      }))
      .then((dataUrl) => { if (!cancelled) setQrDataUrl(dataUrl); })
      .catch(() => { if (!cancelled) setError('Unable to create the pool join QR code.'); });
    return () => { cancelled = true; };
  }, [id]);

  return <ProtectedRoute>
    <main className="pickem-print-page">
      <div className="pickem-print-controls">
        <button type="button" onClick={() => router.push(`/admin/league/${id}`)}>← Commissioner</button>
        <label>Week <select aria-label="Printable week" value={week} onChange={(event) => router.push(`/admin/league/${id}/pickem-printable?week=${event.target.value}`)}>{Array.from({ length: 18 }, (_, index) => <option key={index + 1}>{index + 1}</option>)}</select></label>
        <button type="button" onClick={() => window.print()} disabled={!sheet || !qrDataUrl}>Print / Save PDF</button>
      </div>
      {error && <div className="pickem-print-error" role="alert">{error}</div>}
      {sheet && <article className="pickem-paper-sheet">
        <header>
          <div><span>RUN MY POOL</span><h1>{sheet.pool_name}</h1></div>
          <div className="pickem-paper-heading">
            <strong>WEEK {sheet.week} PICK &apos;EM</strong>
            {qrDataUrl && <div className="pickem-paper-qr"><img src={qrDataUrl} alt="Scan to join this pool" /><small>SCAN TO JOIN</small></div>}
          </div>
        </header>
        <section className="pickem-paper-fields">
          <label>NAME <span /></label>
        </section>
        <p className="pickem-paper-directions">
          Select {sheet.required_picks === sheet.games.length ? 'one winner for every matchup' : `${sheet.required_picks} matchup${sheet.required_picks === 1 ? '' : 's'}`} below.
        </p>
        {sheet.games.length ? <section className="pickem-paper-games">
          {sheet.games.map((game) => <div className="pickem-paper-game" key={game.game_id}>
            <time>{new Date(game.start_time).toLocaleString('en-US', { timeZone: 'America/New_York', weekday: 'short', month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit', timeZoneName: 'short' })}</time>
            <label><i /> <b>{game.away_team.abbrv}</b></label>
            <span>VS</span>
            <label><b>{game.home_team.abbrv}</b> <i /></label>
            <small>{game.away_team.name} vs {game.home_team.name}</small>
          </div>)}
        </section> : <p className="pickem-paper-empty">No games are currently scheduled in this pool&apos;s Week {sheet.week} slate.</p>}
        {sheet.requires_tiebreaker && <section className="pickem-paper-tiebreaker"><b>LATE MONDAY NIGHT GAME — TOTAL SCORE</b><span /></section>}
        <footer>
          <span>Return this completed sheet to your pool commissioner before the pool&apos;s weekly deadline.</span>
          <strong>RunMyPool.net</strong>
        </footer>
      </article>}
    </main>
    <style jsx global>{`
      .pickem-print-page { min-height: 100vh; background: #17223a; padding: 24px; color: #111827; }
      .pickem-print-controls { max-width: 850px; margin: 0 auto 18px; display: flex; gap: 12px; align-items: center; justify-content: flex-end; color: white; }
      .pickem-print-controls button, .pickem-print-controls select { padding: 9px 12px; border-radius: 6px; border: 1px solid #94a3b8; }
      .pickem-print-controls button { background: #26d07c; color: #082116; border: 0; font-weight: 700; cursor: pointer; }
      .pickem-print-controls button:first-child { margin-right: auto; background: #e2e8f0; color: #17223a; }
      .pickem-print-error { max-width: 850px; margin: auto; background: #fee2e2; color: #991b1b; padding: 16px; border-radius: 8px; }
      .pickem-paper-sheet { box-sizing: border-box; width: 8.5in; min-height: 11in; margin: auto; padding: .24in .35in .2in; background: white; border-top: 7px solid #000; color: #000; font-family: Arial, sans-serif; }
      .pickem-paper-sheet, .pickem-paper-sheet * { color: #000 !important; }
      .pickem-paper-sheet header { display: flex; justify-content: space-between; align-items: center; border-bottom: 3px solid #111827; padding-bottom: 6px; }
      .pickem-paper-sheet header > div:first-child > span { font-weight: 900; letter-spacing: .16em; font-size: 11px; }
      .pickem-paper-sheet h1 { margin: 2px 0 0; font-size: 25px; }
      .pickem-paper-heading { display: flex; align-items: center; gap: 12px; }
      .pickem-paper-heading > strong { font-size: 20px; white-space: nowrap; }
      .pickem-paper-qr { display: flex; flex-direction: column; align-items: center; font-weight: 800; }
      .pickem-paper-qr img { display: block; width: .68in; height: .68in; image-rendering: crisp-edges; }
      .pickem-paper-qr small { margin-top: 1px; font-size: 7px; letter-spacing: .08em; }
      .pickem-paper-fields { margin: 8px 0 7px; }
      .pickem-paper-fields label { display: flex; align-items: end; gap: 8px; font-size: 12px; font-weight: 700; }
      .pickem-paper-fields span { flex: 1; height: 18px; border-bottom: 1px solid #111827; }
      .pickem-paper-directions { font-size: 11px; margin: 0 0 7px; }
      .pickem-paper-games { display: grid; grid-template-columns: 1fr 1fr; gap: 4px 9px; }
      .pickem-paper-game { display: grid; grid-template-columns: 1fr auto 1fr; align-items: center; gap: 5px; border: 1.5px solid #334155; border-radius: 4px; padding: 3px 6px; break-inside: avoid; }
      .pickem-paper-game time { grid-column: 1 / -1; font-size: 8px; font-weight: 600; }
      .pickem-paper-game label { display: flex; align-items: center; gap: 7px; font-size: 16px; min-width: 0; }
      .pickem-paper-game label:last-child { justify-content: flex-end; text-align: right; }
      .pickem-paper-game i { width: 17px; height: 17px; border: 2px solid #111827; border-radius: 2px; flex: 0 0 auto; }
      .pickem-paper-game > span { font-size: 10px; font-weight: 800; }
      .pickem-paper-game small { grid-column: 1 / -1; font-size: 8px; text-align: center; }
      .pickem-paper-tiebreaker { display: flex; gap: 12px; align-items: end; margin-top: 7px; padding: 6px 9px; border: 2px solid #111827; font-size: 11px; break-inside: avoid; }
      .pickem-paper-tiebreaker span { flex: 1; min-width: 100px; height: 22px; border-bottom: 2px solid #111827; }
      .pickem-paper-empty { border: 1px dashed #94a3b8; padding: 24px; text-align: center; }
      .pickem-paper-sheet footer { display: flex; justify-content: space-between; gap: 12px; margin-top: 6px; border-top: 1px solid #000; padding-top: 5px; font-size: 8px; }
      .pickem-paper-sheet footer strong { letter-spacing: .05em; white-space: nowrap; }
      @media (max-width: 900px) { .pickem-paper-sheet { width: 100%; min-height: auto; } .pickem-paper-games { grid-template-columns: 1fr; } }
      @media print {
        @page { size: letter portrait; margin: 0; }
        html, body, #__next { width: 8.5in !important; height: 10.95in !important; min-height: 0 !important; margin: 0 !important; padding: 0 !important; background: white !important; overflow: hidden !important; }
        .pickem-print-page { position: fixed; inset: 0; width: 8.5in; height: 10.95in; min-height: 0; margin: 0; padding: 0; overflow: hidden; background: white; }
        .pickem-print-controls, .pickem-print-error { display: none !important; }
        .pickem-paper-sheet { position: absolute; inset: 0; width: 8.5in; height: 10.95in; min-height: 0; max-height: 10.95in; margin: 0; box-shadow: none; overflow: hidden; page-break-before: avoid; page-break-after: avoid; break-before: avoid-page; break-after: avoid-page; print-color-adjust: exact; }
        .pickem-paper-games { grid-template-columns: 1fr 1fr; }
        .pickem-paper-game { break-inside: avoid; page-break-inside: avoid; }
      }
    `}</style>
  </ProtectedRoute>;
}
