import { useState } from 'react';

export default function MemberWeeklyRecap({ poolId, enabled, onChange }) {
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const updatePreference = async (nextEnabled) => {
    setSaving(true);
    setError('');
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/pools/${poolId}/member-recap-preference`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ enabled: nextEnabled }),
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.detail || 'Unable to update weekly recaps.');
      onChange(data.enabled);
    } catch (err) {
      setError(err.message || 'Unable to update weekly recaps.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <section id="weekly-recap" className="member-weekly-recap" aria-labelledby="weekly-recap-title">
      <div>
        <span>Stay in the loop</span>
        <h2 id="weekly-recap-title">Your Weekly Recap</h2>
        <p>Get your entry results, remaining-entry count, and pool progress by email after each completed week.</p>
        <small>Only your own entry details are included. You can turn this off at any time.</small>
      </div>
      <label>
        <input
          type="checkbox"
          checked={enabled}
          disabled={saving}
          onChange={(event) => updatePreference(event.target.checked)}
        />
        <span>{saving ? 'Saving…' : enabled ? 'Weekly recaps on' : 'Email me weekly recaps'}</span>
      </label>
      {error && <p role="alert" className="member-weekly-recap__error">{error}</p>}
    </section>
  );
}
