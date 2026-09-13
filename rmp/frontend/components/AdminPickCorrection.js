import { useEffect, useState } from 'react';

async function request(path, options = {}) {
  const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}${path}`, {
    ...options,
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${localStorage.getItem('access_token')}` },
  });
  const data = await response.json();
  if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'Unable to load or correct picks. Please try again.');
  return data;
}

const fieldStyle = { display: 'block', width: '100%', minWidth: 0, padding: '0.75rem', marginTop: '0.5rem' };

export default function AdminPickCorrection({ poolId }) {
  const [users, setUsers] = useState([]);
  const [teams, setTeams] = useState([]);
  const [userId, setUserId] = useState('');
  const [picks, setPicks] = useState([]);
  const [pickId, setPickId] = useState('');
  const [team, setTeam] = useState('');
  const [reason, setReason] = useState('');
  const [loading, setLoading] = useState(true);
  const [loadingPicks, setLoadingPicks] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [retry, setRetry] = useState(0);
  const selectedPick = picks.find((pick) => pick.id === pickId);

  useEffect(() => {
    let cancelled = false;
    Promise.all([request(`/admin/pools/${poolId}/users-overview`), request('/teams/')])
      .then(([overview, allTeams]) => {
        if (cancelled) return;
        setUsers([...overview.users].sort((a, b) => a.email.localeCompare(b.email)));
        setTeams([...allTeams].sort((a, b) => a.abbrv.localeCompare(b.abbrv)));
      })
      .catch((err) => { if (!cancelled) setError(err.message); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [poolId, retry]);

  useEffect(() => {
    if (!userId) return;
    let cancelled = false;
    request(`/admin/pools/${poolId}/users/${userId}/correction-picks`)
      .then((data) => { if (!cancelled) setPicks(data); })
      .catch((err) => { if (!cancelled) setError(err.message); })
      .finally(() => { if (!cancelled) setLoadingPicks(false); });
    return () => { cancelled = true; };
  }, [poolId, userId, retry]);

  async function save(event) {
    event.preventDefault();
    if (!selectedPick || !team || team === selectedPick.team || saving) return;
    setSaving(true); setError(''); setMessage('');
    try {
      const updated = await request(`/admin/pools/${poolId}/picks/${selectedPick.id}`, {
        method: 'PATCH', body: JSON.stringify({ team, reason: reason.trim() || null }),
      });
      setPicks((current) => current.map((pick) => pick.id === selectedPick.id ? { ...pick, ...updated } : pick));
      setMessage(`${selectedPick.entry_name} · Week ${selectedPick.week}: ${selectedPick.team} corrected to ${updated.team}.`);
      setTeam(''); setReason('');
    } catch (err) { setError(err.message); }
    finally { setSaving(false); }
  }

  return <section className="admin-user-overview" aria-labelledby="correct-pick-title">
    <h4 id="correct-pick-title">Correct Pick</h4>
    <p>Select a user and their saved pick, then choose the replacement team. Corrections are recorded in the audit log.</p>
    <form onSubmit={save}>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 240px), 1fr))', gap: '1rem' }}>
        <label>Username<select style={fieldStyle} value={userId} disabled={loading || saving} onChange={(event) => {
          setUserId(event.target.value); setPicks([]); setPickId(''); setTeam(''); setReason(''); setError(''); setMessage(''); setLoadingPicks(Boolean(event.target.value));
        }}><option value="">{loading ? 'Loading users…' : 'Select a user'}</option>
          {users.map((account) => <option key={account.id} value={account.id}>{account.email}</option>)}
        </select></label>
        <label>User’s pick<select style={fieldStyle} value={pickId} disabled={!userId || loadingPicks || saving} onChange={(event) => { setPickId(event.target.value); setTeam(''); setReason(''); setError(''); setMessage(''); }}>
          <option value="">{loadingPicks ? 'Loading picks…' : 'Select a pick'}</option>
          {picks.map((pick) => <option key={pick.id} value={pick.id}>{pick.entry_name} · Week {pick.week} · {pick.team}</option>)}
        </select></label>
        <label>Modified pick<select style={fieldStyle} value={team} disabled={!selectedPick || saving} onChange={(event) => setTeam(event.target.value)}>
          <option value="">Select a team</option>{teams.map((item) => <option key={item.id} value={item.abbrv} disabled={item.abbrv === selectedPick?.team}>{item.abbrv}</option>)}
        </select></label>
      </div>
      <p><strong>Current pick: {selectedPick ? selectedPick.team : 'Select a pick above'}</strong></p>
      {userId && !loadingPicks && !error && picks.length === 0 && <p>No saved picks for this user in this pool.</p>}
      <label>Reason for correction<textarea style={fieldStyle} rows={3} value={reason} disabled={saving} onChange={(event) => setReason(event.target.value)} placeholder="Enter reason for this pick correction..." /></label>
      <button type="submit" disabled={!selectedPick || !team || team === selectedPick.team || saving || loadingPicks} style={{ marginTop: '1rem' }}>{saving ? 'Saving…' : 'Correct Pick'}</button>
    </form>
    {message && <p role="status">{message}</p>}
    {error && <div role="alert">{error} <button type="button" disabled={saving} onClick={() => { setError(''); setLoading(true); setLoadingPicks(Boolean(userId)); setPicks([]); setPickId(''); setTeam(''); setRetry((value) => value + 1); }}>Retry</button></div>}
  </section>;
}
