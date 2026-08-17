import { useEffect, useState } from 'react';

async function ownerReportRequest(poolId, path, options = {}) {
  const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/pools/${poolId}/${path}`, {
    ...options,
    headers: {
      ...(options.body ? { 'Content-Type': 'application/json' } : {}),
      Authorization: `Bearer ${localStorage.getItem('access_token')}`,
      ...options.headers,
    },
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.detail || 'Unable to load owner reports');
  return data;
}

export default function OwnerPoolReports({ poolId }) {
  const [preference, setPreference] = useState(null);
  const [preview, setPreview] = useState(null);
  const [busy, setBusy] = useState(true);
  const [message, setMessage] = useState('');

  useEffect(() => {
    if (!poolId) return;
    let active = true;
    Promise.all([
      ownerReportRequest(poolId, 'owner-report-preference'),
      ownerReportRequest(poolId, 'owner-report-preview'),
    ])
      .then(([nextPreference, nextPreview]) => {
        if (active) { setPreference(nextPreference); setPreview(nextPreview); }
      })
      .catch((error) => { if (active) setMessage(error.message); })
      .finally(() => { if (active) setBusy(false); });
    return () => { active = false; };
  }, [poolId]);

  const toggle = async () => {
    setBusy(true);
    setMessage('');
    try {
      const next = await ownerReportRequest(poolId, 'owner-report-preference', {
        method: 'PUT',
        body: JSON.stringify({ enabled: !preference.enabled, frequency: 'weekly' }),
      });
      setPreference(next);
      setMessage(next.enabled ? 'Weekly owner reports are on.' : 'Weekly owner reports are off.');
    } catch (error) {
      setMessage(error.message);
    } finally {
      setBusy(false);
    }
  };

  return <section className="owner-pool-reports" aria-labelledby="owner-report-title">
    <div className="owner-pool-reports__heading">
      <span>Owner insights</span>
      <h4 id="owner-report-title">Weekly Pool Report</h4>
      <p>See participation, usage, picks, eliminations, remaining entries, and other signals that show how your pool is performing.</p>
    </div>
    {preview && <div className="owner-pool-reports__metrics" aria-label="Current pool report preview">
      <div><strong>{preview.engaged_members}/{preview.members}</strong><span>Members engaged</span></div>
      <div><strong>{preview.remaining_entries}/{preview.total_entries}</strong><span>Entries remaining</span></div>
      <div><strong>{preview.weekly_entries_with_picks}/{preview.weekly_eligible_entries}</strong><span>Week {preview.week} completion</span></div>
      <div><strong>{preview.season_picks}</strong><span>Season picks</span></div>
    </div>}
    <div className="owner-pool-reports__action">
      <label>
        <input type="checkbox" checked={Boolean(preference?.enabled)} disabled={busy || !preference} onChange={toggle} />
        <span><strong>Email me weekly</strong><small>Delivered to the pool owner. Opt out any time.</small></span>
      </label>
      {preference?.last_sent_at && <small>Last sent {new Date(preference.last_sent_at).toLocaleString()}</small>}
      {message && <p role="status">{message}</p>}
    </div>
  </section>;
}
