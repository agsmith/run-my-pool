import { useState } from 'react';

export default function AdminWeeklyEmailGenerator({ poolId, poolType = 'pickem' }) {
  const isSurvivor = poolType === 'survivor';
  const [week, setWeek] = useState(1);
  const [notes, setNotes] = useState(isSurvivor
    ? 'Survivor rules: one team per entry each week; a loss eliminates the entry; teams cannot be reused.'
    : 'Weekly winner: $60. Season: $300 first, $100 second, $50 third. Monday tiebreaker: closest to the combined total; if equally close, the lower prediction wins; remaining ties split the pot.');
  const [text, setText] = useState('');
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  const generate = async () => {
    setBusy(true); setMessage('');
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/admin/pools/${poolId}/weekly-email`, {
        method: 'POST', headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${localStorage.getItem('access_token')}` },
        body: JSON.stringify({ week, payout_notes: notes.trim() || null }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || 'Unable to generate email.');
      setText(data.text || ''); setMessage('Email draft generated. Review it before sending.');
    } catch (error) { setMessage(error.message); }
    finally { setBusy(false); }
  };
  const copy = async () => { await navigator.clipboard.writeText(text); setMessage('Email copied to your clipboard.'); };
  return <section aria-labelledby="weekly-email-title" style={{ marginBottom: '3rem' }}>
    <h4 id="weekly-email-title" style={{ color: '#2d3748', marginBottom: '1rem' }}>{isSurvivor ? 'Generate Survivor Email' : 'Generate Weekly Email'}</h4>
    <div style={{ backgroundColor: 'white', padding: '1.5rem', borderRadius: '8px', border: '1px solid #e2e8f0' }}>
      <p style={{ color: '#4a5568', marginTop: 0 }}>{isSurvivor ? 'Create a tailored Survivor update with surviving entries, eliminated entries, team usage, game results, and advancement scenarios.' : 'Create a tailored Pick ’Em update with weekly picks, standings, game results, and remaining-game scenarios.'}</p>
      <label>Email week<select aria-label="Weekly email week" value={week} onChange={(event) => setWeek(Number(event.target.value))} style={{ display: 'block', padding: '0.65rem', marginTop: '0.4rem' }}>{Array.from({ length: 18 }, (_, index) => <option key={index + 1} value={index + 1}>Week {index + 1}</option>)}</select></label>
      <label style={{ display: 'block', marginTop: '1rem' }}>{isSurvivor ? 'Survivor rules and payout notes' : 'Payout and tiebreaker notes'}<textarea rows={3} value={notes} onChange={(event) => setNotes(event.target.value)} style={{ display: 'block', width: '100%', padding: '0.65rem', marginTop: '0.4rem' }} /></label>
      <button type="button" onClick={generate} disabled={busy} style={{ marginTop: '1rem' }}>{busy ? 'Generating…' : 'Generate email draft'}</button>
      {text && <><textarea aria-label="Generated weekly email" value={text} onChange={(event) => setText(event.target.value)} rows={16} style={{ display: 'block', width: '100%', marginTop: '1rem', padding: '0.75rem', fontFamily: 'inherit' }} /><button type="button" onClick={copy} style={{ marginTop: '0.75rem' }}>Copy email</button></>}
      {message && <p role="status">{message}</p>}
    </div>
  </section>;
}
